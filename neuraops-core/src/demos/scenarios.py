"""
NeuraOps Demo Scenarios
Comprehensive demonstrations showcasing all NeuraOps capabilities with sample data and interactive tutorials
"""

import asyncio
import logging
import json
import math
import random
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

try:
    import aiofiles
except ImportError:
    aiofiles = None

from ..core.command_executor import CommandExecutor, SafetyLevel
from ..modules.logs.analyzer import LogAnalyzer
from ..modules.infrastructure.monitoring import InfrastructureMonitor
from ..modules.infrastructure.templates import TemplateEngine
from ..modules.ai.assistant import AIAssistant, process_user_query
from ..modules.ai.analysis_engine import AdvancedAIAnalysisEngine, AnalysisContext, ContextType
from ..modules.ai.predictive import PredictiveAnalytics

logger = logging.getLogger(__name__)


class DemoType(Enum):
    """Types of demo scenarios"""

    INCIDENT_RESPONSE = "incident_response"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    SECURITY_AUDIT = "security_audit"
    INFRASTRUCTURE_DEPLOYMENT = "infrastructure_deployment"
    AI_ASSISTANT_SHOWCASE = "ai_assistant_showcase"
    PREDICTIVE_ANALYTICS = "predictive_analytics"
    COMPREHENSIVE_WORKFLOW = "comprehensive_workflow"


@dataclass
class DemoStep:
    """Individual step in a demo scenario"""

    step_number: int
    title: str
    description: str
    command: Optional[str] = None
    expected_output: Optional[str] = None
    explanation: Optional[str] = None
    sample_data: Optional[Dict[str, Any]] = None
    interactive: bool = False


@dataclass
class DemoScenario:
    """Complete demo scenario"""

    scenario_id: str
    name: str
    description: str
    duration_minutes: int
    complexity: str  # "beginner", "intermediate", "advanced"
    prerequisites: List[str]
    steps: List[DemoStep]
    sample_data_files: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)


class NeuraOpsDemoEngine:
    """Engine for running NeuraOps demonstration scenarios"""

    def __init__(self):
        self.command_executor = CommandExecutor()
        self.sample_data_dir = Path(__file__).parent / "sample_data"
        self.demo_scenarios = self._initialize_demo_scenarios()

        # Ensure sample data directory exists
        self.sample_data_dir.mkdir(exist_ok=True)

    def _initialize_demo_scenarios(self) -> Dict[str, DemoScenario]:
        """Initialize all demo scenarios"""

        scenarios = {}

        # 1. Incident Response Demo
        scenarios["incident_response"] = DemoScenario(
            scenario_id="incident_response",
            name="🚨 Incident Response Workflow",
            description="Demonstrate comprehensive incident analysis and response capabilities",
            duration_minutes=15,
            complexity="intermediate",
            prerequisites=["Sample log files", "Kubernetes cluster (optional)"],
            learning_objectives=[
                "Log analysis and pattern recognition",
                "Root cause analysis with AI",
                "Infrastructure impact assessment",
                "Automated remediation suggestions",
            ],
            steps=[
                DemoStep(
                    step_number=1,
                    title="Incident Detection",
                    description="Analyze logs to detect and classify the incident",
                    command="neuraops logs analyze demo_logs/error_spike.log --ai-analysis",
                    explanation="The log analyzer will identify error patterns and classify the incident severity",
                    sample_data={
                        "log_type": "application_error",
                        "severity": "high",
                        "error_rate": "15%",
                        "affected_services": ["user-service", "auth-service"],
                    },
                ),
                DemoStep(
                    step_number=2,
                    title="Infrastructure Health Check",
                    description="Check infrastructure status during the incident",
                    command="neuraops infra check --namespace production",
                    explanation="Verify if infrastructure issues are contributing to the incident",
                ),
                DemoStep(
                    step_number=3,
                    title="AI Root Cause Analysis",
                    description="Use AI to determine the most likely root cause",
                    command="neuraops ai analyze-incident --logs demo_logs/error_spike.log --infra-state current",
                    explanation="AI analysis will correlate log patterns with infrastructure state to identify root cause",
                    interactive=True,
                ),
                DemoStep(
                    step_number=4,
                    title="Generate Remediation Plan",
                    description="Create an AI-powered remediation plan",
                    explanation="Based on the analysis, NeuraOps will suggest specific remediation steps",
                    sample_data={
                        "remediation_steps": [
                            "Scale up user-service deployment to 3 replicas",
                            "Restart auth-service pods",
                            "Apply rate limiting configuration",
                            "Monitor error rates for 30 minutes",
                        ],
                        "estimated_resolution_time": "10 minutes",
                    },
                ),
                DemoStep(
                    step_number=5,
                    title="Execute Remediation",
                    description="Execute the recommended remediation steps",
                    command="neuraops infra scale deployment user-service 3 --namespace production",
                    explanation="Implement the AI-recommended scaling action to resolve the incident",
                ),
            ],
            sample_data_files=["demo_logs/error_spike.log", "demo_logs/normal_operation.log"],
        )
        # 2. Performance Optimization Demo
        scenarios["performance_optimization"] = DemoScenario(
            scenario_id="performance_optimization",
            name="⚡ Performance Optimization Workshop",
            description="Identify and resolve performance bottlenecks using AI-powered analysis",
            duration_minutes=20,
            complexity="intermediate",
            prerequisites=["Running applications", "Performance metrics"],
            learning_objectives=[
                "Performance bottleneck identification",
                "Resource utilization analysis",
                "AI-powered optimization recommendations",
                "Predictive scaling strategies",
            ],
            steps=[
                DemoStep(
                    step_number=1,
                    title="Baseline Performance Assessment",
                    description="Establish current performance baseline",
                    command="neuraops infra monitor --duration 120 --output baseline_metrics.json",
                    explanation="Collect 2 minutes of infrastructure metrics to establish baseline",
                ),
                DemoStep(
                    step_number=2,
                    title="Performance Analysis",
                    description="Analyze current performance and identify bottlenecks",
                    command="neuraops infra performance-analysis --output perf_report.json",
                    explanation="AI will analyze metrics to identify performance bottlenecks and optimization opportunities",
                ),
                DemoStep(
                    step_number=3,
                    title="Predictive Capacity Planning",
                    description="Forecast future capacity needs",
                    command="neuraops ai predict-capacity --resources kubernetes,docker --horizon 7_days",
                    explanation="Use predictive analytics to forecast when scaling will be needed",
                    sample_data={
                        "predictions": {
                            "user-service": {
                                "current_cpu": 75,
                                "predicted_7d": 85,
                                "scaling_needed": True,
                            },
                            "api-gateway": {
                                "current_cpu": 45,
                                "predicted_7d": 50,
                                "scaling_needed": False,
                            },
                        }
                    },
                ),
                DemoStep(
                    step_number=4,
                    title="Implement Optimizations",
                    description="Apply AI-recommended optimizations",
                    command="neuraops infra apply-optimizations --recommendations perf_report.json",
                    explanation="Implement the performance optimizations suggested by the AI analysis",
                ),
                DemoStep(
                    step_number=5,
                    title="Validate Improvements",
                    description="Verify that optimizations improved performance",
                    command="neuraops infra monitor --duration 120 --compare-baseline baseline_metrics.json",
                    explanation="Compare post-optimization metrics with the baseline to validate improvements",
                ),
            ],
            sample_data_files=[
                "demo_metrics/performance_baseline.json",
                "demo_metrics/optimization_results.json",
            ],
        )

        # 3. Security Audit Demo
        scenarios["security_audit"] = DemoScenario(
            scenario_id="security_audit",
            name="🔐 Comprehensive Security Audit",
            description="Complete security assessment with compliance checking and remediation",
            duration_minutes=25,
            complexity="advanced",
            prerequisites=["Infrastructure access", "Security scanning tools"],
            learning_objectives=[
                "Multi-layered security scanning",
                "Compliance validation",
                "Vulnerability prioritization",
                "Security remediation planning",
            ],
            steps=[
                DemoStep(
                    step_number=1,
                    title="Infrastructure Security Scan",
                    description="Scan infrastructure for security vulnerabilities",
                    command="neuraops infra security-scan --comprehensive --output security_report.json",
                    explanation="Comprehensive security scan of containers, configurations, and network settings",
                ),
                DemoStep(
                    step_number=2,
                    title="Compliance Check",
                    description="Validate compliance against multiple standards",
                    command="neuraops infra compliance-check --standard cis --standard pci --output compliance_report.json",
                    explanation="Check compliance against CIS benchmarks and PCI DSS requirements",
                ),
                DemoStep(
                    step_number=3,
                    title="AI Security Analysis",
                    description="Use AI to analyze security findings and prioritize risks",
                    command="neuraops ai security-assessment --scan-results security_report.json --compliance-results compliance_report.json",
                    explanation="AI will analyze all security findings and create a prioritized remediation plan",
                    interactive=True,
                    sample_data={
                        "critical_vulnerabilities": 2,
                        "high_priority_issues": 5,
                        "compliance_gaps": ["SSH root login enabled", "Missing TLS configuration"],
                        "security_score": 72,
                    },
                ),
                DemoStep(
                    step_number=4,
                    title="Generate Security Roadmap",
                    description="Create a comprehensive security improvement roadmap",
                    explanation="AI will generate a timeline-based security improvement plan with cost estimates",
                    sample_data={
                        "roadmap": {
                            "immediate": ["Fix critical vulnerabilities", "Disable SSH root login"],
                            "short_term": [
                                "Implement TLS encryption",
                                "Update container base images",
                            ],
                            "long_term": [
                                "Implement zero-trust architecture",
                                "Advanced threat detection",
                            ],
                        }
                    },
                ),
                DemoStep(
                    step_number=5,
                    title="Automated Remediation",
                    description="Execute automated fixes for low-risk issues",
                    command="neuraops ai auto-remediate --security-findings security_report.json --risk-threshold low",
                    explanation="Automatically fix low-risk security issues while flagging high-risk items for manual review",
                ),
            ],
            sample_data_files=[
                "demo_security/vuln_scan.json",
                "demo_security/compliance_baseline.json",
            ],
        )

        # 4. Infrastructure Deployment Demo
        scenarios["infrastructure_deployment"] = DemoScenario(
            scenario_id="infrastructure_deployment",
            name="🏗️ Smart Infrastructure Deployment",
            description="End-to-end infrastructure deployment with AI-powered templates and monitoring",
            duration_minutes=18,
            complexity="beginner",
            prerequisites=["Docker", "Kubernetes (optional)"],
            learning_objectives=[
                "AI-powered template generation",
                "Infrastructure as Code best practices",
                "Deployment automation",
                "Real-time monitoring setup",
            ],
            steps=[
                DemoStep(
                    step_number=1,
                    title="Generate Application Template",
                    description="Create infrastructure templates for a web application",
                    command="neuraops infra generate webapp-stack --output ./demo-app --var app_name=neuraops-demo --var replicas=3",
                    explanation="AI will generate Kubernetes manifests, Dockerfile, and configuration files",
                ),
                DemoStep(
                    step_number=2,
                    title="Validate Templates",
                    description="Validate generated templates before deployment",
                    command="neuraops infra apply ./demo-app --dry-run --namespace demo",
                    explanation="Validate Kubernetes manifests and check for potential issues",
                ),
                DemoStep(
                    step_number=3,
                    title="Deploy Infrastructure",
                    description="Deploy the application infrastructure",
                    command="neuraops infra apply ./demo-app --namespace demo",
                    explanation="Deploy all components to Kubernetes cluster",
                ),
                DemoStep(
                    step_number=4,
                    title="Monitor Deployment",
                    description="Monitor deployment health and resource utilization",
                    command="neuraops infra monitor --namespace demo --duration 180",
                    explanation="Real-time monitoring of deployed resources with health checks",
                ),
                DemoStep(
                    step_number=5,
                    title="AI Health Assessment",
                    description="Get AI insights on deployment health",
                    command="neuraops ai assess-deployment --namespace demo",
                    explanation="AI will analyze deployment state and provide optimization recommendations",
                    interactive=True,
                ),
            ],
            sample_data_files=[
                "demo_templates/webapp_config.json",
                "demo_templates/k8s_manifests/",
            ],
        )

        # 5. AI Assistant Showcase
        scenarios["ai_assistant_showcase"] = DemoScenario(
            scenario_id="ai_assistant_showcase",
            name="🤖 AI Assistant Capabilities",
            description="Interactive demonstration of the AI assistant's natural language processing",
            duration_minutes=12,
            complexity="beginner",
            prerequisites=["None"],
            learning_objectives=[
                "Natural language command processing",
                "Context-aware assistance",
                "Intelligent troubleshooting",
                "Command suggestions and explanations",
            ],
            steps=[
                DemoStep(
                    step_number=1,
                    title="Natural Language Commands",
                    description="Demonstrate natural language to CLI command translation",
                    explanation="Show how the AI assistant understands natural language requests",
                    interactive=True,
                    sample_data={
                        "queries": [
                            "Check if my Kubernetes pods are healthy",
                            "Analyze the recent error logs",
                            "Show me the CPU usage of my containers",
                            "Generate a Docker template for a web application",
                        ]
                    },
                ),
                DemoStep(
                    step_number=2,
                    title="Context-Aware Assistance",
                    description="Show how the assistant maintains conversation context",
                    explanation="The assistant remembers previous interactions and provides relevant suggestions",
                    interactive=True,
                ),
                DemoStep(
                    step_number=3,
                    title="Intelligent Troubleshooting",
                    description="Demonstrate AI-guided troubleshooting workflows",
                    explanation="Show how the assistant can guide users through complex troubleshooting scenarios",
                    interactive=True,
                    sample_data={
                        "scenario": "My application is running slowly",
                        "expected_flow": [
                            "Check system resources",
                            "Analyze application logs",
                            "Review infrastructure metrics",
                            "Identify bottlenecks",
                            "Suggest optimizations",
                        ],
                    },
                ),
                DemoStep(
                    step_number=4,
                    title="Command Explanations",
                    description="Show how the assistant explains commands and their purpose",
                    command="neuraops ai explain kubectl get pods --all-namespaces",
                    explanation="The assistant provides detailed explanations of commands and their usage",
                ),
            ],
        )

        # 6. Predictive Analytics Demo
        scenarios["predictive_analytics"] = DemoScenario(
            scenario_id="predictive_analytics",
            name="🔮 Predictive Analytics Showcase",
            description="Demonstrate forecasting and proactive issue detection capabilities",
            duration_minutes=16,
            complexity="advanced",
            prerequisites=["Historical metrics data", "Multiple resources"],
            learning_objectives=[
                "Capacity forecasting",
                "Anomaly prediction",
                "Failure prediction",
                "Proactive scaling recommendations",
            ],
            steps=[
                DemoStep(
                    step_number=1,
                    title="Capacity Forecasting",
                    description="Forecast resource capacity needs for the next 30 days",
                    command="neuraops ai predict-capacity --resources demo-resources.json --horizon 30_days --output capacity_forecast.json",
                    explanation="AI analyzes historical usage patterns to predict future capacity requirements",
                    sample_data={
                        "resources": [
                            {"type": "kubernetes", "id": "user-service", "current_cpu": 65},
                            {"type": "kubernetes", "id": "api-gateway", "current_cpu": 45},
                            {"type": "docker", "id": "redis-cache", "current_cpu": 30},
                        ]
                    },
                ),
                DemoStep(
                    step_number=2,
                    title="Anomaly Prediction",
                    description="Predict potential anomalies in the next week",
                    command="neuraops ai predict-anomalies --resources user-service,api-gateway --horizon 7_days",
                    explanation="AI predicts when and where anomalies are likely to occur based on historical patterns",
                ),
                DemoStep(
                    step_number=3,
                    title="Failure Risk Assessment",
                    description="Assess failure risks for critical components",
                    command="neuraops ai predict-failures --critical-resources critical_resources.json",
                    explanation="Evaluate the likelihood of component failures and suggest preventive actions",
                    sample_data={
                        "high_risk_components": [
                            {
                                "id": "database-primary",
                                "risk_score": 0.8,
                                "predicted_failure": "3 days",
                            },
                            {
                                "id": "load-balancer",
                                "risk_score": 0.6,
                                "predicted_failure": "10 days",
                            },
                        ]
                    },
                ),
                DemoStep(
                    step_number=4,
                    title="Proactive Scaling Plan",
                    description="Generate proactive scaling recommendations",
                    command="neuraops ai generate-scaling-plan --forecast capacity_forecast.json --cost-optimize",
                    explanation="Create a timeline of when to scale resources based on predictions and cost optimization",
                ),
                DemoStep(
                    step_number=5,
                    title="Cost Impact Analysis",
                    description="Analyze cost implications of predictive scaling",
                    explanation="Show how proactive scaling affects costs compared to reactive scaling",
                    sample_data={
                        "cost_comparison": {
                            "reactive_scaling": "$450/month",
                            "proactive_scaling": "$380/month",
                            "savings": "$70/month (15.6%)",
                        }
                    },
                ),
            ],
            sample_data_files=[
                "demo_metrics/capacity_history.json",
                "demo_metrics/anomaly_patterns.json",
            ],
        )

        # 7. Comprehensive Workflow Demo
        scenarios["comprehensive_workflow"] = DemoScenario(
            scenario_id="comprehensive_workflow",
            name="🎯 Complete NeuraOps Workflow",
            description="End-to-end demonstration of all NeuraOps capabilities",
            duration_minutes=30,
            complexity="advanced",
            prerequisites=["Full environment setup"],
            learning_objectives=[
                "Complete DevOps workflow automation",
                "AI-driven decision making",
                "Integrated monitoring and analysis",
                "Proactive infrastructure management",
            ],
            steps=[
                DemoStep(
                    step_number=1,
                    title="Infrastructure Assessment",
                    description="Comprehensive assessment of current infrastructure state",
                    command="neuraops infra comprehensive-analysis --cloud --output initial_assessment.json",
                ),
                DemoStep(
                    step_number=2,
                    title="AI Assistant Consultation",
                    description="Consult with AI assistant about optimization opportunities",
                    explanation="Use natural language to discuss findings with the AI assistant",
                    interactive=True,
                ),
                DemoStep(
                    step_number=3,
                    title="Generate Improvement Plan",
                    description="Create comprehensive improvement plan using AI analysis",
                    command="neuraops ai generate-improvement-plan --assessment initial_assessment.json --priorities cost,security,performance",
                ),
                DemoStep(
                    step_number=4,
                    title="Implement Optimizations",
                    description="Execute the improvement plan with monitoring",
                    command="neuraops ai execute-plan --plan improvement_plan.json --monitor --confirm-each",
                ),
                DemoStep(
                    step_number=5,
                    title="Validate Results",
                    description="Validate improvements and update baselines",
                    command="neuraops infra comprehensive-analysis --compare-baseline initial_assessment.json --output final_assessment.json",
                ),
                DemoStep(
                    step_number=6,
                    title="Predictive Planning",
                    description="Set up predictive monitoring and planning",
                    command="neuraops ai setup-predictive-monitoring --resources all --enable-auto-scaling",
                ),
            ],
            sample_data_files=[
                "demo_complete/initial_state.json",
                "demo_complete/improvement_plan.json",
            ],
        )

        return scenarios

    async def run_demo(self, scenario_id: str, interactive: bool = True) -> Dict[str, Any]:
        """Run a complete demo scenario"""

        if scenario_id not in self.demo_scenarios:
            raise ValueError(f"Unknown demo scenario: {scenario_id}")

        scenario = self.demo_scenarios[scenario_id]
        demo_results = {
            "scenario_id": scenario_id,
            "name": scenario.name,
            "start_time": datetime.now().isoformat(),
            "steps_completed": [],
            "step_results": {},
            "overall_success": True,
            "error_messages": [],
        }

        logger.info(f"Starting demo scenario: {scenario.name}")

        # Prepare sample data
        await self._prepare_sample_data(scenario)

        # Execute each step
        for step in scenario.steps:
            try:
                step_result = await self._execute_demo_step(step, scenario, interactive)
                demo_results["steps_completed"].append(step.step_number)
                demo_results["step_results"][f"step_{step.step_number}"] = step_result

                if not step_result.get("success", True):
                    demo_results["overall_success"] = False
                    demo_results["error_messages"].append(f"Step {step.step_number} failed: {step_result.get('error', 'Unknown error')}")

            except Exception as e:
                logger.error(f"Demo step {step.step_number} failed: {str(e)}")
                demo_results["overall_success"] = False
                demo_results["error_messages"].append(f"Step {step.step_number} exception: {str(e)}")

                if not interactive:
                    # In non-interactive mode, stop on errors
                    break

        demo_results["end_time"] = datetime.now().isoformat()
        demo_results["actual_duration"] = (datetime.fromisoformat(demo_results["end_time"]) - datetime.fromisoformat(demo_results["start_time"])).total_seconds() / 60

        return demo_results

    async def _execute_demo_step(self, step: DemoStep, scenario: DemoScenario, interactive: bool) -> Dict[str, Any]:
        """Execute an individual demo step"""

        step_result = {
            "step_number": step.step_number,
            "title": step.title,
            "start_time": datetime.now().isoformat(),
            "success": True,
        }

        try:
            logger.info(f"Executing demo step {step.step_number}: {step.title}")

            # Show step information
            if interactive:
                print(
                    f"\
--- Step {step.step_number}: {step.title} ---"
                )
                print(f"Description: {step.description}")
                if step.explanation:
                    print(f"Explanation: {step.explanation}")

            # Execute command if provided
            if step.command:
                if interactive:
                    print(f"Command: {step.command}")
                    await asyncio.to_thread(input, "Press Enter to execute command...")

                # Execute the command (in demo mode, we'll simulate execution)
                command_result = self._simulate_command_execution(step.command)
                step_result["command_result"] = command_result

                if interactive:
                    print(f"Result: {command_result.get('summary', 'Command executed successfully')}")

            # Handle interactive steps
            if step.interactive and interactive:
                interaction_result = await self._handle_interactive_step(step, scenario)
                step_result["interaction_result"] = interaction_result

            # Add sample data to results
            if step.sample_data:
                step_result["sample_data"] = step.sample_data

            step_result["end_time"] = datetime.now().isoformat()

        except Exception as e:
            step_result["success"] = False
            step_result["error"] = str(e)
            step_result["end_time"] = datetime.now().isoformat()

        return step_result

    def _simulate_command_execution(self, command: str) -> Dict[str, Any]:
        """Simulate command execution for demo purposes"""

        # In demo mode, we simulate command results rather than executing them
        # This allows the demo to work without requiring full infrastructure setup

        if "logs analyze" in command:
            return {
                "summary": "Analyzed 1,247 log entries, found 23 errors, 156 warnings",
                "patterns": ["Database connection timeout", "Memory allocation issues"],
                "recommendations": ["Increase database connection pool", "Review memory limits"],
            }

        elif "infra check" in command:
            return {
                "summary": "Infrastructure health: 85% (4/5 components healthy)",
                "unhealthy_resources": ["user-service-pod-3"],
                "recommendations": ["Restart unhealthy pod", "Check resource limits"],
            }

        elif "infra monitor" in command:
            return {
                "summary": "Monitoring completed, collected 120 metric snapshots",
                "avg_cpu": 67.5,
                "avg_memory": 58.2,
                "alerts_triggered": 2,
            }

        elif "security-scan" in command:
            return {
                "summary": "Security scan completed, security score: 78/100",
                "vulnerabilities": {"critical": 1, "high": 3, "medium": 8, "low": 12},
                "recommendations": [
                    "Update base images",
                    "Enable network policies",
                    "Implement RBAC",
                ],
            }

        elif "predict-capacity" in command:
            return {
                "summary": "Capacity forecast generated for 7-day horizon",
                "scaling_needed": {"user-service": "Day 4", "api-gateway": "Day 6"},
                "cost_impact": "+$125/month",
                "confidence": 0.84,
            }

        elif "generate" in command and "template" in command:
            return {
                "summary": "Generated infrastructure templates successfully",
                "files_created": [
                    "Dockerfile",
                    "k8s-deployment.yaml",
                    "k8s-service.yaml",
                    "docker-compose.yml",
                ],
                "template_type": "webapp-stack",
            }

        else:
            # Generic success result
            return {"summary": f"Command executed successfully: {command}", "status": "completed"}

    async def _handle_interactive_step(self, step: DemoStep, scenario: DemoScenario, interactive: bool = True) -> Dict[str, Any]:
        """Handle interactive demo steps"""

        if scenario.scenario_id == "ai_assistant_showcase" and step.step_number == 1:
            return await self._handle_ai_assistant_demo(step, interactive)

        elif scenario.scenario_id == "ai_assistant_showcase" and step.step_number == 3:
            return await self._handle_troubleshooting_demo(step)

        elif step.step_number == 3 and "AI" in step.title:
            return await self._handle_ai_analysis_demo(step)

        else:
            # Generic interactive step
            print("This is an interactive step. In a real scenario, you would interact with the system here.")
            if interactive:
                await asyncio.to_thread(input, "Press Enter to continue...")

            return {"interactive_completed": True}

    async def _handle_ai_assistant_demo(self, step: DemoStep, interactive: bool) -> Dict[str, Any]:
        """Handle AI assistant demo interactions"""
        from ..modules.ai.assistant import AIAssistant

        assistant = AIAssistant()
        demo_queries = step.sample_data.get("queries", [])
        interaction_results = []

        for query in demo_queries:
            print(f"User: {query}")
            response = await assistant.process_message(query, "demo_session")
            print(f"Assistant: {response.message}")

            if response.commands:
                print(f"Suggested commands: {', '.join(response.commands)}")

            interaction_results.append({"query": query, "response": response.message, "commands": response.commands})

            if len(demo_queries) > 1 and interactive:
                await asyncio.to_thread(input, "Press Enter for next query...")

        return {"interactions": interaction_results}

    async def _handle_troubleshooting_demo(self, step: DemoStep) -> Dict[str, Any]:
        """Handle troubleshooting demo scenario"""
        from ..modules.ai.assistant import AIAssistant

        assistant = AIAssistant()
        scenario_desc = step.sample_data.get("scenario", "Unknown issue")
        print(f"Troubleshooting Scenario: {scenario_desc}")

        response = await assistant.process_message(scenario_desc, "demo_troubleshooting")
        print(f"Assistant: {response.message}")

        return {
            "troubleshooting_scenario": scenario_desc,
            "assistant_response": response.message,
            "suggested_commands": [s.command for s in response.suggestions],
        }

    async def _handle_ai_analysis_demo(self, step: DemoStep) -> Dict[str, Any]:
        """Handle AI analysis demo"""
        from ..modules.ai.analysis_engine import AdvancedAIAnalysisEngine, AnalysisContext, ContextType

        analysis_engine = AdvancedAIAnalysisEngine()

        # Create sample analysis context
        context = AnalysisContext(
            context_type=ContextType.INFRASTRUCTURE,
            data=step.sample_data or {"demo": "analysis"},
        )

        insight = await analysis_engine.analyze_with_ai(context)

        print("AI Analysis Result:")
        print(f"Title: {insight.title}")
        print(f"Confidence: {insight.confidence:.2f}")
        print(f"Recommendation: {insight.recommendation}")

        return {
            "ai_insight": {
                "title": insight.title,
                "confidence": insight.confidence,
                "recommendation": insight.recommendation,
            }
        }

    async def _prepare_sample_data(self, scenario: DemoScenario):
        """Prepare sample data files for the demo"""

        for data_file in scenario.sample_data_files:
            file_path = self.sample_data_dir / data_file

            # Create directory if it doesn't exist
            self._create_data_directory(file_path)

            # Generate sample data if file doesn't exist
            if not file_path.exists():
                sample_data = self._generate_sample_data(data_file, scenario)
                await self._write_sample_data(file_path, sample_data, data_file)

    def _create_data_directory(self, file_path: Path) -> None:
        """Create directory if it doesn't exist"""
        file_path.parent.mkdir(parents=True, exist_ok=True)

    async def _write_sample_data(self, file_path: Path, sample_data: Any, data_file: str) -> None:
        """Write sample data using appropriate API"""
        if aiofiles:
            await self._write_sample_data_async(file_path, sample_data, data_file)
        else:
            self._write_sample_data_sync(file_path, sample_data, data_file)

    async def _write_sample_data_async(self, file_path: Path, sample_data: Any, data_file: str) -> None:
        """Write sample data using async API"""
        async with aiofiles.open(file_path, "w") as f:
            if data_file.endswith(".json"):
                await f.write(json.dumps(sample_data, indent=2))
            else:
                await f.write(sample_data)

    def _write_sample_data_sync(self, file_path: Path, sample_data: Any, data_file: str) -> None:
        """Write sample data using sync API as fallback"""
        with open(file_path, "w") as f:
            if data_file.endswith(".json"):
                json.dump(sample_data, f, indent=2)
            else:
                f.write(sample_data)

    def _generate_sample_data(self, file_name: str, scenario: DemoScenario) -> Any:
        """Generate realistic sample data for demos"""

        if "error_spike.log" in file_name:
            return self._generate_error_spike_logs()
        elif "capacity_history.json" in file_name:
            return self._generate_capacity_history()
        elif "demo-resources.json" in file_name:
            return self._generate_resource_config()
        else:
            return self._generate_generic_data(file_name, scenario)

    def _generate_error_spike_logs(self) -> str:
        """Generate sample error log with spike pattern"""
        log_entries = []
        base_time = datetime.now() - timedelta(hours=2)

        for i in range(100):
            timestamp = base_time + timedelta(minutes=i)

            # Simulate error spike
            if 40 <= i <= 60:  # Error spike in middle period
                if random.random() < 0.3:  # 30% error rate during spike
                    log_entries.append(f"{timestamp.isoformat()} ERROR [user-service] Database connection timeout after 30s")
                elif random.random() < 0.2:  # 20% warning rate
                    log_entries.append(f"{timestamp.isoformat()} WARN [user-service] High memory usage: 85%")
                else:
                    log_entries.append(f"{timestamp.isoformat()} INFO [user-service] Request processed successfully")
            else:
                # Normal operation
                if random.random() < 0.05:  # 5% error rate normally
                    log_entries.append(f"{timestamp.isoformat()} ERROR [user-service] Request validation failed")
                else:
                    log_entries.append(f"{timestamp.isoformat()} INFO [user-service] Request processed successfully")

        return "\n".join(log_entries)

    def _generate_capacity_history(self) -> Dict[str, Any]:
        """Generate capacity history data"""
        capacity_data = []
        base_time = datetime.now() - timedelta(days=30)

        for i in range(720):  # 30 days of hourly data
            timestamp = base_time + timedelta(hours=i)

            # Simulate gradual increase in usage
            base_cpu = 40 + (i / 720) * 25  # Increase from 40% to 65% over 30 days
            daily_variation = 15 * math.sin(i * 2 * math.pi / 24)  # Daily cycle
            noise = random.gauss(0, 3)  # Random noise

            cpu_usage = max(0, min(100, base_cpu + daily_variation + noise))

            capacity_data.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "resource_id": "user-service",
                    "cpu_usage": round(cpu_usage, 2),
                    "memory_usage": round(cpu_usage * 0.8 + random.gauss(0, 2), 2),  # Memory correlates with CPU
                }
            )

        return {"capacity_history": capacity_data}

    def _generate_resource_config(self) -> Dict[str, Any]:
        """Generate resource configuration data"""
        return {
            "resources": [
                {"type": "kubernetes", "id": "user-service", "namespace": "production"},
                {"type": "kubernetes", "id": "api-gateway", "namespace": "production"},
                {"type": "docker", "id": "redis-cache"},
                {"type": "kubernetes", "id": "database", "namespace": "data"},
            ]
        }

    def _generate_generic_data(self, file_name: str, scenario: DemoScenario) -> Dict[str, Any]:
        """Generate generic sample data"""
        return {
            "demo_data": True,
            "file_name": file_name,
            "scenario": scenario.scenario_id,
            "generated_at": datetime.now().isoformat(),
        }

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """List all available demo scenarios"""

        scenarios_list = []

        for scenario in self.demo_scenarios.values():
            scenarios_list.append(
                {
                    "id": scenario.scenario_id,
                    "name": scenario.name,
                    "description": scenario.description,
                    "duration_minutes": scenario.duration_minutes,
                    "complexity": scenario.complexity,
                    "prerequisites": scenario.prerequisites,
                    "learning_objectives": scenario.learning_objectives,
                    "step_count": len(scenario.steps),
                }
            )

        return scenarios_list

    def get_scenario_details(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific scenario"""

        if scenario_id not in self.demo_scenarios:
            return None

        scenario = self.demo_scenarios[scenario_id]

        return {
            "scenario": {
                "id": scenario.scenario_id,
                "name": scenario.name,
                "description": scenario.description,
                "duration_minutes": scenario.duration_minutes,
                "complexity": scenario.complexity,
                "prerequisites": scenario.prerequisites,
                "learning_objectives": scenario.learning_objectives,
            },
            "steps": [
                {
                    "step_number": step.step_number,
                    "title": step.title,
                    "description": step.description,
                    "command": step.command,
                    "explanation": step.explanation,
                    "interactive": step.interactive,
                }
                for step in scenario.steps
            ],
            "sample_data_files": scenario.sample_data_files,
        }


# Convenience functions for running demos
async def run_quick_demo(demo_type: str = "incident_response") -> Dict[str, Any]:
    """Run a quick demo scenario"""

    demo_engine = NeuraOpsDemoEngine()
    return await demo_engine.run_demo(demo_type, interactive=False)


async def run_interactive_demo(demo_type: str = "ai_assistant_showcase") -> Dict[str, Any]:
    """Run an interactive demo scenario"""

    demo_engine = NeuraOpsDemoEngine()
    return await demo_engine.run_demo(demo_type, interactive=True)


def list_available_demos() -> List[Dict[str, Any]]:
    """List all available demo scenarios"""

    demo_engine = NeuraOpsDemoEngine()
    return demo_engine.list_scenarios()


def create_custom_demo(steps: List[Dict[str, Any]], name: str, description: str) -> str:
    """Create a custom demo scenario"""

    demo_engine = NeuraOpsDemoEngine()

    # Convert step dictionaries to DemoStep objects
    demo_steps = []
    for i, step_data in enumerate(steps):
        demo_step = DemoStep(
            step_number=i + 1,
            title=step_data.get("title", f"Step {i + 1}"),
            description=step_data.get("description", ""),
            command=step_data.get("command"),
            explanation=step_data.get("explanation"),
            interactive=step_data.get("interactive", False),
        )
        demo_steps.append(demo_step)

    # Create custom scenario
    custom_scenario = DemoScenario(
        scenario_id=f"custom_{int(datetime.now().timestamp())}",
        name=name,
        description=description,
        duration_minutes=len(steps) * 3,  # Estimate 3 minutes per step
        complexity="custom",
        prerequisites=["User-defined"],
        steps=demo_steps,
        learning_objectives=["Custom demonstration"],
    )

    # Add to available scenarios
    demo_engine.demo_scenarios[custom_scenario.scenario_id] = custom_scenario

    return custom_scenario.scenario_id
