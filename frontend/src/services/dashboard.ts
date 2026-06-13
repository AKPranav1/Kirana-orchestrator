/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { DashboardMetrics } from '../types';
import { mockDashboardMetrics } from '../data/dashboard';
import { DB_ALERTS_DASHBOARD } from '../config';

export const dashboardService = {
  getDashboard: async (): Promise<DashboardMetrics> => {
    try {
      const res = await fetch(DB_ALERTS_DASHBOARD);
      if (!res.ok) throw new Error('Failed to load dashboard metrics');
      return (await res.json()) as DashboardMetrics;
    } catch (e) {
      // Return mock metrics for demo when backend is not available
      return mockDashboardMetrics;
    }
  }
};
