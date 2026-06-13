/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { DashboardMetrics } from '../types';

export const dashboardService = {
  getDashboard: async (): Promise<DashboardMetrics> => {
    const res = await fetch('http://localhost:8002/dashboard');
    if (!res.ok) throw new Error('Failed to load dashboard metrics');
    return (await res.json()) as DashboardMetrics;
  }
};
