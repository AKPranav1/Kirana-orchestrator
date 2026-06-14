/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { ShoppingCart, Filter, Search, Plus, MessageSquare, Tag, Eye } from 'lucide-react';
import { Order } from '../types';
import { ordersService } from '../services/orders';

interface LiveOrdersProps {
  onOpenNewOrder: () => void;
}

export default function LiveOrders({ onOpenNewOrder }: LiveOrdersProps) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [filter, setFilter] = useState<'All' | 'Received' | 'Processed' | 'Delivered' | 'Pending'>('All');
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeOrder, setActiveOrder] = useState<Order | null>(null);

  useEffect(() => {
    loadOrders();
  }, []);

  const loadOrders = async () => {
    setLoading(true);

    const list = await ordersService.getOrders();

    setOrders(
      list.map((o: any) => ({
        ...o,

        // Basic fields
        id: String(o.id ?? o.order_id ?? ""),
        customerName:
          o.customerName ??
          o.customer_name ??
          o.customer ??
          "Unknown Customer",

        source:
          o.source ??
          o.channel ??
          "WhatsApp",

        status:
          o.status ??
          "Pending",

        totalAmount:
          o.totalAmount ??
          o.total_amount ??
          o.bill_amount ??
          0,

        createdAt:
          o.createdAt ??
          o.created_at ??
          new Date().toISOString(),

        // Normalize items
        items: (o.items ?? []).map((i: any) => ({
          productName:
            i.productName ??
            i.name ??
            "Unknown Item",

          quantity:
            i.quantity ??
            i.qty ??
            1,

          price:
            i.price ??
            i.unit_price ??
            0,
        })),
      }))
    );

    setLoading(false);
  };

  const getStatusStyle = (status: Order['status']) => {
    switch (status) {
      case 'Delivered':
        return 'bg-[#10B981]/10 text-[#4edea3] border-[#10B981]/20';
      case 'Processed':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'Received':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      default:
        return 'bg-[#1F1F1F] text-[#888888] border-[#353534]';
    }
  };

  const filteredOrders = orders.filter(o => {
    const matchesFilter = filter === 'All' || o.status === filter;
    const matchesSearch = (o.customerName ?? "").toLowerCase().includes(search.toLowerCase()) || 
                          String(o.id ?? "").toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Incoming Orders</h2>
          <p className="text-xs text-[#888888] mt-1">See incoming orders from WhatsApp and in-store.</p>
        </div>
        <button 
          onClick={onOpenNewOrder}
          className="px-4 py-2 bg-white text-black hover:bg-[#e2e2e2] font-semibold text-xs rounded-sm flex items-center gap-2 cursor-pointer transition-colors"
        >
          <Plus size={14} /> New Manual Order
        </button>
      </div>

      {/* Filters and Search controls */}
      <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-3 flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#888888]" size={14} />
            <input 
              type="text"
              placeholder="Search by customer or ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm text-xs pl-9 pr-4 py-2 text-white placeholder-[#888888] focus:border-white focus:outline-none"
            />
        </div>

        {/* Categories togglers */}
        <div className="flex gap-1 overflow-x-auto">
          {(['All', 'Received', 'Processed', 'Delivered', 'Pending'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-sm text-xs font-semibold cursor-pointer transition-colors ${
                filter === f 
                  ? 'bg-white text-black' 
                  : 'bg-[#0F0F0F] text-[#888888] hover:text-white hover:bg-[#1C1B1B]'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Orders main list table (Cols 1-8) */}
        <div className="lg:col-span-8 bg-[#121212] border border-[#1F1F1F] rounded-lg overflow-hidden flex flex-col">
          <div className="p-4 border-b border-[#1F1F1F] flex justify-between items-center bg-[#161616]">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-white">Live Transactions</h3>
            <button onClick={loadOrders} className="text-[#888888] hover:text-white text-xs">Refresh</button>
          </div>

          <div className="overflow-x-auto">
            {loading ? (
              <p className="text-xs text-[#888888] p-10 text-center">Loading orders...</p>
            ) : filteredOrders.length === 0 ? (
              <p className="text-xs text-[#888888] p-10 text-center">No orders match filter selection.</p>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#1F1F1F] text-[#888888] text-[10px] uppercase font-bold tracking-wider bg-[#0F0F0F]">
                    <th className="p-4 font-semibold">Order Detail</th>
                    <th className="p-4 font-semibold">Origin</th>
                    <th className="p-4 font-semibold">Summary</th>
                    <th className="p-4 font-semibold text-right">Invoice Value</th>
                    <th className="p-4 font-semibold text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1F1F1F] text-xs">
                  {filteredOrders.map(o => (
                    <tr 
                      key={o.id} 
                      onClick={() => setActiveOrder(o)}
                      className="table-row-hover transition-colors cursor-pointer group"
                    >
                      <td className="p-4">
                        <div className="font-semibold text-white">Order #{o.id}</div>
                        <div className="text-[10px] text-[#888888] mt-0.5">{o.customerName ?? "Unknown Customer"}</div>
                      </td>
                      <td className="p-4">
                        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm text-[10px] font-semibold ${
                          o.source === 'WhatsApp' 
                            ? 'bg-[#25D366]/10 text-[#25D366]' 
                            : 'bg-white/10 text-white'
                        }`}>
                          {o.source === 'WhatsApp' && <MessageSquare size={10} />}
                          {o.source}
                        </span>
                      </td>
                      <td className="p-4 text-[#888888] max-w-xs truncate">
                        {(o.items ?? []).map(i => `${i.quantity}x ${i.productName}`).join(', ')}
                      </td>
                      <td className="p-4 text-right font-semibold text-white font-mono">
                        ₹{o.totalAmount}
                      </td>
                      <td className="p-4 text-right">
                        <span className={`px-2 py-0.5 border rounded-sm text-[10px] font-bold uppercase tracking-wider ${getStatusStyle(o.status)}`}>
                          {o.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Order Details Visual Inspector panel (Cols 9-12) */}
        <div className="lg:col-span-4 bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 flex flex-col justify-between">
          {activeOrder ? (
            <div className="space-y-4">
              <div className="flex justify-between items-start pb-3 border-b border-[#1F1F1F]">
                <div>
                  <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Order Details</h3>
                  <p className="text-[10px] text-[#888888] font-mono mt-0.5">#{activeOrder.id}</p>
                </div>
                <span className={`px-2.5 py-0.5 border rounded-sm text-[10px] font-bold uppercase tracking-wider ${getStatusStyle(activeOrder.status)}`}>
                  {activeOrder.status}
                </span>
              </div>

              {/* Specs */}
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#888888]">Customer Name:</span>
                  <span className="text-white font-semibold">{activeOrder.customerName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#888888]">Channel Source:</span>
                  <span className="text-white font-semibold">{activeOrder.source}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#888888]">Date Registered:</span>
                  <span className="text-white font-mono text-[10px]">{new Date(activeOrder.createdAt).toLocaleTimeString()}</span>
                </div>
              </div>

              {/* Items List */}
              <div className="border-t border-b border-[#1F1F1F] py-3 my-2 space-y-1.5">
                <span className="text-[10px] font-semibold text-[#888888] uppercase tracking-wider block">Line Items</span>
                {(activeOrder.items ?? []).map((i, idx) => (
                  <div key={idx} className="flex justify-between items-center text-xs">
                    <span className="text-[#888888]">{i.productName} <b className="text-white">x{i.quantity}</b></span>
                    <span className="font-mono text-white">₹{i.price * i.quantity}</span>
                  </div>
                ))}
              </div>

              <div className="flex justify-between items-baseline pt-2">
                <span className="text-xs text-[#888888]">Grand Invoice Total:</span>
                <span className="text-lg font-bold font-mono text-white">₹{activeOrder.totalAmount}</span>
              </div>
            </div>
          ) : (
            <div className="text-center py-10 flex flex-col items-center justify-center text-[#888888] flex-1">
              <Eye size={28} className="mb-2" />
              <p className="text-xs">Select any order to inspect structured details and dispatch details.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
