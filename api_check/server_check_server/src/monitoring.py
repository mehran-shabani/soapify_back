import psutil
import platform
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
import httpx
from loguru import logger

class SystemMonitor:
    """Monitor system resources and performance"""
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect current system and process metrics.
        
        Returns a dictionary with a UTC ISO timestamp and the following top-level sections:
        - system: platform, platform_version, architecture, python_version
        - cpu: usage_percent, count, frequency_mhz (None if unavailable)
        - memory: usage_percent, used_gb, total_gb
        - disk: usage_percent, used_gb, total_gb
        - network: bytes_sent_mb, bytes_received_mb
        - process: memory_mb, cpu_percent
        
        On failure returns an empty dict.
        """
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            
            # Network metrics
            network = psutil.net_io_counters()
            bytes_sent_mb = network.bytes_sent / (1024**2)
            bytes_recv_mb = network.bytes_recv / (1024**2)
            
            # Process metrics (for this monitoring app)
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024**2)
            process_cpu_percent = process.cpu_percent()
            
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'system': {
                    'platform': platform.system(),
                    'platform_version': platform.version(),
                    'architecture': platform.machine(),
                    'python_version': platform.python_version(),
                },
                'cpu': {
                    'usage_percent': cpu_percent,
                    'count': cpu_count,
                    'frequency_mhz': cpu_freq.current if cpu_freq else None,
                },
                'memory': {
                    'usage_percent': memory_percent,
                    'used_gb': round(memory_used_gb, 2),
                    'total_gb': round(memory_total_gb, 2),
                },
                'disk': {
                    'usage_percent': disk_percent,
                    'used_gb': round(disk_used_gb, 2),
                    'total_gb': round(disk_total_gb, 2),
                },
                'network': {
                    'bytes_sent_mb': round(bytes_sent_mb, 2),
                    'bytes_received_mb': round(bytes_recv_mb, 2),
                },
                'process': {
                    'memory_mb': round(process_memory_mb, 2),
                    'cpu_percent': process_cpu_percent,
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    async def check_network_latency(self, target_host: str) -> float:
        """
        Measure network latency to a target host by invoking the system `ping` command.
        
        This asynchronous method runs a single ICMP ping to the given target host (platform-specific ping flags) and attempts to parse the round-trip time in milliseconds from the command output. On success it returns the latency in milliseconds as a float; on failure (non-zero exit, unparsable output, or any error) it returns -1. The function handles exceptions internally and does not raise.
        Parameters:
            target_host (str): Hostname or IP address to ping.
        
        Returns:
            float: Round-trip latency in milliseconds, or -1 if the latency could not be determined.
        """
        try:
            import subprocess
            
            # Use ping command
            if platform.system().lower() == 'windows':
                cmd = f"ping -n 1 {target_host}"
            else:
                cmd = f"ping -c 1 {target_host}"
            
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            
            # Parse ping output for latency
            if result.returncode == 0:
                output = result.stdout
                # Extract latency from output (this is simplified)
                # In production, you'd want more robust parsing
                if 'time=' in output:
                    latency_str = output.split('time=')[1].split()[0]
                    return float(latency_str.replace('ms', ''))
            
            return -1  # Indicate failure
            
        except Exception as e:
            logger.error(f"Error checking network latency: {e}")
            return -1

class PerformanceTracker:
    """Track API performance metrics"""
    
    def __init__(self):
        """
        Initialize a PerformanceTracker.
        
        Creates an internal list to store performance metric dictionaries and sets the maximum number of retained metrics (1000).
        """
        self.metrics: List[Dict[str, Any]] = []
        self.max_metrics = 1000  # Keep last 1000 metrics
    
    def add_metric(self, metric: Dict[str, Any]):
        """
        Add a performance metric to the internal store, trimming older entries when capacity is exceeded.
        
        Parameters:
            metric (Dict[str, Any]): Metric dictionary to record. Expected to include a timestamp (UNIX seconds or ISO string) and, for statistics, a numeric `response_time_ms`. An optional boolean `success` flag may be provided to indicate request/result success.
        
        Returns:
            None
        """
        self.metrics.append(metric)
        
        # Keep only recent metrics
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Compute aggregated performance statistics from stored metrics.
        
        Returns a dictionary with:
        - total_requests (int): count of stored metrics.
        - successful_requests (int): metrics where `success` is truthy.
        - failed_requests (int): total minus successful_requests.
        - success_rate_percent (float): percentage of successful requests (0-100).
        - response_times (dict): aggregated timing values in milliseconds:
            - avg_ms (float): mean response time.
            - min_ms (float): minimum response time.
            - max_ms (float): maximum response time.
            - p50_ms (float): 50th percentile (median).
            - p95_ms (float): 95th percentile.
            - p99_ms (float): 99th percentile.
        
        Only metrics containing a `response_time_ms` numeric field are used for timing calculations. If there are no metrics or no response times available, the function returns an empty dict.
        """
        if not self.metrics:
            return {}
        
        response_times = [m['response_time_ms'] for m in self.metrics if 'response_time_ms' in m]
        success_count = sum(1 for m in self.metrics if m.get('success', False))
        total_count = len(self.metrics)
        
        if not response_times:
            return {}
        
        # Calculate percentiles
        response_times.sort()
        p50_idx = int(len(response_times) * 0.5)
        p95_idx = int(len(response_times) * 0.95)
        p99_idx = int(len(response_times) * 0.99)
        
        stats = {
            'total_requests': total_count,
            'successful_requests': success_count,
            'failed_requests': total_count - success_count,
            'success_rate_percent': (success_count / total_count * 100) if total_count > 0 else 0,
            'response_times': {
                'avg_ms': sum(response_times) / len(response_times),
                'min_ms': response_times[0],
                'max_ms': response_times[-1],
                'p50_ms': response_times[p50_idx] if p50_idx < len(response_times) else response_times[-1],
                'p95_ms': response_times[p95_idx] if p95_idx < len(response_times) else response_times[-1],
                'p99_ms': response_times[p99_idx] if p99_idx < len(response_times) else response_times[-1],
            }
        }
        
        return stats
    
    def get_recent_metrics(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """
        Return metrics collected within the last `minutes` minutes.
        
        Filters the internal metrics store and returns entries whose `timestamp` (ISO 8601 string) is strictly more recent than the cutoff time calculated in UTC. Metrics with missing or unparsable `timestamp` values are ignored.
        
        Parameters:
            minutes (int): Lookback window in minutes (default 5).
        
        Returns:
            List[Dict[str, Any]]: List of metric dictionaries recorded within the lookback window.
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        recent_metrics = [
            m for m in self.metrics 
            if datetime.fromisoformat(m.get('timestamp', '')) > cutoff_time
        ]
        
        return recent_metrics

class HealthChecker:
    """Check health of various API endpoints"""
    
    def __init__(self, base_url: str):
        """
        Initialize a HealthChecker with a base URL and predefined endpoints to monitor.
        
        Parameters:
            base_url (str): Base URL used to construct full endpoint URLs for health checks (e.g., "https://example.com").
        """
        self.base_url = base_url
        self.endpoints = [
            {'path': '/health', 'method': 'GET', 'name': 'Health Check'},
            {'path': '/api/v1/voice/', 'method': 'GET', 'name': 'Voice API'},
            {'path': '/api/v1/stt/', 'method': 'GET', 'name': 'STT API'},
            {'path': '/api/v1/checklists/', 'method': 'GET', 'name': 'Checklist API'},
        ]
    
    async def check_all_endpoints(self) -> List[Dict[str, Any]]:
        """
        Check the health of all configured endpoints.
        
        This asynchronously iterates over the monitor's configured endpoints and invokes check_endpoint for each one, collecting the individual health results.
        
        Returns:
            List[Dict[str, Any]]: A list of result dictionaries for each endpoint. Each entry contains fields such as `name`, `path`, `method`, `status` (e.g., "healthy", "unhealthy", or "error"), `status_code` (when available), `response_time_ms`, `checked_at`, and optionally an `error` message when a check fails.
        """
        results = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for endpoint in self.endpoints:
                result = await self.check_endpoint(client, endpoint)
                results.append(result)
        
        return results
    
    async def check_endpoint(self, client: httpx.AsyncClient, endpoint: Dict[str, str]) -> Dict[str, Any]:
        """
        Check a single configured HTTP endpoint and return its health result.
        
        Sends a request to the endpoint built from self.base_url + endpoint['path'], measures round-trip time, and classifies the result as 'healthy' when response.status_code < 400, 'unhealthy' when status_code >= 400, or 'error' when an exception occurs.
        
        Parameters:
            endpoint (dict): Mapping that must include:
                - 'path' (str): URL path appended to the HealthChecker base_url.
                - 'method' (str): HTTP method to use (e.g., 'GET', 'POST').
                - 'name' (str): Human-readable name for the endpoint.
            (client is an httpx.AsyncClient used to perform the request and is intentionally undocumented as a common client service.)
        
        Returns:
            dict: Health check result containing:
                - 'endpoint' (str): the endpoint path checked.
                - 'name' (str): the endpoint name.
                - 'method' (str): HTTP method used.
                - 'status' (str): 'healthy', 'unhealthy', or 'error'.
                - 'status_code' (int) [present on success/error responses]: HTTP status code.
                - 'error' (str) [present when an exception occurred]: error message.
                - 'response_time_ms' (float): elapsed time in milliseconds, rounded to 2 decimals.
                - 'checked_at' (str): ISO-8601 UTC timestamp when the check completed.
        """
        url = f"{self.base_url}{endpoint['path']}"
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await client.request(
                method=endpoint['method'],
                url=url
            )
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return {
                'endpoint': endpoint['path'],
                'name': endpoint['name'],
                'method': endpoint['method'],
                'status': 'healthy' if response.status_code < 400 else 'unhealthy',
                'status_code': response.status_code,
                'response_time_ms': round(response_time, 2),
                'checked_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return {
                'endpoint': endpoint['path'],
                'name': endpoint['name'],
                'method': endpoint['method'],
                'status': 'error',
                'error': str(e),
                'response_time_ms': round(response_time, 2),
                'checked_at': datetime.utcnow().isoformat()
            }