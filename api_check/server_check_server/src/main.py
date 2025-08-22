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
from .diagnostic_system import DiagnosticSystem
from .optimizer import APIOptimizer

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
diagnostic_system = DiagnosticSystem()
api_optimizer = APIOptimizer()

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
    """
    Initialize the application's database and start the background continuous monitoring task.
    
    This is run on application startup: it awaits database initialization via init_db() and then creates an asyncio background task for continuous_monitoring(), storing the task in the module-level `monitoring_task` variable so it can be cancelled on shutdown.
    """
    logger.info("Starting Soapify API Monitor...")
    await init_db()
    
    # Start background monitoring
    global monitoring_task
    monitoring_task = asyncio.create_task(continuous_monitoring())

@app.on_event("shutdown")
async def shutdown_event():
    """
    Perform application shutdown cleanup.
    
    Cancels the background monitoring task (if running) and logs shutdown initiation. Intended to be registered as FastAPI shutdown event handler; does not raise exceptions.
    """
    logger.info("Shutting down Soapify API Monitor...")
    if monitoring_task:
        monitoring_task.cancel()

async def continuous_monitoring():
    """
    Continuously collect system metrics, persist them to the database, and evaluate alerts until cancelled.
    
    This coroutine runs an infinite loop that:
    - Collects metrics from the global SystemMonitor.
    - Persists a PerformanceMetric record to the database for each collection.
    - Invokes check_alerts(metrics) to create Alert records when thresholds are exceeded.
    - Sleeps for settings.TEST_INTERVAL_MINUTES between iterations.
    
    Stops cleanly when cancelled (asyncio.CancelledError). On other exceptions it logs the error and waits 60 seconds before retrying.
    """
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
    """
    Evaluate runtime metrics and create Alert records in the database when thresholds are exceeded.
    
    This function inspects the provided metrics dict for known keys (notably
    `avg_response_time_ms`, `total_requests`, and `failed_requests`) and generates
    alerts when:
    - average response time exceeds settings.ALERT_RESPONSE_TIME_MS, and/or
    - error rate (failed_requests / total_requests * 100) exceeds
      settings.ALERT_ERROR_RATE_PERCENT.
    
    If one or more alert conditions are met, corresponding Alert objects are
    persisted to the database. If `total_requests` is zero or missing, error-rate
    checks are skipped.
    
    Parameters:
        metrics (Dict[str, Any]): A mapping of collected metrics. Expected keys:
            - avg_response_time_ms (number): average response time in milliseconds.
            - total_requests (int): total number of requests observed.
            - failed_requests (int): number of failed requests.
    
    Side effects:
        Persists Alert records to the database when alert conditions are triggered.
    
    Returns:
        None
    """
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
    """
    Render the main monitoring dashboard page.
    
    Renders the "dashboard.html" Jinja2 template and injects the incoming request and the configured API base URL
    so the frontend can make API calls relative to the server configuration.
    
    Parameters:
        request (Request): FastAPI request object used by Jinja2Templates for URL generation and template context.
    
    Returns:
        TemplateResponse: A Jinja2 TemplateResponse rendering the dashboard.
    """
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
    """
    Trigger a server-side test from a webhook request and schedule it to run in the background.
    
    Schedules run_triggered_test(test_type, params) as a background task, marks the global test_results_cache as in progress, and returns an accepted response with a test identifier.
    
    Parameters:
        test_type (str): Identifier of the test to run (e.g., "all", "voice", "stt", "checklist", "load").
        params (Dict[str, Any]): Optional test-specific parameters passed through to the background runner.
    
    Raises:
        HTTPException: 409 Conflict if a test run is already in progress.
    
    Returns:
        JSONResponse: 202 Accepted payload containing status, message, and a generated `test_id` timestamp.
    """
    
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
    """
    Execute a test requested via the frontend webhook and update the shared test_results_cache with progress and results.
    
    Runs the test specified by `test_type` using optional `params`. Supported `test_type` values:
    - "all": run the full sequence via run_all_tests()
    - "voice": run VoiceUploadTest.test_upload(file_path)
    - "stt": run STTTest.test_transcription(audio_url, expected_text)
    - "checklist": run ChecklistTest.test_create_checklist()
    - "load": run LoadTest.run_concurrent_tests(...) for a specified service (defaults to "checklist")
    
    Side effects:
    - Updates test_results_cache["progress"], test_results_cache["latest_results"], and clears test_results_cache["in_progress"] when finished.
    - On exception, records the error in test_results_cache["latest_results"] and sets progress status to "failed".
    
    Parameters:
        test_type (str): Type of test to run (see supported values above).
        params (Dict[str, Any]): Optional parameters used by specific tests (e.g., file_path, audio_url, expected_text, concurrent_requests, service).
    
    Returns:
        None
    """
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
    """
    Return the current background test status for frontend polling.
    
    Returns a JSONResponse with the following keys in its JSON body:
    - in_progress (bool): whether a background test is currently running.
    - progress: current progress information (percentage or a progress structure).
    - latest_results: the most recent test results payload, or None if no results are available.
    """
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
    """
    Accept frontend test results, run the same server-side tests, compare the two, and return a combined payload.
    
    This endpoint handler:
    - Records the incoming frontend test ID and timestamp.
    - Executes server-side tests via run_all_tests() and collects current system metrics.
    - Builds a combined result containing frontend results, server results, system metrics, and a comparison produced by compare_results().
    - Schedules asynchronous persistence of the combined results via background_tasks.add_task(store_combined_results, combined_results).
    
    Parameters:
        frontend_test_id (str): Identifier provided by the frontend to correlate this test run.
        frontend_results (Dict[str, Any]): Results produced by the frontend tests; must be serializable to JSON.
    
    Returns:
        fastapi.responses.JSONResponse: JSON response containing the combined payload with keys
        "test_id", "timestamp", "frontend", "server", and "comparison".
    """
    
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
    """
    Compare test results reported by a frontend run and server-side run and summarize differences.
    
    This function checks, for each supported test type ("voice", "stt", "checklist") present in both inputs:
    - Response time difference (milliseconds). Frontend is expected to use the key "responseTime" and server to use "response_time_ms"; missing values default to 0.
    - Whether the boolean `success` flag matches between frontend and server; missing flags default to False.
    When success flags differ, an entry describing the discrepancy is appended to "discrepancies".
    
    Parameters:
        frontend (Dict): Frontend test results keyed by test type. Expected per-test keys include "responseTime" (ms) and "success" (bool).
        server (Dict): Server-side test results keyed by test type. Expected per-test keys include "response_time_ms" (ms) and "success" (bool).
    
    Returns:
        Dict: A summary with keys:
            - "response_time_diff": mapping test_type -> {"frontend_ms", "server_ms", "difference_ms"}.
            - "success_match": mapping test_type -> bool indicating whether success flags match.
            - "discrepancies": list of discrepancy objects for mismatched success flags.
    """
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
    """
    Persist a synchronized frontend+server test payload as a TestRun record.
    
    Accepts a combined results dictionary (must include a top-level "timestamp" in ISO 8601 format)
    and writes a TestRun entry with test_type "synchronized", endpoint "combined", and the full payload
    stored in the TestRun.test_data field. Any storage errors are logged; the function does not raise.
    """
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
    """
    Trigger a voice upload integration test using a local sample audio file and return the test result.
    
    Runs the VoiceUploadTest.test_upload flow (awaited) against a fixed test file ("./test_audio/sample.wav"), schedules asynchronous persistence of the resulting payload via the provided background task, and returns a JSONResponse containing the test result.
    
    Note: The sample audio file must exist at "./test_audio/sample.wav" for the test to run successfully.
    
    Returns:
        JSONResponse: HTTP response whose content is the test result dictionary.
    """
    test = VoiceUploadTest()
    # You need to have test audio files ready
    test_file = "./test_audio/sample.wav"
    
    result = await test.test_upload(test_file)
    
    # Store result in database
    background_tasks.add_task(store_test_result, result)
    
    return JSONResponse(content=result)

@app.post("/api/test/stt")
async def test_stt(audio_url: str, expected_text: str = None):
    """
    Run a speech-to-text (STT) test against the provided audio URL and return the test result as a JSON response.
    
    Performs an asynchronous STT transcription using STTTest.test_transcription(audio_url, expected_text). The resulting test payload is scheduled to be saved to the database in the background (non-blocking).
    
    Parameters:
        audio_url (str): Publicly accessible URL to the audio file to transcribe.
        expected_text (str, optional): Expected transcription text to compare against the STT output; if provided, the test result will include comparison/validation information.
    
    Returns:
        fastapi.responses.JSONResponse: HTTP JSON response containing the test result dictionary produced by the STT test.
    """
    test = STTTest()
    result = await test.test_transcription(audio_url, expected_text)
    
    # Store result in database
    asyncio.create_task(store_test_result(result))
    
    return JSONResponse(content=result)

@app.post("/api/test/checklist")
async def test_checklist():
    """
    Run the checklist end-to-end test: create a checklist, and if creation succeeds, perform an update and a retrieval.
    
    Returns:
        JSONResponse: A JSONResponse containing the test results. If creation succeeded and returned an ID, the response includes keys "create", "update", and "get" with each step's result object; otherwise the response contains only "create".
    """
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
    """
    Run a load test for the specified test type.
    
    Performs a concurrent load test for the given `test_type`. Currently only the "checklist" type is implemented: it runs `ChecklistTest.test_create_checklist` concurrently `concurrent_requests` times and returns a JSONResponse with aggregated statistics. The "voice" and "stt" types are placeholders and are not implemented.
    
    Parameters:
        test_type (str): The type of load test to run. Supported value: "checklist".
        concurrent_requests (int): Number of concurrent requests to run (default 10).
    
    Returns:
        fastapi.responses.JSONResponse: Aggregated statistics for the completed "checklist" load test.
    
    Raises:
        fastapi.HTTPException: If `test_type` is not supported (HTTP 400).
    """
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
    """
    Return current system metrics as a JSON HTTP response.
    
    Collects the latest metrics from the global system monitor and returns them
    serialized in a FastAPI JSONResponse suitable for API clients.
    
    Returns:
        fastapi.responses.JSONResponse: JSON response containing the metrics dictionary.
    """
    metrics = await system_monitor.collect_metrics()
    return JSONResponse(content=metrics)

@app.get("/api/metrics/performance")
async def get_performance_metrics(hours: int = 24):
    """
    Return system performance metrics collected in the last `hours` hours.
    
    Parameters:
        hours (int): Time window in hours to retrieve metrics for (default: 24). Must be a non-negative integer.
    
    Returns:
        fastapi.responses.JSONResponse: JSON payload with a "metrics" key containing the list of performance metric records for the requested time window.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    
    async with get_db_session() as session:
        # Query metrics from database
        # This is a simplified example, you'd need proper SQLAlchemy queries
        metrics = []  # Fetch from database
        
    return JSONResponse(content={"metrics": metrics})

@app.get("/api/alerts")
async def get_alerts(active_only: bool = True):
    """
    Return a JSONResponse containing alert records.
    
    If active_only is True (default), only currently active/open alerts are returned; if False, historical and resolved alerts are included. The response body is {"alerts": [...]} where each alert is a dict representing the persisted Alert record (fields depend on the Alert model/schema).
    """
    async with get_db_session() as session:
        # Query alerts from database
        alerts = []  # Fetch from database
        
    return JSONResponse(content={"alerts": alerts})

@app.post("/api/test/all")
async def run_all_tests():
    """
    Run the suite of automated tests (voice upload, conditional STT, and checklist) and return their aggregated results.
    
    This coroutine executes:
    - a voice upload test (VoiceUploadTest.test_upload) using the local file "./test_audio/sample.wav";
    - if the voice test reports success and returns an `audio_url`, runs an STT transcription test (STTTest.test_transcription) against that URL;
    - a checklist creation test (ChecklistTest.test_create_checklist).
    
    Returns:
        fastapi.responses.JSONResponse: JSON response whose content is a dict with keys:
            - "voice": result dict from the voice upload test (always present).
            - "stt": result dict from the STT test (present only if the voice test succeeded and provided `audio_url`).
            - "checklist": result dict from the checklist test (always present).
    """
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
    """
    Persist a test run payload to the database as a TestRun record.
    
    Parameters:
        result (Dict[str, Any]): A mapping of fields accepted by the TestRun model (e.g., timestamps, test_type, test_data).
            The dict will be unpacked into TestRun(**result) and committed. The function does not raise on failure;
            any storage error is logged and the exception is swallowed.
    """
    try:
        async with get_db_session() as session:
            test_run = TestRun(**result)
            session.add(test_run)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to store test result: {e}")

@app.post("/api/diagnostics/analyze")
async def analyze_error(request: dict):
    """
    Analyze an error report and return diagnostic information.
    
    Expects `request` to be a dict containing:
    - "error_message" (str): the error message or stack trace to analyze.
    - "context" (dict, optional): additional contextual data to aid diagnosis.
    
    Returns:
    A diagnosis object (typically a dict) produced by the diagnostic system. On internal failure, returns a FastAPI JSONResponse with status 500 and an "error" message.
    """
    try:
        error_message = request.get("error_message", "")
        error_context = request.get("context", {})
        
        # Diagnose the error
        diagnosis = diagnostic_system.diagnose_error(error_message, error_context)
        
        return diagnosis
        
    except Exception as e:
        logger.error(f"Diagnostic error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/diagnostics/test-sequence/{endpoint}")
async def get_test_sequence(endpoint: str):
    """
    Return a generated test sequence for the given API endpoint.
    
    Parameters:
        endpoint (str): The API endpoint identifier or path to generate a test sequence for.
    
    Returns:
        On success: dict with keys "endpoint" (the provided endpoint) and "sequence" (the generated test steps).
        On failure: fastapi.responses.JSONResponse with status_code 500 and a JSON body {"error": "<message>"} describing the failure.
    """
    try:
        sequence = diagnostic_system.generate_test_sequence(endpoint)
        return {"endpoint": endpoint, "sequence": sequence}
    except Exception as e:
        logger.error(f"Test sequence error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/diagnostics/fix-script/{issue_type}")
async def get_fix_script(issue_type: str, os: str = None):
    """
    Return a generated fix script for a given issue type and target operating system.
    
    Attempts to generate a fix script via the diagnostic system and returns a JSON-serializable
    mapping with the requested issue_type, the resolved OS (provided or diagnostic system default),
    and the script content. On internal failure, the function returns a FastAPI JSONResponse with
    HTTP 500 and an error message.
    
    Parameters:
        issue_type (str): Identifier of the issue to generate a fix for (e.g., "memory-leak", "config-mismatch").
        os (str, optional): Target operating system for the fix script (e.g., "linux", "windows"). If omitted,
            the diagnostic system's default OS will be used.
    
    Returns:
        dict | fastapi.responses.JSONResponse: On success, a dict with keys "issue_type", "os", and "script".
            On failure, a JSONResponse with status_code 500 and {"error": "<message>"}.
    """
    try:
        script = diagnostic_system.generate_fix_script(issue_type, os)
        return {
            "issue_type": issue_type,
            "os": os or diagnostic_system.os_type,
            "script": script
        }
    except Exception as e:
        logger.error(f"Fix script error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/optimizer/test-approaches")
async def test_optimization_approaches():
    """
    Run the API optimizer's full set of experiments and record progress/results.
    
    Sets test_results_cache["optimization_in_progress"] and test_results_cache["optimization_progress"] while running, and stores the completed results in test_results_cache["optimization_results"].
    
    Returns:
        dict: Optimization results produced by api_optimizer.optimize_all() on success.
        fastapi.responses.JSONResponse: HTTP 500 JSON response with an "error" key if an exception occurs.
    """
    try:
        test_results_cache["optimization_in_progress"] = True
        test_results_cache["optimization_progress"] = {"status": "Testing approaches..."}
        
        # Run optimization tests
        optimization_results = await api_optimizer.optimize_all()
        
        test_results_cache["optimization_in_progress"] = False
        test_results_cache["optimization_results"] = optimization_results
        
        return optimization_results
        
    except Exception as e:
        logger.error(f"Optimization test error: {e}")
        test_results_cache["optimization_in_progress"] = False
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/optimizer/apply")
async def apply_optimizations(request: dict):
    """
    Apply the provided optimization configurations and generate an optimized project bundle.
    
    Parameters:
        request (dict): Incoming payload expected to contain a "best_configs" mapping with optimization settings.
    
    Returns:
        dict: On success, a dictionary with keys:
            - "success" (bool): True on successful application.
            - "zip_path" (str): File path to the generated optimized zip archive.
            - "report" (Any): Optimization report or metadata returned by the optimizer.
            - "message" (str): Human-readable success message.
        fastapi.responses.JSONResponse: On error, returns an HTTP 500 JSON response with an "error" message.
    """
    try:
        best_configs = request.get("best_configs", {})
        
        # Apply optimizations
        result = await api_optimizer.apply_optimizations(best_configs)
        
        return {
            "success": True,
            "zip_path": result["zip_path"],
            "report": result["report"],
            "message": "Optimizations applied successfully"
        }
        
    except Exception as e:
        logger.error(f"Apply optimization error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=True
    )