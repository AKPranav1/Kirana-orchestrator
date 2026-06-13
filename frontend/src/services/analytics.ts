/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiClient } from './api';
import { Analytics } from '../types';

export const analyticsService = {
  getAnalytics: (): Promise<Analytics> => {
    return apiClient.getAnalytics();
  }
};
