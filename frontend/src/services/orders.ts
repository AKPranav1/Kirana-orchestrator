/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { apiClient } from './api';
import { Order } from '../types';

export const ordersService = {
  getOrders: (): Promise<Order[]> => {
    return (async () => {
      try {
        const res = await fetch("http://localhost:8002/orders");
        if (!res.ok) return [];
        const json = await res.json();
        return json.orders || [];
      } catch (e) {
        return [];
      }
    })();
  },
  
  createOrder: (order: Omit<Order, 'id' | 'createdAt'>): Promise<Order> => {
    return apiClient.createOrder(order);
  },

  extractOrderFromWhatsApp: (textMsg: string): Promise<{ order: Order | null; error?: string }> => {
    return (async () => {
      try {
        // 1) POST to ingestion service to extract and flatten order
        const r1 = await fetch("http://localhost:8001/process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ payload_type: "text", payload: textMsg, customer_phone: "unknown" }),
        });
        if (!r1.ok) {
          return { order: null, error: 'Extraction failed' };
        }
        const flatOrder = await r1.json();

        // 2) Persist via db_alerts
        const r2 = await fetch("http://localhost:8002/log", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ order: flatOrder, shopkeeper_phone: "whatsapp:+919986013436" }),
        });
        if (!r2.ok) {
          const txt = await r2.text();
          return { order: null, error: `Persist failed: ${txt}` };
        }
        const persisted = await r2.json();
        return { order: persisted.order, error: persisted.alert_status ? persisted.alert_status : undefined };
      } catch (e: any) {
        return { order: null, error: e?.message || String(e) };
      }
    })();
  }
};
