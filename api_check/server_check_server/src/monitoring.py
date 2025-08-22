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
        """Collect current system metrics"""
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
        """Check network latency to target host"""
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
        self.metrics: List[Dict[str, Any]] = []
        self.max_metrics = 1000  # Keep last 1000 metrics
    
    def add_metric(self, metric: Dict[str, Any]):
        """Add a performance metric"""
        self.metrics.append(metric)
        
        # Keep only recent metrics
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate performance statistics"""
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
        """Get metrics from the last N minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        recent_metrics = [
            m for m in self.metrics 
            if datetime.fromisoformat(m.get('timestamp', '')) > cutoff_time
        ]
        
        return recent_metrics

class HealthChecker:
    """Check health of various API endpoints"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.endpoints = [
            {'path': '/health', 'method': 'GET', 'name': 'Health Check'},
            {'path': '/api/v1/voice/', 'method': 'GET', 'name': 'Voice API'},
            {'path': '/api/v1/stt/', 'method': 'GET', 'name': 'STT API'},
            {'path': '/api/v1/checklists/', 'method': 'GET', 'name': 'Checklist API'},
        ]
    
    async def check_all_endpoints(self) -> List[Dict[str, Any]]:
        """Check health of all endpoints"""
        results = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for endpoint in self.endpoints:
                result = await self.check_endpoint(client, endpoint)
                results.append(result)
        
        return results
    
    async def check_endpoint(self, client: httpx.AsyncClient, endpoint: Dict[str, str]) -> Dict[str, Any]:
        """Check a single endpoint"""
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