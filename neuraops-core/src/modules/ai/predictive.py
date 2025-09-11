"""
NeuraOps Predictive Analytics Module
Infrastructure forecasting, anomaly prediction, capacity planning, and proactive issue detection
"""

import asyncio
import logging
import json
import math
import re
import secrets
import statistics
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ...core.engine import get_engine
from ...core.command_executor import CommandExecutor, SafetyLevel
from ...core.structured_output import PredictionResult, SeverityLevel
from ...devops_commander.exceptions import PredictionError

logger = logging.getLogger(__name__)


class PredictionType(Enum):
    """Types of predictions"""

    CAPACITY_FORECAST = "capacity_forecast"
    ANOMALY_PREDICTION = "anomaly_prediction"
    FAILURE_PREDICTION = "failure_prediction"
    COST_FORECAST = "cost_forecast"
    PERFORMANCE_TREND = "performance_trend"


class TimeHorizon(Enum):
    """Time horizons for predictions"""

    SHORT_TERM = "1_day"  # 1 day
    MEDIUM_TERM = "7_days"  # 1 week
    LONG_TERM = "30_days"  # 1 month
    EXTENDED = "90_days"  # 3 months


@dataclass
class MetricDataPoint:
    """Data point for time series analysis"""

    timestamp: datetime
    value: float
    metric_name: str
    resource_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionForecast:
    """Forecast prediction result"""

    metric_name: str
    resource_id: str
    current_value: float
    predicted_values: List[Tuple[datetime, float]]  # (timestamp, predicted_value)
    confidence_intervals: List[Tuple[float, float]]  # (lower_bound, upper_bound)
    trend: str  # "increasing", "decreasing", "stable", "volatile"
    confidence: float  # 0-1 confidence score
    horizon: TimeHorizon
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyPrediction:
    """Prediction of potential anomaly"""

    resource_id: str
    metric_name: str
    predicted_anomaly_time: datetime
    predicted_value: float
    normal_range: Tuple[float, float]
    anomaly_score: float  # 0-1 severity of predicted anomaly
    confidence: float  # 0-1 confidence in prediction
    recommended_actions: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapacityForecast:
    """Capacity planning forecast"""

    resource_type: str
    resource_id: str
    current_utilization: float
    predicted_utilization: Dict[str, float]  # horizon -> utilization
    capacity_exhaustion_date: Optional[datetime]
    recommended_scaling: Dict[str, Any]
    cost_implications: Dict[str, float]
    confidence: float


class PredictiveAnalytics:
    """Predictive analytics engine for infrastructure forecasting"""

    def __init__(self):
        self.command_executor = CommandExecutor()
        self.historical_data: Dict[str, List[MetricDataPoint]] = {}
        self.prediction_history: List[Dict[str, Any]] = []
        self.model_accuracy: Dict[str, float] = {}

    async def forecast_capacity(self, resource_type: str, resource_id: str, horizon: TimeHorizon = TimeHorizon.MEDIUM_TERM) -> CapacityForecast:
        """Forecast resource capacity requirements"""

        try:
            # Get historical data for the resource
            historical_data = await self._collect_historical_capacity_data(resource_type, resource_id)

            if not historical_data:
                raise PredictionError(f"Insufficient historical data for {resource_type}:{resource_id}")

            # Analyze current utilization
            current_utilization = self._calculate_current_utilization(historical_data)

            # Generate forecasts for different horizons
            predicted_utilization = {}

            for h in [TimeHorizon.SHORT_TERM, TimeHorizon.MEDIUM_TERM, TimeHorizon.LONG_TERM]:
                if h.value <= horizon.value or h == horizon:
                    forecast = await self._predict_utilization(historical_data, h)
                    predicted_utilization[h.value] = forecast

            # Determine capacity exhaustion date
            exhaustion_date = self._calculate_capacity_exhaustion(historical_data, predicted_utilization)

            # Generate scaling recommendations
            scaling_recommendations = await self._generate_scaling_recommendations(resource_type, predicted_utilization)

            # Estimate cost implications
            cost_implications = self._estimate_cost_implications(resource_type, predicted_utilization)

            # Calculate confidence based on data quality and trend consistency
            confidence = self._calculate_forecast_confidence(historical_data)

            return CapacityForecast(
                resource_type=resource_type,
                resource_id=resource_id,
                current_utilization=current_utilization,
                predicted_utilization=predicted_utilization,
                capacity_exhaustion_date=exhaustion_date,
                recommended_scaling=scaling_recommendations,
                cost_implications=cost_implications,
                confidence=confidence,
            )

        except Exception as e:
            raise PredictionError(f"Capacity forecasting failed: {str(e)}") from e

    async def predict_anomalies(self, resource_ids: List[str], horizon: TimeHorizon = TimeHorizon.MEDIUM_TERM) -> List[AnomalyPrediction]:
        """Predict potential anomalies in resource metrics"""

        predictions = []

        try:
            for resource_id in resource_ids:
                # Get historical data for anomaly patterns
                historical_data = await self._collect_historical_anomaly_data(resource_id)

                if historical_data:
                    # Analyze patterns and predict future anomalies
                    resource_predictions = await self._predict_resource_anomalies(resource_id, historical_data, horizon)
                    predictions.extend(resource_predictions)

            return predictions

        except Exception as e:
            raise PredictionError(f"Anomaly prediction failed: {str(e)}") from e

    async def analyze_trends(self, metric_data: List[MetricDataPoint]) -> Dict[str, Any]:
        """Analyze trends in metric data"""

        # Make function truly async
        await asyncio.sleep(0)

        if len(metric_data) < 5:
            return {"trend": "insufficient_data", "confidence": 0.0}

        # Sort by timestamp
        sorted_data = sorted(metric_data, key=lambda x: x.timestamp)
        values = [point.value for point in sorted_data]

        # Calculate trend statistics
        trend_analysis = {
            "data_points": len(values),
            "time_span_hours": (sorted_data[-1].timestamp - sorted_data[0].timestamp).total_seconds() / 3600,
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "min_value": min(values),
            "max_value": max(values),
        }

        # Simple trend detection
        if len(values) >= 3:
            # Calculate slope using linear regression approximation
            n = len(values)
            x = list(range(n))
            y = values

            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(xi * yi for xi, yi in zip(x, y))
            sum_x2 = sum(xi * xi for xi in x)

            # Slope calculation
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0

            # Determine trend direction
            if abs(slope) < 0.1:  # Threshold for "stable"
                trend = "stable"
            elif slope > 0:
                trend = "increasing"
            else:
                trend = "decreasing"

            # Calculate trend strength
            trend_strength = min(abs(slope) * 10, 1.0)  # Normalize to 0-1

            trend_analysis.update(
                {
                    "trend": trend,
                    "slope": slope,
                    "trend_strength": trend_strength,
                    "confidence": min(0.9, trend_strength + 0.1),  # Higher confidence for stronger trends
                }
            )
        else:
            trend_analysis.update({"trend": "insufficient_data", "confidence": 0.0})

        # Detect volatility
        if trend_analysis["std_dev"] > trend_analysis["mean"] * 0.5:  # High relative std dev
            trend_analysis["volatility"] = "high"
        elif trend_analysis["std_dev"] > trend_analysis["mean"] * 0.2:
            trend_analysis["volatility"] = "medium"
        else:
            trend_analysis["volatility"] = "low"

        return trend_analysis

    async def _collect_kubernetes_metrics(self, resource_id: str) -> List[MetricDataPoint]:
        """Collect Kubernetes resource metrics"""
        data_points = []
        cmd = f"kubectl top pod {resource_id} --no-headers"
        result = await self.command_executor.execute_async(command=cmd, timeout=30, safety_level=SafetyLevel.LOW)

        if result.success and result.stdout:
            parts = result.stdout.strip().split()
            if len(parts) >= 3:
                cpu_usage = parts[1].replace("m", "")
                memory_usage = parts[2].replace("Mi", "")

                data_points.append(
                    MetricDataPoint(
                        timestamp=datetime.now(),
                        value=(float(cpu_usage) / 10 if "m" in parts[1] else float(cpu_usage)),
                        metric_name="cpu_usage",
                        resource_id=resource_id,
                    )
                )

                data_points.append(
                    MetricDataPoint(
                        timestamp=datetime.now(),
                        value=float(memory_usage),
                        metric_name="memory_usage",
                        resource_id=resource_id,
                    )
                )
        return data_points

    async def _collect_docker_metrics(self, resource_id: str) -> List[MetricDataPoint]:
        """Collect Docker container metrics"""
        data_points = []
        cmd = f"docker stats {resource_id} --no-stream --format 'table {{{{.CPUPerc}}}}\\t{{{{.MemUsage}}}}'"
        result = await self.command_executor.execute_async(command=cmd, timeout=30, safety_level=SafetyLevel.LOW)

        if result.success and result.stdout:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:  # Skip header
                parts = lines[1].split("\\t")
                if len(parts) >= 2:
                    cpu_percent = float(parts[0].replace("%", ""))

                    data_points.append(
                        MetricDataPoint(
                            timestamp=datetime.now(),
                            value=cpu_percent,
                            metric_name="cpu_usage",
                            resource_id=resource_id,
                        )
                    )
        return data_points

    def _calculate_cpu_variation(self, i: int, secure_random: secrets.SystemRandom) -> float:
        """Helper: Calculate CPU variation with secure randomness"""
        return 10.0 * math.sin(i * 0.5) + 5.0 * (0.5 - secure_random.random())

    def _generate_daily_cycle_value(self, i: int) -> float:
        """Helper: Generate daily cycle pattern value"""
        return 20.0 * math.sin(i * 2 * math.pi / 24)

    def _generate_anomaly_spike(self, secure_random: secrets.SystemRandom) -> float:
        """Helper: Generate anomaly spike value with secure randomness"""
        return secure_random.uniform(50, 100)

    def _generate_random_variation(self, secure_random: secrets.SystemRandom) -> float:
        """Helper: Generate random variation with secure randomness"""
        return secure_random.gauss(0, 5)

    def _generate_simulated_metrics(self, resource_id: str) -> List[MetricDataPoint]:
        """Generate simulated historical data for demonstration"""
        data_points = []
        current_time = datetime.now()
        secure_random = secrets.SystemRandom()  # Cryptographically secure PRNG

        for i in range(24):  # Last 24 hours
            timestamp = current_time - timedelta(hours=i)

            # Simulate realistic metrics with some variation
            base_cpu = 45.0  # Base CPU usage
            cpu_variation = self._calculate_cpu_variation(i, secure_random)

            data_points.append(
                MetricDataPoint(
                    timestamp=timestamp,
                    value=max(0, min(100, base_cpu + cpu_variation)),
                    metric_name="cpu_usage",
                    resource_id=resource_id,
                )
            )
        return data_points

    async def _collect_historical_capacity_data(self, resource_type: str, resource_id: str) -> List[MetricDataPoint]:
        """Collect historical capacity data for a resource"""
        data_points = []

        try:
            # Collect real-time metrics based on resource type
            if resource_type.lower() == "kubernetes":
                data_points.extend(await self._collect_kubernetes_metrics(resource_id))
            elif resource_type.lower() == "docker":
                data_points.extend(await self._collect_docker_metrics(resource_id))

            # Add simulated historical data for demonstration
            data_points.extend(self._generate_simulated_metrics(resource_id))

            return data_points

        except Exception as e:
            logger.error(f"Failed to collect historical data: {str(e)}")
            return []

    async def _collect_historical_anomaly_data(self, resource_id: str) -> List[MetricDataPoint]:
        """Collect historical data for anomaly analysis"""

        # Make function truly async
        await asyncio.sleep(0)

        # In a real implementation, this would query historical anomaly data
        # For now, we'll return sample data

        data_points = []
        current_time = datetime.now()
        secure_random = secrets.SystemRandom()  # Cryptographically secure PRNG

        # Simulate historical anomalies
        for i in range(168):  # Last week (hourly data)
            timestamp = current_time - timedelta(hours=i)

            # Simulate normal behavior with occasional spikes
            base_value = 50.0
            daily_cycle = self._generate_daily_cycle_value(i)

            # Occasionally add anomalies
            if i % 47 == 0:  # Anomaly every ~2 days
                anomaly_spike = self._generate_anomaly_spike(secure_random)
                value = base_value + daily_cycle + anomaly_spike
            else:
                random_variation = self._generate_random_variation(secure_random)
                value = base_value + daily_cycle + random_variation

            data_points.append(
                MetricDataPoint(
                    timestamp=timestamp,
                    value=max(0, min(100, value)),
                    metric_name="cpu_usage",
                    resource_id=resource_id,
                    metadata={"anomaly": i % 47 == 0},
                )
            )

        return data_points

    def _calculate_current_utilization(self, data_points: List[MetricDataPoint]) -> float:
        """Calculate current resource utilization"""

        if not data_points:
            return 0.0

        # Get the most recent data points (last hour)
        recent_time = datetime.now() - timedelta(hours=1)
        recent_points = [p for p in data_points if p.timestamp > recent_time]

        if not recent_points:
            # Fallback to most recent point
            most_recent = max(data_points, key=lambda x: x.timestamp)
            return most_recent.value

        # Average utilization over the last hour
        return sum(p.value for p in recent_points) / len(recent_points)

    async def _predict_utilization(self, data_points: List[MetricDataPoint], horizon: TimeHorizon) -> float:
        """Predict utilization for given time horizon"""

        if len(data_points) < 5:
            # Insufficient data for prediction
            return self._calculate_current_utilization(data_points)

        # Analyze trend
        trend_analysis = await self.analyze_trends(data_points)

        current_value = self._calculate_current_utilization(data_points)

        # Simple linear prediction based on trend
        slope = trend_analysis.get("slope", 0)

        # Convert horizon to hours
        horizon_hours = {
            TimeHorizon.SHORT_TERM: 24,
            TimeHorizon.MEDIUM_TERM: 168,  # 7 days
            TimeHorizon.LONG_TERM: 720,  # 30 days
            TimeHorizon.EXTENDED: 2160,  # 90 days
        }[horizon]

        # Predict based on linear trend
        predicted_value = current_value + (slope * horizon_hours)

        # Add some dampening for long-term predictions (systems tend to stabilize)
        dampening_factor = 1.0 - (horizon_hours / 2160) * 0.3  # Reduce by up to 30% for extended horizon
        predicted_value = current_value + (predicted_value - current_value) * dampening_factor

        # Ensure realistic bounds
        predicted_value = max(0, min(100, predicted_value))

        return predicted_value

    def _calculate_capacity_exhaustion(self, data_points: List[MetricDataPoint], predicted_utilization: Dict[str, float]) -> Optional[datetime]:
        """Calculate when capacity will be exhausted"""

        # Define capacity exhaustion threshold
        exhaustion_threshold = 95.0  # 95% utilization

        current_value = self._calculate_current_utilization(data_points)

        # Check if we're already at capacity
        if current_value >= exhaustion_threshold:
            return datetime.now()

        # Find when predicted utilization exceeds threshold
        for horizon_str, predicted_value in predicted_utilization.items():
            if predicted_value >= exhaustion_threshold:
                # Calculate approximate date
                horizon_days = {"1_day": 1, "7_days": 7, "30_days": 30, "90_days": 90}[horizon_str]

                # Linear interpolation to find more precise date
                if current_value < predicted_value:
                    progress_ratio = (exhaustion_threshold - current_value) / (predicted_value - current_value)
                    days_to_exhaustion = horizon_days * progress_ratio
                    return datetime.now() + timedelta(days=days_to_exhaustion)

        return None  # Capacity won't be exhausted in forecast horizon

    async def _generate_scaling_recommendations(
        self,
        resource_type: str,
        predicted_utilization: Dict[str, float],
    ) -> Dict[str, Any]:
        """Generate scaling recommendations based on predictions"""

        # Make function truly async
        await asyncio.sleep(0)

        recommendations = {}

        # Check if scaling is needed
        max_predicted = max(predicted_utilization.values())

        if max_predicted > 80:  # High utilization predicted
            if resource_type.lower() == "kubernetes":
                recommendations["action"] = "scale_up"
                recommendations["method"] = "horizontal_pod_autoscaler"
                recommendations["target_replicas"] = math.ceil(max_predicted / 60)  # Target 60% utilization
                recommendations["urgency"] = "high" if max_predicted > 90 else "medium"

            elif resource_type.lower() == "docker":
                recommendations["action"] = "scale_up"
                recommendations["method"] = "container_scaling"
                recommendations["additional_instances"] = math.ceil((max_predicted - 70) / 30)
                recommendations["urgency"] = "high" if max_predicted > 90 else "medium"

            else:
                recommendations["action"] = "monitor_closely"
                recommendations["method"] = "increase_monitoring_frequency"
                recommendations["urgency"] = "medium"

        elif max_predicted < 30:  # Low utilization predicted
            recommendations["action"] = "scale_down"
            recommendations["method"] = "reduce_resources"
            recommendations["potential_savings"] = f"${(70 - max_predicted) * 2:.2f}/month"
            recommendations["urgency"] = "low"

        else:
            recommendations["action"] = "maintain"
            recommendations["method"] = "current_configuration"
            recommendations["urgency"] = "none"

        return recommendations

    def _estimate_cost_implications(
        self,
        resource_type: str,
        predicted_utilization: Dict[str, float],
    ) -> Dict[str, float]:
        """Estimate cost implications of predicted changes"""

        # Simple cost estimation model
        base_cost_per_hour = {
            "kubernetes": 0.50,  # Per pod per hour
            "docker": 0.25,  # Per container per hour
            "vm": 1.00,  # Per VM per hour
            "cloud": 2.00,  # Per cloud instance per hour
        }.get(resource_type.lower(), 0.50)

        current_monthly_cost = base_cost_per_hour * 24 * 30

        cost_implications = {"current_monthly_cost": current_monthly_cost}

        for horizon, predicted_util in predicted_utilization.items():
            # If utilization goes above 80%, we might need to scale up
            if predicted_util > 80:
                scaling_factor = math.ceil(predicted_util / 60)  # Target 60% utilization
                future_cost = current_monthly_cost * scaling_factor
                cost_implications[f"predicted_cost_{horizon}"] = future_cost
                cost_implications[f"cost_increase_{horizon}"] = future_cost - current_monthly_cost

            # If utilization is very low, we might scale down
            elif predicted_util < 30:
                scaling_factor = 0.5  # Scale down by half
                future_cost = current_monthly_cost * scaling_factor
                cost_implications[f"predicted_cost_{horizon}"] = future_cost
                cost_implications[f"cost_savings_{horizon}"] = current_monthly_cost - future_cost

            else:
                cost_implications[f"predicted_cost_{horizon}"] = current_monthly_cost

        return cost_implications

    def _calculate_forecast_confidence(self, data_points: List[MetricDataPoint]) -> float:
        """Calculate confidence in forecast based on data quality"""

        if len(data_points) < 5:
            return 0.1  # Very low confidence with insufficient data

        # Factors affecting confidence:
        # 1. Amount of data
        data_quantity_score = min(1.0, len(data_points) / 100)  # Full score at 100+ points

        # 2. Data recency
        most_recent = max(data_points, key=lambda x: x.timestamp)
        hours_since_recent = (datetime.now() - most_recent.timestamp).total_seconds() / 3600
        recency_score = max(0.1, 1.0 - (hours_since_recent / 24))  # Full score if data is within last hour

        # 3. Data consistency (low variance indicates stable patterns)
        values = [p.value for p in data_points]
        if len(values) > 1:
            mean_value = statistics.mean(values)
            std_dev = statistics.stdev(values)
            consistency_score = max(0.1, 1.0 - (std_dev / mean_value) if mean_value > 0 else 0.5)
        else:
            consistency_score = 0.5

        # Weighted average
        confidence = data_quantity_score * 0.3 + recency_score * 0.4 + consistency_score * 0.3

        return round(confidence, 2)

    async def _predict_resource_anomalies(self, resource_id: str, historical_data: List[MetricDataPoint], horizon: TimeHorizon) -> List[AnomalyPrediction]:
        """Predict anomalies for a specific resource"""

        # Make function truly async
        await asyncio.sleep(0)

        predictions = []

        # Analyze historical anomalies
        anomaly_points = [p for p in historical_data if p.metadata.get("anomaly", False)]
        normal_points = [p for p in historical_data if not p.metadata.get("anomaly", False)]

        if not normal_points:
            return predictions

        # Calculate normal range
        normal_values = [p.value for p in normal_points]
        mean_normal = statistics.mean(normal_values)
        std_normal = statistics.stdev(normal_values) if len(normal_values) > 1 else 0

        normal_range = (mean_normal - 2 * std_normal, mean_normal + 2 * std_normal)

        # Analyze anomaly patterns
        if anomaly_points:
            # Calculate time between anomalies
            anomaly_times = [p.timestamp for p in anomaly_points]
            anomaly_times.sort()

            if len(anomaly_times) > 1:
                intervals = [(anomaly_times[i + 1] - anomaly_times[i]).total_seconds() / 3600 for i in range(len(anomaly_times) - 1)]
                avg_interval = statistics.mean(intervals)

                # Predict next anomaly
                last_anomaly = max(anomaly_times)
                next_anomaly_time = last_anomaly + timedelta(hours=avg_interval)

                # Only predict if within our horizon
                horizon_delta = {
                    TimeHorizon.SHORT_TERM: timedelta(days=1),
                    TimeHorizon.MEDIUM_TERM: timedelta(days=7),
                    TimeHorizon.LONG_TERM: timedelta(days=30),
                    TimeHorizon.EXTENDED: timedelta(days=90),
                }[horizon]

                if next_anomaly_time <= datetime.now() + horizon_delta:
                    # Predict anomaly characteristics
                    anomaly_values = [p.value for p in anomaly_points]
                    predicted_anomaly_value = statistics.mean(anomaly_values)

                    confidence = min(0.8, len(anomaly_points) / 10)  # Higher confidence with more historical anomalies

                    predictions.append(
                        AnomalyPrediction(
                            resource_id=resource_id,
                            metric_name="cpu_usage",
                            predicted_anomaly_time=next_anomaly_time,
                            predicted_value=predicted_anomaly_value,
                            normal_range=normal_range,
                            anomaly_score=min(1.0, (predicted_anomaly_value - mean_normal) / (3 * std_normal)),
                            confidence=confidence,
                            recommended_actions=[
                                "Increase monitoring frequency before predicted anomaly",
                                "Prepare scaling resources",
                                "Review application logs for pattern triggers",
                            ],
                            metadata={
                                "historical_anomalies": len(anomaly_points),
                                "average_interval_hours": avg_interval,
                            },
                        )
                    )

        return predictions

    async def generate_capacity_plan(
        self,
        resource_configs: List[Dict[str, Any]],
        planning_horizon: TimeHorizon = TimeHorizon.LONG_TERM,
    ) -> Dict[str, Any]:
        """Generate comprehensive capacity planning recommendations"""

        capacity_plan = {
            "timestamp": datetime.now().isoformat(),
            "planning_horizon": planning_horizon.value,
            "resource_forecasts": [],
            "scaling_timeline": [],
            "cost_projections": {},
            "risk_assessment": {},
            "recommendations": [],
        }

        total_current_cost = 0
        total_predicted_cost = 0

        for resource_config in resource_configs:
            resource_type = resource_config.get("type")
            resource_id = resource_config.get("id")

            try:
                # Generate forecast for this resource
                forecast = await self.forecast_capacity(resource_type, resource_id, planning_horizon)

                capacity_plan["resource_forecasts"].append(
                    {
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "current_utilization": forecast.current_utilization,
                        "predicted_utilization": forecast.predicted_utilization,
                        "capacity_exhaustion_date": (forecast.capacity_exhaustion_date.isoformat() if forecast.capacity_exhaustion_date else None),
                        "recommended_scaling": forecast.recommended_scaling,
                        "confidence": forecast.confidence,
                    }
                )

                # Add to cost projections
                total_current_cost += forecast.cost_implications.get("current_monthly_cost", 0)
                total_predicted_cost += forecast.cost_implications.get(f"predicted_cost_{planning_horizon.value}", 0)

                # Add scaling events to timeline
                if forecast.capacity_exhaustion_date:
                    capacity_plan["scaling_timeline"].append(
                        {
                            "date": forecast.capacity_exhaustion_date.isoformat(),
                            "resource": f"{resource_type}:{resource_id}",
                            "action": forecast.recommended_scaling.get("action", "scale_up"),
                            "urgency": forecast.recommended_scaling.get("urgency", "medium"),
                        }
                    )

            except Exception as e:
                logger.error(f"Failed to forecast {resource_type}:{resource_id}: {str(e)}")
                continue

        # Sort timeline by date
        capacity_plan["scaling_timeline"].sort(key=lambda x: x["date"])

        # Add cost projections
        capacity_plan["cost_projections"] = {
            "current_monthly_cost": total_current_cost,
            "predicted_monthly_cost": total_predicted_cost,
            "cost_change": total_predicted_cost - total_current_cost,
            "cost_change_percentage": (((total_predicted_cost - total_current_cost) / total_current_cost * 100) if total_current_cost > 0 else 0),
        }

        # Risk assessment
        high_risk_resources = len(
            [f for f in capacity_plan["resource_forecasts"] if f["capacity_exhaustion_date"] and datetime.fromisoformat(f["capacity_exhaustion_date"]) <= datetime.now() + timedelta(days=7)]
        )

        # Determine risk level
        if high_risk_resources > 0:
            risk_level = "high"
        elif total_predicted_cost > total_current_cost * 1.2:
            risk_level = "medium"
        else:
            risk_level = "low"

        capacity_plan["risk_assessment"] = {
            "high_risk_resources": high_risk_resources,
            "total_resources": len(resource_configs),
            "risk_level": risk_level,
        }

        # Generate high-level recommendations
        recommendations = await self._generate_capacity_recommendations(capacity_plan)
        capacity_plan["recommendations"] = recommendations

        return capacity_plan

    async def _generate_capacity_recommendations(self, capacity_plan: Dict[str, Any]) -> List[str]:
        """Generate high-level capacity planning recommendations"""

        engine = get_engine()

        # Prepare summary for AI analysis
        summary = {
            "total_resources": capacity_plan["risk_assessment"]["total_resources"],
            "high_risk_resources": capacity_plan["risk_assessment"]["high_risk_resources"],
            "cost_change_percentage": capacity_plan["cost_projections"]["cost_change_percentage"],
            "scaling_events": len(capacity_plan["scaling_timeline"]),
        }

        prompt = f"""
Generate capacity planning recommendations based on this analysis:

{json.dumps(summary, indent=2)}

Provide 3-5 actionable recommendations focusing on:
1. Resource optimization
2. Cost management
3. Risk mitigation
4. Performance assurance

Format as a numbered list.
"""

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are a capacity planning expert providing strategic infrastructure recommendations.",
            max_tokens=768,
        )

        # Extract numbered recommendations
        recommendations = []
        for line in response.strip().split(
            "\
"
        ):
            if re.match(r"^\\d+\\.", line):
                recommendation = re.sub(r"^\\d+\\.\\s*", "", line).strip()
                if recommendation:
                    recommendations.append(recommendation)

        return recommendations

    async def predict_failures(self, resource_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Predict potential system failures"""

        failure_predictions = []

        for resource_config in resource_configs:
            resource_type = resource_config.get("type")
            resource_id = resource_config.get("id")

            try:
                # Collect health history
                historical_data = await self._collect_historical_capacity_data(resource_type, resource_id)

                # Analyze failure patterns
                failure_indicators = self._analyze_failure_indicators(historical_data)

                if failure_indicators["risk_score"] > 0.6:  # High risk threshold
                    failure_predictions.append(
                        {
                            "resource_type": resource_type,
                            "resource_id": resource_id,
                            "risk_score": failure_indicators["risk_score"],
                            "predicted_failure_time": failure_indicators.get("predicted_failure_time"),
                            "failure_indicators": failure_indicators["indicators"],
                            "preventive_actions": failure_indicators["preventive_actions"],
                            "confidence": failure_indicators["confidence"],
                        }
                    )

            except Exception as e:
                logger.error(f"Failure prediction failed for {resource_type}:{resource_id}: {str(e)}")
                continue

        return failure_predictions

    def _check_high_utilization_indicator(self, recent_values: List[float]) -> Tuple[str, float]:
        """Check for sustained high utilization indicator"""
        if recent_values and statistics.mean(recent_values) > 90:
            return "Sustained high resource utilization (>90%)", 0.3
        return "", 0.0

    def _check_increasing_trend_indicator(self, values: List[float]) -> Tuple[str, float]:
        """Check for increasing trend indicator"""
        if len(values) >= 10:
            recent_trend = values[-5:]  # Last 5 values
            older_trend = values[-10:-5]  # Previous 5 values

            if statistics.mean(recent_trend) > statistics.mean(older_trend) * 1.2:
                return "Rapidly increasing resource utilization trend", 0.2
        return "", 0.0

    def _check_volatility_indicator(self, values: List[float]) -> Tuple[str, float]:
        """Check for high volatility indicator"""
        if len(values) > 1:
            std_dev = statistics.stdev(values)
            mean_val = statistics.mean(values)

            if std_dev > mean_val * 0.5:  # High relative volatility
                return "High volatility in resource metrics", 0.15
        return "", 0.0

    def _check_capacity_spikes_indicator(self, recent_values: List[float]) -> Tuple[str, float]:
        """Check for capacity spikes indicator"""
        if not recent_values:
            return "", 0.0

        near_capacity_count = len([v for v in recent_values if v > 95])
        if near_capacity_count > len(recent_values) * 0.2:  # 20% of recent values near capacity
            return "Frequent resource usage spikes near capacity", 0.25
        return "", 0.0

    def _generate_preventive_actions(self, indicators: List[str]) -> List[str]:
        """Generate preventive actions based on indicators"""
        preventive_actions = []
        indicators_str = str(indicators).lower()

        if "high resource utilization" in indicators_str:
            preventive_actions.extend(["Scale up resources immediately", "Optimize resource-intensive processes"])

        if "increasing" in indicators_str:
            preventive_actions.extend(["Implement auto-scaling policies", "Review capacity planning"])

        if "volatility" in indicators_str:
            preventive_actions.extend(["Investigate causes of metric volatility", "Implement more aggressive monitoring"])

        if "spikes" in indicators_str:
            preventive_actions.extend(["Set up predictive scaling", "Analyze spike trigger patterns"])

        return preventive_actions

    def _analyze_failure_indicators(self, data_points: List[MetricDataPoint]) -> Dict[str, Any]:
        """Analyze indicators that might predict failure"""
        indicators = []
        risk_score = 0.0

        if not data_points:
            return {
                "risk_score": 0.0,
                "indicators": [],
                "preventive_actions": [],
                "confidence": 0.0,
            }

        values = [p.value for p in data_points]
        recent_values = [p.value for p in data_points if (datetime.now() - p.timestamp).hours <= 24]

        # Check all indicators using helper functions
        indicator_checks = [
            self._check_high_utilization_indicator(recent_values),
            self._check_increasing_trend_indicator(values),
            self._check_volatility_indicator(values),
            self._check_capacity_spikes_indicator(recent_values),
        ]

        # Collect indicators and accumulate risk score
        for indicator, score in indicator_checks:
            if indicator:
                indicators.append(indicator)
                risk_score += score

        # Generate preventive actions
        preventive_actions = self._generate_preventive_actions(indicators)

        # Estimate failure time if risk is high
        predicted_failure_time = None
        if risk_score > 0.7 and len(values) >= 5:
            recent_avg = statistics.mean(values[-5:])
            if recent_avg > 85:  # Close to capacity
                days_to_failure = max(1, int(7 * (1 - risk_score)))
                predicted_failure_time = (datetime.now() + timedelta(days=days_to_failure)).isoformat()

        # Calculate confidence based on data quality and pattern clarity
        confidence = min(0.9, 0.3 + (len(data_points) / 100) + (len(indicators) * 0.1))

        return {
            "risk_score": min(1.0, risk_score),
            "indicators": indicators,
            "preventive_actions": preventive_actions,
            "predicted_failure_time": predicted_failure_time,
            "confidence": confidence,
        }

    async def generate_insights_summary(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate AI-powered summary of all predictions"""

        engine = get_engine()

        # Prepare summary data
        summary_data = {
            "total_predictions": len(predictions),
            "high_risk_count": len([p for p in predictions if p.get("risk_score", 0) > 0.7]),
            "predicted_failures": len([p for p in predictions if p.get("predicted_failure_time")]),
            "avg_confidence": (statistics.mean([p.get("confidence", 0) for p in predictions]) if predictions else 0),
        }

        prompt = f"""
Analyze these predictive analytics results:

{json.dumps(summary_data, indent=2)}

Provide insights including:
1. Overall infrastructure health outlook
2. Key risks and concerns
3. Strategic recommendations
4. Priority actions

Focus on actionable insights for infrastructure management.
"""

        response = await engine.generate_text(
            prompt=prompt,
            system_prompt="You are a senior infrastructure architect analyzing predictive analytics results.",
            max_tokens=1024,
        )

        return {
            "ai_insights": response,
            "summary_metrics": summary_data,
            "timestamp": datetime.now().isoformat(),
        }


# Convenience functions for predictive analytics
async def quick_capacity_forecast(resource_type: str, resource_id: str) -> PredictionResult:
    """Quick capacity forecast for a resource"""

    analytics = PredictiveAnalytics()

    try:
        forecast = await analytics.forecast_capacity(resource_type, resource_id, TimeHorizon.MEDIUM_TERM)

        return PredictionResult(
            success=True,
            predictions=[forecast],
            summary={
                "current_utilization": forecast.current_utilization,
                "predicted_utilization_7_days": forecast.predicted_utilization.get("7_days", 0),
                "scaling_needed": forecast.recommended_scaling.get("action") != "maintain",
                "confidence": forecast.confidence,
            },
            severity=(SeverityLevel.WARNING if forecast.capacity_exhaustion_date else SeverityLevel.INFO),
        )

    except Exception as e:
        return PredictionResult(success=False, error_message=str(e), severity=SeverityLevel.ERROR)


async def predict_infrastructure_anomalies(resource_ids: List[str]) -> PredictionResult:
    """Predict anomalies across multiple resources"""

    analytics = PredictiveAnalytics()

    try:
        predictions = await analytics.predict_anomalies(resource_ids, TimeHorizon.MEDIUM_TERM)

        high_risk_predictions = [p for p in predictions if p.anomaly_score > 0.7]

        return PredictionResult(
            success=True,
            predictions=predictions,
            summary={
                "total_predictions": len(predictions),
                "high_risk_anomalies": len(high_risk_predictions),
                "next_predicted_anomaly": (min([p.predicted_anomaly_time for p in predictions]) if predictions else None),
                "average_confidence": (statistics.mean([p.confidence for p in predictions]) if predictions else 0),
            },
            severity=SeverityLevel.HIGH if high_risk_predictions else SeverityLevel.INFO,
        )

    except Exception as e:
        return PredictionResult(success=False, error_message=str(e), severity=SeverityLevel.ERROR)


async def comprehensive_predictive_analysis(
    resource_configs: List[Dict[str, Any]],
) -> PredictionResult:
    """Comprehensive predictive analysis including capacity, anomalies, and failures"""

    analytics = PredictiveAnalytics()

    try:
        # Generate capacity plan
        capacity_plan = await analytics.generate_capacity_plan(resource_configs, TimeHorizon.LONG_TERM)

        # Predict failures
        failure_predictions = await analytics.predict_failures(resource_configs)

        # Generate AI insights summary
        all_predictions = {
            "capacity_plan": capacity_plan,
            "failure_predictions": failure_predictions,
        }

        insights_summary = await analytics.generate_insights_summary(failure_predictions)

        return PredictionResult(
            success=True,
            predictions=all_predictions,
            summary={
                "capacity_plan": capacity_plan,
                "failure_predictions": len(failure_predictions),
                "ai_insights": insights_summary,
                "total_cost_change": capacity_plan["cost_projections"]["cost_change"],
                "risk_level": capacity_plan["risk_assessment"]["risk_level"],
            },
            severity=(SeverityLevel.HIGH if capacity_plan["risk_assessment"]["risk_level"] == "high" else SeverityLevel.INFO),
        )

    except Exception as e:
        return PredictionResult(success=False, error_message=str(e), severity=SeverityLevel.ERROR)
