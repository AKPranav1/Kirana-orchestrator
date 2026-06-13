/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiClient } from './api';
import { Product } from '../types';

export const inventoryService = {
  getInventory: (): Promise<Product[]> => {
    return apiClient.getProducts();
  },

  addProduct: (product: Omit<Product, 'id' | 'margin'>): Promise<Product> => {
    return apiClient.addProduct(product);
  },

  updateProductStock: (productId: string, quantity: number): Promise<Product> => {
    return apiClient.updateProductStock(productId, quantity);
  }
};
