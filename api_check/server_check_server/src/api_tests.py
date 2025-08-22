import httpx
import asyncio
import time
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import aiofiles
from .config import settings
from .models import TestRun, VoiceTestResult

class BaseAPITest:
    def __init__(self):
        self.base_url = settings.API_BASE_URL
        self.timeout = httpx.Timeout(settings.API_TIMEOUT)
        self.headers = {
            "User-Agent": "SoapifyAPITester/1.0"
        }
        if settings.API_TOKEN:
            self.headers["Authorization"] = f"Bearer {settings.API_TOKEN}"
    
    async def make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None, 
        files: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request and capture metrics"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        test_run = {
            "test_type": self.__class__.__name__,
            "endpoint": endpoint,
            "method": method,
            "started_at": datetime.utcnow(),
            "request_headers": self.headers.copy()
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    data=data,
                    files=files,
                    json=json_data
                )
                
                response_time_ms = (time.time() - start_time) * 1000
                
                test_run.update({
                    "completed_at": datetime.utcnow(),
                    "response_time_ms": response_time_ms,
                    "status_code": response.status_code,
                    "success": 200 <= response.status_code < 300,
                    "response_headers": dict(response.headers),
                    "response_body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    "response_size_bytes": len(response.content)
                })
                
                return test_run
                
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Request failed: {e}")
            
            test_run.update({
                "completed_at": datetime.utcnow(),
                "response_time_ms": response_time_ms,
                "success": False,
                "error_message": str(e)
            })
            
            return test_run

class VoiceUploadTest(BaseAPITest):
    """Test voice recording upload functionality"""
    
    async def test_upload(self, audio_file_path: str) -> Dict[str, Any]:
        """Test uploading an audio file"""
        logger.info(f"Testing voice upload with file: {audio_file_path}")
        
        # Get file info
        file_size = os.path.getsize(audio_file_path)
        file_format = os.path.splitext(audio_file_path)[1][1:]  # Remove the dot
        
        # Read file
        async with aiofiles.open(audio_file_path, 'rb') as f:
            file_content = await f.read()
        
        # Prepare multipart upload
        files = {
            'audio': (os.path.basename(audio_file_path), file_content, f'audio/{file_format}')
        }
        
        # Additional form data
        data = {
            'title': f'Test recording {datetime.now().isoformat()}',
            'description': 'Automated test recording'
        }
        
        # Make request
        result = await self.make_request(
            method="POST",
            endpoint="/api/v1/voice/upload/",
            data=data,
            files=files
        )
        
        # Calculate upload speed
        if result['success'] and result['response_time_ms']:
            upload_speed_mbps = (file_size * 8 / 1_000_000) / (result['response_time_ms'] / 1000)
            result['test_data'] = {
                'file_size_bytes': file_size,
                'file_format': file_format,
                'upload_speed_mbps': upload_speed_mbps
            }
        
        return result

class STTTest(BaseAPITest):
    """Test Speech-to-Text functionality"""
    
    async def test_transcription(self, audio_url: str, expected_text: Optional[str] = None) -> Dict[str, Any]:
        """Test STT transcription"""
        logger.info(f"Testing STT with audio URL: {audio_url}")
        
        data = {
            'audio_url': audio_url,
            'language': 'fa'  # Persian
        }
        
        result = await self.make_request(
            method="POST",
            endpoint="/api/v1/stt/transcribe/",
            json_data=data
        )
        
        # Check transcription accuracy if expected text provided
        if result['success'] and expected_text:
            transcription = result.get('response_body', {}).get('transcription', '')
            # Simple accuracy check (can be improved with better algorithms)
            accuracy = self._calculate_text_similarity(transcription, expected_text)
            result['test_data'] = {
                'transcription': transcription,
                'expected_text': expected_text,
                'accuracy_percent': accuracy
            }
        
        return result
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity calculation"""
        # This is a basic implementation, can be improved with libraries like difflib
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return (len(intersection) / len(union)) * 100

class ChecklistTest(BaseAPITest):
    """Test Checklist functionality"""
    
    async def test_create_checklist(self) -> Dict[str, Any]:
        """Test creating a new checklist"""
        logger.info("Testing checklist creation")
        
        data = {
            'title': f'Test Checklist {datetime.now().isoformat()}',
            'items': [
                {'text': 'Test item 1', 'completed': False},
                {'text': 'Test item 2', 'completed': False},
                {'text': 'Test item 3', 'completed': True}
            ]
        }
        
        return await self.make_request(
            method="POST",
            endpoint="/api/v1/checklists/",
            json_data=data
        )
    
    async def test_update_checklist(self, checklist_id: str) -> Dict[str, Any]:
        """Test updating a checklist"""
        logger.info(f"Testing checklist update for ID: {checklist_id}")
        
        data = {
            'items': [
                {'text': 'Test item 1', 'completed': True},
                {'text': 'Test item 2', 'completed': True}
            ]
        }
        
        return await self.make_request(
            method="PUT",
            endpoint=f"/api/v1/checklists/{checklist_id}/",
            json_data=data
        )
    
    async def test_get_checklist(self, checklist_id: str) -> Dict[str, Any]:
        """Test retrieving a checklist"""
        logger.info(f"Testing checklist retrieval for ID: {checklist_id}")
        
        return await self.make_request(
            method="GET",
            endpoint=f"/api/v1/checklists/{checklist_id}/"
        )

class LoadTest:
    """Perform load testing on APIs"""
    
    def __init__(self):
        self.voice_test = VoiceUploadTest()
        self.stt_test = STTTest()
        self.checklist_test = ChecklistTest()
    
    async def run_concurrent_tests(self, test_func, num_concurrent: int = 10) -> List[Dict[str, Any]]:
        """Run multiple tests concurrently"""
        logger.info(f"Running {num_concurrent} concurrent tests")
        
        tasks = []
        for _ in range(num_concurrent):
            tasks.append(test_func())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        failed = len(results) - successful
        
        response_times = [r['response_time_ms'] for r in results if isinstance(r, dict) and 'response_time_ms' in r]
        
        stats = {
            'total_requests': len(results),
            'successful_requests': successful,
            'failed_requests': failed,
            'avg_response_time_ms': sum(response_times) / len(response_times) if response_times else 0,
            'min_response_time_ms': min(response_times) if response_times else 0,
            'max_response_time_ms': max(response_times) if response_times else 0
        }
        
        return stats