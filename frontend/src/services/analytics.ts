/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiClient } from './api';
import { Analytics } from '../types';

export const analyticsService = {
  getAnalytics: (timeframe: '7d' | '30d'): Promise<Analytics> => {
    return apiClient.getAnalytics(timeframe);
  }
};