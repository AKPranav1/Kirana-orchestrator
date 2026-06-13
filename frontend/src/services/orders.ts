/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiClient } from './api';
import { Order } from '../types';

export const ordersService = {
  getOrders: (): Promise<Order[]> => {
    return apiClient.getOrders();
  },
  
  createOrder: (order: Omit<Order, 'id' | 'createdAt'>): Promise<Order> => {
    return apiClient.createOrder(order);
  },

  extractOrderFromWhatsApp: (textMsg: string): Promise<{ order: Order | null; error?: string }> => {
    return apiClient.extractOrderFromWhatsApp(textMsg);
  }
};
