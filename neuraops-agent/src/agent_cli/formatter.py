# src/agent_cli/formatter.py
"""
Agent Output Formatter

CLAUDE.md: < 500 lignes, formatage des sorties CLI agent
Formate les données agent pour affichage CLI via le Core
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json


class AgentOutputFormatter:
    """
    Format agent command outputs for CLI display
    
    CLAUDE.md: Single responsibility pour formatage des sorties agent
    """
    
    # Box drawing constants for consistent UI (SonarQube S1192)
    BOX_TOP = "╭──────────────────────────────────────────────────────────────────────────────╮"
    BOX_BOTTOM = "╰──────────────────────────────────────────────────────────────────────────────╯"
    BOX_SIDE = "│"
    BOX_SEPARATOR = "├──────────────────────────────────────────────────────────────────────────────┤"
    
    def __init__(self):
        """Initialize output formatter"""
        pass
    
    def format_for_cli(self, command: str, subcommand: Optional[str], agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format agent data for CLI display via Core
        
        Args:
            command: Main command (e.g., 'health')
            subcommand: Subcommand (e.g., 'disk')
            agent_data: Raw data from agent
            
        Returns:
            Formatted data for CLI display
        """
        command_key = f"{command}.{subcommand}" if subcommand else command
        
        # Route to specific formatter
        formatters = {
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
            "system.info": self._format_system_info,
            "system.system-info": self._format_system_info,
            "system.get-system-info": self._format_system_info,
            "system.environment": self._format_environment,
            "system.show-environment": self._format_environment,
        }
        
        formatter_func = formatters.get(command_key, self._format_generic)
        return formatter_func(agent_data)
    
    def _format_disk_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format disk status data for Rich CLI display - Complexity reduced"""
        if "error" in data:
            return self._format_error_response(data["error"], "disk status")
        
        output_lines = []
        output_lines.extend(self._build_section_header("Disk Status Check"))
        
        if "disk_usage" in data and data["disk_usage"]:
            output_lines.extend(self._format_disk_usage_table(data["disk_usage"]))
        
        if "disk_io" in data and data["disk_io"]:
            output_lines.extend(self._format_disk_io_table(data["disk_io"]))
        
        return self._build_formatted_response(output_lines)
    
    def _build_section_header(self, title: str) -> List[str]:
        """Build standardized section header with box drawing"""
        return [
            self.BOX_TOP,
            f"{self.BOX_SIDE} {title:<76} {self.BOX_SIDE}",
            self.BOX_BOTTOM
        ]
    
    def _format_error_response(self, error: str, context: str) -> Dict[str, Any]:
        """Format error response consistently"""
        return {
            "stdout": f"Error checking {context}: {error}\n",
            "stderr": "",
            "format_type": "error"
        }
    
    def _build_formatted_response(self, output_lines: List[str]) -> Dict[str, Any]:
        """Build final formatted response"""
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "format_type": "table"
        }
    
    def _format_disk_usage_table(self, disk_usage: List[Dict]) -> List[str]:
        """Format disk usage table with proper alignment"""
        lines = []
        lines.append("                                   Disk Usage                                   ")
        lines.append("┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┓")
        lines.append("┃ Mount Point ┃ Device      ┃ Filesystem ┃   Total ┃    Used ┃    Free ┃ Usage ┃")
        lines.append("┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━┩")
        
        for disk in disk_usage:
            lines.append(self._format_disk_usage_row(disk))
        
        lines.append("└─────────────┴─────────────┴────────────┴─────────┴─────────┴─────────┴───────┘")
        return lines
    
    def _format_disk_usage_row(self, disk: Dict) -> str:
        """Format single disk usage row"""
        mount_point = self._truncate_text(disk["mountpoint"], 12)
        device = self._truncate_text(disk["device"], 12) 
        fstype = disk["fstype"][:10] if disk["fstype"] else "unknown"
        total_gb = f"{disk['total_bytes'] / (1024**3):.1f} GB"
        used_gb = f"{disk['used_bytes'] / (1024**3):.1f} GB"
        free_gb = f"{disk['free_bytes'] / (1024**3):.1f} GB"
        usage_percent = f"{disk['percent_used']:.1f}%"
        
        return f"│ {mount_point:<11} │ {device:<11} │ {fstype:<10} │ {total_gb:>7} │ {used_gb:>7} │ {free_gb:>7} │ {usage_percent:>5} │"
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text with ellipsis if too long"""
        return text[:max_length] + "…" if len(text) > max_length else text
    
    def _format_disk_io_table(self, disk_io: Dict) -> List[str]:
        """Format disk I/O statistics table"""
        lines = []
        lines.append("                        Disk I/O Statistics                        ")
        lines.append("┏━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓")
        lines.append("┃ Disk      ┃ Read Count ┃ Write Count ┃ Read Bytes ┃ Write Bytes ┃")
        lines.append("┡━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩")
        
        for disk, stats in disk_io.items():
            lines.append(self._format_disk_io_row(disk, stats))
        
        lines.append("└───────────┴────────────┴─────────────┴────────────┴─────────────┘")
        return lines
    
    def _format_disk_io_row(self, disk: str, stats: Dict) -> str:
        """Format single disk I/O row"""
        disk_name = disk[:9] if disk else "unknown"
        read_count = f"{stats['read_count']:,}"[:11]
        write_count = f"{stats['write_count']:,}"[:12]
        read_gb = f"{stats['read_bytes'] / (1024**3):.2f} GB"
        write_gb = f"{stats['write_bytes'] / (1024**3):.2f} GB"
        
        return f"│ {disk_name:<9} │ {read_count:>10} │ {write_count:>11} │ {read_gb:>10} │ {write_gb:>11} │"
    
    def _format_cpu_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format CPU and memory data"""
        if "error" in data:
            return {
                "stdout": f"Error checking CPU/memory: {data['error']}\n",
                "stderr": "",
                "format_type": "error"
            }
        
        output_lines = []
        output_lines.append(self.BOX_TOP)
        output_lines.append("│ CPU & Memory Status                                                          │")
        output_lines.append(self.BOX_BOTTOM)
        
        if "cpu" in data:
            cpu = data["cpu"]
            output_lines.append("")
            output_lines.append("CPU Information:")
            output_lines.append(f"  Usage: {cpu.get('percent_used', 0):.1f}%")
            output_lines.append(f"  Cores: {cpu.get('count_physical', 'N/A')} physical, {cpu.get('count_logical', 'N/A')} logical")
            if cpu.get('frequency_current'):
                output_lines.append(f"  Frequency: {cpu['frequency_current']:.0f} MHz")
        
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
            "format_type": "info"
        }
    
    def _format_network_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format network status data"""
        if "error" in data:
            return {
                "stdout": f"Error checking network: {data['error']}\n",
                "stderr": "",
                "format_type": "error"
            }
        
        output_lines = []
        output_lines.append(self.BOX_TOP)
        output_lines.append("│ Network Status                                                               │")
        output_lines.append(self.BOX_BOTTOM)
        
        if "interfaces" in data:
            output_lines.append("")
            output_lines.append("Network Interfaces:")
            
            for interface in data["interfaces"][:10]:  # Limit to 10 interfaces
                name = interface["name"]
                is_up = interface.get("stats", {}).get("is_up", False)
                status = "UP" if is_up else "DOWN"
                
                output_lines.append(f"  {name}: {status}")
                
                for addr in interface["addresses"][:3]:  # Limit to 3 addresses per interface
                    if addr["address"] and addr["address"] != "00:00:00:00:00:00":
                        output_lines.append(f"    {addr['address']}")
        
        return {
            "stdout": "\n".join(output_lines) + "\n", 
            "stderr": "",
            "format_type": "info"
        }
    
    def _format_processes(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format processes data"""
        if "error" in data:
            return {
                "stdout": f"Error listing processes: {data['error']}\n",
                "stderr": "",
                "format_type": "error"
            }
        
        output_lines = []
        output_lines.append(self.BOX_TOP)
        output_lines.append("│ Running Processes                                                            │")
        output_lines.append(self.BOX_BOTTOM)
        
        if "processes" in data:
            output_lines.append("")
            output_lines.append("┏━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓")
            output_lines.append("┃  PID  ┃ Name                           ┃ CPU %   ┃ Memory %  ┃ Status          ┃")
            output_lines.append("┡━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩")
            
            for proc in data["processes"][:15]:  # Limit to 15 processes
                pid = str(proc.get("pid", "N/A"))[:6]
                name = str(proc.get("name", "unknown"))[:30]
                cpu_percent = f"{proc.get('cpu_percent', 0):.1f}"[:7]
                memory_percent = f"{proc.get('memory_percent', 0):.1f}"[:9]
                status = str(proc.get("status", "unknown"))[:15]
                
                output_lines.append(f"│ {pid:>5} │ {name:<30} │ {cpu_percent:>7} │ {memory_percent:>9} │ {status:<15} │")
            
            output_lines.append("└───────┴────────────────────────────────┴─────────┴───────────┴─────────────────┘")
            output_lines.append(f"Total processes: {data.get('total_processes', 0)}")
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "format_type": "table"
        }
    
    def _format_monitor_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format monitoring results"""
        if "error" in data:
            return {
                "stdout": f"Error monitoring system: {data['error']}\n",
                "stderr": "",
                "format_type": "error"
            }
        
        output_lines = []
        output_lines.append(self.BOX_TOP)
        output_lines.append("│ System Monitoring Results                                                    │")
        output_lines.append(self.BOX_BOTTOM)
        
        if "summary" in data:
            summary = data["summary"]
            output_lines.append("")
            output_lines.append("Summary Statistics:")
            output_lines.append(f"  CPU Average: {summary.get('cpu_avg', 0):.1f}% (min: {summary.get('cpu_min', 0):.1f}%, max: {summary.get('cpu_max', 0):.1f}%)")
            output_lines.append(f"  Memory Average: {summary.get('memory_avg', 0):.1f}% (min: {summary.get('memory_min', 0):.1f}%, max: {summary.get('memory_max', 0):.1f}%)")
            output_lines.append(f"  Samples: {summary.get('sample_count', 0)}")
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "format_type": "info"
        }
    
    def _format_system_health(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format comprehensive system health data"""
        if "error" in data:
            return {
                "stdout": f"Error checking system health: {data['error']}\n",
                "stderr": "",
                "format_type": "error"
            }
        
        output_lines = []
        output_lines.append(self.BOX_TOP)
        output_lines.append("│ System Health Check                                                          │")
        output_lines.append(self.BOX_BOTTOM)
        
        status = data.get("overall_status", "unknown")
        status_emoji = "✅" if status == "healthy" else "⚠️"
        output_lines.append(f"\nOverall Status: {status_emoji} {status.upper()}")
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "format_type": "info"
        }
    
    def _format_system_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format system information"""
        if "error" in data:
            return {
                "stdout": f"Error getting system info: {data['error']}\n",
                "stderr": "",
                "format_type": "error"
            }
        
        output_lines = []
        output_lines.append(self.BOX_TOP)
        output_lines.append("│ System Information                                                           │")
        output_lines.append(self.BOX_BOTTOM)
        
        if "platform" in data:
            platform = data["platform"]
            output_lines.append("")
            output_lines.append("Platform:")
            output_lines.append(f"  System: {platform.get('system', 'unknown')}")
            output_lines.append(f"  Node: {platform.get('node', 'unknown')}")
            output_lines.append(f"  Release: {platform.get('release', 'unknown')}")
            output_lines.append(f"  Machine: {platform.get('machine', 'unknown')}")
            output_lines.append(f"  Processor: {platform.get('processor', 'unknown')}")
        
        if "python" in data:
            python = data["python"]
            output_lines.append("")
            output_lines.append("Python:")
            output_lines.append(f"  Version: {python.get('version', 'unknown').split()[0]}")
            output_lines.append(f"  Executable: {python.get('executable', 'unknown')}")
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "format_type": "info"
        }
    
    def _format_environment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format environment variables"""
        if "error" in data:
            return {
                "stdout": f"Error showing environment: {data['error']}\n",
                "stderr": "",
                "format_type": "error"
            }
        
        output_lines = []
        output_lines.append(self.BOX_TOP)
        output_lines.append("│ Environment Variables                                                        │")
        output_lines.append(self.BOX_BOTTOM)
        
        if "environment_variables" in data:
            env_vars = data["environment_variables"]
            output_lines.append(f"\nShowing {len(env_vars)} environment variables:")
            output_lines.append("")
            
            for key, value in sorted(env_vars.items()):
                # Truncate long values for display
                display_value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                output_lines.append(f"{key}={display_value}")
            
            if data.get("filtered_count", 0) > 0:
                output_lines.append(f"\n({data['filtered_count']} sensitive variables filtered)")
        
        return {
            "stdout": "\n".join(output_lines) + "\n",
            "stderr": "",
            "format_type": "info"
        }
    
    def _format_generic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format generic data as JSON"""
        return {
            "stdout": json.dumps(data, indent=2) + "\n",
            "stderr": "",
            "format_type": "json"
        }