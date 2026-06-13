/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { DashboardMetrics, Order, Notification } from '../types';

export const mockDashboardMetrics: DashboardMetrics = {
  todaysRevenue: 12450,
  todaysOrdersCount: 42,
  outstandingKhata: 8200,
  lowStockItemsCount: 3,
  pendingDeliveriesCount: 5,
  pendingSupplierPay: 15000,
  storeHealthScore: 94
};

export const mockOrders: Order[] = [
  {
    id: "ord-1042",
    customerName: "Rahul K.",
    items: [
      { productId: "prod-1", productName: "Aashirvaad Atta 5kg", quantity: 2, price: 245.00 },
      { productId: "prod-5", productName: "Fortune Mustard Oil 1L", quantity: 1, price: 175.00 }
    ],
    totalAmount: 665,
    status: "Processed",
    source: "WhatsApp",
    createdAt: "2026-06-13T11:54:00Z" // 2 mins ago compared to 11:56
  },
  {
    id: "ord-1041",
    customerName: "Sharma Ji",
    items: [
      { productId: "prod-2", productName: "Amul Gold Milk 1L", quantity: 3, price: 64.00 }
    ],
    totalAmount: 192,
    status: "Delivered",
    source: "In-Store",
    createdAt: "2026-06-13T11:30:00Z"
  },
  {
    id: "ord-1040",
    customerName: "Ramesh Sharma",
    items: [
      { productId: "prod-4", productName: "Maggi Noodles Pack", quantity: 2, price: 168.00 },
      { productId: "prod-6", productName: "Parle-G Gold Biscuits", quantity: 10, price: 10.00 }
    ],
    totalAmount: 436,
    status: "Received",
    source: "WhatsApp",
    createdAt: "2026-06-13T11:15:00Z"
  },
  {
    id: "ord-1039",
    customerName: "Aarav Gupta",
    items: [
      { productId: "prod-7", productName: "Bru Instant Coffee 100g", quantity: 1, price: 185.00 }
    ],
    totalAmount: 185,
    status: "Pending",
    source: "Manual",
    createdAt: "2026-06-13T10:45:00Z"
  }
];

export const mockRecentActivity = [
  {
    id: "act-1",
    type: "whatsapp_order",
    description: "Order #1042 extracted from WhatsApp",
    timeLabel: "2 mins ago",
    user: "Rahul K.",
    status: "Processed"
  },
  {
    id: "act-2",
    type: "khata_payment",
    description: "Khata payment received: ₹1,200",
    timeLabel: "15 mins ago",
    user: "Sharma Ji",
    status: undefined
  },
  {
    id: "act-3",
    type: "inventory_update",
    description: "Inventory updated via Supplier Invoice",
    timeLabel: "1 hr ago",
    user: "Metro Wholesale",
    status: "Processed"
  },
  {
    id: "act-4",
    type: "low_stock_warning",
    description: "Milk running low - restock needed today",
    timeLabel: "2 hrs ago",
    user: "AI Insights",
    status: undefined
  }
];

export const mockNotifications: Notification[] = [
  {
    id: "notif-1",
    title: "Milk running low",
    description: "Based on current sales velocity, restock needed by tomorrow.",
    type: "warning",
    createdAt: "2026-06-13T10:00:00Z",
    isRead: false
  },
  {
    id: "notif-2",
    title: "Khata Overdue Alarm",
    description: "3 customers have overdue Khata. Total outstanding: ₹4,500 over 15 days.",
    type: "warning",
    createdAt: "2026-06-13T09:30:00Z",
    isRead: false
  },
  {
    id: "notif-3",
    title: "PO Completed",
    description: "PO-2023-104 for Hindustan Unilever marked as Delivered.",
    type: "success",
    createdAt: "2026-06-13T10:30:00Z",
    isRead: true
  }
];
