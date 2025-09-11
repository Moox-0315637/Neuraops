"""
NeuraOps AI-Powered Automation Workflows
Intelligent automation with decision trees, automated remediation, workflow orchestration, and adaptive learning
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
import uuid

from ...core.command_executor import CommandExecutor, SafetyLevel
from .analysis_engine import AdvancedAIAnalysisEngine, AnalysisContext, ContextType
from .assistant import AIAssistant
from .predictive import PredictiveAnalytics

logger = logging.getLogger(__name__)

# Constants
OPERATIONS_TEAM_EMAIL = "ops-team@company.com"


class WorkflowStatus(Enum):
    """Workflow execution status"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionType(Enum):
    """Types of workflow actions"""

    COMMAND = "command"
    AI_ANALYSIS = "ai_analysis"
    DECISION = "decision"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    WAIT = "wait"
    NOTIFICATION = "notification"
    ROLLBACK = "rollback"


class ConditionOperator(Enum):
    """Condition evaluation operators"""

    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX_MATCH = "regex_match"


@dataclass
class WorkflowCondition:
    """Condition for workflow decision making"""

    field: str
    operator: ConditionOperator
    value: Any
    description: Optional[str] = None

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition against context"""
        try:
            actual_value = self._get_nested_value(context, self.field)

            if self.operator == ConditionOperator.EQUALS:
                return actual_value == self.value
            elif self.operator == ConditionOperator.NOT_EQUALS:
                return actual_value != self.value
            elif self.operator == ConditionOperator.GREATER_THAN:
                return float(actual_value) > float(self.value)
            elif self.operator == ConditionOperator.LESS_THAN:
                return float(actual_value) < float(self.value)
            elif self.operator == ConditionOperator.GREATER_EQUAL:
                return float(actual_value) >= float(self.value)
            elif self.operator == ConditionOperator.LESS_EQUAL:
                return float(actual_value) <= float(self.value)
            elif self.operator == ConditionOperator.CONTAINS:
                return str(self.value) in str(actual_value)
            elif self.operator == ConditionOperator.NOT_CONTAINS:
                return str(self.value) not in str(actual_value)
            elif self.operator == ConditionOperator.REGEX_MATCH:
                import re

                return bool(re.search(str(self.value), str(actual_value)))

        except Exception as e:
            logger.error(f"Error evaluating condition {self.field} {self.operator.value} {self.value}: {e}")
            return False

        return False

    def _get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get nested value from dictionary using dot notation"""
        keys = field.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            elif isinstance(value, list) and key.isdigit():
                value = value[int(key)]
            else:
                return None

        return value


@dataclass
class WorkflowAction:
    """Individual workflow action"""

    action_id: str
    action_type: ActionType
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    conditions: List[WorkflowCondition] = field(default_factory=list)
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    rollback_action: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

    def should_execute(self, context: Dict[str, Any]) -> bool:
        """Check if action should execute based on conditions"""
        if not self.conditions:
            return True

        return all(condition.evaluate(context) for condition in self.conditions)


@dataclass
class DecisionNode:
    """Decision tree node for workflow branching"""

    node_id: str
    name: str
    conditions: List[WorkflowCondition]
    true_path: List[str]  # Action IDs to execute if conditions are true
    false_path: List[str]  # Action IDs to execute if conditions are false
    description: Optional[str] = None

    def evaluate(self, context: Dict[str, Any]) -> List[str]:
        """Evaluate conditions and return path to follow"""
        all_true = all(condition.evaluate(context) for condition in self.conditions)
        return self.true_path if all_true else self.false_path


@dataclass
class WorkflowExecution:
    """Workflow execution state and results"""

    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    current_action: Optional[str] = None
    completed_actions: List[str] = field(default_factory=list)
    failed_actions: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    error_messages: List[str] = field(default_factory=list)
    rollback_performed: bool = False

    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate execution duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return datetime.now() - self.start_time
        return None


@dataclass
class AutomationWorkflow:
    """Complete automation workflow definition"""

    workflow_id: str
    name: str
    description: str
    version: str
    actions: List[WorkflowAction]
    decision_nodes: List[DecisionNode] = field(default_factory=list)
    entry_point: str = "start"
    triggers: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None  # Cron expression
    timeout_minutes: Optional[int] = None
    max_retries: int = 3
    rollback_strategy: str = "on_failure"  # "on_failure", "manual", "never"
    learning_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowOrchestrator:
    """Main workflow orchestration engine"""

    def __init__(self):
        self.command_executor = CommandExecutor()
        self.ai_engine = AdvancedAIAnalysisEngine()
        self.ai_assistant = AIAssistant()
        self.predictive_analytics = PredictiveAnalytics()

        self.workflows: Dict[str, AutomationWorkflow] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.learning_data: Dict[str, List[Dict[str, Any]]] = {}

        # Workflow execution queue
        self.execution_queue: List[str] = []
        self.running_executions: Dict[str, asyncio.Task] = {}

    async def register_workflow(self, workflow: AutomationWorkflow) -> str:
        """Register a new workflow"""
        # Make function truly async
        await asyncio.sleep(0)

        self.workflows[workflow.workflow_id] = workflow

        # Initialize learning data
        if workflow.learning_enabled:
            self.learning_data[workflow.workflow_id] = []

        logger.info(f"Registered workflow: {workflow.name} ({workflow.workflow_id})")
        return workflow.workflow_id

    async def execute_workflow(self, workflow_id: str, context: Optional[Dict[str, Any]] = None, dry_run: bool = False) -> WorkflowExecution:
        """Execute a workflow"""

        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self.workflows[workflow_id]
        execution_id = str(uuid.uuid4())

        # Create execution record
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(),
            context=context or {},
        )

        self.executions[execution_id] = execution

        try:
            # Execute workflow
            if dry_run:
                await self._dry_run_workflow(workflow, execution)
            else:
                task = asyncio.create_task(self._execute_workflow_async(workflow, execution))
                self.running_executions[execution_id] = task
                await task

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_messages.append(f"Workflow execution failed: {str(e)}")
            logger.error(f"Workflow {workflow_id} execution failed: {e}")

        finally:
            execution.end_time = datetime.now()
            if execution_id in self.running_executions:
                del self.running_executions[execution_id]

        # Learn from execution
        if workflow.learning_enabled:
            await self._learn_from_execution(workflow, execution)

        return execution

    async def _handle_action_execution(self, workflow: AutomationWorkflow, action: WorkflowAction, execution: WorkflowExecution) -> bool:
        """Handle execution of a single action and update execution state"""
        success = await self._execute_action(workflow, action, execution)

        if success:
            execution.completed_actions.append(action.action_id)
            return True
        else:
            execution.failed_actions.append(action.action_id)
            if workflow.rollback_strategy == "on_failure":
                await self._perform_rollback(workflow, execution)
            return False

    def _handle_decision_evaluation(self, decision: DecisionNode, execution: WorkflowExecution) -> List[str]:
        """Handle evaluation of a decision node"""
        path = decision.evaluate(execution.context)
        execution.completed_actions.append(decision.node_id)
        return path

    def _check_workflow_timeout(self, workflow: AutomationWorkflow, execution: WorkflowExecution) -> bool:
        """Check if workflow has timed out"""
        if workflow.timeout_minutes and execution.duration:
            if execution.duration.total_seconds() > workflow.timeout_minutes * 60:
                execution.status = WorkflowStatus.FAILED
                execution.error_messages.append("Workflow timeout exceeded")
                return True
        return False

    async def _process_current_actions(self, workflow: AutomationWorkflow, current_actions: List[str], execution: WorkflowExecution) -> List[str]:
        """Process current actions and return next actions to execute"""
        next_actions = []

        for action_id in current_actions:
            # Find action or decision node
            action = self._find_action(workflow, action_id)
            decision = self._find_decision_node(workflow, action_id)

            if action:
                success = await self._handle_action_execution(workflow, action, execution)
                if success:
                    # Add any next actions based on workflow logic
                    next_actions.extend(self._get_next_actions(workflow))
                else:
                    # Break on failure
                    break

            elif decision:
                path = self._handle_decision_evaluation(decision, execution)
                next_actions.extend(path)

        return next_actions

    async def _execute_workflow_async(self, workflow: AutomationWorkflow, execution: WorkflowExecution):
        """Execute workflow asynchronously"""
        logger.info(f"Starting workflow execution: {workflow.name}")

        # Start from entry point
        current_actions = [workflow.entry_point]

        while current_actions and execution.status == WorkflowStatus.RUNNING:
            # Process current actions and get next actions
            next_actions = await self._process_current_actions(workflow, current_actions, execution)
            current_actions = next_actions

            # Check timeout
            if self._check_workflow_timeout(workflow, execution):
                break

        if execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.COMPLETED

    async def _execute_action(self, workflow: AutomationWorkflow, action: WorkflowAction, execution: WorkflowExecution) -> bool:
        """Execute individual workflow action"""

        logger.info(f"Executing action: {action.name}")
        execution.current_action = action.action_id

        # Check conditions
        if not action.should_execute(execution.context):
            logger.info(f"Action {action.name} skipped due to conditions")
            return True

        # Check dependencies
        for dep in action.dependencies:
            if dep not in execution.completed_actions:
                logger.warning(f"Action {action.name} dependency {dep} not completed")
                return False

        try:
            success = False

            if action.action_type == ActionType.COMMAND:
                success = await self._execute_command_action(action, execution)

            elif action.action_type == ActionType.AI_ANALYSIS:
                success = await self._execute_ai_analysis_action(action, execution)

            elif action.action_type == ActionType.DECISION:
                success = await self._execute_decision_action(action, execution)

            elif action.action_type == ActionType.CONDITION:
                success = await self._execute_condition_action(action, execution)

            elif action.action_type == ActionType.PARALLEL:
                success = await self._execute_parallel_action(workflow, action, execution)

            elif action.action_type == ActionType.SEQUENTIAL:
                success = await self._execute_sequential_action(workflow, action, execution)

            elif action.action_type == ActionType.WAIT:
                success = await self._execute_wait_action(action, execution)

            elif action.action_type == ActionType.NOTIFICATION:
                success = await self._execute_notification_action(action, execution)

            elif action.action_type == ActionType.ROLLBACK:
                success = await self._execute_rollback_action(workflow, action, execution)

            # Store action result
            execution.results[action.action_id] = {
                "success": success,
                "timestamp": datetime.now().isoformat(),
                "parameters": action.parameters,
            }

            return success

        except Exception as e:
            logger.error(f"Action {action.name} failed: {e}")
            execution.error_messages.append(f"Action {action.name} failed: {str(e)}")
            return False

    async def _execute_command_action(self, action: WorkflowAction, execution: WorkflowExecution) -> bool:
        """Execute command action"""

        command = action.parameters.get("command")
        if not command:
            return False

        # Replace variables in command
        command = self._replace_variables(command, execution.context)

        # Execute command
        safety_level = SafetyLevel(action.parameters.get("safety_level", "MEDIUM"))

        result = await self.command_executor.execute_command(command=command, safety_level=safety_level, timeout=action.timeout_seconds)

        # Store result in context
        execution.context[f"{action.action_id}_result"] = result

        return result.success

    async def _execute_ai_analysis_action(self, action: WorkflowAction, execution: WorkflowExecution) -> bool:
        """Execute AI analysis action"""

        analysis_type = action.parameters.get("analysis_type", "infrastructure")
        data_source = action.parameters.get("data_source")

        # Get data from context or parameters
        if data_source and data_source in execution.context:
            data = execution.context[data_source]
        else:
            data = action.parameters.get("data", {})

        # Create analysis context
        context_type = ContextType(analysis_type.upper())
        analysis_context = AnalysisContext(context_type=context_type, data=data)

        # Perform AI analysis
        insight = await self.ai_engine.analyze_with_ai(analysis_context)

        # Store result
        execution.context[f"{action.action_id}_insight"] = {
            "title": insight.title,
            "summary": insight.summary,
            "recommendation": insight.recommendation,
            "confidence": insight.confidence,
            "severity": insight.severity.value,
            "tags": insight.tags,
            "evidence": insight.evidence,
        }

        return True

    async def _execute_decision_action(self, action: WorkflowAction, execution: WorkflowExecution) -> bool:
        """Execute decision action using AI assistant"""

        question = action.parameters.get("question")
        options = action.parameters.get("options", [])

        if not question:
            return False

        # Use AI assistant to make decision
        decision_prompt = f"Decision needed: {question}\nOptions: {', '.join(options)}\nContext: {json.dumps(execution.context, indent=2)}"

        response = await self.ai_assistant.process_message(decision_prompt, execution.execution_id)

        # Store decision
        execution.context[f"{action.action_id}_decision"] = {
            "question": question,
            "options": options,
            "response": response.message,
            "chosen_option": self._extract_chosen_option(response.message, options),
        }

        return True

    async def _execute_condition_action(self, action: WorkflowAction, execution: WorkflowExecution) -> bool:
        """Execute condition evaluation action"""
        # Make function truly async
        await asyncio.sleep(0)

        conditions = action.conditions
        result = all(condition.evaluate(execution.context) for condition in conditions)

        execution.context[f"{action.action_id}_condition_result"] = result
        return True

    async def _execute_parallel_action(self, workflow: AutomationWorkflow, action: WorkflowAction, execution: WorkflowExecution) -> bool:
        """Execute parallel action group"""

        parallel_actions = action.parameters.get("actions", [])

        # Execute all actions in parallel
        tasks = []
        for action_id in parallel_actions:
            parallel_action = self._find_action(workflow, action_id)
            if parallel_action:
                task = asyncio.create_task(self._execute_action(workflow, parallel_action, execution))
                tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check if all succeeded
        success = all(isinstance(result, bool) and result for result in results)

        execution.context[f"{action.action_id}_parallel_results"] = results
        return success

    async def _execute_sequential_action(self, workflow: AutomationWorkflow, action: WorkflowAction, execution: WorkflowExecution) -> bool:
        """Execute sequential action group"""

        sequential_actions = action.parameters.get("actions", [])

        # Execute actions in sequence
        for action_id in sequential_actions:
            sequential_action = self._find_action(workflow, action_id)
            if sequential_action:
                success = await self._execute_action(workflow, sequential_action, execution)
                if not success:
                    return False

        return True

    async def _execute_wait_action(self, action: WorkflowAction, execution: WorkflowExecution) -> bool:
        """Execute wait action"""

        wait_seconds = action.parameters.get("seconds", 1)
        await asyncio.sleep(wait_seconds)

        execution.context[f"{action.action_id}_wait_completed"] = True
        return True

    async def _execute_notification_action(self, action: WorkflowAction, execution: WorkflowExecution) -> bool:
        """Execute notification action"""
        # Make function truly async
        await asyncio.sleep(0)

        message = action.parameters.get("message", "Workflow notification")
        recipients = action.parameters.get("recipients", [])

        # Replace variables in message
        message = self._replace_variables(message, execution.context)

        # Log notification (in real implementation, send actual notifications)
        logger.info(f"Workflow notification: {message} (Recipients: {recipients})")

        execution.context[f"{action.action_id}_notification_sent"] = {
            "message": message,
            "recipients": recipients,
            "timestamp": datetime.now().isoformat(),
        }

        return True

    async def _execute_rollback_action(self, workflow: AutomationWorkflow, action: WorkflowAction, execution: WorkflowExecution) -> bool:
        """Execute rollback action"""

        await self._perform_rollback(workflow, execution)
        return True

    async def _perform_rollback(self, workflow: AutomationWorkflow, execution: WorkflowExecution):
        """Perform workflow rollback"""

        logger.info(f"Performing rollback for workflow {workflow.name}")
        execution.rollback_performed = True

        # Execute rollback actions in reverse order
        for action_id in reversed(execution.completed_actions):
            action = self._find_action(workflow, action_id)
            if action and action.rollback_action:
                rollback_action = self._find_action(workflow, action.rollback_action)
                if rollback_action:
                    await self._execute_action(workflow, rollback_action, execution)

    async def _dry_run_workflow(self, workflow: AutomationWorkflow, execution: WorkflowExecution):
        """Perform dry run of workflow"""
        # Make function truly async
        await asyncio.sleep(0)

        logger.info(f"Performing dry run of workflow: {workflow.name}")

        # Simulate workflow execution without actually running actions
        execution.results["dry_run"] = True
        execution.results["actions_to_execute"] = []

        current_actions = [workflow.entry_point]

        while current_actions:
            next_actions = []

            for action_id in current_actions:
                action = self._find_action(workflow, action_id)
                decision = self._find_decision_node(workflow, action_id)

                if action:
                    execution.results["actions_to_execute"].append(
                        {
                            "action_id": action.action_id,
                            "name": action.name,
                            "type": action.action_type.value,
                            "description": action.description,
                            "parameters": action.parameters,
                        }
                    )
                    next_actions.extend(self._get_next_actions(workflow, action_id))

                elif decision:
                    # For dry run, assume first path
                    path = decision.true_path
                    next_actions.extend(path)

            current_actions = next_actions

        execution.status = WorkflowStatus.COMPLETED

    async def _learn_from_execution(self, workflow: AutomationWorkflow, execution: WorkflowExecution):
        """Learn from workflow execution for future optimization"""
        # Make function truly async
        await asyncio.sleep(0)

        learning_record = {
            "execution_id": execution.execution_id,
            "workflow_id": workflow.workflow_id,
            "success": execution.status == WorkflowStatus.COMPLETED,
            "duration": execution.duration.total_seconds() if execution.duration else None,
            "actions_completed": len(execution.completed_actions),
            "actions_failed": len(execution.failed_actions),
            "context_size": len(execution.context),
            "error_count": len(execution.error_messages),
            "timestamp": execution.start_time.isoformat(),
        }

        self.learning_data[workflow.workflow_id].append(learning_record)

        # Keep only last 100 executions for learning
        if len(self.learning_data[workflow.workflow_id]) > 100:
            self.learning_data[workflow.workflow_id] = self.learning_data[workflow.workflow_id][-100:]

        logger.info(f"Recorded learning data for workflow {workflow.name}")

    def _find_action(self, workflow: AutomationWorkflow, action_id: str) -> Optional[WorkflowAction]:
        """Find action by ID in workflow"""
        return next((action for action in workflow.actions if action.action_id == action_id), None)

    def _find_decision_node(self, workflow: AutomationWorkflow, node_id: str) -> Optional[DecisionNode]:
        """Find decision node by ID in workflow"""
        return next((node for node in workflow.decision_nodes if node.node_id == node_id), None)

    def _get_next_actions(self, workflow: AutomationWorkflow, action_id: Optional[str] = None) -> List[str]:
        """Get next actions to execute based on workflow logic"""
        # This would be implemented based on specific workflow graph structure
        # For now, return empty list (actions define their own next steps)
        # If action_id provided, could return specific next actions for that action
        return []

    def _replace_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Replace variables in text using context"""
        import re

        # Replace variables like ${variable_name}
        def replace_var(match):
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))

        return re.sub(r"\$\{([^}]+)\}", replace_var, text)

    def _extract_chosen_option(self, response: str, options: List[str]) -> Optional[str]:
        """Extract chosen option from AI response"""
        response_lower = response.lower()

        for option in options:
            if option.lower() in response_lower:
                return option

        return None

    async def get_workflow_statistics(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow execution statistics"""
        # Make function truly async
        await asyncio.sleep(0)

        if workflow_id not in self.learning_data:
            return {}

        learning_data = self.learning_data[workflow_id]

        if not learning_data:
            return {}

        total_executions = len(learning_data)
        successful_executions = sum(1 for record in learning_data if record["success"])

        durations = [record["duration"] for record in learning_data if record["duration"]]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "workflow_id": workflow_id,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "average_duration_seconds": avg_duration,
            "last_execution": learning_data[-1]["timestamp"] if learning_data else None,
        }

    async def optimize_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Optimize workflow based on learning data"""

        if workflow_id not in self.workflows or workflow_id not in self.learning_data:
            return {"error": "Workflow not found or no learning data available"}

        workflow = self.workflows[workflow_id]
        learning_data = self.learning_data[workflow_id]

        if not learning_data:
            return {"error": "No learning data available"}

        # Analyze patterns in learning data
        optimizations = []

        # Check for frequently failing actions
        for record in learning_data:
            if not record["success"]:
                # Analyze which actions might be problematic
                # This is a simplified version - real implementation would be more sophisticated
                pass

        # Suggest timeout adjustments based on average durations
        stats = await self.get_workflow_statistics(workflow_id)

        if stats["average_duration_seconds"] > 0:
            suggested_timeout = int(stats["average_duration_seconds"] * 1.5)  # 150% of average

            if not workflow.timeout_minutes or workflow.timeout_minutes * 60 > suggested_timeout:
                optimizations.append(
                    {
                        "type": "timeout_optimization",
                        "current_timeout": (workflow.timeout_minutes * 60 if workflow.timeout_minutes else None),
                        "suggested_timeout": suggested_timeout,
                        "reasoning": f"Based on average execution time of {stats['average_duration_seconds']:.1f} seconds",
                    }
                )

        return {
            "workflow_id": workflow_id,
            "optimization_suggestions": optimizations,
            "current_stats": stats,
        }


# Workflow builder helpers
class WorkflowBuilder:
    """Helper class for building workflows"""

    def __init__(self, workflow_id: str, name: str, description: str):
        self.workflow = AutomationWorkflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            version="1.0",
            actions=[],
            decision_nodes=[],
        )

    def add_command_action(
        self,
        action_id: str,
        name: str,
        command: str,
        description: str = "",
        safety_level: str = "MEDIUM",
        timeout: Optional[int] = None,
    ) -> "WorkflowBuilder":
        """Add command action to workflow"""

        action = WorkflowAction(
            action_id=action_id,
            action_type=ActionType.COMMAND,
            name=name,
            description=description,
            parameters={"command": command, "safety_level": safety_level},
            timeout_seconds=timeout,
        )

        self.workflow.actions.append(action)
        return self

    def add_ai_analysis_action(self, action_id: str, name: str, analysis_type: str, data_source: str, description: str = "") -> "WorkflowBuilder":
        """Add AI analysis action to workflow"""

        action = WorkflowAction(
            action_id=action_id,
            action_type=ActionType.AI_ANALYSIS,
            name=name,
            description=description,
            parameters={"analysis_type": analysis_type, "data_source": data_source},
        )

        self.workflow.actions.append(action)
        return self

    def add_decision_node(
        self,
        node_id: str,
        name: str,
        conditions: List[WorkflowCondition],
        true_path: List[str],
        false_path: List[str],
        description: str = "",
    ) -> "WorkflowBuilder":
        """Add decision node to workflow"""

        decision_node = DecisionNode(
            node_id=node_id,
            name=name,
            conditions=conditions,
            true_path=true_path,
            false_path=false_path,
            description=description,
        )

        self.workflow.decision_nodes.append(decision_node)
        return self

    def add_notification_action(self, action_id: str, name: str, message: str, recipients: List[str], description: str = "") -> "WorkflowBuilder":
        """Add notification action to workflow"""

        action = WorkflowAction(
            action_id=action_id,
            action_type=ActionType.NOTIFICATION,
            name=name,
            description=description,
            parameters={"message": message, "recipients": recipients},
        )

        self.workflow.actions.append(action)
        return self

    def set_entry_point(self, action_id: str) -> "WorkflowBuilder":
        """Set workflow entry point"""
        self.workflow.entry_point = action_id
        return self

    def set_timeout(self, minutes: int) -> "WorkflowBuilder":
        """Set workflow timeout"""
        self.workflow.timeout_minutes = minutes
        return self

    def enable_learning(self, enabled: bool = True) -> "WorkflowBuilder":
        """Enable/disable workflow learning"""
        self.workflow.learning_enabled = enabled
        return self

    def build(self) -> AutomationWorkflow:
        """Build and return the workflow"""
        return self.workflow


# Pre-defined workflow templates
async def create_incident_response_workflow() -> AutomationWorkflow:
    """Create standard incident response workflow"""
    # Make function truly async
    await asyncio.sleep(0)

    builder = WorkflowBuilder(
        workflow_id="incident_response_standard",
        name="Standard Incident Response",
        description="Automated incident detection, analysis, and response workflow",
    )

    # Detection phase
    builder.add_command_action(
        action_id="detect_anomalies",
        name="Detect Anomalies",
        command="neuraops infra monitor --anomaly-detection --duration 300",
        description="Monitor infrastructure for anomalies",
    )

    # Analysis phase
    builder.add_ai_analysis_action(
        action_id="analyze_incident",
        name="Analyze Incident",
        analysis_type="infrastructure",
        data_source="detect_anomalies_result",
        description="AI analysis of detected anomalies",
    )

    # Decision point
    builder.add_decision_node(
        node_id="severity_check",
        name="Check Severity",
        conditions=[WorkflowCondition("analyze_incident_insight.severity", ConditionOperator.EQUALS, "HIGH")],
        true_path=["immediate_response"],
        false_path=["standard_response"],
        description="Determine response based on incident severity",
    )

    # High severity response
    builder.add_notification_action(
        action_id="immediate_response",
        name="Immediate Alert",
        message="HIGH SEVERITY INCIDENT DETECTED: ${analyze_incident_insight.title}",
        recipients=[OPERATIONS_TEAM_EMAIL, "oncall@company.com"],
    )

    # Standard response
    builder.add_notification_action(
        action_id="standard_response",
        name="Standard Alert",
        message="Incident detected: ${analyze_incident_insight.title}",
        recipients=[OPERATIONS_TEAM_EMAIL],
    )

    return builder.set_entry_point("detect_anomalies").set_timeout(60).build()


async def create_performance_optimization_workflow() -> AutomationWorkflow:
    """Create performance optimization workflow"""
    # Make function truly async
    await asyncio.sleep(0)

    builder = WorkflowBuilder(
        workflow_id="performance_optimization",
        name="Performance Optimization",
        description="Automated performance monitoring and optimization workflow",
    )

    # Monitor performance
    builder.add_command_action(
        action_id="monitor_performance",
        name="Monitor Performance",
        command="neuraops infra performance-analysis --duration 600",
        description="Analyze current performance metrics",
    )

    # AI analysis
    builder.add_ai_analysis_action(
        action_id="analyze_performance",
        name="Analyze Performance",
        analysis_type="performance",
        data_source="monitor_performance_result",
        description="AI-powered performance analysis",
    )

    # Optimization decision
    builder.add_decision_node(
        node_id="optimization_needed",
        name="Check if Optimization Needed",
        conditions=[WorkflowCondition("analyze_performance_insight.confidence", ConditionOperator.GREATER_THAN, 0.8)],
        true_path=["apply_optimizations"],
        false_path=["schedule_next_check"],
        description="Determine if optimization is recommended",
    )

    # Apply optimizations
    builder.add_command_action(
        action_id="apply_optimizations",
        name="Apply Optimizations",
        command="neuraops infra apply-optimizations --recommendations ${analyze_performance_insight}",
        description="Apply AI-recommended optimizations",
    )

    # Schedule next check
    builder.add_notification_action(
        action_id="schedule_next_check",
        name="Schedule Next Check",
        message="Performance check completed. Next check scheduled.",
        recipients=[OPERATIONS_TEAM_EMAIL],
    )

    return builder.set_entry_point("monitor_performance").set_timeout(120).build()


async def create_security_audit_workflow() -> AutomationWorkflow:
    """Create security audit workflow"""
    # Make function truly async
    await asyncio.sleep(0)

    builder = WorkflowBuilder(
        workflow_id="security_audit",
        name="Security Audit",
        description="Automated security scanning and remediation workflow",
    )

    # Security scan
    builder.add_command_action(
        action_id="security_scan",
        name="Security Scan",
        command="neuraops infra security-scan --comprehensive",
        description="Comprehensive security scan",
    )

    # Compliance check
    builder.add_command_action(
        action_id="compliance_check",
        name="Compliance Check",
        command="neuraops infra compliance-check --standard cis --standard pci",
        description="Check compliance against standards",
    )

    # AI security analysis
    builder.add_ai_analysis_action(
        action_id="analyze_security",
        name="Analyze Security",
        analysis_type="security",
        data_source="security_scan_result",
        description="AI analysis of security findings",
    )

    # Critical vulnerability check
    builder.add_decision_node(
        node_id="critical_vulns",
        name="Check Critical Vulnerabilities",
        conditions=[WorkflowCondition("analyze_security_insight.severity", ConditionOperator.EQUALS, "CRITICAL")],
        true_path=["immediate_remediation"],
        false_path=["scheduled_remediation"],
        description="Check for critical vulnerabilities requiring immediate attention",
    )

    # Immediate remediation
    builder.add_command_action(
        action_id="immediate_remediation",
        name="Immediate Remediation",
        command="neuraops ai auto-remediate --security-findings ${security_scan_result} --risk-threshold high",
        description="Immediate remediation of critical issues",
    )

    # Scheduled remediation
    builder.add_notification_action(
        action_id="scheduled_remediation",
        name="Schedule Remediation",
        message="Security audit completed. Remediation plan: ${analyze_security_insight.recommendation}",
        recipients=["security-team@company.com"],
    )

    return builder.set_entry_point("security_scan").set_timeout(180).build()


# Convenience functions
async def create_workflow_orchestrator() -> WorkflowOrchestrator:
    """Create and initialize workflow orchestrator"""
    orchestrator = WorkflowOrchestrator()

    # Register built-in workflows
    incident_workflow = await create_incident_response_workflow()
    await orchestrator.register_workflow(incident_workflow)

    performance_workflow = await create_performance_optimization_workflow()
    await orchestrator.register_workflow(performance_workflow)

    security_workflow = await create_security_audit_workflow()
    await orchestrator.register_workflow(security_workflow)

    return orchestrator
