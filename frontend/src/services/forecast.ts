/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Forecast } from '../types';
import { DB_ALERTS_FORECAST } from '../config';

export const forecastService = {
  getForecasts: async (): Promise<Forecast[]> => {
    try {
      const res = await fetch(DB_ALERTS_FORECAST);
      if (!res.ok) throw new Error(`forecast ${res.status}`);
      const json = await res.json();
      return json as Forecast[];
    } catch (e) {
      // Backend unavailable — return empty list so UI shows no forecasts instead of demo mocks
      console.warn('forecastService.getForecasts failed:', e);
      return [];
    }
  }
};
