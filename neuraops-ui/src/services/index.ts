/**
 * NeuraOps Services Index
 * Barrel export for all services
 */

// Export API service
export { apiService, ApiService, ApiError } from './api'

// Re-export types that services might need
export type * from '@/types'