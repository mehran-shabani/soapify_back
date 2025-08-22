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
        """
        Initialize BaseAPITest with API connection settings.
        
        Sets:
        - base_url from settings.API_BASE_URL
        - timeout as an httpx.Timeout using settings.API_TIMEOUT
        - default request headers including a User-Agent
        - an Authorization Bearer header when settings.API_TOKEN is present
        """
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
        """
        Perform an asynchronous HTTP request to the API, record timing and response metrics, and return a consolidated test run record.
        
        This method builds the full URL from the instance's base_url and the provided endpoint, issues the request using httpx.AsyncClient, and captures:
        - timestamps (started_at and completed_at in UTC),
        - response_time_ms (float, milliseconds),
        - HTTP status_code and a boolean success flag (True for 2xx responses),
        - response_headers, response_body (parsed as JSON when the response Content-Type starts with "application/json", otherwise as text), and response_size_bytes.
        If an exception occurs, the returned record will include success=False and error_message instead of response details.
        
        Parameters:
            method: HTTP method (e.g., "GET", "POST").
            endpoint: Path appended to the configured base_url (should include leading slash if needed).
            data: Optional form-encoded payload for the request.
            files: Optional multipart file payload (as expected by httpx).
            json_data: Optional JSON-serializable payload sent as the request body.
        
        Returns:
            dict: A test_run dictionary containing at minimum:
                - test_type (str): calling class name
                - endpoint (str)
                - method (str)
                - started_at (datetime, UTC)
                - completed_at (datetime, UTC)
                - response_time_ms (float)
                - status_code (int) [when available]
                - success (bool)
                - request_headers, response_headers (dict) [when available]
                - response_body (dict or str) [when available]
                - response_size_bytes (int) [when available]
                - error_message (str) [on exception]
        """
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
        """
        Upload a local audio file to the voice upload endpoint and return a structured test result.
        
        Reads the file at `audio_file_path`, posts it as multipart/form-data to /api/v1/voice/upload/, and returns the result produced by `make_request`. On a successful upload (HTTP 2xx and a measured response time), the returned dictionary will include a `test_data` entry with:
        - file_size_bytes: size of the uploaded file in bytes
        - file_format: file extension without the leading dot
        - upload_speed_mbps: measured upload throughput in megabits per second
        
        Parameters:
            audio_file_path (str): Path to the local audio file to upload.
        
        Returns:
            Dict[str, Any]: The test run record returned by `make_request`, potentially augmented with `test_data` on success.
        """
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
        """
        Send an audio URL to the STT endpoint and return the API test result, optionally evaluating transcription accuracy.
        
        Calls POST /api/v1/stt/transcribe/ with payload {'audio_url': audio_url, 'language': 'fa'} and returns the test-run dictionary produced by make_request. If the request succeeds and expected_text is provided, computes a simple word-level accuracy percentage and attaches a `test_data` dict with keys: `transcription`, `expected_text`, and `accuracy_percent`.
        Parameters:
            audio_url (str): Publicly accessible URL of the audio to transcribe.
            expected_text (Optional[str]): If provided, used to compute a simple accuracy percentage against the returned transcription.
        
        Returns:
            Dict[str, Any]: A test_run dictionary containing request/response metadata produced by make_request; may include `test_data` when accuracy was evaluated.
        """
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
        """
        Compute a word-level similarity percentage between two texts using the Jaccard index.
        
        Performs a case-insensitive, whitespace-based tokenization of each input into unique words,
        then returns the Jaccard similarity (intersection / union) as a percentage in the range 0.0–100.0.
        If either text contains no words after tokenization, the function returns 0.0.
        
        Parameters:
            text1 (str): First text to compare.
            text2 (str): Second text to compare.
        
        Returns:
            float: Similarity percentage (0.0 to 100.0).
        """
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
        """
        Create a new checklist on the API and return the test run result.
        
        Builds a checklist payload with a timestamped title and three items (two incomplete, one completed),
        sends it as JSON to POST /api/v1/checklists/, and returns the consolidated test-run dictionary
        produced by make_request (includes timing, status, response body/headers, and success flag).
        Returns:
            Dict[str, Any]: Test-run record containing request/response metadata and any parsed response body.
        """
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
        """
        Update a checklist's items by sending a PUT request to the checklist endpoint.
        
        Sends a JSON payload that marks two checklist items as completed to /api/v1/checklists/{checklist_id}/
        and returns the consolidated test run record produced by make_request.
        
        Parameters:
            checklist_id (str): ID of the checklist to update.
        
        Returns:
            Dict[str, Any]: A test_run dictionary containing request/response metrics and fields such as
            'success', 'status_code', 'response_time_ms', 'response_body', and optionally 'error_message'.
        """
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
        """
        Retrieve a checklist by ID and return a consolidated test run record.
        
        Parameters:
            checklist_id (str): Identifier of the checklist to retrieve; used to construct the GET endpoint.
        
        Returns:
            Dict[str, Any]: A test_run dictionary containing metrics and response data (includes keys such as
                - test_type
                - endpoint
                - method
                - started_at
                - completed_at
                - response_time_ms
                - status_code
                - success
                - response_headers
                - response_body (parsed JSON when applicable)
                - response_size_bytes
                - error_message (present on failure)
        """
        logger.info(f"Testing checklist retrieval for ID: {checklist_id}")
        
        return await self.make_request(
            method="GET",
            endpoint=f"/api/v1/checklists/{checklist_id}/"
        )

class LoadTest:
    """Perform load testing on APIs"""
    
    def __init__(self):
        """
        Initialize LoadTest by creating instances of the available API test helpers.
        
        Creates:
        - voice_test: VoiceUploadTest instance for voice upload scenarios.
        - stt_test: STTTest instance for speech-to-text transcription scenarios.
        - checklist_test: ChecklistTest instance for checklist CRUD scenarios.
        """
        self.voice_test = VoiceUploadTest()
        self.stt_test = STTTest()
        self.checklist_test = ChecklistTest()
    
    async def run_concurrent_tests(self, test_func, num_concurrent: int = 10) -> List[Dict[str, Any]]:
        """
        Run the given asynchronous test function concurrently and aggregate basic metrics.
        
        Args:
            test_func: An async callable (no-argument) that performs a single test and returns a dict-like result when awaited. Results that are exceptions (raised during execution) are captured and counted as failures.
            num_concurrent (int): Number of concurrent invocations to run (default 10).
        
        Returns:
            dict: Aggregated statistics with the following keys:
                - total_requests (int): Total number of invocations attempted.
                - successful_requests (int): Count of results that are dict-like and have a truthy 'success' value.
                - failed_requests (int): Count of invocations that did not meet the success criteria (including exceptions).
                - avg_response_time_ms (float): Average of available response_time_ms values (0 if none).
                - min_response_time_ms (float): Minimum response_time_ms observed (0 if none).
                - max_response_time_ms (float): Maximum response_time_ms observed (0 if none).
        """
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