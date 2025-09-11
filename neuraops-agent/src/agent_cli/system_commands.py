# src/agent_cli/system_commands.py
"""
Agent-side System Commands

CLAUDE.md: < 500 lignes, system info sur l'hôte agent
Collecte des informations système locales (platform, environment)
"""
import platform
import os
import sys
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging


class AgentSystemCommands:
    """
    System information commands that execute on agent host
    
    CLAUDE.md: Single responsibility pour informations système locales
    """
    
    def __init__(self):
        """Initialize system commands"""
        self.logger = logging.getLogger(__name__)
    
    def get_system_info(self, detailed: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive system information from agent host
        
        Args:
            detailed: Include detailed system information
            
        Returns:
            Dictionary with system information
        """
        try:
            result = {
                "timestamp": datetime.now().isoformat(),
                "platform": {},
                "python": {},
                "system": {},
                "hardware": {}
            }
            
            # Platform information
            result["platform"] = {
                "system": platform.system(),
                "node": platform.node(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "architecture": platform.architecture(),
                "platform": platform.platform()
            }
            
            # Python information
            result["python"] = {
                "version": sys.version,
                "version_info": {
                    "major": sys.version_info.major,
                    "minor": sys.version_info.minor,
                    "micro": sys.version_info.micro,
                    "releaselevel": sys.version_info.releaselevel,
                    "serial": sys.version_info.serial
                },
                "executable": sys.executable,
                "prefix": sys.prefix
            }
            
            # Basic system information
            result["system"] = {
                "hostname": platform.node(),
                "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
                "home": os.environ.get("HOME", os.environ.get("USERPROFILE", "unknown")),
                "shell": os.environ.get("SHELL", "unknown"),
                "path": os.environ.get("PATH", ""),
                "timezone": str(datetime.now().astimezone().tzinfo),
                "uptime": self._get_uptime() if detailed else None
            }
            
            # Hardware information (if detailed)
            if detailed:
                result["hardware"] = self._get_hardware_info()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def show_environment(self, pattern: Optional[str] = None, sensitive: bool = False) -> Dict[str, Any]:
        """
        Get environment variables from agent host
        
        Args:
            pattern: Filter environment variables by pattern
            sensitive: Include potentially sensitive variables
            
        Returns:
            Dictionary with environment information
        """
        try:
            result = {
                "timestamp": datetime.now().isoformat(),
                "hostname": platform.node(),
                "environment_variables": {},
                "filtered_count": 0,
                "total_count": len(os.environ)
            }
            
            # List of sensitive environment variable patterns
            sensitive_patterns = [
                "password", "secret", "key", "token", "auth", "credential",
                "api_key", "private", "cert", "ssl", "tls", "pass"
            ] if not sensitive else []
            
            filtered_env = {}
            filtered_count = 0
            
            for key, value in os.environ.items():
                # Apply pattern filter
                if pattern and pattern.lower() not in key.lower():
                    continue
                
                # Filter sensitive variables
                if not sensitive and any(sensitive_word in key.lower() for sensitive_word in sensitive_patterns):
                    filtered_count += 1
                    filtered_env[key] = "***FILTERED***"
                    continue
                
                # Truncate very long values
                if len(value) > 1000:
                    filtered_env[key] = value[:997] + "..."
                else:
                    filtered_env[key] = value
            
            result["environment_variables"] = filtered_env
            result["filtered_count"] = filtered_count
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error showing environment: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def _get_uptime(self) -> Optional[Dict[str, Any]]:
        """Get system uptime (if available)"""
        try:
            if platform.system() == "Linux":
                with open("/proc/uptime", "r") as f:
                    uptime_seconds = float(f.readline().split()[0])
                    
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                
                return {
                    "total_seconds": uptime_seconds,
                    "days": days,
                    "hours": hours,
                    "minutes": minutes,
                    "formatted": f"{days}d {hours}h {minutes}m"
                }
                
            elif platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ["sysctl", "-n", "kern.boottime"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Parse boottime and calculate uptime
                    # This is a simplified version
                    return {"status": "available_but_not_parsed"}
                    
            elif platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "os", "get", "lastbootuptime", "/value"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return {"status": "available_but_not_parsed"}
            
            return {"status": "not_available"}
            
        except Exception as e:
            self.logger.debug(f"Could not get uptime: {e}")
            return {"status": "error", "error": str(e)}
    
    def _get_hardware_info(self) -> Dict[str, Any]:
        """Get detailed hardware information (if available)"""
        hardware = {
            "cpu": {},
            "memory": {},
            "storage": {},
            "network": {}
        }
        
        try:
            # Try to get CPU info
            if platform.system() == "Linux":
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        cpu_info = f.read()
                        # Parse basic CPU information
                        for line in cpu_info.split('\n'):
                            if line.startswith('model name'):
                                hardware["cpu"]["model"] = line.split(':', 1)[1].strip()
                                break
                except Exception:
                    pass
            
            # Try to get memory info
            try:
                import psutil
                memory = psutil.virtual_memory()
                hardware["memory"] = {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2)
                }
            except ImportError:
                pass
            
        except Exception as e:
            self.logger.debug(f"Could not get detailed hardware info: {e}")
            hardware["error"] = str(e)
        
        return hardware
    
    def get_disk_info(self) -> Dict[str, Any]:
        """Get disk/storage information"""
        try:
            import psutil
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "hostname": platform.node(),
                "disks": []
            }
            
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percent_used": usage.percent
                    }
                    result["disks"].append(disk_info)
                except OSError:
                    # Handles PermissionError, FileNotFoundError and other OS errors
                    continue
            
            return result
            
        except ImportError:
            return {"error": "psutil not available", "timestamp": datetime.now().isoformat()}
        except Exception as e:
            self.logger.error(f"Error getting disk info: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_network_config(self) -> Dict[str, Any]:
        """Get network configuration information"""
        try:
            import psutil
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "hostname": platform.node(),
                "interfaces": []
            }
            
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for interface_name, addresses in interfaces.items():
                interface_info = {
                    "name": interface_name,
                    "addresses": [],
                    "is_up": stats[interface_name].isup if interface_name in stats else False,
                    "speed_mbps": stats[interface_name].speed if interface_name in stats else None
                }
                
                for addr in addresses:
                    addr_info = {
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask
                    }
                    interface_info["addresses"].append(addr_info)
                
                result["interfaces"].append(interface_info)
            
            return result
            
        except ImportError:
            return {"error": "psutil not available", "timestamp": datetime.now().isoformat()}
        except Exception as e:
            self.logger.error(f"Error getting network config: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}