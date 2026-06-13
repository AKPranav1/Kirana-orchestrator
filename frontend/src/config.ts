/**
 * Centralized frontend configuration for backend base URLs.
 * Uses Vite env variables when available, falls back to local defaults for dev.
 */
export const INGESTION_BASE = (import.meta.env.VITE_INGESTION_URL as string) || 'http://localhost:8001';
export const DB_ALERTS_BASE = (import.meta.env.VITE_DB_ALERTS_URL as string) || 'http://localhost:8002';

// Convenience endpoints
export const INGESTION_PROCESS = `${INGESTION_BASE}/process`;
export const DB_ALERTS_LOG = `${DB_ALERTS_BASE}/log`;
export const DB_ALERTS_ORDERS = `${DB_ALERTS_BASE}/orders`;
export const DB_ALERTS_FORECAST = `${DB_ALERTS_BASE}/forecast`;
export const DB_ALERTS_DASHBOARD = `${DB_ALERTS_BASE}/dashboard`;
