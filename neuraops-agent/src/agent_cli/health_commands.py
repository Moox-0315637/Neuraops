# src/agent_cli/health_commands.py
"""
Agent-side Health Commands

Health monitoring sur l'hôte agent
Collecte des informations système locales (disque, CPU, mémoire, réseau)
"""
import psutil
import platform
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging


class AgentHealthCommands:
    """
    Health monitoring commands that execute on agent host
    
    Single responsibility pour monitoring local
    """
    
    def __init__(self):
        """Initialize health commands"""
        self.logger = logging.getLogger(__name__)
    
    def check_disk_status(self, all_filesystems: bool = False) -> Dict[str, Any]:
        """
        Get disk usage and I/O statistics from agent host
        
        Args:
            all_filesystems: Include special filesystems
            
        Returns:
            Dictionary with disk usage and I/O statistics
        """
        try:
            result = {
                "timestamp": datetime.now().isoformat(),
                "hostname": platform.node(),
                "disk_usage": [],
                "disk_io": {}
            }
            
            # Get disk partitions
            partitions = psutil.disk_partitions(all=all_filesystems)
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    partition_info = {
                        "mountpoint": partition.mountpoint,
                        "device": partition.device,
                        "fstype": partition.fstype,
                        "total_bytes": usage.total,
                        "used_bytes": usage.used,
                        "free_bytes": usage.free,
                        "percent_used": usage.percent
                    }
                    result["disk_usage"].append(partition_info)
                    
                except OSError:
                    # Handles PermissionError, FileNotFoundError and other OS errors
                    continue
            
            # Get disk I/O statistics
            try:
                io_stats = psutil.disk_io_counters(perdisk=True)
                if io_stats:
                    for disk, stats in io_stats.items():
                        result["disk_io"][disk] = {
                            "read_count": stats.read_count,
                            "write_count": stats.write_count,
                            "read_bytes": stats.read_bytes,
                            "write_bytes": stats.write_bytes,
                            "read_time": stats.read_time,
                            "write_time": stats.write_time
                        }
            except Exception as e:
                self.logger.warning(f"Could not get disk I/O stats: {e}")
                result["disk_io"] = {}
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking disk status: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def check_cpu_memory(self) -> Dict[str, Any]:
        """
        Get CPU and memory information from agent host
        
        Returns:
            Dictionary with CPU and memory statistics
        """
        try:
            result = {
                "timestamp": datetime.now().isoformat(),
                "hostname": platform.node(),
                "cpu": {},
                "memory": {},
                "swap": {}
            }
            
            # CPU Information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_count_physical = psutil.cpu_count(logical=False)
            cpu_freq = psutil.cpu_freq()
            
            result["cpu"] = {
                "percent_used": cpu_percent,
                "count_logical": cpu_count_logical,
                "count_physical": cpu_count_physical,
                "frequency_current": cpu_freq.current if cpu_freq else None,
                "frequency_min": cpu_freq.min if cpu_freq else None,
                "frequency_max": cpu_freq.max if cpu_freq else None,
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
            }
            
            # Memory Information
            memory = psutil.virtual_memory()
            result["memory"] = {
                "total_bytes": memory.total,
                "available_bytes": memory.available,
                "used_bytes": memory.used,
                "free_bytes": memory.free,
                "percent_used": memory.percent,
                "cached_bytes": getattr(memory, 'cached', 0),
                "buffers_bytes": getattr(memory, 'buffers', 0)
            }
            
            # Swap Information
            swap = psutil.swap_memory()
            result["swap"] = {
                "total_bytes": swap.total,
                "used_bytes": swap.used,
                "free_bytes": swap.free,
                "percent_used": swap.percent,
                "sin_bytes": swap.sin,
                "sout_bytes": swap.sout
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking CPU/memory: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def check_network_status(self) -> Dict[str, Any]:
        """
        Get network interfaces and statistics from agent host
        
        Returns:
            Dictionary with network information
        """
        try:
            result = self._init_network_result()
            result["interfaces"] = self._get_network_interfaces()
            result["io_stats"] = self._get_network_io_stats()
            result["connections"] = self._get_active_connections()
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking network status: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def _init_network_result(self) -> Dict[str, Any]:
        """Initialize base result structure for network status"""
        return {
            "timestamp": datetime.now().isoformat(),
            "hostname": platform.node(),
            "interfaces": [],
            "connections": [],
            "io_stats": {}
        }
    
    def _get_network_interfaces(self) -> List[Dict[str, Any]]:
        """Get network interfaces and their statistics"""
        interfaces_list = []
        
        try:
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for interface, addresses in interfaces.items():
                if_info = self._build_interface_info(interface, addresses, stats)
                interfaces_list.append(if_info)
                
        except Exception as e:
            self.logger.warning(f"Could not get network interfaces: {e}")
            
        return interfaces_list
    
    def _build_interface_info(self, interface: str, addresses: List, stats: Dict) -> Dict[str, Any]:
        """Build interface information dictionary"""
        if_info = {
            "name": interface,
            "addresses": [],
            "stats": {}
        }
        
        # Process addresses
        for addr in addresses:
            addr_info = self._format_address_info(addr)
            if_info["addresses"].append(addr_info)
        
        # Add interface statistics
        if interface in stats:
            if_info["stats"] = self._format_interface_stats(stats[interface])
        
        return if_info
    
    def _format_address_info(self, addr) -> Dict[str, Any]:
        """Format network address information"""
        return {
            "family": addr.family.name if hasattr(addr.family, 'name') else str(addr.family),
            "address": addr.address,
            "netmask": addr.netmask,
            "broadcast": addr.broadcast
        }
    
    def _format_interface_stats(self, stat) -> Dict[str, Any]:
        """Format interface statistics"""
        return {
            "is_up": stat.isup,
            "duplex": stat.duplex.name if hasattr(stat.duplex, 'name') else str(stat.duplex),
            "speed_mbps": stat.speed,
            "mtu": stat.mtu
        }
    
    def _get_network_io_stats(self) -> Dict[str, Any]:
        """Get network I/O statistics per interface"""
        io_stats = {}
        
        try:
            net_io = psutil.net_io_counters(pernic=True)
            if net_io:
                for interface, stats in net_io.items():
                    io_stats[interface] = {
                        "bytes_sent": stats.bytes_sent,
                        "bytes_recv": stats.bytes_recv,
                        "packets_sent": stats.packets_sent,
                        "packets_recv": stats.packets_recv,
                        "errin": stats.errin,
                        "errout": stats.errout,
                        "dropin": stats.dropin,
                        "dropout": stats.dropout
                    }
        except Exception as e:
            self.logger.warning(f"Could not get network I/O stats: {e}")
            
        return io_stats
    
    def _get_active_connections(self) -> List[Dict[str, Any]]:
        """Get active network connections (limited to 50)"""
        connections_list = []
        
        try:
            connections = psutil.net_connections(kind='inet')[:50]
            for conn in connections:
                conn_info = self._format_connection_info(conn)
                connections_list.append(conn_info)
                
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            # May not have permissions to see all connections
            self.logger.debug("Access denied for network connections")
            
        return connections_list
    
    def _format_connection_info(self, conn) -> Dict[str, Any]:
        """Format connection information"""
        return {
            "family": conn.family.name if hasattr(conn.family, 'name') else str(conn.family),
            "type": conn.type.name if hasattr(conn.type, 'name') else str(conn.type),
            "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
            "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
            "status": conn.status,
            "pid": conn.pid
        }
    
    def list_processes(self, limit: int = 20, sort_by: str = "cpu") -> Dict[str, Any]:
        """
        Get running processes from agent host
        
        Args:
            limit: Maximum number of processes to return
            sort_by: Sort criteria ("cpu", "memory", "name")
            
        Returns:
            Dictionary with process information
        """
        try:
            result = {
                "timestamp": datetime.now().isoformat(),
                "hostname": platform.node(),
                "processes": [],
                "total_processes": 0
            }
            
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    proc_info = proc.info
                    proc_info['create_time'] = proc.create_time()
                    processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Skip processes that disappear or are inaccessible
                    continue
            
            result["total_processes"] = len(processes)
            
            # Sort processes
            if sort_by == "cpu":
                processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            elif sort_by == "memory":
                processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
            elif sort_by == "name":
                processes.sort(key=lambda x: x.get('name', '').lower())
            
            # Limit results
            result["processes"] = processes[:limit]
            
            return result
            
        except (KeyError, ValueError, TypeError, AttributeError) as e:
            # Catch specific non-psutil exceptions
            self.logger.error(f"Error listing processes: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def monitor_system(self, duration_seconds: int = 10, interval_seconds: int = 1) -> Dict[str, Any]:
        """
        Monitor system resources for a period
        
        Args:
            duration_seconds: How long to monitor
            interval_seconds: Sampling interval
            
        Returns:
            Dictionary with monitoring data
        """
        try:
            result = {
                "start_time": datetime.now().isoformat(),
                "hostname": platform.node(),
                "samples": [],
                "summary": {}
            }
            
            samples = []
            end_time = time.time() + duration_seconds
            
            while time.time() < end_time:
                sample = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "swap_percent": psutil.swap_memory().percent if psutil.swap_memory().total > 0 else 0
                }
                samples.append(sample)
                time.sleep(interval_seconds)
            
            result["samples"] = samples
            result["end_time"] = datetime.now().isoformat()
            
            # Calculate summary statistics
            if samples:
                cpu_values = [s["cpu_percent"] for s in samples]
                memory_values = [s["memory_percent"] for s in samples]
                
                result["summary"] = {
                    "cpu_avg": sum(cpu_values) / len(cpu_values),
                    "cpu_max": max(cpu_values),
                    "cpu_min": min(cpu_values),
                    "memory_avg": sum(memory_values) / len(memory_values),
                    "memory_max": max(memory_values),
                    "memory_min": min(memory_values),
                    "sample_count": len(samples)
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error monitoring system: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}