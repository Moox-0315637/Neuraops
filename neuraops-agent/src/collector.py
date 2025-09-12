"""System metrics collector for NeuraOps Agent."""

import platform
import socket
import os
import psutil
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .config import AgentConfig


@dataclass
class SystemInfo:
    """Static system information."""
    hostname: str
    os_name: str
    os_version: str
    architecture: str
    cpu_count: int
    cpu_model: str
    memory_total: int
    boot_time: datetime


@dataclass
class MetricsSnapshot:
    """Real-time metrics snapshot."""
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


class MetricsCollector:
    """Collects system metrics and filesystem information."""
    
    def __init__(self, config: AgentConfig):
        """Initialize collector with configuration."""
        self.config = config
        self._system_info: Optional[SystemInfo] = None
        
        # Cache for expensive operations
        self._last_disk_check = 0
        self._disk_cache: Dict[str, Any] = {}
    
    def get_system_info(self) -> SystemInfo:
        """Get static system information (cached)."""
        if self._system_info is None:
            self._system_info = self._collect_system_info()
        return self._system_info
    
    def _collect_system_info(self) -> SystemInfo:
        """Collect static system information."""
        # CPU info
        cpu_model = "Unknown"
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        cpu_model = line.split(":")[1].strip()
                        break
        except (FileNotFoundError, IndexError):
            pass
        
        return SystemInfo(
            hostname=socket.gethostname(),
            os_name=platform.system(),
            os_version=platform.release(),
            architecture=platform.machine(),
            cpu_count=psutil.cpu_count(logical=True),
            cpu_model=cpu_model,
            memory_total=psutil.virtual_memory().total,
            boot_time=datetime.fromtimestamp(psutil.boot_time())
        )
    
    def collect_metrics(self) -> MetricsSnapshot:
        """Collect current system metrics."""
        memory = psutil.virtual_memory()
        
        # CPU load average (Unix only)
        load_avg = None
        if hasattr(os, 'getloadavg'):
            load_avg = list(os.getloadavg())
        
        # Disk I/O
        disk_io = {}
        try:
            io_counters = psutil.disk_io_counters()
            if io_counters:
                disk_io = {
                    "read_bytes": io_counters.read_bytes,
                    "write_bytes": io_counters.write_bytes,
                    "read_count": io_counters.read_count,
                    "write_count": io_counters.write_count
                }
        except Exception:
            pass
        
        # Network I/O
        network_io = {}
        try:
            net_counters = psutil.net_io_counters()
            if net_counters:
                network_io = {
                    "bytes_sent": net_counters.bytes_sent,
                    "bytes_recv": net_counters.bytes_recv,
                    "packets_sent": net_counters.packets_sent,
                    "packets_recv": net_counters.packets_recv
                }
        except Exception:
            pass
        
        # Uptime
        uptime = time.time() - psutil.boot_time()
        
        return MetricsSnapshot(
            timestamp=datetime.now(),
            cpu_percent=psutil.cpu_percent(interval=0.1),
            cpu_load_avg=load_avg,
            memory_percent=memory.percent,
            memory_used=memory.used,
            memory_available=memory.available,
            disk_usage=self._get_disk_usage(),
            network_io=network_io,
            disk_io=disk_io,
            process_count=len(psutil.pids()),
            uptime_seconds=int(uptime)
        )
    
    def _get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage with caching to avoid frequent I/O."""
        now = time.time()
        
        # Cache disk info for 30 seconds
        if now - self._last_disk_check < 30 and self._disk_cache:
            return self._disk_cache
        
        disk_usage = {}
        
        try:
            # Get disk usage for root filesystem
            root_usage = psutil.disk_usage("/")
            disk_usage["/"] = {
                "total": root_usage.total,
                "used": root_usage.used,
                "free": root_usage.free,
                "percent": root_usage.percent
            }
            
            # Get usage for other significant mount points
            for partition in psutil.disk_partitions():
                if partition.mountpoint == "/":
                    continue
                
                # Skip virtual filesystems
                if partition.fstype in ("tmpfs", "devtmpfs", "sysfs", "proc"):
                    continue
                
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent,
                        "fstype": partition.fstype
                    }
                except OSError:  # PermissionError is subclass of OSError
                    # Skip inaccessible mount points
                    continue
        
        except Exception as e:
            disk_usage = {"error": str(e)}
        
        self._disk_cache = disk_usage
        self._last_disk_check = now
        
        return disk_usage
    
    def collect_filesystem(self) -> List[Dict[str, Any]]:
        """Collect detailed filesystem information."""
        if not self.config.collect_filesystem:
            return []
        
        filesystems = []
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                filesystem = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "opts": partition.opts,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                }
                
                filesystems.append(filesystem)
                
            except OSError:  # PermissionError is subclass of OSError
                # Skip inaccessible mount points
                continue
        
        return filesystems
    
    def collect_all(self) -> Dict[str, Any]:
        """Collect all available metrics and info."""
        data = {
            "agent_name": self.config.agent_name,
            "timestamp": datetime.now().isoformat(),
            "metrics": self.collect_metrics(),
        }
        
        if self.config.collect_system_info:
            data["system_info"] = self.get_system_info()
        
        if self.config.collect_filesystem:
            data["filesystem"] = self.collect_filesystem()
        
        return data
    
    def collect_basic(self) -> Dict[str, Any]:
        """Collect basic metrics only (faster)."""
        memory = psutil.virtual_memory()
        
        return {
            "agent_name": self.config.agent_name,
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": memory.percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "uptime": int(time.time() - psutil.boot_time())
        }