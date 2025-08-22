from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware  # Add CORS support
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from loguru import logger
import uvicorn

from .config import settings
from .api_tests import VoiceUploadTest, STTTest, ChecklistTest, LoadTest
from .monitoring import SystemMonitor, PerformanceTracker
from .database import init_db, get_db_session
from .models import TestRun, VoiceTestResult, PerformanceMetric, Alert

app = FastAPI(title="Soapify API Monitor", version="1.0.0")

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
system_monitor = SystemMonitor()
performance_tracker = PerformanceTracker()

# Setup templates
templates = Jinja2Templates(directory="templates")

# Background task for continuous monitoring
monitoring_task = None

# Store test results for frontend access
test_results_cache = {
    "latest_results": None,
    "in_progress": False,
    "progress": {}
}

@app.on_event("startup")
async def startup_event():
    """Initialize database and start monitoring"""
    logger.info("Starting Soapify API Monitor...")
    await init_db()
    
    # Start background monitoring
    global monitoring_task
    monitoring_task = asyncio.create_task(continuous_monitoring())

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources"""
    logger.info("Shutting down Soapify API Monitor...")
    if monitoring_task:
        monitoring_task.cancel()

async def continuous_monitoring():
    """Run continuous monitoring tasks"""
    while True:
        try:
            # Run system monitoring
            metrics = await system_monitor.collect_metrics()
            
            # Store metrics in database
            async with get_db_session() as session:
                metric = PerformanceMetric(**metrics)
                session.add(metric)
                await session.commit()
            
            # Check for alerts
            await check_alerts(metrics)
            
            # Wait for next interval
            await asyncio.sleep(settings.TEST_INTERVAL_MINUTES * 60)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in continuous monitoring: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying

async def check_alerts(metrics: Dict[str, Any]):
    """Check metrics and create alerts if needed"""
    alerts = []
    
    # Check response time
    if metrics.get('avg_response_time_ms', 0) > settings.ALERT_RESPONSE_TIME_MS:
        alerts.append({
            'alert_type': 'high_response_time',
            'severity': 'warning',
            'message': f"Average response time ({metrics['avg_response_time_ms']:.2f}ms) exceeds threshold ({settings.ALERT_RESPONSE_TIME_MS}ms)",
            'details': metrics
        })
    
    # Check error rate
    total_requests = metrics.get('total_requests', 0)
    failed_requests = metrics.get('failed_requests', 0)
    if total_requests > 0:
        error_rate = (failed_requests / total_requests) * 100
        if error_rate > settings.ALERT_ERROR_RATE_PERCENT:
            alerts.append({
                'alert_type': 'high_error_rate',
                'severity': 'error',
                'message': f"Error rate ({error_rate:.2f}%) exceeds threshold ({settings.ALERT_ERROR_RATE_PERCENT}%)",
                'details': metrics
            })
    
    # Store alerts in database
    if alerts:
        async with get_db_session() as session:
            for alert_data in alerts:
                alert = Alert(**alert_data)
                session.add(alert)
            await session.commit()

# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main monitoring dashboard"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "api_base_url": settings.API_BASE_URL
    })

# NEW: Webhook endpoint for frontend to trigger tests
@app.post("/api/webhook/trigger-test")
async def trigger_test_webhook(
    test_type: str,
    background_tasks: BackgroundTasks,
    params: Dict[str, Any] = {}
):
    """Webhook endpoint for frontend to trigger server-side tests"""
    
    if test_results_cache["in_progress"]:
        raise HTTPException(status_code=409, detail="Tests already in progress")
    
    test_results_cache["in_progress"] = True
    test_results_cache["progress"] = {"status": "starting", "test_type": test_type}
    
    # Run test in background
    background_tasks.add_task(run_triggered_test, test_type, params)
    
    return JSONResponse(content={
        "status": "accepted",
        "message": f"Test {test_type} triggered successfully",
        "test_id": datetime.utcnow().isoformat()
    })

async def run_triggered_test(test_type: str, params: Dict[str, Any]):
    """Run test triggered by frontend webhook"""
    try:
        test_results_cache["progress"] = {"status": "running", "test_type": test_type}
        
        if test_type == "all":
            results = await run_all_tests()
        elif test_type == "voice":
            test = VoiceUploadTest()
            results = await test.test_upload(params.get("file_path", "./test_audio/sample.wav"))
        elif test_type == "stt":
            test = STTTest()
            results = await test.test_transcription(
                params.get("audio_url", ""),
                params.get("expected_text")
            )
        elif test_type == "checklist":
            test = ChecklistTest()
            results = await test.test_create_checklist()
        elif test_type == "load":
            load_test = LoadTest()
            concurrent = params.get("concurrent_requests", 10)
            service = params.get("service", "checklist")
            
            if service == "checklist":
                stats = await load_test.run_concurrent_tests(
                    ChecklistTest().test_create_checklist,
                    concurrent
                )
            results = {"load_test": stats}
        else:
            results = {"error": "Unknown test type"}
        
        test_results_cache["latest_results"] = results
        test_results_cache["progress"] = {"status": "completed", "test_type": test_type}
        
    except Exception as e:
        logger.error(f"Error in triggered test: {e}")
        test_results_cache["latest_results"] = {"error": str(e)}
        test_results_cache["progress"] = {"status": "failed", "error": str(e)}
    finally:
        test_results_cache["in_progress"] = False

# NEW: Endpoint to check test progress
@app.get("/api/webhook/test-status")
async def get_test_status():
    """Get current test status for frontend polling"""
    return JSONResponse(content={
        "in_progress": test_results_cache["in_progress"],
        "progress": test_results_cache["progress"],
        "latest_results": test_results_cache["latest_results"]
    })

# NEW: Endpoint for synchronized testing
@app.post("/api/webhook/sync-test")
async def synchronized_test(
    frontend_test_id: str,
    frontend_results: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Receive frontend test results and run server-side tests in sync"""
    
    # Store frontend results
    frontend_timestamp = datetime.utcnow()
    
    # Run server-side tests
    server_results = await run_all_tests()
    
    # Combine results
    combined_results = {
        "test_id": frontend_test_id,
        "timestamp": frontend_timestamp.isoformat(),
        "frontend": {
            "results": frontend_results,
            "source": "client"
        },
        "server": {
            "results": server_results,
            "source": "server",
            "system_metrics": await system_monitor.collect_metrics()
        },
        "comparison": compare_results(frontend_results, server_results)
    }
    
    # Store combined results
    background_tasks.add_task(store_combined_results, combined_results)
    
    return JSONResponse(content=combined_results)

def compare_results(frontend: Dict, server: Dict) -> Dict:
    """Compare frontend and server results"""
    comparison = {
        "response_time_diff": {},
        "success_match": {},
        "discrepancies": []
    }
    
    # Compare response times
    for test_type in ["voice", "stt", "checklist"]:
        if test_type in frontend and test_type in server:
            frontend_time = frontend[test_type].get("responseTime", 0)
            server_time = server[test_type].get("response_time_ms", 0)
            
            comparison["response_time_diff"][test_type] = {
                "frontend_ms": frontend_time,
                "server_ms": server_time,
                "difference_ms": abs(frontend_time - server_time)
            }
            
            # Check if success status matches
            frontend_success = frontend[test_type].get("success", False)
            server_success = server[test_type].get("success", False)
            
            comparison["success_match"][test_type] = frontend_success == server_success
            
            if not comparison["success_match"][test_type]:
                comparison["discrepancies"].append({
                    "test": test_type,
                    "issue": "Success status mismatch",
                    "frontend": frontend_success,
                    "server": server_success
                })
    
    return comparison

async def store_combined_results(results: Dict):
    """Store combined test results"""
    try:
        async with get_db_session() as session:
            # Store as a special test run
            test_run = TestRun(
                test_type="synchronized",
                endpoint="combined",
                method="POST",
                started_at=datetime.fromisoformat(results["timestamp"]),
                completed_at=datetime.utcnow(),
                success=True,
                test_data=results
            )
            session.add(test_run)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to store combined results: {e}")

@app.post("/api/test/voice")
async def test_voice_upload(background_tasks: BackgroundTasks):
    """Trigger voice upload test"""
    test = VoiceUploadTest()
    # You need to have test audio files ready
    test_file = "./test_audio/sample.wav"
    
    result = await test.test_upload(test_file)
    
    # Store result in database
    background_tasks.add_task(store_test_result, result)
    
    return JSONResponse(content=result)

@app.post("/api/test/stt")
async def test_stt(audio_url: str, expected_text: str = None):
    """Trigger STT test"""
    test = STTTest()
    result = await test.test_transcription(audio_url, expected_text)
    
    # Store result in database
    asyncio.create_task(store_test_result(result))
    
    return JSONResponse(content=result)

@app.post("/api/test/checklist")
async def test_checklist():
    """Trigger checklist test"""
    test = ChecklistTest()
    
    # Create checklist
    create_result = await test.test_create_checklist()
    
    if create_result['success']:
        checklist_id = create_result.get('response_body', {}).get('id')
        if checklist_id:
            # Test update
            update_result = await test.test_update_checklist(checklist_id)
            # Test get
            get_result = await test.test_get_checklist(checklist_id)
            
            return JSONResponse(content={
                'create': create_result,
                'update': update_result,
                'get': get_result
            })
    
    return JSONResponse(content={'create': create_result})

@app.post("/api/test/load/{test_type}")
async def test_load(test_type: str, concurrent_requests: int = 10):
    """Run load test"""
    load_test = LoadTest()
    
    if test_type == "voice":
        # Implement voice load test
        pass
    elif test_type == "stt":
        # Implement STT load test
        pass
    elif test_type == "checklist":
        stats = await load_test.run_concurrent_tests(
            ChecklistTest().test_create_checklist,
            concurrent_requests
        )
        return JSONResponse(content=stats)
    else:
        raise HTTPException(status_code=400, detail="Invalid test type")

@app.get("/api/metrics/system")
async def get_system_metrics():
    """Get current system metrics"""
    metrics = await system_monitor.collect_metrics()
    return JSONResponse(content=metrics)

@app.get("/api/metrics/performance")
async def get_performance_metrics(hours: int = 24):
    """Get performance metrics for the last N hours"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    async with get_db_session() as session:
        # Query metrics from database
        # This is a simplified example, you'd need proper SQLAlchemy queries
        metrics = []  # Fetch from database
        
    return JSONResponse(content={"metrics": metrics})

@app.get("/api/alerts")
async def get_alerts(active_only: bool = True):
    """Get alerts"""
    async with get_db_session() as session:
        # Query alerts from database
        alerts = []  # Fetch from database
        
    return JSONResponse(content={"alerts": alerts})

@app.post("/api/test/all")
async def run_all_tests():
    """Run all tests in sequence"""
    results = {}
    
    # Voice test
    voice_test = VoiceUploadTest()
    results['voice'] = await voice_test.test_upload("./test_audio/sample.wav")
    
    # STT test (using result from voice test if available)
    if results['voice']['success']:
        audio_url = results['voice'].get('response_body', {}).get('audio_url')
        if audio_url:
            stt_test = STTTest()
            results['stt'] = await stt_test.test_transcription(audio_url)
    
    # Checklist test
    checklist_test = ChecklistTest()
    results['checklist'] = await checklist_test.test_create_checklist()
    
    return JSONResponse(content=results)

async def store_test_result(result: Dict[str, Any]):
    """Store test result in database"""
    try:
        async with get_db_session() as session:
            test_run = TestRun(**result)
            session.add(test_run)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to store test result: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=True
    )