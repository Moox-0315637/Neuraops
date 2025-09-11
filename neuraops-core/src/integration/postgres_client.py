"""
PostgreSQL Integration Client for NeuraOps API

Database operations for persistent storage following CLAUDE.md: < 150 lines.
Handles agent registration, command history, and workflow data.
"""
from typing import Optional, Dict, Any, List
import asyncio
import asyncpg
from datetime import datetime
import structlog

from ..devops_commander.config import get_config

logger = structlog.get_logger()

# Constants for database operations (Fixes S1192)
UPDATE_NO_ROWS_RESULT = "UPDATE 0"


class PostgreSQLClient:
    """
    PostgreSQL client for NeuraOps persistent storage
    
    CLAUDE.md: Single Responsibility - Database operations only
    CLAUDE.md: Fail Fast - Handle connection failures gracefully
    """
    
    def __init__(self, database_url: Optional[str] = None):
        config = get_config()
        self.database_url = database_url or getattr(config, 'database_url', 
            'postgresql://neuraops:password@localhost:5432/neuraops')
        self.pool: Optional[asyncpg.Pool] = None
        self.connected = False
    
    async def connect(self) -> bool:
        """
        Establish PostgreSQL connection pool
        
        CLAUDE.md: Fail Fast - Early connection validation
        """
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=30,
                server_settings={
                    'timezone': 'UTC'
                }
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute('SELECT 1')
            
            self.connected = True
            logger.info("PostgreSQL connection pool established")
            
            # Initialize schema if needed
            await self.initialize_schema()
            
            # Initialize default users
            await self.initialize_default_users()
            
            return True
            
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            self.connected = False
            return False
    
    async def disconnect(self):
        """Close PostgreSQL connection pool"""
        if self.pool:
            await self.pool.close()
            self.connected = False
            logger.info("PostgreSQL connection pool closed")
    
    async def initialize_schema(self):
        """
        Initialize database schema
        
        CLAUDE.md: Simple schema for core entities
        """
        if not self.connected or not self.pool:
            return
        
        schema_sql = """
        -- Users table for authentication
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_login TIMESTAMP WITH TIME ZONE,
            is_active BOOLEAN DEFAULT true
        );
        
        -- Alerts table for system monitoring
        CREATE TABLE IF NOT EXISTS alerts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title VARCHAR(200) NOT NULL,
            message TEXT NOT NULL,
            severity VARCHAR(20) NOT NULL,
            source VARCHAR(100) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            acknowledged BOOLEAN DEFAULT false,
            acknowledged_by VARCHAR(50),
            acknowledged_at TIMESTAMP WITH TIME ZONE,
            resolved BOOLEAN DEFAULT false,
            resolved_by VARCHAR(50),
            resolved_at TIMESTAMP WITH TIME ZONE,
            metadata JSONB
        );
        
        -- Agents table
        CREATE TABLE IF NOT EXISTS agents (
            agent_id VARCHAR(255) PRIMARY KEY,
            agent_name VARCHAR(100) NOT NULL,
            hostname VARCHAR(255) NOT NULL,
            capabilities TEXT[] NOT NULL,
            status VARCHAR(50) DEFAULT 'active',
            registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_seen TIMESTAMP WITH TIME ZONE,
            metadata JSONB
        );
        
        -- Command executions table
        CREATE TABLE IF NOT EXISTS command_executions (
            command_id UUID PRIMARY KEY,
            command_text TEXT NOT NULL,
            action_type VARCHAR(50) NOT NULL,
            safety_level VARCHAR(20) NOT NULL,
            requested_by VARCHAR(255) NOT NULL,
            target_agents TEXT[] NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            timeout_seconds INTEGER DEFAULT 300,
            requires_approval BOOLEAN DEFAULT false,
            approved_by VARCHAR(255),
            approved_at TIMESTAMP WITH TIME ZONE,
            error_message TEXT
        );
        
        -- Workflow executions table
        CREATE TABLE IF NOT EXISTS workflow_executions (
            execution_id UUID PRIMARY KEY,
            workflow_name VARCHAR(200) NOT NULL,
            template_id VARCHAR(100),
            status VARCHAR(50) DEFAULT 'pending',
            created_by VARCHAR(255) NOT NULL,
            assigned_agents TEXT[] NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            context_variables JSONB,
            step_results JSONB,
            error_message TEXT
        );
        
        -- System logs table for log management
        CREATE TABLE IF NOT EXISTS system_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            level VARCHAR(20) NOT NULL,
            source VARCHAR(100) NOT NULL,
            message TEXT NOT NULL,
            metadata JSONB
        );
        
        -- Command history table for tracking command executions
        CREATE TABLE IF NOT EXISTS command_history (
            id VARCHAR(255) PRIMARY KEY,
            agent_id VARCHAR(255) NOT NULL,
            command TEXT NOT NULL,
            status VARCHAR(50) NOT NULL,
            output TEXT,
            error TEXT,
            started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        );
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
        CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged);
        CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);
        CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
        CREATE INDEX IF NOT EXISTS idx_command_executions_status ON command_executions(status);
        CREATE INDEX IF NOT EXISTS idx_command_executions_created_at ON command_executions(created_at);
        CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status);
        CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
        CREATE INDEX IF NOT EXISTS idx_system_logs_source ON system_logs(source);
        CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_command_history_agent_id ON command_history(agent_id);
        CREATE INDEX IF NOT EXISTS idx_command_history_status ON command_history(status);
        CREATE INDEX IF NOT EXISTS idx_command_history_started_at ON command_history(started_at);
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(schema_sql)
            logger.info("Database schema initialized")
            
        except Exception as e:
            logger.error("Failed to initialize schema", error=str(e))
    
    async def register_agent(self, agent_data: Dict[str, Any]) -> bool:
        """
        Register new agent in database
        
        CLAUDE.md: Safety-First - Validate agent data
        """
        if not self.connected or not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO agents (agent_id, agent_name, hostname, capabilities, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (agent_id) DO UPDATE SET
                        agent_name = EXCLUDED.agent_name,
                        hostname = EXCLUDED.hostname,
                        capabilities = EXCLUDED.capabilities,
                        metadata = EXCLUDED.metadata,
                        last_seen = NOW()
                """, 
                    agent_data["agent_id"],
                    agent_data["agent_name"], 
                    agent_data["hostname"],
                    agent_data["capabilities"],
                    agent_data.get("metadata", {})
                )
            
            logger.info("Agent registered in database", agent_id=agent_data["agent_id"])
            return True
            
        except Exception as e:
            logger.error("Failed to register agent", 
                        agent_id=agent_data.get("agent_id"), error=str(e))
            return False
    
    async def store_command_execution(self, command_data: Dict[str, Any]) -> bool:
        """Store command execution in database"""
        if not self.connected or not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO command_executions 
                    (command_id, command_text, action_type, safety_level, 
                     requested_by, target_agents, timeout_seconds, requires_approval)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                    command_data["command_id"],
                    command_data["command"],
                    command_data["action_type"],
                    command_data["safety_level"],
                    command_data["requested_by"],
                    command_data["target_agents"],
                    command_data.get("timeout_seconds", 300),
                    command_data.get("requires_approval", False)
                )
            
            logger.info("Command execution stored", command_id=command_data["command_id"])
            return True
            
        except Exception as e:
            logger.error("Failed to store command execution", 
                        command_id=command_data.get("command_id"), error=str(e))
            return False
    
    async def get_agent_list(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get list of registered agents"""
        if not self.connected or not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT agent_id, agent_name, hostname, capabilities, 
                           status, registered_at, last_seen, metadata
                    FROM agents
                    ORDER BY registered_at DESC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error("Failed to get agent list", error=str(e))
            return []

    
    async def create_user(self, username: str, email: str, password_hash: str, role: str = "user") -> bool:
        """Create a new user in the database"""
        if not self.connected or not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES ($1, $2, $3, $4)
                """, username, email, password_hash, role)
            
            logger.info("User created", username=username)
            return True
            
        except Exception as e:
            logger.error("Failed to create user", username=username, error=str(e))
            return False
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        if not self.connected or not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, username, email, password_hash, role, 
                           created_at, last_login, is_active
                    FROM users
                    WHERE username = $1 AND is_active = true
                """, username)
            
            return dict(row) if row else None
            
        except Exception as e:
            logger.error("Failed to get user", username=username, error=str(e))
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        if not self.connected or not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, username, email, password_hash, role, 
                           created_at, last_login, is_active
                    FROM users
                    WHERE email = $1 AND is_active = true
                """, email)
            
            return dict(row) if row else None
            
        except Exception as e:
            logger.error("Failed to get user by email", email=email, error=str(e))
            return None
    
    async def update_user_last_login(self, username: str) -> bool:
        """Update user's last login timestamp"""
        if not self.connected or not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE users 
                    SET last_login = NOW()
                    WHERE username = $1
                """, username)
            
            return True
            
        except Exception as e:
            logger.error("Failed to update last login", username=username, error=str(e))
            return False
    
    async def initialize_default_users(self):
        """Initialize default admin user if no users exist"""
        if not self.connected or not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                # Check if any users exist
                count = await conn.fetchval("SELECT COUNT(*) FROM users")
                
                if count == 0:
                    # Import password hashing here to avoid circular imports
                    from passlib.context import CryptContext
                    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                    
                    # Create default admin user
                    # Get admin password from environment variable or use secure default
                    import os
                    admin_password = os.getenv('DEFAULT_ADMIN_PASSWORD', 'ChangeThisSecurePassword123!')
                    admin_username = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
                    admin_hash = pwd_context.hash(admin_password)
                    await conn.execute("""
                        INSERT INTO users (username, email, password_hash, role)
                        VALUES ($1, $2, $3, $4)
                    """, admin_username, f"{admin_username}@neuraops.com", admin_hash, "admin")
                    
                    logger.info("Default admin user created")
                    
        except Exception as e:
            logger.error("Failed to initialize default users", error=str(e))

    
    async def create_alert(self, title: str, message: str, severity: str, source: str, metadata: dict = None) -> Optional[str]:
        """Create a new alert in the database"""
        if not self.connected or not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                alert_id = await conn.fetchval("""
                    INSERT INTO alerts (title, message, severity, source, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """, title, message, severity, source, metadata or {})
            
            logger.info("Alert created", alert_id=str(alert_id), severity=severity)
            return str(alert_id)
            
        except Exception as e:
            logger.error("Failed to create alert", error=str(e))
            return None
    
    async def get_alerts(self, acknowledged: Optional[bool] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get alerts from the database"""
        if not self.connected or not self.pool:
            return []
        
        try:
            query = """
                SELECT id, title, message, severity, source, created_at,
                       acknowledged, acknowledged_by, acknowledged_at,
                       resolved, resolved_by, resolved_at, metadata
                FROM alerts
            """
            params = []
            
            if acknowledged is not None:
                query += " WHERE acknowledged = $1"
                params.append(acknowledged)
            
            query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1) + " OFFSET $" + str(len(params) + 2)
            params.extend([limit, offset])
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error("Failed to get alerts", error=str(e))
            return []
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        if not self.connected or not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE alerts 
                    SET acknowledged = true, acknowledged_by = $1, acknowledged_at = NOW()
                    WHERE id = $2
                """, acknowledged_by, alert_id)
            
            return result != UPDATE_NO_ROWS_RESULT
            
        except Exception as e:
            logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
            return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve an alert"""
        if not self.connected or not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE alerts 
                    SET resolved = true, resolved_by = $1, resolved_at = NOW()
                    WHERE id = $2
                """, resolved_by, alert_id)
            
            return result != UPDATE_NO_ROWS_RESULT
            
        except Exception as e:
            logger.error("Failed to resolve alert", alert_id=alert_id, error=str(e))
            return False

    
    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Optional[str]:
        """Create a new workflow in the database"""
        if not self.connected or not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                workflow_id = await conn.fetchval("""
                    INSERT INTO workflow_executions (workflow_name, template_id, created_by, assigned_agents, context_variables)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING execution_id
                """, 
                    workflow_data["name"],
                    workflow_data.get("template_id"),
                    workflow_data["created_by"],
                    workflow_data.get("assigned_agents", []),
                    workflow_data.get("context_variables", {})
                )
            
            logger.info("Workflow created", workflow_id=str(workflow_id))
            return str(workflow_id)
            
        except Exception as e:
            logger.error("Failed to create workflow", error=str(e))
            return None
    
    async def get_workflows(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get workflows from the database"""
        if not self.connected or not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT execution_id, workflow_name, template_id, status, created_by,
                           assigned_agents, created_at, started_at, completed_at,
                           context_variables, step_results, error_message
                    FROM workflow_executions
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error("Failed to get workflows", error=str(e))
            return []
    
    async def update_workflow_status(self, workflow_id: str, status: str, step_results: dict = None) -> bool:
        """Update workflow status and results"""
        if not self.connected or not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                if status == 'running' and step_results is None:
                    result = await conn.execute("""
                        UPDATE workflow_executions 
                        SET status = $1, started_at = NOW()
                        WHERE execution_id = $2
                    """, status, workflow_id)
                elif status in ['completed', 'failed']:
                    result = await conn.execute("""
                        UPDATE workflow_executions 
                        SET status = $1, completed_at = NOW(), step_results = $2
                        WHERE execution_id = $3
                    """, status, step_results or {}, workflow_id)
                else:
                    result = await conn.execute("""
                        UPDATE workflow_executions 
                        SET status = $1
                        WHERE execution_id = $2
                    """, status, workflow_id)
            
            return result != UPDATE_NO_ROWS_RESULT
            
        except Exception as e:
            logger.error("Failed to update workflow status", workflow_id=workflow_id, error=str(e))
            return False
    
    # Additional methods needed for real implementations
    
    async def get_agents(self) -> List[Dict[str, Any]]:
        """Get list of all agents"""
        return await self.get_agent_list()
    
    async def get_logs(self, level: Optional[str] = None, source: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get system logs from database"""
        if not self.connected or not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                where_clause = "WHERE 1=1"
                params = []
                param_count = 0
                
                if level:
                    param_count += 1
                    where_clause += f" AND level = ${param_count}"
                    params.append(level.upper())
                
                if source:
                    param_count += 1
                    where_clause += f" AND source ILIKE ${param_count}"
                    params.append(f"%{source}%")
                
                param_count += 1
                where_clause += f" ORDER BY timestamp DESC LIMIT ${param_count}"
                params.append(limit)
                
                query = f"""
                    SELECT id, timestamp, level, source, message, metadata
                    FROM system_logs 
                    {where_clause}
                """
                
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error("Failed to get logs", error=str(e))
            return []
    
    async def get_commands(self, agent_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get commands from database"""
        if not self.connected or not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                where_clause = "WHERE 1=1"
                params = []
                param_count = 0
                
                if agent_id:
                    param_count += 1
                    where_clause += f" AND agent_id = ${param_count}"
                    params.append(agent_id)
                
                if status:
                    param_count += 1
                    where_clause += f" AND status = ${param_count}"
                    params.append(status)
                
                param_count += 1
                where_clause += f" ORDER BY started_at DESC LIMIT ${param_count}"
                params.append(limit)
                
                query = f"""
                    SELECT id, agent_id, command, status, output, error, started_at, completed_at
                    FROM command_history 
                    {where_clause}
                """
                
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error("Failed to get commands", error=str(e))
            return []
    
    async def get_command_by_id(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Get specific command by ID"""
        if not self.connected or not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id, agent_id, command, status, output, error, started_at, completed_at
                    FROM command_history 
                    WHERE id = $1
                """, command_id)
                
                return dict(row) if row else None
                
        except Exception as e:
            logger.error("Failed to get command", command_id=command_id, error=str(e))
            return None
    
    async def create_command(self, command_id: str, agent_id: str, command: str, status: str,
                           output: Optional[str] = None, error: Optional[str] = None,
                           started_at: Optional[datetime] = None, completed_at: Optional[datetime] = None) -> bool:
        """Create a new command record"""
        if not self.connected or not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO command_history (id, agent_id, command, status, output, error, started_at, completed_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        output = EXCLUDED.output,
                        error = EXCLUDED.error,
                        completed_at = EXCLUDED.completed_at
                """, command_id, agent_id, command, status, output, error, started_at, completed_at)
                
                return True
                
        except Exception as e:
            logger.error("Failed to create command", command_id=command_id, error=str(e))
            return False
    
    async def get_workflow_by_id(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get specific workflow execution by ID"""
        if not self.connected or not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT execution_id, workflow_name, template_id, status, created_by, created_at, started_at, completed_at, step_results
                    FROM workflow_executions 
                    WHERE execution_id = $1
                """, execution_id)
                
                return dict(row) if row else None
                
        except Exception as e:
            logger.error("Failed to get workflow", execution_id=execution_id, error=str(e))
            return None
