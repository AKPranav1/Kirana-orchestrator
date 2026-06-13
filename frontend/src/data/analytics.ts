/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Analytics } from '../types';

export const mockAnalyticsData: Analytics = {
  totalRevenue: 342500,
  totalOrders: 1140,
  khataRecoveryRate: 88.5,
  topProducts: [
    { name: "Aashirvaad Atta 5kg", salesCount: 310, revenue: 75950 },
    { name: "Fortune Mustard Oil 1L", salesCount: 220, revenue: 38500 },
    { name: "Amul Gold Milk 1L", salesCount: 450, revenue: 28800 },
    { name: "Maggi Noodles Pack", salesCount: 160, revenue: 26880 }
  ],
  categoryDistribution: [
    { name: "Grains", value: 38 },
    { name: "Dairy", value: 25 },
    { name: "Beverages", value: 15 },
    { name: "Snacks", value: 12 },
    { name: "Others", value: 10 }
  ],
  trendData: [
    { date: "06-07", revenue: 8400, orders: 32 },
    { date: "06-08", revenue: 9200, orders: 35 },
    { date: "06-09", revenue: 11500, orders: 40 },
    { date: "06-10", revenue: 10800, orders: 38 },
    { date: "06-11", revenue: 13400, orders: 45 },
    { date: "06-12", revenue: 14200, orders: 48 },
    { date: "06-13", revenue: 12450, orders: 42 } // Todays values match
  ]
};
export const mockKhataAgeing = [
  { range: "0-15 Days", amount: 15000 },
  { range: "16-30 Days", amount: 8200 },
  { range: "31-45 Days", amount: 3500 },
  { range: "45+ Days", amount: 1200 }
];
