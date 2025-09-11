"""Enhanced system metrics collector for Docker deployment with host access."""

import platform
import socket
import os
import psutil
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from .config import AgentConfig


@dataclass
class DockerSystemInfo:
    """System information adapted for Docker deployment."""
    hostname: str
    container_hostname: str
    os_name: str
    os_version: str
    architecture: str
    cpu_count: int
    cpu_model: str
    memory_total: int
    boot_time: datetime
    docker_mode: bool = True
    host_paths: Optional[Dict[str, str]] = None


@dataclass
class DockerMetricsSnapshot:
    """Enhanced metrics snapshot with Docker-specific info."""
    timestamp: datetime
    cpu_percent: float
    cpu_load_avg: Optional[List[float]]
    memory_percent: float
    memory_used: int
    memory_available: int
    disk_usage: Dict[str, Any]
    network_io: Dict[str, int]
    disk_io: Dict[str, int]
    process_count: int
    uptime_seconds: int
    # Docker-specific metrics
    docker_containers: Optional[List[Dict[str, Any]]] = None
    host_filesystem: Optional[Dict[str, Any]] = None


class DockerMetricsCollector:
    """Enhanced metrics collector for Docker deployment with host system access."""
    
    def __init__(self, config: AgentConfig):
        """Initialize collector with Docker-aware configuration."""
        self.config = config
        self._system_info: Optional[DockerSystemInfo] = None
        
        # Host paths from environment variables
        self.host_paths = {
            'root': os.getenv('HOST_ROOT', '/host'),
            'proc': os.getenv('HOST_PROC', '/host/proc'),
            'sys': os.getenv('HOST_SYS', '/host/sys'),
            'dev': os.getenv('HOST_DEV', '/host/dev'),
            'var_log': os.getenv('HOST_VAR_LOG', '/host/var/log')
        }
        
        # Cache for expensive operations
        self._last_disk_check = 0
        self._disk_cache: Dict[str, Any] = {}
        self._docker_available = self._check_docker_availability()
    
    def _check_docker_availability(self) -> bool:
        """Check if Docker socket is available for container monitoring."""
        docker_socket = Path('/var/run/docker.sock')
        return docker_socket.exists() and docker_socket.is_socket()
    
    def get_system_info(self) -> DockerSystemInfo:
        """Get static system information (cached)."""
        if self._system_info is None:
            self._system_info = self._collect_docker_system_info()
        return self._system_info
    
    def _collect_docker_system_info(self) -> DockerSystemInfo:
        """Collect system information with Docker awareness."""
        cpu_model = self._get_cpu_model()
        memory_total = self._get_total_memory()
        
        return DockerSystemInfo(
            hostname=socket.gethostname(),
            container_hostname=os.getenv('HOSTNAME', socket.gethostname()),
            os_name=platform.system(),
            os_version=platform.release(),
            architecture=platform.machine(),
            cpu_count=psutil.cpu_count(logical=True),
            cpu_model=cpu_model,
            memory_total=memory_total,
            boot_time=self._get_host_boot_time(),
            docker_mode=True,
            host_paths=self.host_paths
        )
    
    def _get_cpu_model(self) -> str:
        """Extract CPU model from host or container /proc/cpuinfo."""
        # Try host path first
        cpu_info_path = Path(self.host_paths['proc']) / 'cpuinfo'
        cpu_model = self._read_cpu_model_from_file(cpu_info_path)
        
        # Fallback to container path
        if cpu_model == "Unknown":
            cpu_model = self._read_cpu_model_from_file(Path("/proc/cpuinfo"))
        
        return cpu_model
    
    def _read_cpu_model_from_file(self, cpu_info_path: Path) -> str:
        """Read CPU model from a cpuinfo file."""
        try:
            if cpu_info_path.exists():
                with open(cpu_info_path, "r") as f:
                    for line in f:
                        if "model name" in line:
                            return line.split(":")[1].strip()
        except (FileNotFoundError, IndexError, PermissionError):
            pass
        return "Unknown"
    
    def _get_total_memory(self) -> int:
        """Get total memory from host or container."""
        # Default to container memory
        memory_total = psutil.virtual_memory().total
        
        # Try to get host memory
        try:
            meminfo_path = Path(self.host_paths['proc']) / 'meminfo'
            if meminfo_path.exists():
                with open(meminfo_path, 'r') as f:
                    for line in f:
                        if line.startswith('MemTotal:'):
                            # Convert from kB to bytes
                            memory_total = int(line.split()[1]) * 1024
                            break
        except (FileNotFoundError, ValueError, PermissionError):
            pass
        
        return memory_total
    
    def _get_host_boot_time(self) -> datetime:
        """Get host boot time from /host/proc/stat if available."""
        try:
            stat_path = Path(self.host_paths['proc']) / 'stat'
            if stat_path.exists():
                with open(stat_path, 'r') as f:
                    for line in f:
                        if line.startswith('btime'):
                            boot_timestamp = int(line.split()[1])
                            return datetime.fromtimestamp(boot_timestamp)
        except (FileNotFoundError, ValueError, IndexError, PermissionError):
            pass
        
        # Fallback to container boot time
        return datetime.fromtimestamp(psutil.boot_time())
    
    def collect_metrics(self) -> DockerMetricsSnapshot:
        """Collect current system metrics with Docker enhancements."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("[DEBUG] Starting collect_metrics method")
        
        # Use host memory instead of container memory
        host_memory = self._get_host_memory_info()
        logger.info(f"[DEBUG] Got host memory: {host_memory}")
        
        # CPU load average from host
        load_avg = self._get_host_load_avg()
        logger.info(f"[DEBUG] Got load avg: {load_avg}")
        
        # Disk I/O
        disk_io = {}
        try:
            io_counters = psutil.disk_io_counters()
            if io_counters:
                disk_io = {
                    'read_bytes': io_counters.read_bytes,
                    'write_bytes': io_counters.write_bytes,
                    'read_count': io_counters.read_count,
                    'write_count': io_counters.write_count
                }
        except Exception:
            pass
        
        # Network I/O
        network_io = {}
        try:
            io_counters = psutil.net_io_counters()
            if io_counters:
                network_io = {
                    'bytes_sent': io_counters.bytes_sent,
                    'bytes_recv': io_counters.bytes_recv,
                    'packets_sent': io_counters.packets_sent,
                    'packets_recv': io_counters.packets_recv
                }
        except Exception:
            pass
        
        # Enhanced disk usage with host filesystem
        disk_usage = self._collect_disk_usage()
        
        # Docker containers info if available
        docker_containers = None
        if self._docker_available:
            docker_containers = self._collect_docker_info()
        
        # Host filesystem info
        host_filesystem = self._collect_host_filesystem_info()
        
        # Get host CPU usage
        host_cpu_percent = self._get_host_cpu_percent()
        
        # Get host process count
        host_process_count = self._get_host_process_count()
        
        # Get host uptime
        host_uptime = self._get_host_uptime()
        
        # Debug logging
        logger.info(f"[DEBUG] collect_metrics - CPU: {host_cpu_percent}, Memory %: {host_memory.get('percent', 0)}")
        logger.info(f"[DEBUG] collect_metrics - Memory used: {host_memory.get('used', 0)}, available: {host_memory.get('available', 0)}")
        
        return DockerMetricsSnapshot(
            timestamp=datetime.now(),
            cpu_percent=host_cpu_percent,  # Use real host CPU
            cpu_load_avg=load_avg,
            memory_percent=host_memory.get('percent', 0.0),  # Use real host memory %
            memory_used=host_memory.get('used', 0),
            memory_available=host_memory.get('available', 0),
            disk_usage=disk_usage,
            network_io=network_io,
            disk_io=disk_io,
            process_count=host_process_count,
            uptime_seconds=host_uptime,
            docker_containers=docker_containers,
            host_filesystem=host_filesystem
        )
    
    def _collect_disk_usage(self) -> Dict[str, Any]:
        """Collect disk usage for both container and host filesystem."""
        disk_usage = {}
        
        # Container disk usage
        try:
            container_usage = psutil.disk_usage('/')
            disk_usage['container'] = {
                'total': container_usage.total,
                'used': container_usage.used,
                'free': container_usage.free,
                'percent': (container_usage.used / container_usage.total) * 100
            }
        except Exception:
            pass
        
        # Host disk usage
        host_root = Path(self.host_paths['root'])
        if host_root.exists():
            try:
                host_usage = psutil.disk_usage(str(host_root))
                disk_usage['host'] = {
                    'total': host_usage.total,
                    'used': host_usage.used,
                    'free': host_usage.free,
                    'percent': (host_usage.used / host_usage.total) * 100
                }
            except Exception:
                pass
        
        return disk_usage
    
    def _collect_docker_info(self) -> Optional[List[Dict[str, Any]]]:
        """Collect Docker container information if available."""
        if not self._docker_available:
            return None
        
        try:
            # Simple container count and basic info
            # In a real implementation, you might use docker-py library
            # For now, we'll get basic process info
            
            # This is a simplified approach - in production you'd want proper Docker API integration
            docker_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] in ['docker', 'containerd', 'runc']:
                        docker_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(proc.info['cmdline'][:5]) if proc.info['cmdline'] else ''
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return docker_processes if docker_processes else None
        except Exception:
            return None
    
    def _collect_host_filesystem_info(self) -> Optional[Dict[str, Any]]:
        """Collect host filesystem information."""
        try:
            host_root = Path(self.host_paths['root'])
            if not host_root.exists():
                return None
            
            filesystem_info = {
                'mounted_paths': list(self.host_paths.keys()),
                'accessible_paths': []
            }
            
            # Check which paths are accessible
            for name, path in self.host_paths.items():
                try:
                    if Path(path).exists():
                        filesystem_info['accessible_paths'].append(name)
                except PermissionError:
                    pass
            
            return filesystem_info
        except Exception:
            return None
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as dictionary for JSON serialization."""
        metrics = self.collect_metrics()
        return asdict(metrics)
    
    def get_system_info_dict(self) -> Dict[str, Any]:
        """Get system info as dictionary for JSON serialization."""
        info = self.get_system_info()
        return asdict(info)
    
    def collect_all(self) -> Dict[str, Any]:
        """Collect all available metrics and info."""
        metrics = self.collect_metrics()
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DEBUG] DockerMetricsCollector - CPU: {metrics.cpu_percent}, Memory %: {metrics.memory_percent}")
        logger.info(f"[DEBUG] DockerMetricsCollector - Memory used: {metrics.memory_used}, available: {metrics.memory_available}")
        logger.info(f"[DEBUG] DockerMetricsCollector - Uptime: {metrics.uptime_seconds}, Load avg: {metrics.cpu_load_avg}")
        
        # Convert to dictionary manually to handle datetime serialization
        data = {
            "agent_name": self.config.agent_name,
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "timestamp": metrics.timestamp.isoformat(),
                "cpu_percent": metrics.cpu_percent,
                "cpu_load_avg": metrics.cpu_load_avg,
                "memory_percent": metrics.memory_percent,
                "memory_used": metrics.memory_used,
                "memory_available": metrics.memory_available,
                "disk_usage": metrics.disk_usage,
                "network_io": metrics.network_io,
                "disk_io": metrics.disk_io,
                "process_count": metrics.process_count,
                "uptime_seconds": metrics.uptime_seconds,
                "docker_containers": metrics.docker_containers,
                "host_filesystem": metrics.host_filesystem
            }
        }
        
        if hasattr(self.config, 'collect_system_info') and self.config.collect_system_info:
            data["system_info"] = self.get_system_info_dict()
        
        return data
    
    def _get_host_memory_info(self) -> Dict[str, int]:
        """Get host memory information from /host/proc/meminfo."""
        try:
            meminfo_path = Path(self.host_paths['proc']) / 'meminfo'
            if not meminfo_path.exists():
                # Fallback to container memory
                memory = psutil.virtual_memory()
                return {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent
                }
            
            memory_data = {}
            with open(meminfo_path, 'r') as f:
                for line in f:
                    if line.startswith(('MemTotal:', 'MemAvailable:', 'MemFree:')):
                        key, value = line.split()[:2]
                        # Convert from kB to bytes
                        memory_data[key[:-1]] = int(value) * 1024
            
            # Calculate used and available memory
            total = memory_data.get('MemTotal', 0)
            available = memory_data.get('MemAvailable', memory_data.get('MemFree', 0))
            used = total - available
            percent = (used / total * 100) if total > 0 else 0
            
            return {
                'total': total,
                'available': available,
                'used': used,
                'percent': round(percent, 1)
            }
        except (FileNotFoundError, ValueError, PermissionError):
            # Fallback to container memory
            memory = psutil.virtual_memory()
            return {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percent': memory.percent
            }
    
    def _get_host_load_avg(self) -> Optional[List[float]]:
        """Get host load average from /host/proc/loadavg."""
        try:
            loadavg_path = Path(self.host_paths['proc']) / 'loadavg'
            if loadavg_path.exists():
                with open(loadavg_path, 'r') as f:
                    values = f.read().strip().split()[:3]
                    return [float(v) for v in values]
        except (FileNotFoundError, ValueError, PermissionError):
            pass
        
        # Fallback to container load average
        if hasattr(os, 'getloadavg'):
            try:
                return list(os.getloadavg())
            except OSError:
                pass
        return None
    
    def _get_host_cpu_percent(self) -> float:
        """Get host CPU usage from /host/proc/stat."""
        try:
            stat_path = Path(self.host_paths['proc']) / 'stat'
            if not stat_path.exists():
                return psutil.cpu_percent(interval=1)
            
            # Read CPU stats twice with a small interval
            def read_cpu_stats():
                with open(stat_path, 'r') as f:
                    line = f.readline()
                    if line.startswith('cpu '):
                        return [int(x) for x in line.split()[1:8]]
                return None
            
            stats1 = read_cpu_stats()
            if not stats1:
                return psutil.cpu_percent(interval=1)
            
            time.sleep(0.1)  # Small interval
            stats2 = read_cpu_stats()
            if not stats2:
                return psutil.cpu_percent(interval=1)
            
            # Calculate CPU usage percentage
            total1 = sum(stats1)
            total2 = sum(stats2)
            idle1 = stats1[3]  # idle time
            idle2 = stats2[3]
            
            total_diff = total2 - total1
            idle_diff = idle2 - idle1
            
            if total_diff > 0:
                cpu_percent = ((total_diff - idle_diff) / total_diff) * 100
                return round(max(0, min(100, cpu_percent)), 1)
                
        except (FileNotFoundError, ValueError, PermissionError, IndexError):
            pass
        
        # Fallback to container CPU
        return psutil.cpu_percent(interval=1)
    
    def _get_host_process_count(self) -> int:
        """Get host process count from /host/proc."""
        try:
            proc_path = Path(self.host_paths['proc'])
            if proc_path.exists():
                # Count numeric directories in /proc (each represents a process)
                count = 0
                for item in proc_path.iterdir():
                    if item.is_dir() and item.name.isdigit():
                        count += 1
                return count
        except (FileNotFoundError, PermissionError):
            pass
        
        # Fallback to container process count
        return len(psutil.pids())
    
    def _get_host_uptime(self) -> int:
        """Get host uptime from /host/proc/uptime."""
        try:
            uptime_path = Path(self.host_paths['proc']) / 'uptime'
            if uptime_path.exists():
                with open(uptime_path, 'r') as f:
                    uptime_seconds = float(f.read().split()[0])
                    return int(uptime_seconds)
        except (FileNotFoundError, ValueError, PermissionError):
            pass
        
        # Fallback to container uptime
        return int(time.time() - psutil.boot_time())