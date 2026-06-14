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

// Helper: delay for simulation (not used in prod)
const delay = (ms = 400) => new Promise(resolve => setTimeout(resolve, ms));

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

  // --- CUSTOMERS (ENRICHED) ---
  getCustomers: async (): Promise<Customer[]> => {
    try {
      // 1. Fetch raw customers (leaderboard)
      const res = await fetch(`${DB_ALERTS_BASE}/customers/leaderboard`);
      if (!res.ok) throw new Error(`getCustomers ${res.status}`);
      const json = await res.json();
      let customers = json.customers || [];

      // 2. Fetch all khata balances (to compute khataBalance, order_count, lifetime_spend)
      const khataRes = await fetch(`${DB_ALERTS_BASE}/khata`);
      const khataData = await khataRes.json();
      const khataMap = new Map(); // key: customerName -> total_outstanding
      if (khataData.transactions) {
        khataData.transactions.forEach((tx: any) => {
          const name = tx.customerName;
          const amount = tx.amount;
          if (!khataMap.has(name)) khataMap.set(name, 0);
          
          if (tx.type === 'payment') {
            khataMap.set(name, khataMap.get(name) - amount);
          } else {
            khataMap.set(name, khataMap.get(name) + amount);
          }
        });
      }

      // 3. Fetch all orders to compute avgBasket and lifetimeSpend if missing
      const ordersRes = await fetch(DB_ALERTS_ORDERS);
      let ordersMap = new Map(); // key: customerName -> { totalSpend, orderCount }
      if (ordersRes.ok) {
        const ordersJson = await ordersRes.json();
        const orders = ordersJson.orders || [];
        for (const order of orders) {
          const name = order.customer_name || order.customerName;
          if (!name) continue;
          const amount = order.total_amount || order.totalAmount || 0;
          if (!ordersMap.has(name)) ordersMap.set(name, { totalSpend: 0, orderCount: 0 });
          const entry = ordersMap.get(name);
          entry.totalSpend += amount;
          entry.orderCount += 1;
        }
      }

      // 4. Enrich each customer
      const enriched: Customer[] = customers.map((c: any) => {
        const name = c.customer_name || c.name || "";
        const outstanding = khataMap.get(name) || 0;
        // Frontend expects khataBalance negative for overdue (money owed by customer)
        const khataBalance = -outstanding;
        const orderStats = ordersMap.get(name) || { totalSpend: 0, orderCount: 0 };
        const lifetimeSpend = c.lifetime_spend ?? orderStats.totalSpend;
        const orderCount = c.order_count ?? orderStats.orderCount;
        const avgBasket = orderCount > 0 ? lifetimeSpend / orderCount : 0;

        let status: 'Frequent' | 'Overdue' | 'Standard' = 'Standard';
        if (khataBalance < -1000) status = 'Overdue';
        else if (orderCount > 5) status = 'Frequent';

        return {
          id: c.id || name,
          name: name,
          phone: c.customer_phone || c.phone || "",
          status,
          khataBalance,
          avgBasket,
          lifetimeSpend,
          lastOrderDate: c.last_order_at || undefined,
        };
      });
      return enriched;
    } catch (e) {
      console.warn('apiClient.getCustomers failed:', e);
      return [];
    }
  },

  addCustomer: async (customer: Omit<Customer, 'id' | 'khataBalance' | 'avgBasket' | 'lifetimeSpend'>): Promise<Customer> => {
    try {
      const payload = {
        customer_name: customer.name,
        customer_phone: customer.phone,
        store_id: "store_001",
        lifetime_spend: 0,
        order_count: 0,
      };
      const res = await fetch(`${DB_ALERTS_BASE}/customers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`addCustomer ${res.status}`);
      const json = await res.json();
      const raw = json.customer;
      return {
        id: raw.id || raw.customer_name,
        name: raw.customer_name,
        phone: raw.customer_phone,
        status: 'Standard',
        khataBalance: 0,
        avgBasket: 0,
        lifetimeSpend: 0,
      };
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
      // If customerId provided, try to get by name
      const res = await fetch(`${DB_ALERTS_BASE}/khata/${encodeURIComponent(customerId)}`);
      if (!res.ok) return [];
      const data = await res.json();
      const entries = data.entries || [];
      return entries.map((e: any, idx: number) => ({
        id: `${customerId}-${e.order_id}-${idx}`,
        customerId: customerId,
        customerName: customerId,
        type: e.settled ? 'payment' : 'credit',
        amount: e.amount,
        date: e.date,
        description: e.description || `Order ${e.order_id}`,
      }));
    } catch (e) {
      console.warn('apiClient.getKhataTransactions failed:', e);
      return [];
    }
  },

  addKhataTransaction: async (customerId: string, type: 'credit' | 'payment', amount: number, description: string): Promise<KhataTransaction> => {
    try {
      const payload = { customerId, type, amount, description };
      console.log('[api] addKhataTransaction payload:', payload);

      const res = await fetch(`${DB_ALERTS_BASE}/khata/tx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error('[api] addKhataTransaction failed:', res.status, errorText);
        throw new Error(`HTTP ${res.status}: ${errorText}`);
      }

      const json = await res.json();
      console.log('[api] addKhataTransaction response:', json);
      
      // Ensure the returned transaction matches KhataTransaction type
      return {
        id: json.transaction.id,
        customerId: json.transaction.customerId,
        customerName: json.transaction.customerName,
        type: json.transaction.type as 'credit' | 'payment',
        amount: json.transaction.amount,
        date: json.transaction.date,
        description: json.transaction.description,
      };
    } catch (e) {
      console.error('apiClient.addKhataTransaction failed:', e);
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
        // ---- Extract items robustly ----
        let itemsArray: any[] = [];

        if (o.items && Array.isArray(o.items)) {
          // Direct items array (flat order)
          itemsArray = o.items;
        } else if (o.processed_splits && Array.isArray(o.processed_splits)) {
          // Nested splits (from ingestion)
          for (const split of o.processed_splits) {
            if (split.items && Array.isArray(split.items)) {
              itemsArray.push(...split.items);
            }
          }
        } else if (o.raw_items && Array.isArray(o.raw_items)) {
          itemsArray = o.raw_items;
        }

        // Map each item to expected frontend format
        const mappedItems = itemsArray.map((i: any) => ({
          productId: i.productId || i.product_id || i.id,
          productName: i.name || i.productName || i.item_name || 'Unknown Item',
          quantity: Number(i.qty ?? i.quantity ?? 0),
          price: Number(i.unit_price ?? i.price ?? 0),
        }));

        // Safely extract total amount
        const totalAmount = Number(o.total_amount ?? o.totalAmount ?? 0);

        // Extract date
        let createdAt = o.created_at || o.createdAt;
        if (!createdAt) createdAt = new Date().toISOString();

        return {
          id: o.order_id || o.id,
          customerName: o.customer_name || o.customerName || 'Unknown Customer',
          items: mappedItems,
          totalAmount,
          status: o.status || 'Pending',
          source: o.source || (o.input_type === 'whatsapp' ? 'WhatsApp' : 'Manual'),
          createdAt,
        };
      });
    } catch (e) {
      console.warn('apiClient.getOrders failed:', e);
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
      const res = await fetch(`${DB_ALERTS_BASE}/purchase_orders/${encodeURIComponent(poId)}/approve`, { method: 'POST' });
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
      const res = await fetch(`${DB_ALERTS_BASE}/purchase_orders/${encodeURIComponent(poId)}/receive`, { method: 'POST' });
      if (!res.ok) throw new Error(`receivePurchaseOrder ${res.status}`);
      const json = await res.json();
      return json.purchase_order;
    } catch (e) {
      console.warn('apiClient.receivePurchaseOrder failed:', e);
      throw e;
    }
  },

  // --- ANALYTICS (COMPUTED FROM ORDERS) ---
  getAnalytics: async (): Promise<Analytics> => {
    try {
      // Try backend first (may be incomplete)
      const backendRes = await fetch(`${DB_ALERTS_BASE}/analytics`);
      let backendData: any = {};
      if (backendRes.ok) backendData = await backendRes.json();

      // Fetch all orders to compute missing metrics
      const orders = await apiClient.getOrders();
      if (!orders.length) {
        return {
          totalRevenue: 0,
          totalOrders: 0,
          khataRecoveryRate: 0,
          topProducts: [],
          categoryDistribution: [],
          trendData: [],
        };
      }

      // 1. Basic totals
      const totalRevenue = orders.reduce((sum, o) => sum + (o.totalAmount || 0), 0);
      const totalOrders = orders.length;

      // 2. Top products (by revenue)
      const productSales = new Map<string, { name: string; salesCount: number; revenue: number }>();
      for (const order of orders) {
        for (const item of order.items) {
          const name = item.productName;
          const rev = (item.price || 0) * (item.quantity || 0);
          if (!productSales.has(name)) {
            productSales.set(name, { name, salesCount: 0, revenue: 0 });
          }
          const entry = productSales.get(name)!;
          entry.salesCount += item.quantity || 0;
          entry.revenue += rev;
        }
      }
      const topProducts = Array.from(productSales.values())
        .sort((a, b) => b.revenue - a.revenue)
        .slice(0, 5);

      // 3. Category distribution (requires products catalog mapping)
      // Fallback: group by first letter of product name or use a static map
      // For better accuracy, fetch products and join
      let products: Product[] = [];
      try {
        products = await apiClient.getProducts();
      } catch (e) { /* ignore */ }
      const categoryMap = new Map<string, number>();
      for (const item of productSales.keys()) {
        const prod = products.find(p => p.name === item);
        const cat = prod?.category || "Other";
        const revenue = productSales.get(item)?.revenue || 0;
        categoryMap.set(cat, (categoryMap.get(cat) || 0) + revenue);
      }
      const totalCatRevenue = Array.from(categoryMap.values()).reduce((a, b) => a + b, 0);
      const categoryDistribution = Array.from(categoryMap.entries()).map(([name, value]) => ({
        name,
        value: totalCatRevenue ? Math.round((value / totalCatRevenue) * 100) : 0,
      }));

      // 4. Trend data (last 30 days)
      const now = new Date();
      const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      const filteredOrders = orders.filter(o => new Date(o.createdAt) >= thirtyDaysAgo);
      const dailyMap = new Map<string, { revenue: number; orders: number }>();
      filteredOrders.forEach(o => {
        const date = new Date(o.createdAt).toISOString().slice(0, 10);
        if (!dailyMap.has(date)) dailyMap.set(date, { revenue: 0, orders: 0 });
        const entry = dailyMap.get(date)!;
        entry.revenue += o.totalAmount || 0;
        entry.orders += 1;
      });
      const trendData = Array.from(dailyMap.entries())
        .map(([date, val]) => ({ date, revenue: val.revenue, orders: val.orders }))
        .sort((a, b) => a.date.localeCompare(b.date));

      // 5. Khata recovery rate (payments / credits over last 30 days)
      let khataRecoveryRate = 0;
      try {
        const khataTxns = await apiClient.getKhataTransactions();
        const recentTxns = khataTxns.filter(t => new Date(t.date) >= thirtyDaysAgo);
        const totalCredits = recentTxns.filter(t => t.type === 'credit').reduce((s, t) => s + t.amount, 0);
        const totalPayments = recentTxns.filter(t => t.type === 'payment').reduce((s, t) => s + t.amount, 0);
        khataRecoveryRate = totalCredits > 0 ? (totalPayments / totalCredits) : 0;
      } catch (e) { /* ignore */ }

      return {
        totalRevenue,
        totalOrders,
        khataRecoveryRate,
        topProducts,
        categoryDistribution,
        trendData,
      };
    } catch (e) {
      console.warn('apiClient.getAnalytics failed:', e);
      return {
        totalRevenue: 0,
        totalOrders: 0,
        khataRecoveryRate: 0,
        topProducts: [],
        categoryDistribution: [],
        trendData: [],
      };
    }
  },

  // --- NOTIFICATIONS (static demo) ---
  getNotifications: async (): Promise<Notification[]> => {
    // Static demo notifications (you can modify or fetch from backend later)
    const baseNotifications: Notification[] = [
      { 
        id: '1', 
        title: 'Low Stock Alert', 
        description: 'Milk stock below 5 units', 
        type: 'warning', 
        createdAt: new Date().toISOString(), 
        isRead: false 
      },
      { 
        id: '2', 
        title: 'Khata Overdue', 
        description: 'Anjali Sharma owes ₹4250', 
        type: 'warning', 
        createdAt: new Date().toISOString(), 
        isRead: false 
      },
    ];
    const readIds = JSON.parse(localStorage.getItem('readNotificationIds') || '[]');
    return baseNotifications.map(n => ({
      ...n,
      isRead: readIds.includes(n.id)
    }));
  },


  markNotificationsAsRead: async (): Promise<void> => {
    // Get all notification IDs
    const baseNotifications: Notification[] = [
      { id: '1', title: 'Low Stock Alert', description: 'Milk stock below 5 units', type: 'warning', createdAt: new Date().toISOString(), isRead: false },
      { id: '2', title: 'Khata Overdue', description: 'Anjali Sharma owes ₹4250', type: 'warning', createdAt: new Date().toISOString(), isRead: false },
    ];
    const allIds = baseNotifications.map(n => n.id);
    // Store in localStorage
    localStorage.setItem('readNotificationIds', JSON.stringify(allIds));
    
    // Optional: also call backend if you have a real endpoint
    try {
      await fetch(`${DB_ALERTS_BASE}/notifications/mark-read`, { method: 'POST' });
    } catch (e) {
      // Ignore backend errors – frontend already handles it
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