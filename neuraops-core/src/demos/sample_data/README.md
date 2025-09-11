# NeuraOps Demo Sample Data

This directory contains sample data files used by NeuraOps demo scenarios. The data is automatically generated when demos are run if the files don't already exist.

## Data Categories

### Logs Data (`demo_logs/`)
- `error_spike.log` - Sample application logs with simulated error spike
- `normal_operation.log` - Baseline application logs during normal operation

### Metrics Data (`demo_metrics/`)
- `performance_baseline.json` - Performance metrics baseline
- `optimization_results.json` - Post-optimization performance metrics
- `capacity_history.json` - Historical capacity utilization data
- `anomaly_patterns.json` - Historical anomaly patterns for prediction

### Security Data (`demo_security/`)
- `vuln_scan.json` - Sample vulnerability scan results
- `compliance_baseline.json` - Compliance assessment baseline

### Infrastructure Templates (`demo_templates/`)
- `webapp_config.json` - Web application configuration template
- `k8s_manifests/` - Sample Kubernetes manifests
- `docker_templates/` - Sample Docker configurations

### Complete Workflow Data (`demo_complete/`)
- `initial_state.json` - Initial infrastructure assessment
- `improvement_plan.json` - AI-generated improvement plan

## Data Generation

Sample data is automatically generated with realistic patterns:

- **Time series data** includes daily cycles, gradual trends, and random noise
- **Log data** includes realistic error patterns and severity distributions  
- **Security data** reflects common vulnerability types and compliance gaps
- **Infrastructure data** represents typical deployment configurations

## Usage in Demos

Each demo scenario specifies which sample data files it requires in the `sample_data_files` list. The demo engine automatically:

1. Creates the sample data directory structure
2. Generates missing sample data files before running the demo
3. Uses realistic data patterns appropriate for each demo scenario

## Customization

You can replace any generated sample data files with your own data to customize demo scenarios for your specific use case. Just ensure the file format matches what the demo expects.
