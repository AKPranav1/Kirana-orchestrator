/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiClient } from './api';
import { Supplier, PurchaseOrder } from '../types';

export const suppliersService = {
  getSuppliers: (): Promise<Supplier[]> => {
    return apiClient.getSuppliers();
  },

  addSupplier: (supplier: Omit<Supplier, 'id' | 'outstandingBalance'>): Promise<Supplier> => {
    return apiClient.addSupplier(supplier);
  },

  getPurchaseOrders: (): Promise<PurchaseOrder[]> => {
    return apiClient.getPurchaseOrders();
  },

  createPurchaseOrder: (poData: Omit<PurchaseOrder, 'id' | 'createdAt' | 'status'>): Promise<PurchaseOrder> => {
    return apiClient.createPurchaseOrder(poData);
  },

  approvePurchaseOrder: (poId: string): Promise<PurchaseOrder> => {
    return apiClient.approvePurchaseOrder(poId);
  },

  receivePurchaseOrder: (poId: string): Promise<PurchaseOrder> => {
    return apiClient.receivePurchaseOrder(poId);
  }
};
