# src/api/services/command_format_service.py
"""
Command Format Service

CLAUDE.md: < 500 lignes, formatage sorties commandes pour CLI
Transforme les données brutes agent en sortie CLI formatée
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging


class CommandFormatService:
    """
    Format command outputs for CLI display
    
    CLAUDE.md: Single responsibility pour formatage CLI
    """
    
    def __init__(self):
        """Initialize command format service"""
        self.logger = logging.getLogger(__name__)

    def _create_section_header(self, title: str) -> List[str]:
        """Create standardized section header with box borders"""
        return [
            self.BOX_TOP_BORDER,
            self.BOX_HEADER_SEPARATOR.format(title=title),
            self.BOX_BOTTOM_BORDER
        ]
    
    def _handle_format_error(self, error_msg: str, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle formatting errors uniformly"""
        return {
            "stdout": f"{error_msg}\n",
            "stderr": "",
            "return_code": raw_result.get("return_code", 1)
        }
    
    def format_command_output(
        self, 
        command: str, 
        subcommand: Optional[str],
        raw_result: Dict[str, Any], 
        format_type: str = "cli"
    ) -> Dict[str, Any]:
        """
        Format command output for CLI display
        
        Args:
            command: Main command (e.g., 'health')
            subcommand: Subcommand (e.g., 'disk')
            raw_result: Raw result from agent or core
            format_type: Output format ("cli", "json", "table")
            
        Returns:
            Formatted output ready for CLI display
        """
        try:
            # Extract agent data if available
            agent_data = raw_result.get("agent_data", raw_result)
            
            if format_type == "json":
                return {
                    "stdout": json.dumps(agent_data, indent=2) + "\n",
                    "stderr": "",
                    "return_code": raw_result.get("return_code", 0)
                }
            
            # Route to specific formatter
            command_key = f"{command}.{subcommand}" if subcommand else command
            formatter_func = self._get_formatter(command_key)
            
            if formatter_func:
                return formatter_func(agent_data, raw_result)
            else:
                # Generic formatting
                return self._format_generic(agent_data, raw_result)
        
        except Exception as e:
            self.logger.error(f"Error formatting command output: {e}")
            return {
                "stdout": f"Error formatting output: {e}\n",
                "stderr": "",
                "return_code": 1
            }
    
    def _get_formatter(self, command_key: str):
        """Get specific formatter function for command"""
        formatters = {
            # Health commands
            "health.disk": self._format_disk_status,
            "health.check-disk-status": self._format_disk_status,
            "health.cpu-memory": self._format_cpu_memory,
            "health.check-cpu-memory": self._format_cpu_memory,
            "health.network": self._format_network_status,
            "health.check-network": self._format_network_status,
            "health.processes": self._format_processes,
            "health.list-processes": self._format_processes,
            "health.monitor": self._format_monitor_results,
            "health.system-health": self._format_system_health,
            
            # System commands
            "system.info": self._format_system_info,
            "system.system-info": self._format_system_info,
            "system.get-system-info": self._format_system_info,
            "system.environment": self._format_environment,
            "system.show-environment": self._format_environment,
        }
        
        return formatters.get(command_key)
    
    def _format_disk_usage_table(self, disk_usage_data: List[Dict[str, Any]]) -> List[str]:
        """Format disk usage data into table format"""
        if not disk_usage_data:
            return []
            
        output_lines = []
        output_lines.append("                                   Disk Usage                                   ")
        output_lines.append("┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┓")
        output_lines.append("┃ Mount Point ┃ Device      ┃ Filesystem ┃   Total ┃    Used ┃    Free ┃ Usage ┃")
        output_lines.append("┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━┩")
        
        for disk in disk_usage_data:
            mount_point = disk["mountpoint"][:12] + "…" if len(disk["mountpoint"]) > 12 else disk["mountpoint"]
            device = disk["device"][:12] + "…" if len(disk["device"]) > 12 else disk["device"]
            fstype = disk["fstype"][:10] if disk["fstype"] else "unknown"
            total_gb = f"{disk['total_bytes'] / (1024**3):.1f} GB"
            used_gb = f"{disk['used_bytes'] / (1024**3):.1f} GB"
            free_gb = f"{disk['free_bytes'] / (1024**3):.1f} GB"
            usage_percent = f"{disk['percent_used']:.1f}%"
            
            output_lines.append(f"│ {mount_point:<11} │ {device:<11} │ {fstype:<10} │ {total_gb:>7} │ {used_gb:>7} │ {free_gb:>7} │ {usage_percent:>5} │")
        
        output_lines.append("└─────────────┴─────────────┴────────────┴─────────┴─────────┴─────────┴───────┘")
        return output_lines

    def _format_disk_io_table(self, disk_io_data: Dict[str, Dict[str, Any]]) -> List[str]:
        """Format disk I/O data into table format"""
        if not disk_io_data:
            return []
            
        output_lines = []
        output_lines.append("                        Disk I/O Statistics                        ")
        output_lines.append("┏━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓")
        output_lines.append("┃ Disk      ┃ Read Count ┃ Write Count ┃ Read Bytes ┃ Write Bytes ┃")
        output_lines.append("┡━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩")
        
        for disk, stats in disk_io_data.items():
            disk_name = disk[:9] if disk else "unknown"
            read_count = f"{stats['read_count']:,}"[:11]
            write_count = f"{stats['write_count']:,}"[:12]
            read_gb = f"{stats['read_bytes'] / (1024**3):.2f} GB"
            write_gb = f"{stats['write_bytes'] / (1024**3):.2f} GB"
            
            output_lines.append(f"│ {disk_name:<9} │ {read_count:>10} │ {write_count:>11} │ {read_gb:>10} │ {write_gb:>11} │")
        
        output_lines.append("└───────────┴────────────┴─────────────┴────────────┴─────────────┘")
        return output_lines

    def _format_disk_status(self, data: Dict[str, Any], raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format disk status data for Rich CLI display"""
        if "error" in data:
            return self._handle_format_error(f"Error checking disk status: {data['error']}", raw_result)
        
        # Create header
        output_lines = self._create_section_header("Disk Status Check")
        
        # Add disk usage table if available
        if "disk_usage" in data and data["disk_usage"]:
            output_lines.extend(self._format_disk_usage_table(data["disk_usage"]))
        
        # Add disk I/O table if available
        if "disk_io" in data and data["disk_io"]:
            output_lines.extend(self._format_disk_io_table(data["disk_io"]))
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "return_code": raw_result.get("return_code", 0)
        }
    
    def _format_cpu_memory(self, data: Dict[str, Any], raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format CPU and memory data"""
        if "error" in data:
            return self._handle_format_error(f"Error checking CPU/memory: {data['error']}", raw_result)
        
        # Create header
        output_lines = self._create_section_header("CPU & Memory Status")
        
        # CPU Information
        if "cpu" in data:
            cpu = data["cpu"]
            output_lines.append("")
            output_lines.append("CPU Information:")
            output_lines.append(f"  Usage: {cpu.get('percent_used', 0):.1f}%")
            output_lines.append(f"  Cores: {cpu.get('count_physical', 'N/A')} physical, {cpu.get('count_logical', 'N/A')} logical")
            if cpu.get('frequency_current'):
                output_lines.append(f"  Frequency: {cpu['frequency_current']:.0f} MHz")
        
        # Memory Information
        if "memory" in data:
            memory = data["memory"]
            total_gb = memory.get('total_bytes', 0) / (1024**3)
            used_gb = memory.get('used_bytes', 0) / (1024**3)
            free_gb = memory.get('free_bytes', 0) / (1024**3)
            
            output_lines.append("")
            output_lines.append("Memory Information:")
            output_lines.append(f"  Total: {total_gb:.1f} GB")
            output_lines.append(f"  Used: {used_gb:.1f} GB ({memory.get('percent_used', 0):.1f}%)")
            output_lines.append(f"  Free: {free_gb:.1f} GB")
        
        # Swap Information
        if "swap" in data and data["swap"].get("total_bytes", 0) > 0:
            swap = data["swap"]
            total_gb = swap.get('total_bytes', 0) / (1024**3)
            used_gb = swap.get('used_bytes', 0) / (1024**3)
            
            output_lines.append("")
            output_lines.append("Swap Information:")
            output_lines.append(f"  Total: {total_gb:.1f} GB")
            output_lines.append(f"  Used: {used_gb:.1f} GB ({swap.get('percent_used', 0):.1f}%)")
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "return_code": raw_result.get("return_code", 0)
        }
    
    def _get_interface_status(self, interface: Dict[str, Any]) -> tuple:
        """Extract interface status and first valid address"""
        name = interface["name"]
        is_up = interface.get("stats", {}).get("is_up", False)
        status = "UP" if is_up else "DOWN"
        
        # Find first valid address
        if "addresses" in interface:
            for addr in interface["addresses"][:3]:  # Max 3 addresses
                if addr.get("address") and addr["address"] != "00:00:00:00:00:00":
                    return name, status, addr["address"]
        
        return name, status, "No valid address"

    def _format_network_interfaces(self, interfaces_data: List[Dict[str, Any]]) -> List[str]:
        """Format network interfaces data"""
        if not interfaces_data:
            return []
            
        output_lines = ["", "Network Interfaces:"]
        
        for interface in interfaces_data[:10]:  # Limit to 10 interfaces
            name, status, address = self._get_interface_status(interface)
            output_lines.append(f"  {name}: {status}")
            output_lines.append(f"    {address}")
        
        return output_lines

    def _format_network_status(self, data: Dict[str, Any], raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format network status data"""
        if "error" in data:
            return self._handle_format_error(f"Error checking network: {data['error']}", raw_result)
        
        # Create header
        output_lines = self._create_section_header("Network Status")
        
        # Add network interfaces if available
        if "interfaces" in data:
            output_lines.extend(self._format_network_interfaces(data["interfaces"]))
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "return_code": raw_result.get("return_code", 0)
        }
    
    def _format_processes(self, data: Dict[str, Any], raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format processes data"""
        if "error" in data:
            return self._handle_format_error(f"Error checking processes: {data['error']}", raw_result)
        
        # Create header
        output_lines = self._create_section_header("System Processes")
        
        if "processes" in data and data["processes"]:
            output_lines.append("")
            output_lines.append("Top Processes by CPU Usage:")
            output_lines.append("┏━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
            output_lines.append("┃  PID  ┃ Process Name & CPU Usage                                     ┃")
            output_lines.append("┡━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩")
            
            # Show top 10 processes by CPU
            for process in data["processes"][:10]:
                pid = process.get("pid", "N/A")
                name = process.get("name", "Unknown")[:40]
                cpu = process.get("cpu_percent", 0.0)
                memory = process.get("memory_percent", 0.0)
                
                info = f"{name} (CPU: {cpu:.1f}%, Memory: {memory:.1f}%)"
                output_lines.append(f"│ {pid:>5} │ {info:<60} │")
            
            output_lines.append("└───────┴──────────────────────────────────────────────────────────────┘")
            
            total_processes = len(data["processes"])
            output_lines.append("")
            output_lines.append(f"Total Processes: {total_processes}")
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "return_code": raw_result.get("return_code", 0)
        }
    
    def _format_monitor_results(self, data: Dict[str, Any], raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format monitor results data"""
        if "error" in data:
            return self._handle_format_error(f"Error in monitoring: {data['error']}", raw_result)
        
        # Create header
        output_lines = self._create_section_header("System Monitor")
        
        if "summary" in data:
            summary = data["summary"]
            output_lines.append("")
            output_lines.append("System Summary:")
            output_lines.append(f"  CPU Usage: {summary.get('cpu_percent', 0):.1f}%")
            output_lines.append(f"  Memory Usage: {summary.get('memory_percent', 0):.1f}%")
            output_lines.append(f"  Disk Usage: {summary.get('disk_percent', 0):.1f}%")
            
            if "alerts" in summary:
                output_lines.append("")
                output_lines.append("Alerts:")
                for alert in summary["alerts"]:
                    output_lines.append(f"  - {alert}")
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "return_code": raw_result.get("return_code", 0)
        }
    
    def _format_system_health(self, data: Dict[str, Any], raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format system health data"""
        if "error" in data:
            return self._handle_format_error(f"Error checking system health: {data['error']}", raw_result)
        
        # Create header
        output_lines = self._create_section_header("System Health Check")
        
        if "status" in data:
            status = data["status"]
            output_lines.append("")
            output_lines.append(f"Overall Status: {status}")
        
        if "checks" in data:
            output_lines.append("")
            output_lines.append("Health Checks:")
            for check in data["checks"]:
                status_icon = "✅" if check.get("status") == "OK" else "❌"
                output_lines.append(f"  {status_icon} {check.get('name', 'Unknown')}: {check.get('message', 'No details')}")
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "return_code": raw_result.get("return_code", 0)
        }
    
    def _format_system_info(self, data: Dict[str, Any], raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format system info data"""
        if "error" in data:
            return self._handle_format_error(f"Error getting system info: {data['error']}", raw_result)
        
        # Create header
        output_lines = self._create_section_header("System Information")
        
        if "platform" in data:
            platform = data["platform"]
            output_lines.append("")
            output_lines.append("Platform Information:")
            output_lines.append(f"  System: {platform.get('system', 'Unknown')}")
            output_lines.append(f"  Release: {platform.get('release', 'Unknown')}")
            output_lines.append(f"  Version: {platform.get('version', 'Unknown')}")
            output_lines.append(f"  Machine: {platform.get('machine', 'Unknown')}")
            output_lines.append(f"  Processor: {platform.get('processor', 'Unknown')}")
        
        if "uptime" in data:
            uptime_seconds = data["uptime"]
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            output_lines.append("")
            output_lines.append(f"Uptime: {hours}h {minutes}m")
        
        if "users" in data:
            output_lines.append("")
            output_lines.append(f"Active Users: {len(data['users'])}")
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "return_code": raw_result.get("return_code", 0)
        }
    
    def _format_environment(self, data: Dict[str, Any], raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format environment data"""
        if "error" in data:
            return self._handle_format_error(f"Error getting environment: {data['error']}", raw_result)
        
        # Create header
        output_lines = self._create_section_header("Environment Variables")
        
        if "variables" in data and isinstance(data["variables"], dict):
            output_lines.append("")
            output_lines.append("Key Environment Variables:")
            
            # Show important environment variables
            important_vars = ["PATH", "HOME", "USER", "SHELL", "LANG", "PWD"]
            for var in important_vars:
                if var in data["variables"]:
                    value = data["variables"][var]
                    # Truncate long values
                    if len(value) > 60:
                        value = value[:57] + "..."
                    output_lines.append(f"  {var}: {value}")
            
            # Show count of all variables
            total_vars = len(data["variables"])
            output_lines.append("")
            output_lines.append(f"Total Variables: {total_vars}")
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "return_code": raw_result.get("return_code", 0)
        }
    
    def _format_generic(self, data: Dict[str, Any], raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format generic data as JSON"""
        return {
            "stdout": json.dumps(data, indent=2) + "\n",
            "stderr": "",
            "return_code": raw_result.get("return_code", 0)
        }

    
    # Constants for eliminating duplicated strings (SonarQube S1192)
    BOX_TOP_BORDER = "╭──────────────────────────────────────────────────────────────────────────────╮"
    BOX_BOTTOM_BORDER = "╰──────────────────────────────────────────────────────────────────────────────╯"
    BOX_HEADER_SEPARATOR = "│ {title:<76} │"


# Global service instance
_format_service_instance: Optional[CommandFormatService] = None


def get_command_format_service() -> CommandFormatService:
    """Get singleton command format service instance"""
    global _format_service_instance
    if _format_service_instance is None:
        _format_service_instance = CommandFormatService()
    return _format_service_instance