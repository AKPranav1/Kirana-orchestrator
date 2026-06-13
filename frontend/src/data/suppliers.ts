/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Supplier, PurchaseOrder } from '../types';

export const mockSuppliers: Supplier[] = [
  {
    id: "sup-1",
    name: "Hindustan Unilever",
    category: "FMCG Goods",
    contactName: "Ramesh K.",
    phone: "+91 98765 43210",
    avgDeliveryDays: 2.4,
    outstandingBalance: 45200
  },
  {
    id: "sup-2",
    name: "ITC Limited",
    category: "Tobacco & Staples",
    contactName: "Sunita P.",
    phone: "+91 91234 56789",
    avgDeliveryDays: 1.8,
    outstandingBalance: 12450
  },
  {
    id: "sup-3",
    name: "Amul Dairy Co.",
    category: "Dairy Products",
    contactName: "Vikram S.",
    phone: "+91 99887 76655",
    avgDeliveryDays: 0.5,
    outstandingBalance: 8900
  },
  {
    id: "sup-4",
    name: "Tata Consumer Products",
    category: "Beverages & Staples",
    contactName: "Divya N.",
    phone: "+91 98321 04567",
    avgDeliveryDays: 2.1,
    outstandingBalance: 15000
  }
];

export const mockPurchaseOrders: PurchaseOrder[] = [
  {
    id: "PO-2023-104",
    supplierId: "sup-1",
    supplierName: "Hindustan Unilever",
    items: [
      { productId: "prod-1", productName: "Aashirvaad Atta 5kg", quantity: 50, costPrice: 210.00 },
      { productId: "prod-5", productName: "Fortune Mustard Oil 1L", quantity: 30, costPrice: 155.00 }
    ],
    totalAmount: 15400,
    status: "Delivered",
    createdAt: "2026-06-13T10:30:00Z"
  },
  {
    id: "PO-2023-105",
    supplierId: "sup-2",
    supplierName: "ITC Limited",
    items: [
      { productId: "prod-4", productName: "Maggi 2-Min Masala Noodles", quantity: 50, costPrice: 145.00 },
      { productId: "prod-6", productName: "Parle-G Gold Biscuits", quantity: 110, costPrice: 8.50 }
    ],
    totalAmount: 8200,
    status: "In Transit",
    createdAt: "2026-06-12T14:20:00Z",
    estimatedDelivery: "Est. Tomorrow",
    deliveryProgress: 66
  },
  {
    id: "PO-2023-106",
    supplierId: "sup-3",
    supplierName: "Amul Dairy Co.",
    items: [
      { productId: "prod-2", productName: "Amul Gold Milk 1L", quantity: 36, costPrice: 58.00 }
    ],
    totalAmount: 2100,
    status: "Awaiting Approval",
    createdAt: "2026-06-13T09:15:00Z"
  }
];
