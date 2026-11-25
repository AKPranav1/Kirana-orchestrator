import assert from 'node:assert/strict';
import test from 'node:test';
import { submitManualOrder } from './orderCommands.ts';

test('a manual khata sale uses one canonical request and the server total', async () => {
  const calls: { url: string; body: any }[] = [];
  const transport = (async (url: string, init: RequestInit) => {
    calls.push({ url, body: JSON.parse(init.body as string) });
    return new Response(JSON.stringify({ order: { order_id: 'ord-1', customer_name: 'Demo', total_amount: 60,
      status: 'Processed', created_at: '2026-11-26T00:00:00Z', items: [{ product_id: 'rice', name: 'Rice', qty: 1, unit_price: 60 }] } }));
  }) as typeof fetch;
  const result = await submitManualOrder({ requestId: 'manual-0001', customerName: 'Demo', payment_mode: 'khata',
    items: [{ productId: 'rice', productName: 'Rice', quantity: 1, price: 1 }], totalAmount: 1, status: 'Processed', source: 'In-Store' }, transport);
  assert.equal(calls.length, 1);
  assert.ok(calls[0].url.endsWith('/orders'));
  assert.equal(calls[0].body.request_id, 'manual-0001');
  assert.equal(calls[0].body.payment_mode, 'khata');
  assert.deepEqual(calls[0].body.items, [{ product_id: 'rice', qty: 1 }]);
  assert.equal(result.totalAmount, 60);
  assert.equal(result.id, 'ord-1');
});

test('failed order responses surface server validation rather than success', async () => {
  const transport = (async () => new Response(JSON.stringify({ detail: 'Insufficient stock' }), { status: 409 })) as typeof fetch;
  await assert.rejects(() => submitManualOrder({ requestId: 'manual-0001', customerName: 'Demo', items: [], totalAmount: 0,
    status: 'Pending', source: 'Manual' }, transport), /Insufficient stock/);
});
