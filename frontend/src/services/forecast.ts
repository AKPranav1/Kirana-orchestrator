/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiClient } from './api';
import { Forecast } from '../types';

export const forecastService = {
  getForecasts: (): Promise<Forecast[]> => {
    return apiClient.getForecasts();
  }
};
