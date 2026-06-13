/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { DashboardMetrics } from '../types';
import { mockDashboardMetrics } from '../data/dashboard';

export const dashboardService = {
  getDashboard: async (): Promise<DashboardMetrics> => {
    try {
      const res = await fetch('http://localhost:8002/dashboard');
      if (!res.ok) throw new Error('Failed to load dashboard metrics');
      return (await res.json()) as DashboardMetrics;
    } catch (e) {
      // Return mock metrics for demo when backend is not available
      return mockDashboardMetrics;
    }
  }
};
