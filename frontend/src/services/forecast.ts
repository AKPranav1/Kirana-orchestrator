/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Forecast } from '../types';
import { mockForecasts } from '../data/forecast';
import { DB_ALERTS_FORECAST } from '../config';

export const forecastService = {
  getForecasts: async (): Promise<Forecast[]> => {
    try {
      const res = await fetch(DB_ALERTS_FORECAST);
      if (!res.ok) throw new Error(`forecast ${res.status}`);
      const json = await res.json();
      return json as Forecast[];
    } catch (e) {
      // Prefer persisted forecasts if available, otherwise use mock forecasts for demo
      return JSON.parse(localStorage.getItem('ka_forecasts') || 'null') || mockForecasts;
    }
  }
};
