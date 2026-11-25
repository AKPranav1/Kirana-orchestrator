import { API_BASE } from '../config';
import type { Order } from '../types';
import { apiFetch, checkedJson } from './http';

export function orderView(raw: any): Order {
  return {
    id: raw.order_id, customerName: raw.customer_name, customerPhone: raw.customer_phone,
    totalAmount: raw.total_amount, status: raw.status, createdAt: raw.created_at,
    source: raw.input_type === 'whatsapp' ? 'WhatsApp' : 'In-Store',
    items: raw.items.map((item: any) => ({ productId: item.product_id, productName: item.name,
      quantity: item.qty, price: item.unit_price, unit: item.unit })),
  };
}

export async function submitManualOrder(order: Omit<Order, 'id' | 'createdAt'>, transport = apiFetch): Promise<Order> {
  const body = {
    request_id: order.requestId || crypto.randomUUID(), customer_name: order.customerName,
    customer_phone: order.customerPhone || '', payment_mode: order.payment_mode || 'cash', input_type: 'manual',
    items: order.items.map(item => ({ product_id: item.productId, qty: item.quantity, ...(item.unit ? { unit: item.unit } : {}) })),
  };
  const result = await checkedJson(await transport(`${API_BASE}/orders`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  }));
  return orderView(result.order);
}
