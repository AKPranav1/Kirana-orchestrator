/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Product, Customer, Order, Supplier, PurchaseOrder, Forecast, DashboardMetrics, Analytics, Notification, StoreSettings, KhataTransaction } from '../types';

// Default settings used when localStorage missing
const DEFAULT_SETTINGS: StoreSettings = {
  storeName: "Kirana AI",
  ownerName: "Store Owner",
  phone: "+91 98765 43210",
  whatsappEnabled: true,
  storeStatus: "Online",
  autoExtractWhatsapp: true,
  lowStockThreshold: 5
};

// No local mock storage: frontend uses db_alerts endpoints directly and
// returns empty/default values when backend is unavailable.

// Central simulated API client with simulated latencies for realistic UX
const delay = (ms = 400) => new Promise(resolve => setTimeout(resolve, ms));

import { dashboardService } from './dashboard';
import { INGESTION_PROCESS, DB_ALERTS_BASE, DB_ALERTS_ORDERS, DB_ALERTS_LOG } from '../config';

export const apiClient = {
  // --- DASHBOARD ---
  // Delegate to dashboardService which prefers backend and provides a safe fallback
  getDashboard: async (): Promise<DashboardMetrics> => {
    return dashboardService.getDashboard();
  },

  // --- PRODUCTS / INVENTORY ---
  getProducts: async (): Promise<Product[]> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/products`);
      if (!res.ok) throw new Error(`getProducts ${res.status}`);
      const json = await res.json();
      return json.products || [];
    } catch (e) {
      console.warn('apiClient.getProducts failed:', e);
      return [];
    }
  },

  addProduct: async (product: Omit<Product, 'id' | 'margin'>): Promise<Product> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(product),
      });
      if (!res.ok) throw new Error(`addProduct ${res.status}`);
      const json = await res.json();
      return json.product;
    } catch (e) {
      console.warn('apiClient.addProduct failed:', e);
      throw e;
    }
  },

  updateProductStock: async (productId: string, quantity: number): Promise<Product> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/products/${encodeURIComponent(productId)}/stock`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stockQuantity: quantity }),
      });
      if (!res.ok) throw new Error(`updateProductStock ${res.status}`);
      const json = await res.json();
      return json.product;
    } catch (e) {
      console.warn('apiClient.updateProductStock failed:', e);
      throw e;
    }
  },

  // --- CUSTOMERS ---
  getCustomers: async (): Promise<Customer[]> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/customers/leaderboard`);
      if (!res.ok) throw new Error(`getCustomers ${res.status}`);
      const json = await res.json();
      return json.customers || [];
    } catch (e) {
      console.warn('apiClient.getCustomers failed:', e);
      return [];
    }
  },

  addCustomer: async (customer: Omit<Customer, 'id' | 'khataBalance' | 'avgBasket' | 'lifetimeSpend'>): Promise<Customer> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/customers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(customer),
      });
      if (!res.ok) throw new Error(`addCustomer ${res.status}`);
      const json = await res.json();
      return json.customer;
    } catch (e) {
      console.warn('apiClient.addCustomer failed:', e);
      throw e;
    }
  },

  getKhataTransactions: async (customerId?: string): Promise<KhataTransaction[]> => {
    try {
      if (!customerId) {
        const res = await fetch(`${DB_ALERTS_BASE}/khata`);
        if (!res.ok) throw new Error(`getKhataTransactions ${res.status}`);
        const json = await res.json();
        return json.transactions || [];
      }

      // If caller provided a customerId, attempt best-effort mapping via leaderboard
      const customersRes = await fetch(`${DB_ALERTS_BASE}/customers/leaderboard`);
      if (!customersRes.ok) throw new Error('leaderboard fetch failed');
      const customersJson = await customersRes.json();
      const customers = customersJson.customers || [];
      const matched = customers.find((c: any) => c.id === customerId || c.customerId === customerId || c.name === customerId);
      if (matched) {
        const name = matched.customer_name || matched.name || matched.customerName;
        if (name) {
          const res = await fetch(`${DB_ALERTS_BASE}/khata/${encodeURIComponent(name)}`);
          if (!res.ok) throw new Error(`khata ${res.status}`);
          const json = await res.json();
          return (json.entries || []).map((e: any, idx: number) => ({
            id: `${name}-${e.order_id}-${idx}`,
            customerId: name,
            customerName: name,
            type: 'credit',
            amount: e.amount,
            date: e.date,
            description: `Order ${e.order_id}`,
          }));
        }
      }

      return [];
    } catch (e) {
      console.warn('apiClient.getKhataTransactions failed:', e);
      return [];
    }
  },

  addKhataTransaction: async (customerId: string, type: 'credit' | 'payment', amount: number, description: string): Promise<KhataTransaction> => {
    try {
      const payload = { customerId, type, amount, description };
      const res = await fetch(`${DB_ALERTS_BASE}/khata/tx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`addKhataTransaction ${res.status}`);
      const json = await res.json();
      return json.transaction;
    } catch (e) {
      console.warn('apiClient.addKhataTransaction failed:', e);
      throw e;
    }
  },

  // --- ORDERS ---
  getOrders: async (): Promise<Order[]> => {
    try {
      const res = await fetch(DB_ALERTS_ORDERS);
      if (!res.ok) throw new Error(`getOrders ${res.status}`);
      const json = await res.json();
      return json.orders || [];
    } catch (e) {
      console.warn('apiClient.getOrders failed:', e);
      return [];
    }
  },

  createOrder: async (orderData: Omit<Order, 'id' | 'createdAt'>): Promise<Order> => {
    try {
      // Use ingestion pipeline when available to normalize and persist order
      const r1 = await fetch(INGESTION_PROCESS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload_type: 'flat_order', payload: orderData }),
      });
      if (!r1.ok) throw new Error(`ingestion failed ${r1.status}`);
      const flatOrder = await r1.json();

      const r2 = await fetch(DB_ALERTS_LOG, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: flatOrder, shopkeeper_phone: '' }),
      });
      if (!r2.ok) throw new Error(`createOrder ${r2.status}`);
      const persisted = await r2.json();
      return persisted.order as Order;
    } catch (e) {
      console.warn('apiClient.createOrder failed:', e);
      throw e;
    }
  },

  // --- SUPPLIERS ---
  getSuppliers: async (): Promise<Supplier[]> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/suppliers`);
      if (!res.ok) throw new Error(`getSuppliers ${res.status}`);
      const json = await res.json();
      return json.suppliers || [];
    } catch (e) {
      console.warn('apiClient.getSuppliers failed:', e);
      return [];
    }
  },

  addSupplier: async (supplier: Omit<Supplier, 'id' | 'outstandingBalance'>): Promise<Supplier> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/suppliers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(supplier),
      });
      if (!res.ok) throw new Error(`addSupplier ${res.status}`);
      const json = await res.json();
      return json.supplier;
    } catch (e) {
      console.warn('apiClient.addSupplier failed:', e);
      throw e;
    }
  },

  getPurchaseOrders: async (): Promise<PurchaseOrder[]> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/purchase_orders`);
      if (!res.ok) throw new Error(`getPurchaseOrders ${res.status}`);
      const json = await res.json();
      return json.purchase_orders || [];
    } catch (e) {
      console.warn('apiClient.getPurchaseOrders failed:', e);
      return [];
    }
  },

  createPurchaseOrder: async (poData: Omit<PurchaseOrder, 'id' | 'createdAt' | 'status'>): Promise<PurchaseOrder> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/purchase_orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(poData),
      });
      if (!res.ok) throw new Error(`createPurchaseOrder ${res.status}`);
      const json = await res.json();
      return json.purchase_order;
    } catch (e) {
      console.warn('apiClient.createPurchaseOrder failed:', e);
      throw e;
    }
  },

  approvePurchaseOrder: async (poId: string): Promise<PurchaseOrder> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/purchase_orders/${encodeURIComponent(poId)}/approve`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`approvePurchaseOrder ${res.status}`);
      const json = await res.json();
      return json.purchase_order;
    } catch (e) {
      console.warn('apiClient.approvePurchaseOrder failed:', e);
      throw e;
    }
  },

  receivePurchaseOrder: async (poId: string): Promise<PurchaseOrder> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/purchase_orders/${encodeURIComponent(poId)}/receive`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`receivePurchaseOrder ${res.status}`);
      const json = await res.json();
      return json.purchase_order;
    } catch (e) {
      console.warn('apiClient.receivePurchaseOrder failed:', e);
      throw e;
    }
  },

  // Forecasts served by frontend/src/services/forecast.ts — keep single canonical client

  // --- ANALYTICS ---
  getAnalytics: async (): Promise<Analytics> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/analytics`);
      if (!res.ok) throw new Error(`getAnalytics ${res.status}`);
      const json = await res.json();
      return json.analytics || {};
    } catch (e) {
      console.warn('apiClient.getAnalytics failed:', e);
      return {} as Analytics;
    }
  },

  // --- NOTIFICATIONS ---
  getNotifications: async (): Promise<Notification[]> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/notifications`);
      if (!res.ok) throw new Error(`getNotifications ${res.status}`);
      const json = await res.json();
      return json.notifications || [];
    } catch (e) {
      console.warn('apiClient.getNotifications failed:', e);
      return [];
    }
  },

  markNotificationsAsRead: async (): Promise<void> => {
    try {
      await fetch(`${DB_ALERTS_BASE}/notifications/mark-read`, { method: 'POST' });
    } catch (e) {
      console.warn('apiClient.markNotificationsAsRead failed:', e);
    }
  },

  // --- SETTINGS ---
  getSettings: async (): Promise<StoreSettings> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/settings`);
      if (!res.ok) throw new Error(`getSettings ${res.status}`);
      const json = await res.json();
      return json.settings || DEFAULT_SETTINGS;
    } catch (e) {
      console.warn('apiClient.getSettings failed:', e);
      return DEFAULT_SETTINGS;
    }
  },

  saveSettings: async (settings: StoreSettings): Promise<StoreSettings> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (!res.ok) throw new Error(`saveSettings ${res.status}`);
      const json = await res.json();
      return json.settings;
    } catch (e) {
      console.warn('apiClient.saveSettings failed:', e);
      return settings;
    }
  },

  // --- WHATSAPP SIMULATED SERVICE ENGINE ---
  extractOrderFromWhatsApp: async (textMsg: string): Promise<{ order: Order | null; error?: string }> => {
    // Forward extraction to the ingestion service and persist via db_alerts
    try {
      const r1 = await fetch(INGESTION_PROCESS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload_type: 'text', payload: textMsg, customer_phone: 'unknown' }),
      });
      if (!r1.ok) return { order: null, error: 'Extraction failed' };
      const flatOrder = await r1.json();

      const r2 = await fetch(DB_ALERTS_LOG, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: flatOrder, shopkeeper_phone: 'whatsapp:+919986013436' }),
      });
      if (!r2.ok) return { order: null, error: 'Persist failed' };
      const persisted = await r2.json();
      return { order: persisted.order };
    } catch (e: any) {
      return { order: null, error: e?.message || String(e) };
    }
  }
};

// suppliersService is provided in frontend/src/services/suppliers.ts — do not duplicate here.
