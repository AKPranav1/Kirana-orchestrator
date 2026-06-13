/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Product, Customer, Order, Supplier, PurchaseOrder, Forecast, DashboardMetrics, Analytics, Notification, StoreSettings, KhataTransaction } from '../types';
import { mockProducts } from '../data/products';
import { mockCustomers, mockKhataTransactions } from '../data/customers';
import { mockSuppliers, mockPurchaseOrders } from '../data/suppliers';
import { mockForecasts } from '../data/forecast';
import { mockAnalyticsData } from '../data/analytics';
import { mockDashboardMetrics, mockOrders, mockNotifications } from '../data/dashboard';

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

// Initialize localStorage with mock data if not already present
function initStorage() {
  if (typeof window === 'undefined') return;

  if (!localStorage.getItem('ka_products')) {
    localStorage.setItem('ka_products', JSON.stringify(mockProducts));
  }
  if (!localStorage.getItem('ka_customers')) {
    localStorage.setItem('ka_customers', JSON.stringify(mockCustomers));
  }
  if (!localStorage.getItem('ka_khata_txns')) {
    localStorage.setItem('ka_khata_txns', JSON.stringify(mockKhataTransactions));
  }
  if (!localStorage.getItem('ka_suppliers')) {
    localStorage.setItem('ka_suppliers', JSON.stringify(mockSuppliers));
  }
  if (!localStorage.getItem('ka_purchase_orders')) {
    localStorage.setItem('ka_purchase_orders', JSON.stringify(mockPurchaseOrders));
  }
  if (!localStorage.getItem('ka_forecasts')) {
    localStorage.setItem('ka_forecasts', JSON.stringify(mockForecasts));
  }
  if (!localStorage.getItem('ka_orders')) {
    localStorage.setItem('ka_orders', JSON.stringify(mockOrders));
  }
  if (!localStorage.getItem('ka_notifications')) {
    localStorage.setItem('ka_notifications', JSON.stringify(mockNotifications));
  }
  if (!localStorage.getItem('ka_settings')) {
    const defaultSettings: StoreSettings = {
      storeName: "Kirana AI",
      ownerName: "Store Owner",
      phone: "+91 98765 43210",
      whatsappEnabled: true,
      storeStatus: "Online",
      autoExtractWhatsapp: true,
      lowStockThreshold: 5
    };
    localStorage.setItem('ka_settings', JSON.stringify(defaultSettings));
  }
}

initStorage();

// Storage helper functions
const getStored = <T>(key: string): T | null => {
  // Default to null when key missing so callers can explicitly handle missing state.
  const raw = localStorage.getItem(key);
  if (!raw) return null;
  return JSON.parse(raw) as T;
};

const setStored = <T>(key: string, data: T) => {
  localStorage.setItem(key, JSON.stringify(data));
};

// Central simulated API client with simulated latencies for realistic UX
const delay = (ms = 400) => new Promise(resolve => setTimeout(resolve, ms));

import { dashboardService } from './dashboard';

export const apiClient = {
  // --- DASHBOARD ---
  // Delegate to dashboardService which prefers backend and provides a safe fallback
  getDashboard: async (): Promise<DashboardMetrics> => {
    return dashboardService.getDashboard();
  },

  // --- PRODUCTS / INVENTORY ---
  getProducts: async (): Promise<Product[]> => {
    await delay(300);
    return getStored<Product[]>('ka_products') || mockProducts;
  },

  addProduct: async (product: Omit<Product, 'id' | 'margin'>): Promise<Product> => {
    await delay(400);
    const products = getStored<Product[]>('ka_products') || mockProducts;
    const margin = parseFloat((( (product.unitPrice - product.costPrice) / product.unitPrice ) * 100).toFixed(1));
    const newProduct: Product = {
      ...product,
      id: `prod-${Date.now()}`,
      margin,
      status: product.stockQuantity === 0 ? 'Out of Stock' : product.stockQuantity < 5 ? 'Low Stock' : 'In Stock'
    };
    products.unshift(newProduct);
    setStored('ka_products', products);
    return newProduct;
  },

  updateProductStock: async (productId: string, quantity: number): Promise<Product> => {
    await delay(200);
    const products = getStored<Product[]>('ka_products') || mockProducts;
    const idx = products.findIndex(p => p.id === productId);
    if (idx === -1) throw new Error("Product not found");
    
    products[idx].stockQuantity = Math.max(0, quantity);
    products[idx].status = products[idx].stockQuantity === 0 ? 'Out of Stock' : products[idx].stockQuantity < 5 ? 'Low Stock' : 'In Stock';
    setStored('ka_products', products);
    return products[idx];
  },

  // --- CUSTOMERS ---
  getCustomers: async (): Promise<Customer[]> => {
    await delay(300);
    // Prefer backend when available (demo mode). Fallback to localStorage on error.
    try {
      const res = await fetch('http://localhost:8002/customers/leaderboard');
      if (!res.ok) throw new Error('backend error');
      const json = await res.json();
      return json.customers || [];
    } catch (e) {
      return getStored<Customer[]>('ka_customers') || mockCustomers;
    }
  },

  addCustomer: async (customer: Omit<Customer, 'id' | 'khataBalance' | 'avgBasket' | 'lifetimeSpend'>): Promise<Customer> => {
    await delay(400);
    const customers = getStored<Customer[]>('ka_customers') || mockCustomers;
    const newCustomer: Customer = {
      ...customer,
      id: `cust-${Date.now()}`,
      khataBalance: 0,
      avgBasket: 0,
      lifetimeSpend: 0,
      status: 'Standard'
    };
    customers.push(newCustomer);
    setStored('ka_customers', customers);
    return newCustomer;
  },

  getKhataTransactions: async (customerId?: string): Promise<KhataTransaction[]> => {
    await delay(200);
    // Prefer backend for khata transactions, fallback to localStorage
    try {
      if (!customerId) {
        // Fetch flattened khata transactions across all customers
        const res = await fetch('http://localhost:8002/khata');
        if (!res.ok) throw new Error('backend error');
        const json = await res.json();
        return json.transactions || [];
      }

      // If caller provided a customerId, try backend by customer name first (frontend uses customer id strings like 'cust-1' but backend stores customer_name strings).
      // We'll attempt to find the customer by name via the leaderboard and then request backend khata for that name as a best-effort mapping.
      const customersRes = await fetch('http://localhost:8002/customers/leaderboard');
      if (customersRes.ok) {
        const customersJson = await customersRes.json();
        const customers = customersJson.customers || [];
        const matched = customers.find((c: any) => c.id === customerId || c.customerId === customerId || c.name === customerId);
        if (matched) {
          const name = matched.customer_name || matched.name || matched.customerName;
          if (name) {
            const res = await fetch(`http://localhost:8002/khata/${encodeURIComponent(name)}`);
            if (res.ok) {
              const json = await res.json();
              // Backend returns full khata ledger; return its entries as transactions
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
        }
      }

      // If backend attempts didn't succeed or mapping not found, fall back to localStorage filtering
      const txns = getStored<KhataTransaction[]>('ka_khata_txns') || mockKhataTransactions;
      return txns.filter(t => t.customerId === customerId);
    } catch (e) {
      const txns = getStored<KhataTransaction[]>('ka_khata_txns') || mockKhataTransactions;
      if (customerId) return txns.filter(t => t.customerId === customerId);
      return txns;
    }
  },

  addKhataTransaction: async (customerId: string, type: 'credit' | 'payment', amount: number, description: string): Promise<KhataTransaction> => {
    await delay(400);
    const customers = getStored<Customer[]>('ka_customers') || mockCustomers;
    const txns = getStored<KhataTransaction[]>('ka_khata_txns') || mockKhataTransactions;
    const custIdx = customers.findIndex(c => c.id === customerId);
    if (custIdx === -1) throw new Error("Customer not found");

    const newTxn: KhataTransaction = {
      id: `txn-${Date.now()}`,
      customerId,
      customerName: customers[custIdx].name,
      type,
      amount,
      date: new Date().toISOString(),
      description
    };
    txns.unshift(newTxn);
    setStored('ka_khata_txns', txns);

    // Update customer Khata balance
    // credit means customer took items on credit, so Khata balance becomes more negative (customer owes more)
    // payment means customer paid back, so Khata balance increases towards 0 or positive
    const delta = type === 'credit' ? -amount : amount;
    customers[custIdx].khataBalance += delta;
    if (type === 'payment') {
      customers[custIdx].lifetimeSpend += amount; // optional representation
    }
    customers[custIdx].status = customers[custIdx].khataBalance < -1000 ? 'Overdue' : 'Standard';
    setStored('ka_customers', customers);

    return newTxn;
  },

  // --- ORDERS ---
  getOrders: async (): Promise<Order[]> => {
    // fetch from backend live orders
    try {
      const res = await fetch('http://localhost:8002/orders');
      if (!res.ok) throw new Error('orders fetch failed');
      const json = await res.json();
      return json.orders || [];
    } catch (e) {
      await delay(300);
      return getStored<Order[]>('ka_orders') || mockOrders;
    }
  },

  createOrder: async (orderData: Omit<Order, 'id' | 'createdAt'>): Promise<Order> => {
    await delay(500);
    const orders = getStored<Order[]>('ka_orders') || mockOrders;
    const products = getStored<Product[]>('ka_products') || mockProducts;
    const customers = getStored<Customer[]>('ka_customers') || mockCustomers;

    const newOrder: Order = {
      ...orderData,
      id: `ord-${orders.length + 1043}`,
      createdAt: new Date().toISOString()
    };
    orders.unshift(newOrder);
    setStored('ka_orders', orders);

    // Deduct stock and update products
    newOrder.items.forEach(item => {
      const pIdx = products.findIndex(p => p.id === item.productId);
      if (pIdx !== -1) {
        products[pIdx].stockQuantity = Math.max(0, products[pIdx].stockQuantity - item.quantity);
        products[pIdx].status = products[pIdx].stockQuantity === 0 ? 'Out of Stock' : products[pIdx].stockQuantity < 5 ? 'Low Stock' : 'In Stock';
      }
    });
    setStored('ka_products', products);

    // Update customer avg basket & spend if customer bound
    if (newOrder.customerId) {
      const cIdx = customers.findIndex(c => c.id === newOrder.customerId);
      if (cIdx !== -1) {
        customers[cIdx].lifetimeSpend += newOrder.totalAmount;
        customers[cIdx].lastOrderDate = newOrder.createdAt;
        customers[cIdx].avgBasket = Math.round((customers[cIdx].avgBasket + newOrder.totalAmount) / 2);
        setStored('ka_customers', customers);
      }
    }

    // Add notification if stock falls low
    const lowStockNotify = products.filter(p => p.status === 'Low Stock');
    if (lowStockNotify.length > 0) {
      const notifs = getStored<Notification[]>('ka_notifications') || mockNotifications;
      lowStockNotify.forEach(p => {
        if (!notifs.some(n => n.title.includes(p.name))) {
          notifs.unshift({
            id: `notif-${Date.now()}-${p.id}`,
            title: `${p.name} running low`,
            description: `Only ${p.stockQuantity} units left in stock. Reorder suggested.`,
            type: 'warning',
            createdAt: new Date().toISOString(),
            isRead: false
          });
        }
      });
      setStored('ka_notifications', notifs);
    }

    return newOrder;
  },

  // --- SUPPLIERS ---
  getSuppliers: async (): Promise<Supplier[]> => {
    await delay(300);
    return getStored<Supplier[]>('ka_suppliers') || mockSuppliers;
  },

  addSupplier: async (supplier: Omit<Supplier, 'id' | 'outstandingBalance'>): Promise<Supplier> => {
    await delay(400);
    const suppliers = getStored<Supplier[]>('ka_suppliers') || mockSuppliers;
    const newSupplier: Supplier = {
      ...supplier,
      id: `sup-${Date.now()}`,
      outstandingBalance: 0
    };
    suppliers.push(newSupplier);
    setStored('ka_suppliers', suppliers);
    return newSupplier;
  },

  getPurchaseOrders: async (): Promise<PurchaseOrder[]> => {
    await delay(300);
    return getStored<PurchaseOrder[]>('ka_purchase_orders') || mockPurchaseOrders;
  },

  createPurchaseOrder: async (poData: Omit<PurchaseOrder, 'id' | 'createdAt' | 'status'>): Promise<PurchaseOrder> => {
    await delay(400);
    const pos = getStored<PurchaseOrder[]>('ka_purchase_orders') || mockPurchaseOrders;
    const newPO: PurchaseOrder = {
      ...poData,
      id: `PO-2023-${pos.length + 107}`,
      status: 'Awaiting Approval',
      createdAt: new Date().toISOString()
    };
    pos.unshift(newPO);
    setStored('ka_purchase_orders', pos);
    return newPO;
  },

  approvePurchaseOrder: async (poId: string): Promise<PurchaseOrder> => {
    await delay(400);
    const pos = getStored<PurchaseOrder[]>('ka_purchase_orders') || mockPurchaseOrders;
    const suppliers = getStored<Supplier[]>('ka_suppliers') || mockSuppliers;
    const idx = pos.findIndex(p => p.id === poId);
    if (idx === -1) throw new Error("Purchase order not found");

    pos[idx].status = 'In Transit';
    pos[idx].estimatedDelivery = 'Est. in 2 days';
    pos[idx].deliveryProgress = 10;
    setStored('ka_purchase_orders', pos);

    // Add to suppliers outstanding payable
    const supIdx = suppliers.findIndex(s => s.id === pos[idx].supplierId);
    if (supIdx !== -1) {
      suppliers[supIdx].outstandingBalance += pos[idx].totalAmount;
      setStored('ka_suppliers', suppliers);
    }

    return pos[idx];
  },

  receivePurchaseOrder: async (poId: string): Promise<PurchaseOrder> => {
    await delay(500);
    const pos = getStored<PurchaseOrder[]>('ka_purchase_orders') || mockPurchaseOrders;
    const products = getStored<Product[]>('ka_products') || mockProducts;
    const idx = pos.findIndex(p => p.id === poId);
    if (idx === -1) throw new Error("Purchase order not found");

    pos[idx].status = 'Delivered';
    pos[idx].deliveryProgress = 100;
    setStored('ka_purchase_orders', pos);

    // Credit products stock
    pos[idx].items.forEach(item => {
      const pIdx = products.findIndex(p => p.id === item.productId);
      if (pIdx !== -1) {
        products[pIdx].stockQuantity += item.quantity;
        products[pIdx].status = 'In Stock';
      }
    });
    setStored('ka_products', products);

    // Create notification
    const notifs = getStored<Notification[]>('ka_notifications') || mockNotifications;
    notifs.unshift({
      id: `notif-${Date.now()}`,
      title: "Stock Received",
      description: `Inventory credited with items from ${pos[idx].supplierName}.`,
      type: 'success',
      createdAt: new Date().toISOString(),
      isRead: false
    });
    setStored('ka_notifications', notifs);

    return pos[idx];
  },

  // Forecasts served by frontend/src/services/forecast.ts — keep single canonical client

  // --- ANALYTICS ---
  getAnalytics: async (): Promise<Analytics> => {
    await delay(300);
    return mockAnalyticsData;
  },

  // --- NOTIFICATIONS ---
  getNotifications: async (): Promise<Notification[]> => {
    await delay(100);
    return getStored<Notification[]>('ka_notifications') || mockNotifications;
  },

  markNotificationsAsRead: async (): Promise<void> => {
    const notifs = getStored<Notification[]>('ka_notifications') || mockNotifications;
    notifs.forEach(n => n.isRead = true);
    setStored('ka_notifications', notifs);
  },

  // --- SETTINGS ---
  getSettings: async (): Promise<StoreSettings> => {
    await delay(100);
    return getStored<StoreSettings>('ka_settings') || DEFAULT_SETTINGS;
  },

  saveSettings: async (settings: StoreSettings): Promise<StoreSettings> => {
    await delay(200);
    setStored('ka_settings', settings);
    return settings;
  },

  // --- WHATSAPP SIMULATED SERVICE ENGINE ---
  extractOrderFromWhatsApp: async (textMsg: string): Promise<{ order: Order | null; error?: string }> => {
    // Forward extraction to the ingestion service and persist via db_alerts
    try {
      const r1 = await fetch('http://localhost:8001/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload_type: 'text', payload: textMsg, customer_phone: 'unknown' }),
      });
      if (!r1.ok) return { order: null, error: 'Extraction failed' };
      const flatOrder = await r1.json();

      const r2 = await fetch('http://localhost:8002/log', {
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
