/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiFetch as fetch } from './http';
import { apiClient } from './api';
import { Order } from '../types';
import { INGESTION_PROCESS, DB_ALERTS_ORDERS, DB_ALERTS_LOG } from '../config';

export const ordersService = {
  getOrders: (): Promise<Order[]> => {
    return (async () => {
      try {
        const res = await fetch(DB_ALERTS_ORDERS);
        if (!res.ok) return [];
        const json = await res.json();
        return json.orders || [];
      } catch (e) {
        console.warn('ordersService.getOrders failed:', e);
        return [];
      }
    })();
  },
  
  createOrder: (order: Omit<Order, 'id' | 'createdAt'>): Promise<Order> => {
    return apiClient.createOrder(order);
  },
  extractOrder: (text: string, customerName?: string) => apiClient.extractOrder(text, customerName),
};
