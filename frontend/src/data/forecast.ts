/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Forecast } from '../types';

export const mockForecasts: Forecast[] = [
  {
    productId: "prod-1",
    product_name: "Aashirvaad Atta 5kg",
    current_stock: 42,
    predicted_daily_demand: 12.5,
    predicted_stockout_days: 3,
    recommended_reorder_quantity: 100,
    confidence: 0.94,
    recommendation_text: "High daily consumption combined with upcoming festival season in Kolkata indicates immediate restocking needed to prevent a stockout in 3 days."
  },
  {
    productId: "prod-2",
    product_name: "Amul Gold Milk 1L",
    current_stock: 4,
    predicted_daily_demand: 15.0,
    predicted_stockout_days: 0,
    recommended_reorder_quantity: 60,
    confidence: 0.98,
    recommendation_text: "Critical low stock. Daily demand is exceptionally stable. Restock 60 units instantly; supplier Co. has a 0.5-day delivery turnaround."
  },
  {
    productId: "prod-3",
    product_name: "Tata Salt 1kg",
    current_stock: 0,
    predicted_daily_demand: 4.8,
    predicted_stockout_days: 0,
    recommended_reorder_quantity: 50,
    confidence: 0.92,
    recommendation_text: "Item is currently out of stock, leading to potential lost sales of estimated ₹135 daily. Order 50 packets immediately."
  },
  {
    productId: "prod-4",
    product_name: "Maggi 2-Min Masala Noodles (Pack of 12)",
    current_stock: 28,
    predicted_daily_demand: 6.2,
    predicted_stockout_days: 4,
    recommended_reorder_quantity: 80,
    confidence: 0.89,
    recommendation_text: "Consistently selling snack item. Replenish with 80 units now to lock in wholesale margin discount of 13.7% from ITC Limited."
  },
  {
    productId: "prod-5",
    product_name: "Fortune Mustard Oil 1L",
    current_stock: 18,
    predicted_daily_demand: 3.1,
    predicted_stockout_days: 5,
    recommended_reorder_quantity: 40,
    confidence: 0.86,
    recommendation_text: "Steady shelf life velocity. Recommend triggering an order of 40 units in the next 48 hours to maintain continuous availability."
  }
];
