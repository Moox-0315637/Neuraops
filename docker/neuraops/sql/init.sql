-- NeuraOps Core API Database Schema
-- PostgreSQL initialization script

-- Create database if not exists (handled by docker-compose environment variables)
-- Database: neuraops
-- User: neuraops

-- ====================================
-- EXTENSIONS
-- ====================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ====================================
-- AGENTS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS agents (
    agent_id VARCHAR(255) PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    capabilities TEXT[] NOT NULL DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'disconnected', 'error')),
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    api_key_hash VARCHAR(255),
    jwt_token_hash VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for agents table
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_hostname ON agents(hostname);
CREATE INDEX IF NOT EXISTS idx_agents_last_seen ON agents(last_seen);
CREATE INDEX IF NOT EXISTS idx_agents_capabilities ON agents USING GIN(capabilities);

-- ====================================
-- COMMAND EXECUTIONS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS command_executions (
    command_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    command_text TEXT NOT NULL,
    description TEXT,
    action_type VARCHAR(50) NOT NULL,
    safety_level VARCHAR(20) NOT NULL CHECK (safety_level IN ('safe', 'cautious', 'risky', 'dangerous')),
    requested_by VARCHAR(255) NOT NULL REFERENCES agents(agent_id),
    target_agents TEXT[] NOT NULL DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'timeout')),
    exit_code INTEGER,
    stdout TEXT,
    stderr TEXT,
    execution_time_seconds DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    timeout_seconds INTEGER DEFAULT 300,
    requires_approval BOOLEAN DEFAULT false,
    approved_by VARCHAR(255) REFERENCES agents(agent_id),
    approved_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for command_executions table
CREATE INDEX IF NOT EXISTS idx_command_executions_status ON command_executions(status);
CREATE INDEX IF NOT EXISTS idx_command_executions_created_at ON command_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_command_executions_requested_by ON command_executions(requested_by);
CREATE INDEX IF NOT EXISTS idx_command_executions_safety_level ON command_executions(safety_level);

-- ====================================
-- WORKFLOW EXECUTIONS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS workflow_executions (
    execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_name VARCHAR(200) NOT NULL,
    template_id VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('draft', 'pending', 'running', 'paused', 'completed', 'failed', 'cancelled')),
    created_by VARCHAR(255) NOT NULL REFERENCES agents(agent_id),
    assigned_agents TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    context_variables JSONB DEFAULT '{}',
    step_results JSONB DEFAULT '{}',
    current_step VARCHAR(100),
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for workflow_executions table
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_created_by ON workflow_executions(created_by);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_created_at ON workflow_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_template_id ON workflow_executions(template_id);

-- ====================================
-- WORKFLOW TEMPLATES TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS workflow_templates (
    template_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) CHECK (category IN ('infrastructure', 'incident', 'maintenance', 'deployment')),
    version VARCHAR(20) DEFAULT '1.0.0',
    author VARCHAR(255),
    tags TEXT[] DEFAULT '{}',
    min_safety_level VARCHAR(20) DEFAULT 'cautious',
    required_capabilities TEXT[] DEFAULT '{}',
    steps JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for workflow_templates table
CREATE INDEX IF NOT EXISTS idx_workflow_templates_category ON workflow_templates(category);
CREATE INDEX IF NOT EXISTS idx_workflow_templates_tags ON workflow_templates USING GIN(tags);

-- ====================================
-- AGENT METRICS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS agent_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id),
    cpu_usage DECIMAL(5, 2) CHECK (cpu_usage >= 0 AND cpu_usage <= 100),
    memory_usage DECIMAL(5, 2) CHECK (memory_usage >= 0 AND memory_usage <= 100),
    disk_usage DECIMAL(5, 2) CHECK (disk_usage >= 0 AND disk_usage <= 100),
    active_tasks INTEGER DEFAULT 0 CHECK (active_tasks >= 0),
    completed_tasks INTEGER DEFAULT 0 CHECK (completed_tasks >= 0),
    error_count INTEGER DEFAULT 0 CHECK (error_count >= 0),
    uptime_seconds INTEGER CHECK (uptime_seconds >= 0),
    system_info JSONB DEFAULT '{}',
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for agent_metrics table
CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent_id ON agent_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_collected_at ON agent_metrics(collected_at DESC);

-- Partitioning for metrics (optional for large-scale deployments)
-- Can be enabled by creating partitions by month/week

-- ====================================
-- AUDIT LOG TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    actor_id VARCHAR(255),
    actor_type VARCHAR(50) DEFAULT 'agent',
    target_type VARCHAR(100),
    target_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    result VARCHAR(50) CHECK (result IN ('success', 'failure', 'partial')),
    ip_address INET,
    user_agent TEXT,
    request_data JSONB DEFAULT '{}',
    response_data JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for audit_logs table
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_id ON audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- ====================================
-- API KEYS TABLE
-- ====================================
CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    capabilities TEXT[] DEFAULT '{}',
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count INTEGER DEFAULT 0
);

-- Indexes for api_keys table
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);

-- ====================================
-- FUNCTIONS & TRIGGERS
-- ====================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflow_templates_updated_at BEFORE UPDATE ON workflow_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to clean old metrics (retention policy)
CREATE OR REPLACE FUNCTION clean_old_metrics()
RETURNS void AS $$
BEGIN
    DELETE FROM agent_metrics 
    WHERE collected_at < NOW() - INTERVAL '7 days';
    
    DELETE FROM audit_logs 
    WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- ====================================
-- DEFAULT DATA
-- ====================================

-- Insert default workflow templates
INSERT INTO workflow_templates (template_id, name, description, category, steps) 
VALUES 
    ('health-check-basic', 'Basic Health Check', 'Perform basic system health checks', 'maintenance', 
     '[{"step_id": "1", "name": "Check Services", "step_type": "command"}, {"step_id": "2", "name": "Check Resources", "step_type": "command"}]'::jsonb),
    ('incident-response-db', 'Database Incident Response', 'Respond to database incidents', 'incident',
     '[{"step_id": "1", "name": "Identify Issue", "step_type": "analysis"}, {"step_id": "2", "name": "Mitigate", "step_type": "command"}]'::jsonb)
ON CONFLICT (template_id) DO NOTHING;

-- ====================================
-- PERMISSIONS (adjust as needed)
-- ====================================
-- Grant permissions to neuraops user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO neuraops;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO neuraops;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO neuraops;