"""
NeuraOps Advanced AI Analysis Engine
Sophisticated AI-powered analysis with multi-step reasoning, context awareness, and adaptive learning
"""

import logging
import json
import re
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ...core.engine import get_engine
from ...core.command_executor import CommandExecutor
from ...core.structured_output import SeverityLevel
from ...devops_commander.exceptions import AnalysisError

logger = logging.getLogger(__name__)

# Constants
NO_INSIGHTS_MESSAGE = "No insights generated"


class AnalysisMode(Enum):
    """Modes of AI analysis"""

    QUICK = "quick"  # Fast analysis with basic insights
    DEEP = "deep"  # Comprehensive analysis with detailed reasoning
    INTERACTIVE = "interactive"  # Step-by-step interactive analysis
    PREDICTIVE = "predictive"  # Predictive analysis with forecasting


class ContextType(Enum):
    """Types of analysis context"""

    LOGS = "logs"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    COST = "cost"


@dataclass
class AnalysisContext:
    """Context for AI analysis"""

    context_type: ContextType
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 1  # 1-5, higher is more important


@dataclass
class AIInsight:
    """AI-generated insight"""

    insight_id: str
    title: str
    description: str
    confidence: float  # 0-1 confidence score
    impact: str
    recommendation: str
    reasoning: List[str]  # Step-by-step reasoning
    evidence: List[str]  # Supporting evidence
    context_type: ContextType
    severity: SeverityLevel
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AnalysisWorkflow:
    """Multi-step analysis workflow"""

    workflow_id: str
    name: str
    description: str
    steps: List[str]
    context_requirements: List[ContextType]
    estimated_duration: int  # seconds


class AdvancedAIAnalysisEngine:
    """Advanced AI analysis engine with sophisticated reasoning capabilities"""

    def __init__(self):
        self.command_executor = CommandExecutor()
        self.analysis_history: List[AIInsight] = []
        self.context_cache: Dict[str, AnalysisContext] = {}
        self.user_feedback: Dict[str, Dict[str, Any]] = {}
        self.learned_patterns: Dict[str, Any] = {}

        # Pre-defined analysis workflows
        self.workflows = {
            "incident_analysis": AnalysisWorkflow(
                workflow_id="incident_analysis",
                name="Incident Root Cause Analysis",
                description="Comprehensive incident analysis with root cause identification",
                steps=[
                    "collect_incident_data",
                    "analyze_logs_for_errors",
                    "check_infrastructure_state",
                    "identify_timeline",
                    "determine_root_cause",
                    "generate_remediation_plan",
                ],
                context_requirements=[ContextType.LOGS, ContextType.INFRASTRUCTURE],
                estimated_duration=300,
            ),
            "performance_optimization": AnalysisWorkflow(
                workflow_id="performance_optimization",
                name="Performance Optimization Analysis",
                description="Identify performance bottlenecks and optimization opportunities",
                steps=[
                    "collect_performance_metrics",
                    "analyze_resource_utilization",
                    "identify_bottlenecks",
                    "assess_scaling_options",
                    "generate_optimization_plan",
                ],
                context_requirements=[ContextType.PERFORMANCE, ContextType.INFRASTRUCTURE],
                estimated_duration=240,
            ),
            "security_assessment": AnalysisWorkflow(
                workflow_id="security_assessment",
                name="Comprehensive Security Assessment",
                description="Multi-layered security analysis with threat modeling",
                steps=[
                    "scan_infrastructure_security",
                    "analyze_access_patterns",
                    "check_compliance_status",
                    "identify_vulnerabilities",
                    "assess_threat_landscape",
                    "generate_security_roadmap",
                ],
                context_requirements=[ContextType.SECURITY, ContextType.COMPLIANCE],
                estimated_duration=420,
            ),
        }

    async def analyze_with_ai(
        self,
        context: AnalysisContext,
        mode: AnalysisMode = AnalysisMode.DEEP,
    ) -> AIInsight:
        """Perform AI-powered analysis with specified context and mode"""

        try:
            engine = get_engine()

            # Select analysis approach based on mode
            if mode == AnalysisMode.QUICK:
                return await self._quick_analysis(context, engine)
            elif mode == AnalysisMode.DEEP:
                return await self._deep_analysis(context, engine)
            elif mode == AnalysisMode.INTERACTIVE:
                return await self._interactive_analysis(context, engine)
            elif mode == AnalysisMode.PREDICTIVE:
                return await self._predictive_analysis(context, engine)
            else:
                raise AnalysisError(f"Unsupported analysis mode: {mode}")

        except Exception as e:
            raise AnalysisError(f"AI analysis failed: {str(e)}") from e

    async def _quick_analysis(self, context: AnalysisContext, engine) -> AIInsight:
        """Quick analysis with basic AI insights"""

        # Construct prompt for quick analysis
        prompt = self._build_analysis_prompt(context, "quick")

        try:
            response = await engine.generate_text(
                prompt=prompt,
                system_prompt="You are an expert DevOps analyst. Provide concise, actionable insights.",
                max_tokens=512,
            )

            # Parse AI response into structured insight
            insight = self._parse_ai_response(response, context, confidence=0.7)
            insight.metadata["analysis_mode"] = "quick"

            return insight

        except Exception as e:
            logger.error(f"Quick analysis failed: {str(e)}")
            return self._create_fallback_insight(context, str(e))

    async def _deep_analysis(self, context: AnalysisContext, engine) -> AIInsight:
        """Deep analysis with comprehensive AI reasoning"""

        # Multi-step analysis process
        analysis_steps = [
            "data_assessment",
            "pattern_recognition",
            "root_cause_analysis",
            "impact_assessment",
            "recommendation_generation",
        ]

        reasoning = []
        evidence = []

        for step in analysis_steps:
            step_prompt = self._build_step_prompt(context, step)

            step_response = await engine.generate_text(
                prompt=step_prompt,
                system_prompt=f"You are performing {step.replace('_', ' ')} as part of a comprehensive DevOps analysis.",
                max_tokens=256,
            )

            reasoning.append(f"{step.replace('_', ' ').title()}: {step_response}")
            evidence.append(step_response)

        # Generate final comprehensive analysis
        final_prompt = self._build_comprehensive_prompt(context, reasoning)

        final_response = await engine.generate_text(
            prompt=final_prompt,
            system_prompt="You are an expert DevOps analyst providing comprehensive insights with detailed reasoning.",
            max_tokens=1024,
        )

        insight = self._parse_ai_response(final_response, context, confidence=0.9)
        insight.reasoning = reasoning
        insight.evidence = evidence
        insight.metadata["analysis_mode"] = "deep"

        return insight

    async def _interactive_analysis(self, context: AnalysisContext, engine) -> AIInsight:
        """Interactive analysis with user guidance"""

        # This would typically involve user interaction, but for now we'll simulate
        prompt = self._build_analysis_prompt(context, "interactive")

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are an interactive DevOps assistant. Ask clarifying questions and provide step-by-step guidance.",
            max_tokens=768,
        )

        insight = self._parse_ai_response(response, context, confidence=0.8)
        insight.metadata["analysis_mode"] = "interactive"

        return insight

    async def _predictive_analysis(self, context: AnalysisContext, engine) -> AIInsight:
        """Predictive analysis with forecasting"""

        # Include historical data for prediction
        historical_context = self._get_historical_context(context)

        prompt = self._build_predictive_prompt(context, historical_context)

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are a predictive analytics expert. Analyze trends and forecast future states.",
            max_tokens=768,
        )

        insight = self._parse_ai_response(response, context, confidence=0.6)
        insight.metadata["analysis_mode"] = "predictive"
        insight.metadata["forecast_horizon"] = "7 days"

        return insight

    def _build_analysis_prompt(self, context: AnalysisContext, mode: str) -> str:
        """Build AI prompt for analysis"""

        data_summary = self._summarize_context_data(context)

        base_prompt = f"""
Analyze the following {context.context_type.value} data:

{data_summary}

Context metadata:
{json.dumps(context.metadata, indent=2)}

Analysis mode: {mode}
"""

        if mode == "quick":
            base_prompt += """
Provide a quick analysis focusing on:
1. Most critical issue (if any)
2. Primary recommendation
3. Confidence level
"""
        elif mode == "deep":
            base_prompt += """
Provide comprehensive analysis including:
1. Detailed assessment of current state
2. Identification of patterns and anomalies
3. Root cause analysis if issues found
4. Risk assessment and impact analysis
5. Prioritized recommendations with reasoning
"""
        elif mode == "interactive":
            base_prompt += """
Provide interactive analysis by:
1. Asking relevant clarifying questions
2. Explaining your reasoning process
3. Offering multiple solution approaches
4. Providing step-by-step guidance
"""

        return base_prompt

    def _build_step_prompt(self, context: AnalysisContext, step: str) -> str:
        """Build prompt for specific analysis step"""

        data_summary = self._summarize_context_data(context)

        step_prompts = {
            "data_assessment": f"Assess the quality and completeness of this {context.context_type.value} data: {data_summary}",
            "pattern_recognition": f"Identify patterns, trends, and anomalies in this {context.context_type.value} data: {data_summary}",
            "root_cause_analysis": f"Analyze potential root causes for any issues found in this {context.context_type.value} data: {data_summary}",
            "impact_assessment": f"Assess the impact and severity of findings in this {context.context_type.value} data: {data_summary}",
            "recommendation_generation": f"Generate specific, actionable recommendations based on this {context.context_type.value} analysis: {data_summary}",
        }

        return step_prompts.get(step, f"Analyze this {context.context_type.value} data for {step}: {data_summary}")

    def _build_comprehensive_prompt(self, context: AnalysisContext, reasoning: List[str]) -> str:
        """Build final comprehensive analysis prompt"""

        reasoning_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(reasoning))

        return f"""
Based on the following step-by-step analysis of {context.context_type.value} data:

{reasoning_text}

Provide a comprehensive final analysis including:
1. Executive summary of findings
2. Key insights and their confidence levels
3. Prioritized recommendations
4. Implementation guidance
5. Expected outcomes

Focus on actionable insights that will help improve system reliability, performance, and security.
"""

    def _build_predictive_prompt(self, context: AnalysisContext, historical_context: Dict[str, Any]) -> str:
        """Build prompt for predictive analysis"""

        current_data = self._summarize_context_data(context)
        historical_summary = json.dumps(historical_context, indent=2)

        return f"""
Perform predictive analysis on {context.context_type.value} data:

Current state:
{current_data}

Historical patterns:
{historical_summary}

Provide predictive insights including:
1. Trend analysis and trajectory
2. Predicted future states (next 7 days)
3. Potential issues that may arise
4. Proactive recommendations
5. Confidence intervals for predictions
"""

    def _summarize_context_data(self, context: AnalysisContext) -> str:
        """Summarize context data for AI prompt"""

        data = context.data

        if context.context_type == ContextType.LOGS:
            return self._summarize_log_data(data)
        elif context.context_type == ContextType.INFRASTRUCTURE:
            return self._summarize_infrastructure_data(data)
        elif context.context_type == ContextType.SECURITY:
            return self._summarize_security_data(data)
        elif context.context_type == ContextType.PERFORMANCE:
            return self._summarize_performance_data(data)
        else:
            return json.dumps(data, indent=2)[:1000]  # Truncate if too long

    def _summarize_log_data(self, data: Dict[str, Any]) -> str:
        """Summarize log data for analysis"""

        summary = []

        if "log_entries" in data:
            entries = data["log_entries"]
            summary.append(f"Total log entries: {len(entries)}")

            # Count by severity
            severity_counts = {}
            for entry in entries:
                severity = entry.get("severity", "unknown")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            summary.append(f"Severity distribution: {severity_counts}")

            # Recent error samples
            errors = [e for e in entries if e.get("severity") in ["error", "critical"]]
            if errors:
                summary.append(f"Recent errors: {[e.get('message', '')[:100] for e in errors[:3]]}")

        if "patterns" in data:
            summary.append(f"Identified patterns: {data['patterns']}")

        if "anomalies" in data:
            summary.append(f"Anomalies detected: {len(data['anomalies'])}")

        return "\n".join(summary)

    def _summarize_infrastructure_data(self, data: Dict[str, Any]) -> str:
        """Summarize infrastructure data for analysis"""

        summary = []

        if "resources" in data:
            resources = data["resources"]
            summary.append(f"Total resources: {len(resources)}")

            # Health status
            healthy = len([r for r in resources if r.get("healthy", False)])
            summary.append(f"Healthy resources: {healthy}/{len(resources)} ({healthy/len(resources)*100:.1f}%)")

            # Resource types
            types = {}
            for resource in resources:
                res_type = resource.get("resource_type", "unknown")
                types[res_type] = types.get(res_type, 0) + 1

            summary.append(f"Resource types: {types}")

        if "alerts" in data:
            summary.append(f"Active alerts: {len(data['alerts'])}")

        if "metrics" in data:
            metrics = data["metrics"]
            summary.append(f"Key metrics: {json.dumps(metrics, indent=2)[:200]}")

        return "\n".join(summary)

    def _summarize_security_data(self, data: Dict[str, Any]) -> str:
        """Summarize security data for analysis"""

        summary = []

        if "vulnerabilities" in data:
            vuln_count = len(data["vulnerabilities"])
            summary.append(f"Vulnerabilities found: {vuln_count}")

            # Group by severity
            severity_counts = {}
            for vuln in data["vulnerabilities"]:
                severity = vuln.get("severity", "unknown")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            summary.append(f"Vulnerability severity: {severity_counts}")

        if "compliance_status" in data:
            summary.append(f"Compliance status: {data['compliance_status']}")

        if "security_events" in data:
            summary.append(f"Security events: {len(data['security_events'])}")

        return "\n".join(summary)

    def _summarize_performance_data(self, data: Dict[str, Any]) -> str:
        """Summarize performance data for analysis"""

        summary = []

        if "cpu_usage" in data:
            summary.append(f"CPU usage: {data['cpu_usage']}%")

        if "memory_usage" in data:
            summary.append(f"Memory usage: {data['memory_usage']}%")

        if "response_times" in data:
            times = data["response_times"]
            avg_time = sum(times) / len(times) if times else 0
            summary.append(f"Average response time: {avg_time:.2f}ms")

        if "throughput" in data:
            summary.append(f"Throughput: {data['throughput']} req/s")

        return "\n".join(summary)

    def _parse_ai_response(self, response: str, context: AnalysisContext, confidence: float) -> AIInsight:
        """Parse AI response into structured insight"""

        # Simple parsing - in production, this would be more sophisticated
        lines = response.strip().split("\n")

        title = "AI Analysis Result"
        description = response[:200] + "..." if len(response) > 200 else response
        impact = "Moderate"
        recommendation = "Review findings and take appropriate action"

        # Try to extract structured information
        for line in lines:
            if line.lower().startswith(("title:", "issue:", "problem:")):
                title = line.split(":", 1)[1].strip()
            elif line.lower().startswith(("recommendation:", "action:", "solution:")):
                recommendation = line.split(":", 1)[1].strip()
            elif line.lower().startswith(("impact:", "severity:", "priority:")):
                impact = line.split(":", 1)[1].strip()

        # Determine severity based on keywords
        severity = SeverityLevel.INFO
        if any(word in response.lower() for word in ["critical", "severe", "urgent"]):
            severity = SeverityLevel.CRITICAL
        elif any(word in response.lower() for word in ["high", "important", "significant"]):
            severity = SeverityLevel.HIGH
        elif any(word in response.lower() for word in ["medium", "moderate", "warning"]):
            severity = SeverityLevel.MEDIUM

        return AIInsight(
            insight_id=f"ai_{context.context_type.value}_{int(datetime.now().timestamp())}",
            title=title,
            description=description,
            confidence=confidence,
            impact=impact,
            recommendation=recommendation,
            reasoning=[response],
            evidence=[f"AI analysis of {context.context_type.value} data"],
            context_type=context.context_type,
            severity=severity,
        )

    def _create_fallback_insight(self, context: AnalysisContext, error_message: str) -> AIInsight:
        """Create fallback insight when AI analysis fails"""

        return AIInsight(
            insight_id=f"fallback_{context.context_type.value}_{int(datetime.now().timestamp())}",
            title="Analysis Error",
            description=f"AI analysis could not be completed: {error_message}",
            confidence=0.1,
            impact="Unknown",
            recommendation="Manual analysis recommended",
            reasoning=["AI analysis failed"],
            evidence=[error_message],
            context_type=context.context_type,
            severity=SeverityLevel.WARNING,
        )

    async def execute_workflow(self, workflow_id: str, contexts: List[AnalysisContext]) -> List[AIInsight]:
        """Execute a predefined analysis workflow"""

        if workflow_id not in self.workflows:
            raise AnalysisError(f"Unknown workflow: {workflow_id}")

        workflow = self.workflows[workflow_id]
        insights = []

        # Validate required contexts
        available_types = {ctx.context_type for ctx in contexts}
        required_types = set(workflow.context_requirements)

        if not required_types.issubset(available_types):
            missing = required_types - available_types
            raise AnalysisError(f"Missing required context types for workflow {workflow_id}: {missing}")

        # Execute workflow steps
        for step in workflow.steps:
            step_insight = await self._execute_workflow_step(step, contexts, workflow)
            insights.append(step_insight)

        # Generate workflow summary
        summary_insight = await self._generate_workflow_summary(workflow, insights)
        insights.append(summary_insight)

        return insights

    async def _execute_workflow_step(self, step: str, contexts: List[AnalysisContext], workflow: AnalysisWorkflow) -> AIInsight:
        """Execute individual workflow step"""

        engine = get_engine()

        # Find relevant context for this step
        relevant_context = self._select_relevant_context(step, contexts)

        step_prompt = f"""
Execute workflow step: {step}
Workflow: {workflow.name}
Context: {self._summarize_context_data(relevant_context)}

Provide specific insights for this step.
"""

        response = await engine.generate_text(
            prompt=step_prompt,
            system_prompt=f"You are executing step '{step}' in the {workflow.name} workflow.",
            max_tokens=512,
        )

        insight = self._parse_ai_response(response, relevant_context, confidence=0.8)
        insight.metadata["workflow_id"] = workflow.workflow_id
        insight.metadata["workflow_step"] = step

        return insight

    async def _generate_workflow_summary(self, workflow: AnalysisWorkflow, step_insights: List[AIInsight]) -> AIInsight:
        """Generate summary insight for completed workflow"""

        engine = get_engine()

        # Combine insights from all steps
        step_summaries = [f"{insight.metadata.get('workflow_step', 'Unknown')}: {insight.title}" for insight in step_insights]

        summary_prompt = f"""
Workflow: {workflow.name}
Description: {workflow.description}

Step results:
{chr(10).join(step_summaries)}

Provide a comprehensive workflow summary including:
1. Overall assessment
2. Key findings across all steps
3. Integrated recommendations
4. Next steps
"""

        response = await engine.generate_text(
            prompt=summary_prompt,
            system_prompt="You are summarizing a completed analysis workflow. Provide comprehensive insights.",
            max_tokens=768,
        )

        return AIInsight(
            insight_id=f"workflow_summary_{workflow.workflow_id}_{int(datetime.now().timestamp())}",
            title=f"{workflow.name} Summary",
            description=response,
            confidence=0.85,
            impact="Workflow completed",
            recommendation="Review all step findings and implement recommendations",
            reasoning=[f"Workflow {workflow.name} completed with {len(step_insights)} steps"],
            evidence=[insight.title for insight in step_insights],
            context_type=ContextType.INFRASTRUCTURE,  # Default
            severity=SeverityLevel.INFO,
            metadata={
                "workflow_id": workflow.workflow_id,
                "workflow_step": "summary",
                "steps_completed": len(step_insights),
            },
        )

    def _select_relevant_context(self, step: str, contexts: List[AnalysisContext]) -> AnalysisContext:
        """Select most relevant context for a workflow step"""

        # Simple selection logic - could be enhanced with ML
        step_context_mapping = {
            "collect_incident_data": ContextType.LOGS,
            "analyze_logs_for_errors": ContextType.LOGS,
            "check_infrastructure_state": ContextType.INFRASTRUCTURE,
            "collect_performance_metrics": ContextType.PERFORMANCE,
            "analyze_resource_utilization": ContextType.PERFORMANCE,
            "scan_infrastructure_security": ContextType.SECURITY,
            "check_compliance_status": ContextType.COMPLIANCE,
        }

        preferred_type = step_context_mapping.get(step, ContextType.INFRASTRUCTURE)

        # Find context with preferred type
        for context in contexts:
            if context.context_type == preferred_type:
                return context

        # Fallback to highest priority context
        return max(contexts, key=lambda c: c.priority)

    def _get_historical_context(self, context: AnalysisContext) -> Dict[str, Any]:
        """Get historical context for predictive analysis"""

        # Look for similar past contexts
        historical = []

        for cached_context in self.context_cache.values():
            if cached_context.context_type == context.context_type and (datetime.now() - cached_context.timestamp).days <= 30:
                historical.append(
                    {
                        "timestamp": cached_context.timestamp.isoformat(),
                        "summary": self._summarize_context_data(cached_context)[:200],
                    }
                )

        return {
            "historical_contexts": historical,
            "context_count": len(historical),
            "time_range": "30 days",
        }

    def store_context(self, context: AnalysisContext):
        """Store context for future reference"""

        context_key = f"{context.context_type.value}_{context.timestamp.isoformat()}"
        self.context_cache[context_key] = context

        # Clean old contexts (keep last 30 days)
        cutoff_time = datetime.now() - timedelta(days=30)
        self.context_cache = {k: v for k, v in self.context_cache.items() if v.timestamp > cutoff_time}

    def learn_from_feedback(self, insight_id: str, feedback: Dict[str, Any]):
        """Learn from user feedback on insights"""

        self.user_feedback[insight_id] = {
            "feedback": feedback,
            "timestamp": datetime.now().isoformat(),
        }

        # Update learned patterns based on feedback
        feedback_type = feedback.get("type", "unknown")

        if feedback_type == "accuracy":
            accuracy_score = feedback.get("score", 0.5)
            if insight_id in [insight.insight_id for insight in self.analysis_history]:
                # Store pattern for future learning
                pattern_key = f"accuracy_{feedback.get('context_type', 'general')}"
                if pattern_key not in self.learned_patterns:
                    self.learned_patterns[pattern_key] = []

                self.learned_patterns[pattern_key].append({"score": accuracy_score, "timestamp": datetime.now().isoformat()})

    def get_learned_insights(self, context_type: ContextType) -> Dict[str, Any]:
        """Get insights learned from user feedback"""

        pattern_key = f"accuracy_{context_type.value}"

        if pattern_key in self.learned_patterns:
            scores = [p["score"] for p in self.learned_patterns[pattern_key]]
            avg_accuracy = sum(scores) / len(scores) if scores else 0.5

            return {
                "average_accuracy": avg_accuracy,
                "feedback_count": len(scores),
                "trend": ("improving" if scores[-3:] and sum(scores[-3:]) > sum(scores[:3]) else "stable"),
            }

        return {"average_accuracy": 0.5, "feedback_count": 0, "trend": "unknown"}

    async def generate_contextual_recommendations(self, contexts: List[AnalysisContext]) -> List[str]:
        """Generate contextual recommendations based on multiple contexts"""

        engine = get_engine()

        # Combine context summaries
        context_summaries = []
        for context in contexts:
            summary = self._summarize_context_data(context)
            context_summaries.append(f"{context.context_type.value}: {summary}")

        combined_summary = "\n\n".join(context_summaries)

        prompt = f"""
Based on the following multi-context analysis:

{combined_summary}

Generate holistic recommendations that consider:
1. Cross-system dependencies
2. Resource optimization opportunities
3. Security and compliance requirements
4. Performance implications
5. Cost considerations

Provide 3-5 specific, actionable recommendations ranked by priority.
"""

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are a senior DevOps architect providing holistic system recommendations.",
            max_tokens=768,
        )

        # Parse recommendations from response
        recommendations = []
        lines = response.strip().split("\n")

        for line in lines:
            # Look for numbered or bulleted recommendations
            if re.match(r"^\d+\.", line) or line.startswith("- ") or line.startswith("* "):
                recommendation = re.sub(r"^\d+\.\s*", "", line)  # Remove numbering
                recommendation = re.sub(r"^[-*]\s*", "", recommendation)  # Remove bullets
                if recommendation.strip():
                    recommendations.append(recommendation.strip())

        return recommendations[:5]  # Return top 5

    async def explain_reasoning(self, insight: AIInsight) -> str:
        """Generate detailed explanation of AI reasoning"""

        engine = get_engine()

        prompt = f"""
Explain the reasoning behind this analysis insight:

Title: {insight.title}
Description: {insight.description}
Recommendation: {insight.recommendation}
Confidence: {insight.confidence:.2f}
Context: {insight.context_type.value}

Provide a clear explanation of:
1. Why this conclusion was reached
2. What evidence supports it
3. What alternatives were considered
4. How confident we should be in this assessment
5. What could change this assessment
"""

        explanation = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are explaining AI reasoning to help users understand and trust the analysis.",
            max_tokens=512,
        )

        return explanation

    def get_analysis_metrics(self) -> Dict[str, Any]:
        """Get metrics about analysis engine performance"""

        total_analyses = len(self.analysis_history)

        if total_analyses == 0:
            return {
                "total_analyses": 0,
                "average_confidence": 0,
                "analysis_types": {},
                "feedback_coverage": 0,
            }

        # Calculate metrics
        avg_confidence = sum(insight.confidence for insight in self.analysis_history) / total_analyses

        analysis_types = {}
        for insight in self.analysis_history:
            context_type = insight.context_type.value
            analysis_types[context_type] = analysis_types.get(context_type, 0) + 1

        feedback_coverage = len(self.user_feedback) / total_analyses if total_analyses > 0 else 0

        return {
            "total_analyses": total_analyses,
            "average_confidence": avg_confidence,
            "analysis_types": analysis_types,
            "feedback_coverage": feedback_coverage,
            "learned_patterns": len(self.learned_patterns),
        }


# Convenience functions for common analysis scenarios
async def analyze_incident(log_data: Dict[str, Any], infrastructure_data: Dict[str, Any]) -> AIInsight:
    """Analyze incident using AI with log and infrastructure context"""

    engine = AdvancedAIAnalysisEngine()

    # Create contexts
    log_context = AnalysisContext(context_type=ContextType.LOGS, data=log_data, priority=5)

    infra_context = AnalysisContext(context_type=ContextType.INFRASTRUCTURE, data=infrastructure_data, priority=4)

    # Execute incident analysis workflow
    insights = await engine.execute_workflow("incident_analysis", [log_context, infra_context])

    # Return the summary insight (last one)
    return insights[-1] if insights else engine._create_fallback_insight(log_context, NO_INSIGHTS_MESSAGE)


async def optimize_performance(performance_data: Dict[str, Any], infrastructure_data: Dict[str, Any]) -> AIInsight:
    """AI-powered performance optimization analysis"""

    engine = AdvancedAIAnalysisEngine()

    perf_context = AnalysisContext(context_type=ContextType.PERFORMANCE, data=performance_data, priority=5)

    infra_context = AnalysisContext(context_type=ContextType.INFRASTRUCTURE, data=infrastructure_data, priority=4)

    insights = await engine.execute_workflow("performance_optimization", [perf_context, infra_context])

    return insights[-1] if insights else engine._create_fallback_insight(perf_context, NO_INSIGHTS_MESSAGE)


async def assess_security(security_data: Dict[str, Any], compliance_data: Dict[str, Any]) -> AIInsight:
    """AI-powered security assessment"""

    engine = AdvancedAIAnalysisEngine()

    security_context = AnalysisContext(context_type=ContextType.SECURITY, data=security_data, priority=5)

    compliance_context = AnalysisContext(context_type=ContextType.COMPLIANCE, data=compliance_data, priority=4)

    insights = await engine.execute_workflow("security_assessment", [security_context, compliance_context])

    return insights[-1] if insights else engine._create_fallback_insight(security_context, NO_INSIGHTS_MESSAGE)


async def quick_ai_insight(data: Dict[str, Any], context_type: ContextType) -> AIInsight:
    """Quick AI insight for any type of data"""

    engine = AdvancedAIAnalysisEngine()

    context = AnalysisContext(context_type=context_type, data=data)

    return await engine.analyze_with_ai(context, mode=AnalysisMode.QUICK)
