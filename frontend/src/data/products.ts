/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Product } from '../types';

export const mockProducts: Product[] = [
  {
    id: "prod-1",
    name: "Aashirvaad Atta 5kg",
    sku: "SKU-ASH-001",
    category: "Grains",
    unitPrice: 245.00,
    costPrice: 210.00,
    margin: 14.2,
    supplierId: "sup-1",
    supplierName: "Hindustan Unilever",
    status: "In Stock",
    stockQuantity: 42
  },
  {
    id: "prod-2",
    name: "Amul Gold Milk 1L",
    sku: "SKU-AML-102",
    category: "Dairy",
    unitPrice: 64.00,
    costPrice: 58.00,
    margin: 9.3,
    supplierId: "sup-3",
    supplierName: "Amul Dairy Co.",
    status: "Low Stock",
    stockQuantity: 4
  },
  {
    id: "prod-3",
    name: "Tata Salt 1kg",
    sku: "SKU-TAT-001",
    category: "Spices",
    unitPrice: 28.00,
    costPrice: 24.00,
    margin: 14.2,
    supplierId: "sup-2",
    supplierName: "ITC Limited",
    status: "Out of Stock",
    stockQuantity: 0
  },
  {
    id: "prod-4",
    name: "Maggi 2-Min Masala Noodles (Pack of 12)",
    sku: "SKU-MAG-302",
    category: "Snacks",
    unitPrice: 168.00,
    costPrice: 145.00,
    margin: 13.7,
    supplierId: "sup-2",
    supplierName: "ITC Limited",
    status: "In Stock",
    stockQuantity: 28
  },
  {
    id: "prod-5",
    name: "Fortune Mustard Oil 1L",
    sku: "SKU-FOR-401",
    category: "Oils",
    unitPrice: 175.00,
    costPrice: 155.00,
    margin: 11.4,
    supplierId: "sup-1",
    supplierName: "Hindustan Unilever",
    status: "In Stock",
    stockQuantity: 18
  },
  {
    id: "prod-6",
    name: "Parle-G Gold Biscuits 100g",
    sku: "SKU-PAR-022",
    category: "Snacks",
    unitPrice: 10.00,
    costPrice: 8.50,
    margin: 15.0,
    supplierId: "sup-2",
    supplierName: "ITC Limited",
    status: "In Stock",
    stockQuantity: 150
  },
  {
    id: "prod-7",
    name: "Bru Instant Coffee 100g",
    sku: "SKU-BRU-112",
    category: "Beverages",
    unitPrice: 185.00,
    costPrice: 160.00,
    margin: 13.5,
    supplierId: "sup-1",
    supplierName: "Hindustan Unilever",
    status: "Low Stock",
    stockQuantity: 3
  },
  {
    id: "prod-8",
    name: "Taj Mahal Tea 250g",
    sku: "SKU-TAJ-221",
    category: "Beverages",
    unitPrice: 195.00,
    costPrice: 170.00,
    margin: 12.8,
    supplierId: "sup-1",
    supplierName: "Hindustan Unilever",
    status: "In Stock",
    stockQuantity: 12
  }
];
