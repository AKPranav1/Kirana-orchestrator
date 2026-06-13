/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Forecast } from '../types';

export const forecastService = {
  getForecasts: async (): Promise<Forecast[]> => {
    try {
      const res = await fetch('http://localhost:8002/forecast');
      if (!res.ok) return [];
      const json = await res.json();
      return json as Forecast[];
    } catch (e) {
      return [];
    }
  }
};
