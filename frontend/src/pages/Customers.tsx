/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Users, Search, Plus, Star, AlertTriangle, Send, ScrollText, X, Wallet, History } from 'lucide-react';
import { Customer } from '../types';
import { customersService } from '../services/customers';

const formatMoney = (value: number): string => {
  let rounded = Math.round((value || 0) * 100) / 100;
  if (rounded === -0) rounded = 0;
  return rounded.toFixed(2);
};

interface LedgerEntry {
  id: string;
  type: 'credit' | 'payment';
  date: string;
  description: string;
  amount: number;
  runningBalance: number;
}

interface OrderHistory {
  id: string;
  order_id: string;
  total_amount: number;
  created_at: string;
  items: any[];
  status: string;
}

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  
  const [settleCustomer, setSettleCustomer] = useState<Customer | null>(null);
  const [settleAmount, setSettleAmount] = useState("");
  const [settleDesc, setSettleDesc] = useState("Settle partial outstanding ledger");
  const [settleLoading, setSettleLoading] = useState(false);

  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newPhone, setNewPhone] = useState("");

  const [selectedCustomerForHistory, setSelectedCustomerForHistory] = useState<Customer | null>(null);
  const [ledgerEntries, setLedgerEntries] = useState<LedgerEntry[]>([]);
  const [ledgerLoading, setLedgerLoading] = useState(false);

  const [selectedCustomerForOrders, setSelectedCustomerForOrders] = useState<Customer | null>(null);
  const [customerOrders, setCustomerOrders] = useState<OrderHistory[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);

  useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = async () => {
    setLoading(true);
    const list = await customersService.getCustomers();
    setCustomers(list);
    setLoading(false);
  };

  const handleAddCustomer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !newPhone.trim()) return;
    try {
      await customersService.addCustomer({
        name: newName,
        phone: newPhone,
        status: 'Standard'
      });
      setNewName("");
      setNewPhone("");
      setShowAddForm(false);
      loadCustomers();
    } catch (err) {
      alert("Error adding customer");
    }
  };

  const handleRecordPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settleCustomer || !settleAmount || parseFloat(settleAmount) <= 0) return;
    setSettleLoading(true);
    try {
      await customersService.addKhataTransaction(
        settleCustomer.name,
        'payment',
        parseFloat(settleAmount),
        settleDesc
      );
      setSettleAmount("");
      setSettleCustomer(null);
      await loadCustomers();
      if (selectedCustomerForHistory?.id === settleCustomer.id) {
        await handleViewHistory(settleCustomer);
      }
    } catch (err) {
      console.error(err);
      alert("Error processing khata settlement.");
    } finally {
      setSettleLoading(false);
    }
  };

  const handleViewHistory = async (customer: Customer) => {
    setSelectedCustomerForHistory(customer);
    setLedgerLoading(true);
    try {
      const txns = await customersService.getKhataTransactions(customer.name);
      const sorted = [...txns].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
      let balance = 0;
      const entriesWithBalance = sorted.map(t => {
        const amount = t.type === 'credit' ? t.amount : -t.amount;
        balance += amount;
        return {
          id: t.id,
          type: t.type,
          date: t.date,
          description: t.description,
          amount: t.amount,
          runningBalance: balance,
        };
      });
      setLedgerEntries([...entriesWithBalance].reverse());
    } catch (err) {
      console.error(err);
      setLedgerEntries([]);
    } finally {
      setLedgerLoading(false);
    }
  };

  const handleViewOrderHistory = async (customer: Customer) => {
    setSelectedCustomerForOrders(customer);
    setOrdersLoading(true);
    try {
      const res = await fetch(`http://localhost:8002/orders`);
      const data = await res.json();
      const allOrders = data.orders || [];
      
      const filtered = allOrders.filter((order: any) => 
        order.customer_name === customer.name ||
        order.customerName === customer.name
      );
      
      setCustomerOrders(filtered);
    } catch (err) {
      console.error(err);
      setCustomerOrders([]);
    } finally {
      setOrdersLoading(false);
    }
  };

  const filteredCustomers = customers.filter(c =>
    (c.name ?? "").toLowerCase().includes(search.toLowerCase()) ||
    (c.phone ?? "").includes(search)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Customer Directory</h2>
          <p className="text-xs text-[#888888] mt-1">Manage relationships, WhatsApp billing linkages, and outstanding Khata registers.</p>
        </div>
        <button onClick={() => setShowAddForm(true)} className="px-4 py-2 bg-white text-black hover:bg-[#e2e2e2] font-semibold text-xs rounded-sm flex items-center gap-2 cursor-pointer">
          <Plus size={14} /> Add New Customer
        </button>
      </div>

      {showAddForm && (
        <form onSubmit={handleAddCustomer} className="bg-[#121212] border border-[#10B981]/30 p-5 rounded-md space-y-4 max-w-md">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-white">Create Customer Ledger Profile</h3>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Full Name" className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white" required />
            <input type="text" value={newPhone} onChange={(e) => setNewPhone(e.target.value)} placeholder="Phone (+91)" className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white" required />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowAddForm(false)} className="px-3 py-1.5 bg-transparent border border-[#1F1F1F] text-[#888888]">Cancel</button>
            <button type="submit" className="px-3 py-1.5 bg-[#10B981] text-black font-semibold rounded-sm">Register</button>
          </div>
        </form>
      )}

      <div className="relative w-full max-w-2xl bg-[#121212] border border-[#1F1F1F] rounded-lg p-2">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#888888]" size={14} />
        <input type="text" placeholder="Search directory..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full bg-transparent border-none text-xs pl-8 pr-4 py-1.5 text-white placeholder-[#888888] focus:outline-none" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredCustomers.map(c => {
          const khataOwed = Math.abs(c.khataBalance ?? 0);
          const isOwed = (c.khataBalance ?? 0) > 0;
          const isZero = khataOwed === 0;
          const isOverdue = isOwed && khataOwed > 1000;
          const isFrequent = (c.orderCount || 0) > 5;

          return (
            <div key={c.id} className={`bg-[#121212] border rounded-md p-5 flex flex-col justify-between h-full hover:border-[#353534] transition-all relative ${isOverdue ? 'border-red-500/20' : 'border-[#1F1F1F]'}`}>
              {isOverdue && <div className="absolute top-0 left-0 right-0 h-1 bg-red-400"></div>}
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-[#1C1B1B] border border-[#1F1F1F] flex items-center justify-center text-white font-semibold text-sm">{c.name.charAt(0)}</div>
                  <div>
                    <button onClick={() => handleViewHistory(c)} className="text-left hover:underline">
                      <h4 className="text-xs font-bold text-white cursor-pointer">{c.name}</h4>
                    </button>
                    <p className="text-[10px] text-[#888888] mt-0.5">{c.phone}</p>
                  </div>
                </div>
                {isFrequent && <span className="bg-[#10B981]/15 text-[#4edea3] text-[10px] uppercase font-bold py-0.5 px-2 rounded-sm flex items-center gap-1"><Star size={10} /> Frequent</span>}
                {isOverdue && <span className="bg-red-400/10 text-red-400 text-[10px] uppercase font-bold py-0.5 px-2 rounded-sm flex items-center gap-1"><AlertTriangle size={10} /> Overdue</span>}
              </div>
              
              <div className="grid grid-cols-2 gap-3 mb-5 text-xs">
                <div className="p-2.5 rounded-sm border bg-[#0F0F0F] border-[#1F1F1F]">
                  <p className="text-[9px] text-[#888888] uppercase font-bold">Khata Balance</p>
                  <p className={`font-semibold font-mono text-xs mt-1 ${isOwed ? 'text-red-400' : 'text-green-500'}`}>
                    ₹ {formatMoney(khataOwed)}
                  </p>
                </div>
                <div className="p-2.5 rounded-sm border bg-[#0F0F0F] border-[#1F1F1F]">
                  <p className="text-[9px] text-[#888888] uppercase font-bold">Total Orders</p>
                  <p className="font-semibold text-white font-mono text-xs mt-1">{c.orderCount || 0}</p>
                </div>
                <div className="p-2.5 rounded-sm border bg-[#0F0F0F] border-[#1F1F1F]">
                  <p className="text-[9px] text-[#888888] uppercase font-bold">Avg Basket</p>
                  <p className="font-semibold text-white font-mono text-xs mt-1">₹ {formatMoney(c.avgBasket ?? 0)}</p>
                </div>
                <div className="p-2.5 rounded-sm border bg-[#0F0F0F] border-[#1F1F1F]">
                  <p className="text-[9px] text-[#888888] uppercase font-bold">Lifetime Revenue</p>
                  <p className="font-semibold text-[#4edea3] font-mono text-xs mt-1">₹ {formatMoney(c.lifetimeSpend ?? 0)}</p>
                </div>
              </div>
              
              <div className="flex gap-2">
                <button 
                  onClick={() => { 
                    navigator.clipboard.writeText(`Namaste ${c.name}, please settle Khata balance ₹${khataOwed}.`); 
                    alert("WhatsApp message copied!"); 
                  }} 
                  className="flex-1 bg-transparent border border-[#1F1F1F] hover:border-white text-xs font-semibold py-1.5 rounded-sm text-[#888888] hover:text-white flex items-center justify-center gap-1"
                >
                  <Send size={12} /> WhatsApp
                </button>
                <button 
                  onClick={() => handleViewOrderHistory(c)} 
                  className="flex-1 bg-[#1C1B1B] hover:bg-blue-500 hover:text-white border border-[#1F1F1F] text-xs font-semibold py-1.5 rounded-sm text-white flex items-center justify-center gap-1"
                >
                  <History size={12} /> Orders
                </button>
                <button 
                  onClick={() => setSettleCustomer(c)} 
                  className="flex-1 bg-[#1C1B1B] hover:bg-white hover:text-black border border-[#1F1F1F] text-xs font-semibold py-1.5 rounded-sm text-white flex items-center justify-center gap-1"
                >
                  <Wallet size={12} /> Settle
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Settle Khata Modal */}
      {settleCustomer && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <form onSubmit={handleRecordPayment} className="bg-[#121212] border border-[#1F1F1F] rounded-md p-5 w-full max-w-sm space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-[#1F1F1F]">
              <h3 className="text-xs font-semibold text-white">Record Khata Payback</h3>
              <button type="button" onClick={() => setSettleCustomer(null)} className="text-[#888888] hover:text-white">✕</button>
            </div>
            <p className="text-xs text-[#888888]">
              Recording a payment reduces <b className="text-white">{settleCustomer.name}</b>'s open credit balance of ₹{formatMoney(Math.abs(settleCustomer.khataBalance ?? 0))}.
            </p>
            
            <div className="space-y-3">
              <input 
                type="number" 
                step="0.01"
                value={settleAmount} 
                onChange={(e) => setSettleAmount(e.target.value)} 
                placeholder="Enter payment amount" 
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white" 
                required 
                min="0.01"
              />
              <input 
                type="text" 
                value={settleDesc} 
                onChange={(e) => setSettleDesc(e.target.value)} 
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white" 
                required 
              />
            </div>
            
            <div className="flex gap-2">
              <button 
                type="button" 
                onClick={() => {
                  const fullAmount = Math.abs(settleCustomer.khataBalance ?? 0);
                  setSettleAmount(fullAmount.toFixed(2));
                  setSettleDesc("Full khata settlement");
                }}
                className="flex-1 bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-semibold py-2 rounded-sm hover:bg-amber-500/30 transition"
              >
                Clear All Khata
              </button>
              <button 
                type="submit" 
                disabled={settleLoading} 
                className="flex-1 bg-[#10B981] text-black font-semibold text-xs py-2 rounded-sm disabled:opacity-50"
              >
                {settleLoading ? "Processing..." : "Approve Payment"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Khata Ledger Modal */}
      {selectedCustomerForHistory && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-[#121212] border border-[#1F1F1F] rounded-md w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden">
            <div className="p-4 border-b border-[#1F1F1F] flex justify-between items-center bg-[#161616]">
              <div>
                <h3 className="text-sm font-semibold text-white">Khata Ledger: {selectedCustomerForHistory.name}</h3>
                <p className="text-[10px] text-[#888888]">{selectedCustomerForHistory.phone}</p>
              </div>
              <button onClick={() => setSelectedCustomerForHistory(null)} className="text-[#888888] hover:text-white"><X size={18} /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {ledgerLoading ? <p className="text-xs text-center text-[#888888] py-10">Loading ledger...</p> : ledgerEntries.length === 0 ? <p className="text-xs text-center text-[#888888] py-10">No transactions found.</p> : (
                <div className="space-y-3">
                  <div className="grid grid-cols-12 gap-2 text-[10px] font-bold text-[#888888] uppercase border-b border-[#1F1F1F] pb-2">
                    <div className="col-span-3">Date</div><div className="col-span-5">Description</div><div className="col-span-2 text-right">Amount</div><div className="col-span-2 text-right">Balance</div>
                  </div>
                  {ledgerEntries.map(entry => {
                    const isCredit = entry.type === 'credit';
                    const amountDisplay = isCredit ? `+ ₹${formatMoney(entry.amount)}` : `- ₹${formatMoney(entry.amount)}`;
                    const amountClass = isCredit ? 'text-red-400' : 'text-green-500';
                    const balanceColor = entry.runningBalance === 0 ? 'text-green-500' : 'text-red-500';
                    return (
                      <div key={entry.id} className="grid grid-cols-12 gap-2 text-xs border-b border-[#1F1F1F] py-2">
                        <div className="col-span-3 text-[#888888]">{new Date(entry.date).toLocaleString()}</div>
                        <div className="col-span-5">
                          {entry.type === 'payment' ? 'Payment: ' : 'Credit: '}{entry.description}
                        </div>
                        <div className={`col-span-2 text-right font-mono ${amountClass}`}>{amountDisplay}</div>
                        <div className={`col-span-2 text-right font-mono font-bold ${balanceColor}`}>₹{formatMoney(entry.runningBalance)}</div>
                      </div>
                    );
                  })}
                  <div className="grid grid-cols-12 gap-2 text-xs pt-3 border-t border-[#1F1F1F] mt-2">
                    <div className="col-span-8 text-right font-bold text-white">Current Outstanding:</div>
                    <div className="col-span-2 text-right font-bold font-mono text-red-500">
                      ₹{formatMoney(Math.abs(selectedCustomerForHistory.khataBalance ?? 0))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Order History Modal */}
      {selectedCustomerForOrders && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-[#121212] border border-[#1F1F1F] rounded-md w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden">
            <div className="p-4 border-b border-[#1F1F1F] flex justify-between items-center bg-[#161616]">
              <div>
                <h3 className="text-sm font-semibold text-white">Order History: {selectedCustomerForOrders.name}</h3>
                <p className="text-[10px] text-[#888888]">
                  Total Orders: {selectedCustomerForOrders.orderCount || 0} | 
                  Total Spent: ₹{formatMoney(selectedCustomerForOrders.lifetimeSpend || 0)} | 
                  Avg Order: ₹{formatMoney(selectedCustomerForOrders.avgBasket || 0)}
                </p>
              </div>
              <button onClick={() => setSelectedCustomerForOrders(null)} className="text-[#888888] hover:text-white"><X size={18} /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {ordersLoading ? (
                <p className="text-xs text-center text-[#888888] py-10">Loading orders...</p>
              ) : customerOrders.length === 0 ? (
                <p className="text-xs text-center text-[#888888] py-10">No orders found.</p>
              ) : (
                <div className="space-y-3">
                  {customerOrders.map((order, idx) => (
                    <div key={idx} className="bg-[#0F0F0F] border border-[#1F1F1F] rounded-md p-3 hover:border-[#353534] transition-all">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <span className="text-[10px] text-[#888888]">Order #{order.order_id || order.id}</span>
                          <div className="text-sm font-bold text-white font-mono mt-1">₹{formatMoney(order.total_amount)}</div>
                        </div>
                        <span className="text-[10px] text-[#888888]">{new Date(order.created_at).toLocaleDateString()}</span>
                      </div>
                      <div className="text-[10px] text-[#888888] mt-2">
                        Items: {(order.items || []).map((i: any, idx2: number) => (
                          <span key={idx2}>
                            {idx2 > 0 && ', '}
                            {i.qty || i.quantity}x {i.name || i.productName}
                          </span>
                        ))}
                      </div>
                      <div className="text-[10px] text-[#4edea3] mt-2">Status: {order.status || 'Completed'}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}