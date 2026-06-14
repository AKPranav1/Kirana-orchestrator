/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Product, Customer, Order, Supplier, PurchaseOrder, Forecast, DashboardMetrics, Analytics, Notification, StoreSettings, KhataTransaction } from '../types';
import { dashboardService } from './dashboard';
import { INGESTION_PROCESS, DB_ALERTS_BASE, DB_ALERTS_ORDERS, DB_ALERTS_LOG } from '../config';

const DEFAULT_SETTINGS: StoreSettings = {
  storeName: "Kirana AI",
  ownerName: "Store Owner",
  phone: "+91 98765 43210",
  whatsappEnabled: true,
  storeStatus: "Online",
  autoExtractWhatsapp: true,
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
    try {
      // Fetch all khata records for balances
      const khataRes = await fetch(`${DB_ALERTS_BASE}/khata`);
      if (!khataRes.ok) {
        console.warn('Failed to fetch khata');
        return [];
      }
      
      const khataData = await khataRes.json();
      const khataRecords = khataData.records || [];
      
      // Fetch customer leaderboard for lifetime spend and order count
      const customersRes = await fetch(`${DB_ALERTS_BASE}/customers/leaderboard?limit=100`);
      const customersData = await customersRes.json();
      const customersList = customersData.customers || [];
      
      // Create map for customer metrics
      const customerMetrics = new Map();
      customersList.forEach((c: any) => {
        customerMetrics.set(c.customer_name, {
          lifetimeSpend: c.lifetime_spend || 0,
          orderCount: c.order_count || 0,
          avgBasket: c.order_count > 0 ? (c.lifetime_spend / c.order_count) : 0
        });
      });
      
      // Build customers with all data
      const customers = khataRecords.map((record: any) => {
        const name = record.customer_name;
        const metrics = customerMetrics.get(name) || { lifetimeSpend: 0, orderCount: 0, avgBasket: 0 };
        
        return {
          id: name,
          name: name,
          phone: record.customer_phone || "",
          status: (record.total_outstanding || 0) > 1000 ? 'Overdue' : 'Standard',
          khataBalance: record.total_outstanding || 0,
          avgBasket: metrics.avgBasket,
          lifetimeSpend: metrics.lifetimeSpend,
          orderCount: metrics.orderCount,  // Add this to Customer type
        };
      });
      
      return customers;
    } catch (e) {
      console.error('getCustomers failed:', e);
      return [];
    }
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
    customerId: string,
    type: 'credit' | 'payment',
    amount: number,
    description: string
  ): Promise<{ transaction: KhataTransaction; newBalance: number }> => {
    try {
      // Call your existing /khata/tx endpoint
      const res = await fetch(`${DB_ALERTS_BASE}/khata/tx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          customerId: customerId,
          type: type, 
          amount: amount, 
          description: description 
        }),
      });
      
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`HTTP ${res.status}: ${errorText}`);
      }
      
      const result = await res.json();
      console.log('Khata transaction result:', result);
      
      // Your backend returns { status: "success", transaction: {...} }
      const transaction = result.transaction;
      
      // Get the updated balance by fetching the customer again
      const khataRes = await fetch(`${DB_ALERTS_BASE}/khata/${encodeURIComponent(customerId)}`);
      let newBalance = 0;
      if (khataRes.ok) {
        const khataDoc = await khataRes.json();
        newBalance = khataDoc.total_outstanding || 0;
      }
      
      return {
        transaction: {
          id: transaction.id,
          customerId: customerId,
          customerName: customerId,
          type: type,
          amount: amount,
          date: transaction.date || new Date().toISOString(),
          description: description,
        },
        newBalance: newBalance,
      };
    } catch (e) {
      console.error('addKhataTransaction failed:', e);
      throw e;
    }
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

  createOrder: async (orderData: Omit<Order, 'id' | 'createdAt'>): Promise<Order> => {
    try {
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
      console.warn('createOrder failed:', e);
      throw e;
    }
  },

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
  getAnalytics: async (): Promise<Analytics> => {
    try {
      const res = await fetch(`${DB_ALERTS_BASE}/analytics`);
      if (res.ok) {
        const json = await res.json();
        return json.analytics || {
          totalRevenue: 0,
          totalOrders: 0,
          khataRecoveryRate: 0,
          topProducts: [],
          categoryDistribution: [],
          trendData: [],
        };
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
    const baseNotifications: Notification[] = [
      { id: '1', title: 'Low Stock Alert', description: 'Milk stock below 5 units', type: 'warning', createdAt: new Date().toISOString(), isRead: false },
      { id: '2', title: 'Khata Overdue', description: 'Customer has outstanding balance', type: 'warning', createdAt: new Date().toISOString(), isRead: false },
    ];
    const readIds = JSON.parse(localStorage.getItem('readNotificationIds') || '[]');
    return baseNotifications.map(n => ({ ...n, isRead: readIds.includes(n.id) }));
  },

  markNotificationsAsRead: async (): Promise<void> => {
    const baseNotifications = [
      { id: '1' }, { id: '2' }
    ];
    const allIds = baseNotifications.map(n => n.id);
    localStorage.setItem('readNotificationIds', JSON.stringify(allIds));
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
  extractOrderFromWhatsApp: async (textMsg: string): Promise<{ order: Order | null; error?: string }> => {
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
        body: JSON.stringify({ order: flatOrder, shopkeeper_phone: '' }),
      });
      if (!r2.ok) return { order: null, error: 'Persist failed' };
      const persisted = await r2.json();
      return { order: persisted.order };
    } catch (e: any) {
      return { order: null, error: e?.message || String(e) };
    }
  }
};