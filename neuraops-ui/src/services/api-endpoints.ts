/**
 * NeuraOps API Endpoints Mapping
 * Maps frontend needs to actual available API endpoints
 */

export const API_ENDPOINTS = {
  // Authentication
  auth: {
    login: '/auth/login',
    logout: '/auth/logout',
    register: '/auth/register',
    refresh: '/auth/refresh'
  },
  
  // System
  system: {
    health: '/health',
    metrics: '/system/metrics'
  },
  
  // Workflows
  workflows: {
    list: '/workflows',
    get: (id: string) => `/workflows/${id}`,
    create: '/workflows',
    update: (id: string) => `/workflows/${id}`,
    delete: (id: string) => `/workflows/${id}`,
    execute: (id: string) => `/workflows/${id}/execute`
  },
  
  // Commands (Note: /commands returns 405, might need different method)
  commands: {
    list: '/commands/list',
    get: (id: string) => `/commands/${id}`,
    execute: '/commands/execute'
  },
  
  // Agents (Note: /agents returns auth error, might not be implemented)
  agents: {
    list: '/agents/list',
    get: (id: string) => `/agents/${id}`,
    register: '/agents/register',
    heartbeat: '/agents/heartbeat'
  },
  
  // Alerts (Note: returns 404, might not be implemented)
  alerts: {
    list: '/alerts/list',
    get: (id: string) => `/alerts/${id}`
  }
}

/**
 * Mock data for endpoints that don't exist yet
 */
export const MOCK_RESPONSES = {
  agents: [
    {
      id: '1',
      name: 'Production Agent',
      status: 'active' as const,
      hostname: 'prod-server-01',
      capabilities: ['logs', 'metrics', 'commands'] as const,
      location: 'Paris, France',
      version: '1.0.0',
      lastSeen: new Date(),
      registeredAt: new Date(),
      tags: ['production', 'primary'],
      metadata: {}
    },
    {
      id: '2',
      name: 'Development Agent',
      status: 'inactive' as const,
      hostname: 'dev-server-01',
      capabilities: ['logs', 'metrics'] as const,
      location: 'Paris, France',
      version: '1.0.0',
      lastSeen: new Date(),
      registeredAt: new Date(),
      tags: ['development'],
      metadata: {}
    }
  ],
  
  alerts: [],
  
  commands: []
}