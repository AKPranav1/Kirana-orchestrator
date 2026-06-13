/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiClient } from './api';
import { Customer, KhataTransaction } from '../types';

export const customersService = {
  getCustomers: (): Promise<Customer[]> => {
    return apiClient.getCustomers();
  },

  addCustomer: (customer: Omit<Customer, 'id' | 'khataBalance' | 'avgBasket' | 'lifetimeSpend'>): Promise<Customer> => {
    return apiClient.addCustomer(customer);
  },

  getKhataTransactions: (customerId?: string): Promise<KhataTransaction[]> => {
    return apiClient.getKhataTransactions(customerId);
  },

  addKhataTransaction: (customerId: string, type: 'credit' | 'payment', amount: number, description: string): Promise<KhataTransaction> => {
    return apiClient.addKhataTransaction(customerId, type, amount, description);
  }
};
