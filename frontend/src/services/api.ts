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
const getStored = <T>(key: string): T => {
  return JSON.parse(localStorage.getItem(key) || '[]') as T;
};

const setStored = <T>(key: string, data: T) => {
  localStorage.setItem(key, JSON.stringify(data));
};

// Central simulated API client with simulated latencies for realistic UX
const delay = (ms = 400) => new Promise(resolve => setTimeout(resolve, ms));

export const apiClient = {
  // --- DASHBOARD ---
  getDashboard: async (): Promise<DashboardMetrics> => {
    await delay();
    const products = getStored<Product[]>('ka_products');
    const customers = getStored<Customer[]>('ka_customers');
    const orders = getStored<Order[]>('ka_orders');
    const pos = getStored<PurchaseOrder[]>('ka_purchase_orders');

    // Dynamically calculate metrics based on stored states
    const todaysOrders = orders.filter(o => o.createdAt.startsWith('2026-06-13') || o.createdAt.includes('Today'));
    const todaysRevenue = todaysOrders.reduce((sum, o) => sum + o.totalAmount, 0);
    const outstandingKhata = customers.reduce((sum, c) => c.khataBalance < 0 ? sum + Math.abs(c.khataBalance) : sum, 0);
    const lowStockCount = products.filter(p => p.stockQuantity <= p.unitPrice * 0.02 || p.status === 'Low Stock' || p.stockQuantity < 5).length;
    const pendingDeliveries = pos.filter(po => po.status === 'In Transit').length;
    const pendingSupplierPay = suppliersService.getPendingSupplierPaymentSync();

    return {
      todaysRevenue: todaysRevenue || mockDashboardMetrics.todaysRevenue,
      todaysOrdersCount: todaysOrders.length || mockDashboardMetrics.todaysOrdersCount,
      outstandingKhata: outstandingKhata,
      lowStockItemsCount: lowStockCount,
      pendingDeliveriesCount: pendingDeliveries || mockDashboardMetrics.pendingDeliveriesCount,
      pendingSupplierPay: pendingSupplierPay,
      storeHealthScore: 94
    };
  },

  // --- PRODUCTS / INVENTORY ---
  getProducts: async (): Promise<Product[]> => {
    await delay(300);
    return getStored<Product[]>('ka_products');
  },

  addProduct: async (product: Omit<Product, 'id' | 'margin'>): Promise<Product> => {
    await delay(400);
    const products = getStored<Product[]>('ka_products');
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
    const products = getStored<Product[]>('ka_products');
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
    return getStored<Customer[]>('ka_customers');
  },

  addCustomer: async (customer: Omit<Customer, 'id' | 'khataBalance' | 'avgBasket' | 'lifetimeSpend'>): Promise<Customer> => {
    await delay(400);
    const customers = getStored<Customer[]>('ka_customers');
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
    const txns = getStored<KhataTransaction[]>('ka_khata_txns');
    if (customerId) {
      return txns.filter(t => t.customerId === customerId);
    }
    return txns;
  },

  addKhataTransaction: async (customerId: string, type: 'credit' | 'payment', amount: number, description: string): Promise<KhataTransaction> => {
    await delay(400);
    const customers = getStored<Customer[]>('ka_customers');
    const txns = getStored<KhataTransaction[]>('ka_khata_txns');
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
      if (!res.ok) return [];
      const json = await res.json();
      return json.orders || [];
    } catch (e) {
      await delay(300);
      return getStored<Order[]>('ka_orders');
    }
  },

  createOrder: async (orderData: Omit<Order, 'id' | 'createdAt'>): Promise<Order> => {
    await delay(500);
    const orders = getStored<Order[]>('ka_orders');
    const products = getStored<Product[]>('ka_products');
    const customers = getStored<Customer[]>('ka_customers');

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
      const notifs = getStored<Notification[]>('ka_notifications');
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
    return getStored<Supplier[]>('ka_suppliers');
  },

  addSupplier: async (supplier: Omit<Supplier, 'id' | 'outstandingBalance'>): Promise<Supplier> => {
    await delay(400);
    const suppliers = getStored<Supplier[]>('ka_suppliers');
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
    return getStored<PurchaseOrder[]>('ka_purchase_orders');
  },

  createPurchaseOrder: async (poData: Omit<PurchaseOrder, 'id' | 'createdAt' | 'status'>): Promise<PurchaseOrder> => {
    await delay(400);
    const pos = getStored<PurchaseOrder[]>('ka_purchase_orders');
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
    const pos = getStored<PurchaseOrder[]>('ka_purchase_orders');
    const suppliers = getStored<Supplier[]>('ka_suppliers');
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
    const pos = getStored<PurchaseOrder[]>('ka_purchase_orders');
    const products = getStored<Product[]>('ka_products');
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
    const notifs = getStored<Notification[]>('ka_notifications');
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

  // --- FORECASTS ---
  getForecasts: async (): Promise<Forecast[]> => {
    await delay(400);
    return getStored<Forecast[]>('ka_forecasts');
  },

  // --- ANALYTICS ---
  getAnalytics: async (): Promise<Analytics> => {
    await delay(300);
    return mockAnalyticsData;
  },

  // --- NOTIFICATIONS ---
  getNotifications: async (): Promise<Notification[]> => {
    await delay(100);
    return getStored<Notification[]>('ka_notifications');
  },

  markNotificationsAsRead: async (): Promise<void> => {
    const notifs = getStored<Notification[]>('ka_notifications');
    notifs.forEach(n => n.isRead = true);
    setStored('ka_notifications', notifs);
  },

  // --- SETTINGS ---
  getSettings: async (): Promise<StoreSettings> => {
    await delay(100);
    return getStored<StoreSettings>('ka_settings');
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

const suppliersService = {
  getPendingSupplierPaymentSync: (): number => {
    if (typeof window === 'undefined') return 15000;
    const suppliers = JSON.parse(localStorage.getItem('ka_suppliers') || '[]') as Supplier[];
    return suppliers.reduce((sum, s) => sum + s.outstandingBalance, 0);
  }
};
