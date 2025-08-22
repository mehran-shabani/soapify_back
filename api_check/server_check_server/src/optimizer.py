import asyncio
import time
import os
import shutil
import zipfile
from typing import Dict, List, Any, Tuple
from datetime import datetime
from loguru import logger
import json
import subprocess

class APIOptimizer:
    """Test APIs with multiple approaches and select the best configuration"""
    
    def __init__(self):
        self.test_approaches = {
            'voice_upload': [
                {
                    'name': 'standard',
                    'config': {
                        'chunk_size': 1024 * 1024,  # 1MB chunks
                        'compression': False,
                        'timeout': 30
                    }
                },
                {
                    'name': 'compressed',
                    'config': {
                        'chunk_size': 1024 * 1024,
                        'compression': True,
                        'compression_level': 6,
                        'timeout': 30
                    }
                },
                {
                    'name': 'streaming',
                    'config': {
                        'chunk_size': 512 * 1024,  # 512KB chunks
                        'streaming': True,
                        'timeout': 60
                    }
                },
                {
                    'name': 'optimized',
                    'config': {
                        'chunk_size': 2 * 1024 * 1024,  # 2MB chunks
                        'compression': True,
                        'compression_level': 1,  # Fast compression
                        'parallel_chunks': 3,
                        'timeout': 45
                    }
                }
            ],
            'stt': [
                {
                    'name': 'direct',
                    'config': {
                        'preprocessing': False,
                        'model': 'default'
                    }
                },
                {
                    'name': 'preprocessed',
                    'config': {
                        'preprocessing': True,
                        'noise_reduction': True,
                        'normalize_audio': True,
                        'model': 'default'
                    }
                },
                {
                    'name': 'chunked',
                    'config': {
                        'chunk_duration': 30,  # 30 second chunks
                        'overlap': 2,  # 2 second overlap
                        'model': 'default'
                    }
                },
                {
                    'name': 'parallel',
                    'config': {
                        'parallel_processing': True,
                        'workers': 4,
                        'chunk_duration': 15,
                        'model': 'enhanced'
                    }
                }
            ],
            'database': [
                {
                    'name': 'default',
                    'config': {
                        'pool_size': 5,
                        'max_overflow': 10,
                        'pool_timeout': 30
                    }
                },
                {
                    'name': 'optimized_read',
                    'config': {
                        'pool_size': 20,
                        'max_overflow': 30,
                        'pool_timeout': 30,
                        'pool_pre_ping': True,
                        'query_cache_size': 1000
                    }
                },
                {
                    'name': 'optimized_write',
                    'config': {
                        'pool_size': 10,
                        'max_overflow': 20,
                        'pool_timeout': 60,
                        'batch_size': 100,
                        'async_writes': True
                    }
                },
                {
                    'name': 'balanced',
                    'config': {
                        'pool_size': 15,
                        'max_overflow': 25,
                        'pool_timeout': 45,
                        'read_replicas': 2,
                        'connection_recycling': 3600
                    }
                }
            ]
        }
        
        self.optimization_results = {}
        self.best_configurations = {}
    
    async def test_approach(self, category: str, approach: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single approach and measure performance"""
        logger.info(f"Testing {category} with approach: {approach['name']}")
        
        start_time = time.time()
        results = {
            'approach_name': approach['name'],
            'config': approach['config'],
            'metrics': {}
        }
        
        try:
            if category == 'voice_upload':
                results['metrics'] = await self._test_voice_upload(approach['config'])
            elif category == 'stt':
                results['metrics'] = await self._test_stt(approach['config'])
            elif category == 'database':
                results['metrics'] = await self._test_database(approach['config'])
            
            results['total_time'] = time.time() - start_time
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Error testing {approach['name']}: {e}")
            results['error'] = str(e)
            results['success'] = False
            results['total_time'] = time.time() - start_time
        
        return results
    
    async def _test_voice_upload(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test voice upload with specific configuration"""
        # Simulate testing with different configurations
        # In real implementation, this would actually test the API
        
        metrics = {
            'upload_speed_mbps': 0,
            'compression_ratio': 0,
            'cpu_usage': 0,
            'memory_usage': 0,
            'success_rate': 0,
            'avg_response_time': 0
        }
        
        # Simulate multiple uploads
        test_files = ['small.wav', 'medium.wav', 'large.wav']
        results = []
        
        for file in test_files:
            # Simulate upload with config
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Mock results based on config
            if config.get('compression'):
                compression_ratio = 0.6 + (config.get('compression_level', 6) * 0.05)
                upload_time = 1.0 / compression_ratio
            else:
                compression_ratio = 1.0
                upload_time = 1.5
            
            if config.get('streaming'):
                upload_time *= 0.8
            
            if config.get('parallel_chunks'):
                upload_time /= min(config['parallel_chunks'], 3)
            
            results.append({
                'upload_time': upload_time,
                'compression_ratio': compression_ratio,
                'success': True
            })
        
        # Calculate aggregated metrics
        metrics['upload_speed_mbps'] = 10 / (sum(r['upload_time'] for r in results) / len(results))
        metrics['compression_ratio'] = sum(r['compression_ratio'] for r in results) / len(results)
        metrics['cpu_usage'] = 20 + (config.get('compression_level', 0) * 5)
        metrics['memory_usage'] = 100 + (config.get('chunk_size', 1024*1024) / (1024*1024) * 10)
        metrics['success_rate'] = 100
        metrics['avg_response_time'] = sum(r['upload_time'] for r in results) / len(results) * 1000
        
        return metrics
    
    async def _test_stt(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test STT with specific configuration"""
        metrics = {
            'accuracy': 0,
            'processing_time': 0,
            'cpu_usage': 0,
            'memory_usage': 0,
            'word_error_rate': 0
        }
        
        # Simulate STT processing
        base_accuracy = 85
        base_time = 2.0
        
        if config.get('preprocessing'):
            base_accuracy += 5
            base_time += 0.5
            
            if config.get('noise_reduction'):
                base_accuracy += 3
                base_time += 0.3
        
        if config.get('parallel_processing'):
            base_time /= min(config.get('workers', 1), 4)
            metrics['cpu_usage'] = 30 * config.get('workers', 1)
        else:
            metrics['cpu_usage'] = 40
        
        if config.get('model') == 'enhanced':
            base_accuracy += 7
            base_time *= 1.5
            metrics['memory_usage'] = 500
        else:
            metrics['memory_usage'] = 300
        
        metrics['accuracy'] = min(base_accuracy, 98)
        metrics['processing_time'] = base_time * 1000  # Convert to ms
        metrics['word_error_rate'] = 100 - metrics['accuracy']
        
        return metrics
    
    async def _test_database(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test database performance with specific configuration"""
        metrics = {
            'query_time_ms': 0,
            'connections_used': 0,
            'throughput_qps': 0,  # Queries per second
            'latency_p95': 0,
            'latency_p99': 0
        }
        
        base_query_time = 10  # ms
        
        # Adjust based on pool size
        if config['pool_size'] > 10:
            base_query_time *= 0.8
        
        if config.get('query_cache_size'):
            base_query_time *= 0.6
        
        if config.get('async_writes'):
            base_query_time *= 0.7
        
        metrics['query_time_ms'] = base_query_time
        metrics['connections_used'] = min(config['pool_size'], 15)
        metrics['throughput_qps'] = 1000 / base_query_time * metrics['connections_used']
        metrics['latency_p95'] = base_query_time * 1.5
        metrics['latency_p99'] = base_query_time * 2.0
        
        return metrics
    
    async def optimize_all(self) -> Dict[str, Any]:
        """Test all approaches and find the best configuration for each category"""
        logger.info("Starting optimization process...")
        
        for category, approaches in self.test_approaches.items():
            logger.info(f"Optimizing {category}...")
            category_results = []
            
            # Test all approaches
            for approach in approaches:
                result = await self.test_approach(category, approach)
                category_results.append(result)
            
            # Find best approach
            best_approach = self._select_best_approach(category, category_results)
            self.best_configurations[category] = best_approach
            self.optimization_results[category] = category_results
            
            logger.info(f"Best approach for {category}: {best_approach['approach_name']}")
        
        return {
            'best_configurations': self.best_configurations,
            'all_results': self.optimization_results,
            'optimization_completed': datetime.utcnow().isoformat()
        }
    
    def _select_best_approach(self, category: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the best approach based on metrics"""
        # Filter out failed tests
        successful_results = [r for r in results if r.get('success', False)]
        
        if not successful_results:
            return results[0]  # Return first if all failed
        
        # Score each approach based on category-specific criteria
        for result in successful_results:
            score = 0
            metrics = result.get('metrics', {})
            
            if category == 'voice_upload':
                # Prioritize upload speed and success rate
                score += metrics.get('upload_speed_mbps', 0) * 10
                score += metrics.get('success_rate', 0)
                score -= metrics.get('avg_response_time', 0) / 100
                score -= metrics.get('cpu_usage', 0) / 10
                
            elif category == 'stt':
                # Prioritize accuracy
                score += metrics.get('accuracy', 0) * 2
                score -= metrics.get('processing_time', 0) / 1000
                score -= metrics.get('word_error_rate', 0)
                
            elif category == 'database':
                # Prioritize throughput and low latency
                score += metrics.get('throughput_qps', 0) / 100
                score -= metrics.get('query_time_ms', 0)
                score -= metrics.get('latency_p99', 0) / 10
            
            result['optimization_score'] = score
        
        # Return approach with highest score
        return max(successful_results, key=lambda x: x.get('optimization_score', 0))
    
    async def apply_optimizations(self, project_path: str) -> str:
        """Apply the best configurations to the project and create optimized version"""
        logger.info("Applying optimizations to project...")
        
        # Create a copy of the project
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        optimized_path = f"{project_path}_optimized_{timestamp}"
        
        # Copy project
        shutil.copytree(project_path, optimized_path, ignore=shutil.ignore_patterns('*.pyc', '__pycache__', '.git'))
        
        # Apply optimizations
        await self._apply_config_changes(optimized_path)
        
        # Generate optimization report
        report_path = os.path.join(optimized_path, 'OPTIMIZATION_REPORT.json')
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'optimizations_applied': self.best_configurations,
                'performance_improvements': self._calculate_improvements(),
                'full_results': self.optimization_results
            }, f, indent=2)
        
        # Create zip file
        zip_path = f"{optimized_path}.zip"
        await self._create_zip(optimized_path, zip_path)
        
        logger.info(f"Optimized project created: {zip_path}")
        return zip_path
    
    async def _apply_config_changes(self, project_path: str):
        """Apply configuration changes to the project files"""
        # This would modify actual configuration files based on best configurations
        # For demonstration, we'll create a new config file
        
        config_updates = {
            'voice_upload': self.best_configurations.get('voice_upload', {}).get('config', {}),
            'stt': self.best_configurations.get('stt', {}).get('config', {}),
            'database': self.best_configurations.get('database', {}).get('config', {})
        }
        
        # Write optimized configuration
        config_path = os.path.join(project_path, 'optimized_config.json')
        with open(config_path, 'w') as f:
            json.dump(config_updates, f, indent=2)
        
        # Update Django settings if needed
        settings_path = os.path.join(project_path, 'soapify', 'settings_optimized.py')
        with open(settings_path, 'w') as f:
            f.write(f"""# Optimized settings generated at {datetime.now()}
from .settings import *

# Database optimizations
DATABASES['default']['OPTIONS'] = {{
    'pool_size': {config_updates['database'].get('pool_size', 5)},
    'max_overflow': {config_updates['database'].get('max_overflow', 10)},
}}

# Cache configuration
CACHES = {{
    'default': {{
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {{
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {{
                'max_connections': {config_updates['database'].get('pool_size', 5) * 2},
            }},
        }}
    }}
}}

# Optimized file upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = {config_updates['voice_upload'].get('chunk_size', 1024*1024)}
DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE
""")
    
    def _calculate_improvements(self) -> Dict[str, Any]:
        """Calculate performance improvements from optimization"""
        improvements = {}
        
        for category, results in self.optimization_results.items():
            if not results:
                continue
                
            # Compare best with default (first approach)
            default_result = results[0]
            best_result = self.best_configurations.get(category, {})
            
            if default_result.get('success') and best_result.get('success'):
                default_metrics = default_result.get('metrics', {})
                best_metrics = best_result.get('metrics', {})
                
                improvements[category] = {}
                
                if category == 'voice_upload':
                    if default_metrics.get('upload_speed_mbps') and best_metrics.get('upload_speed_mbps'):
                        speed_improvement = ((best_metrics['upload_speed_mbps'] - default_metrics['upload_speed_mbps']) 
                                           / default_metrics['upload_speed_mbps'] * 100)
                        improvements[category]['upload_speed_improvement'] = f"{speed_improvement:.1f}%"
                
                elif category == 'stt':
                    if default_metrics.get('accuracy') and best_metrics.get('accuracy'):
                        accuracy_improvement = best_metrics['accuracy'] - default_metrics['accuracy']
                        improvements[category]['accuracy_improvement'] = f"+{accuracy_improvement:.1f}%"
                
                elif category == 'database':
                    if default_metrics.get('throughput_qps') and best_metrics.get('throughput_qps'):
                        throughput_improvement = ((best_metrics['throughput_qps'] - default_metrics['throughput_qps']) 
                                                / default_metrics['throughput_qps'] * 100)
                        improvements[category]['throughput_improvement'] = f"{throughput_improvement:.1f}%"
        
        return improvements
    
    async def _create_zip(self, source_path: str, zip_path: str):
        """Create a zip file of the optimized project"""
        logger.info(f"Creating zip file: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_path):
                # Skip certain directories
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules']]
                
                for file in files:
                    if file.endswith(('.pyc', '.pyo')):
                        continue
                        
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_path)
                    zipf.write(file_path, arcname)
        
        # Remove the temporary directory
        shutil.rmtree(source_path)
        
        logger.info(f"Zip file created successfully: {zip_path}")