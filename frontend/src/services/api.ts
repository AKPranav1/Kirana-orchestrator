/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Product, Customer, Order, Supplier, PurchaseOrder, Forecast, DashboardMetrics, Analytics, Notification, StoreSettings, KhataTransaction } from '../types';
import { dashboardService } from './dashboard';
import { apiFetch as fetch, checkedJson } from './http';
import { submitManualOrder } from './orderCommands';
import { INGESTION_PROCESS, DB_ALERTS_BASE, DB_ALERTS_ORDERS, DB_ALERTS_LOG } from '../config';

const DEFAULT_SETTINGS: StoreSettings = {
  storeName: "Kirana AI",
  ownerName: "Store Owner",
  phone: "+91 98765 43210",
  whatsappEnabled: false,
  storeStatus: "Online",
  autoExtractWhatsapp: false,
  lowStockThreshold: 5
};

export const apiClient = {
  // --- DASHBOARD ---
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

  // --- CUSTOMERS - Get all data including lifetime revenue and order history ---
  getCustomers: async (): Promise<Customer[]> => {
    const customers: any[] = [];
    for (let offset = 0; ; offset += 200) {
      const page = await checkedJson(await fetch(`${DB_ALERTS_BASE}/customers/leaderboard?limit=200&offset=${offset}&order_by=name`));
      customers.push(...page.customers);
      if (page.customers.length < 200) break;
    }
    return customers.map((c: any) => ({
      id: c.customer_name, name: c.customer_name, phone: c.customer_phone || '', status: 'Standard',
      khataBalance: -Number(c.total_outstanding || 0), lifetimeSpend: c.lifetime_spend || 0,
      orderCount: c.order_count || 0, avgBasket: c.order_count ? c.lifetime_spend / c.order_count : 0,
      lastOrderDate: c.last_order_at,
    }));
  },

  addCustomer: async (customer: Omit<Customer, 'id' | 'khataBalance' | 'avgBasket' | 'lifetimeSpend'>): Promise<Customer> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/customers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: customer.name,
          customer_phone: customer.phone,
          store_id: "store_001",
        }),
      });
      
      if (!res.ok) throw new Error(`addCustomer ${res.status}`);
      const json = await res.json();
      
      return {
        id: customer.name,
        name: customer.name,
        phone: customer.phone,
        status: 'Standard',
        khataBalance: 0,
        avgBasket: 0,
        lifetimeSpend: 0,
      };
    } catch (e) {
      console.warn('addCustomer failed:', e);
      throw e;
    }
  },

  // SIMPLE: get transactions for a customer
  getKhataTransactions: async (customerId?: string): Promise<KhataTransaction[]> => {
    try {
      if (!customerId) return [];
      
      const res = await fetch(`${DB_ALERTS_BASE}/khata/${encodeURIComponent(customerId)}`);
      if (!res.ok) return [];
      
      const khataDoc = await res.json();
      const entries = khataDoc.entries || [];
      
      return entries.map((entry: any, idx: number) => ({
        id: entry.order_id || `${customerId}-${idx}`,
        customerId: customerId,
        customerName: khataDoc.customer_name || customerId,
        type: entry.settled ? 'payment' : 'credit',
        amount: Math.abs(entry.amount),
        balanceAfter: entry.balance_after_paise === undefined ? undefined : entry.balance_after_paise / 100,
        date: entry.date,
        description: entry.description || `Order ${entry.order_id}`,
      }));
    } catch (e) {
      console.warn('getKhataTransactions failed:', e);
      return [];
    }
  },

  // SIMPLE: add transaction - your backend does the + and -
  addKhataTransaction: async (
    customerId: string, type: 'credit' | 'payment', amount: number, description: string,
    requestId: string = crypto.randomUUID()
  ): Promise<{ transaction: KhataTransaction; newBalance: number }> => {
    return checkedJson(await fetch(`${DB_ALERTS_BASE}/khata/tx`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: requestId, customerId, type, amount, description }),
    }));
  },

  // --- ORDERS ---
  getOrders: async (): Promise<Order[]> => {
    try {
      const res = await fetch(DB_ALERTS_ORDERS);
      if (!res.ok) throw new Error(`getOrders ${res.status}`);
      const json = await res.json();
      const ordersRaw = json.orders || [];

      return ordersRaw.map((o: any) => {
        let itemsArray: any[] = [];
        if (o.items && Array.isArray(o.items)) {
          itemsArray = o.items;
        } else if (o.processed_splits && Array.isArray(o.processed_splits)) {
          for (const split of o.processed_splits) {
            if (split.items && Array.isArray(split.items)) {
              itemsArray.push(...split.items);
            }
          }
        }

        const mappedItems = itemsArray.map((i: any) => ({
          productId: i.productId || i.product_id,
          productName: i.name || i.productName || i.item_name || 'Unknown',
          quantity: Number(i.qty ?? i.quantity ?? 0),
          price: Number(i.unit_price ?? i.price ?? 0),
        }));

        return {
          id: o.order_id || o.id,
          customerName: o.customer_name || o.customerName || 'Unknown',
          items: mappedItems,
          totalAmount: Number(o.total_amount ?? o.totalAmount ?? 0),
          status: o.status || 'Pending',
          source: o.source || (o.input_type === 'whatsapp' ? 'WhatsApp' : 'Manual'),
          createdAt: o.created_at || o.createdAt || new Date().toISOString(),
        };
      });
    } catch (e) {
      console.warn('getOrders failed:', e);
      return [];
    }
  },

  createOrder: (orderData: Omit<Order, 'id' | 'createdAt'>): Promise<Order> => submitManualOrder(orderData),

  // --- SUPPLIERS ---
  getSuppliers: async (): Promise<Supplier[]> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/suppliers`);
      if (!res.ok) throw new Error(`getSuppliers ${res.status}`);
      const json = await res.json();
      return (json.suppliers || []).map((s: any) => ({
        id: s.id,
        name: s.name,
        category: s.category,
        contactName: s.contactName,
        phone: s.phone,
        avgDeliveryDays: s.avgDeliveryDays,
        outstandingBalance: s.outstanding_balance ?? 0,
      }));
    } catch (e) {
      console.warn('getSuppliers failed:', e);
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
      console.warn('addSupplier failed:', e);
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
      console.warn('getPurchaseOrders failed:', e);
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
      console.warn('createPurchaseOrder failed:', e);
      throw e;
    }
  },

  approvePurchaseOrder: async (poId: string): Promise<PurchaseOrder> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/purchase_orders/${encodeURIComponent(poId)}/approve`, { method: 'POST' });
      if (!res.ok) throw new Error(`approvePurchaseOrder ${res.status}`);
      const json = await res.json();
      return json.purchase_order;
    } catch (e) {
      console.warn('approvePurchaseOrder failed:', e);
      throw e;
    }
  },

  receivePurchaseOrder: async (poId: string): Promise<PurchaseOrder> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/purchase_orders/${encodeURIComponent(poId)}/receive`, { method: 'POST' });
      if (!res.ok) throw new Error(`receivePurchaseOrder ${res.status}`);
      const json = await res.json();
      return json.purchase_order;
    } catch (e) {
      console.warn('receivePurchaseOrder failed:', e);
      throw e;
    }
  },

  // --- ANALYTICS ---
  getAnalytics: async (timeframe: '7d' | '30d' = '7d'): Promise<Analytics> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/analytics?timeframe=${timeframe}`);
      if (res.ok) {
        const json = await res.json();
        return json.analytics;
      }
    } catch (e) {
      console.warn('getAnalytics failed:', e);
    }
    
    return {
      totalRevenue: 0,
      totalOrders: 0,
      khataRecoveryRate: 0,
      topProducts: [],
      categoryDistribution: [],
      trendData: [],
    };
  },
  
  // --- NOTIFICATIONS ---
  getNotifications: async (): Promise<Notification[]> => {
    return (await checkedJson(await fetch(`${DB_ALERTS_BASE}/notifications`))).notifications;
  },

  markNotificationsAsRead: async (): Promise<void> => {
    await checkedJson(await fetch(`${DB_ALERTS_BASE}/notifications/mark-read`, { method: 'POST' }));
  },

  // --- SETTINGS ---
  getSettings: async (): Promise<StoreSettings> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/settings`);
      if (!res.ok) throw new Error(`getSettings ${res.status}`);
      const json = await res.json();
      return json.settings || DEFAULT_SETTINGS;
    } catch (e) {
      console.warn('getSettings failed:', e);
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
      console.warn('saveSettings failed:', e);
      return settings;
    }
  },

  // --- WHATSAPP ---
  extractOrder: async (text: string, customerName = 'Walk-in') => {
    return checkedJson(await fetch(INGESTION_PROCESS, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_id: crypto.randomUUID(), payload_type: 'text', payload: text, customer_name: customerName }),
    }));
  }
};
