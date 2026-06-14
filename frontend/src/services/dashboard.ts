/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { DashboardMetrics } from '../types';
import { DB_ALERTS_DASHBOARD } from '../config';

export const dashboardService = {
  getDashboard: async (): Promise<DashboardMetrics> => {
    try {
      const res = await fetch(DB_ALERTS_DASHBOARD);
      if (!res.ok) throw new Error('Failed to load dashboard metrics');
      return (await res.json()) as DashboardMetrics;
    } catch (e) {
      console.warn('dashboardService.getDashboard failed:', e);
      return {
        todaysRevenue: 0,
        todaysOrdersCount: 0,
        outstandingKhata: 0,
        lowStockItemsCount: 0,
        pendingDeliveriesCount: 0,
        pendingSupplierPay: 0,
        storeHealthScore: 0,
      } as DashboardMetrics;
    }
  }
};
