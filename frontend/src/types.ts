/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export interface Product {
  id: string;
  name: string;
  sku: string;
  category: string;
  unitPrice: number;
  costPrice: number;
  margin: number;
  supplierId: string;
  supplierName: string;
  status: 'In Stock' | 'Low Stock' | 'Out of Stock';
  stockQuantity: number;
}

export interface Customer {
  id: string;
  name: string;
  phone: string;
  avatarUrl?: string;
  status: 'Frequent' | 'Overdue' | 'Standard';
  khataBalance: number; // Negative values imply overdue/credit, 0 means settled, Positive means advance
  avgBasket: number;
  lifetimeSpend: number;
  orderCount?: number;
  lastOrderDate?: string;
}

export interface KhataTransaction {
  id: string;
  customerId: string;
  customerName: string;
  type: 'credit' | 'payment';
  amount: number;
  date: string;
  description: string;
}

export interface Khata {
  customerId: string;
  customerName: string;
  balance: number;
  lastUpdated: string;
  transactions: KhataTransaction[];
}

export interface OrderItem {
  productId: string;
  productName: string;
  quantity: number;
  price: number;
}

export interface Order {
  id: string;
  customerId?: string;
  customerName: string;
  items: OrderItem[];
  totalAmount: number;
  status: 'Received' | 'Processed' | 'Delivered' | 'Pending';
  source: 'WhatsApp' | 'In-Store' | 'Manual';
  createdAt: string;
}

export interface Supplier {
  id: string;
  name: string;
  category: string;
  contactName: string;
  phone: string;
  avgDeliveryDays: number;
  outstandingBalance: number;
}

export interface PurchaseOrderItem {
  productId: string;
  productName: string;
  quantity: number;
  costPrice: number;
}

export interface PurchaseOrder {
  id: string;
  supplierId: string;
  supplierName: string;
  items: PurchaseOrderItem[];
  totalAmount: number;
  status: 'Delivered' | 'In Transit' | 'Awaiting Approval' | 'Draft';
  createdAt: string;
  estimatedDelivery?: string;
  deliveryProgress?: number; // percentage progress
}

export interface Forecast {
  productId: string;
  product_name: string;
  current_stock: number;
  predicted_daily_demand: number;
  predicted_stockout_days: number;
  recommended_reorder_quantity: number;
  confidence: number; // e.g., 0.94 -> 94%
  recommendation_text: string;
}

export interface DashboardMetrics {
  todaysRevenue: number;
  todaysOrdersCount: number;
  outstandingKhata: number;
  lowStockItemsCount: number;
  pendingDeliveriesCount: number;
  pendingSupplierPay: number;
  storeHealthScore: number;
}

export interface AnalyticsTrendPoint {
  date: string;
  revenue: number;
  orders: number;
}

export interface Analytics {
  totalRevenue: number;
  totalOrders: number;
  khataRecoveryRate: number;
  topProducts: { name: string; salesCount: number; revenue: number }[];
  categoryDistribution: { name: string; value: number }[];
  trendData: AnalyticsTrendPoint[];
}

export interface Notification {
  id: string;
  title: string;
  description: string;
  type: 'info' | 'warning' | 'success';
  createdAt: string;
  isRead: boolean;
}

export interface StoreSettings {
  storeName: string;
  ownerName: string;
  phone: string;
  whatsappEnabled: boolean;
  storeStatus: 'Online' | 'Offline';
  autoExtractWhatsapp: boolean;
  lowStockThreshold: number;
}
