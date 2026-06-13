/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiClient } from './api';
import { DashboardMetrics } from '../types';

export const dashboardService = {
  getDashboard: (): Promise<DashboardMetrics> => {
    return apiClient.getDashboard();
  }
};
