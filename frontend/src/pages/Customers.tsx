/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Users, Search, Plus, Star, AlertTriangle, Send, ScrollText, Check, DollarSign } from 'lucide-react';
import { Customer } from '../types';
import { customersService } from '../services/customers';

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  
  // Settle Khata Modal state
  const [settleCustomer, setSettleCustomer] = useState<Customer | null>(null);
  const [settleAmount, setSettleAmount] = useState("");
  const [settleDesc, setSettleDesc] = useState("Settle partial outstanding ledger");
  const [settleLoading, setSettleLoading] = useState(false);

  // Add Customer standard form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newPhone, setNewPhone] = useState("");

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
      // payment type credits their khata towards positive (paying back money owed)
      await customersService.addKhataTransaction(
        settleCustomer.id,
        'payment',
        parseFloat(settleAmount),
        settleDesc
      );
      setSettleAmount("");
      setSettleCustomer(null);
      loadCustomers();
    } catch (err) {
      alert("Error processing khata settlement.");
    } finally {
      setSettleLoading(false);
    }
  };

  const filteredCustomers = customers.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase()) || 
    c.phone.includes(search)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Customer Directory</h2>
          <p className="text-xs text-[#888888] mt-1">Manage relationships, WhatsApp billing linkages, and outstanding Khata registers.</p>
        </div>
        <button 
          onClick={() => setShowAddForm(true)}
          className="px-4 py-2 bg-white text-black hover:bg-[#e2e2e2] font-semibold text-xs rounded-sm flex items-center gap-2 cursor-pointer transition-colors"
        >
          <Plus size={14} /> Add New Customer
        </button>
      </div>

      {/* Add customer form overlay block */}
      {showAddForm && (
        <form onSubmit={handleAddCustomer} className="bg-[#121212] border border-[#10B981]/30 p-5 rounded-md space-y-4 max-w-md animate-pulse-soft">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-white">Create Customer Ledger Profile</h3>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="space-y-1">
              <label className="text-[#888888]">Customer Full Name</label>
              <input 
                type="text" 
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Rohan Shinde"
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-[#888888]">Phone (+91)</label>
              <input 
                type="text" 
                value={newPhone}
                onChange={(e) => setNewPhone(e.target.value)}
                placeholder="+91 91100 00000"
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none"
                required
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 text-xs">
            <button 
              type="button" 
              onClick={() => setShowAddForm(false)}
              className="px-3 py-1.5 bg-transparent border border-[#1F1F1F] text-[#888888]"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="px-3 py-1.5 bg-[#10B981] text-black font-semibold rounded-sm"
            >
              Register Customer
            </button>
          </div>
        </form>
      )}

      {/* Search Bar */}
      <div className="relative w-full max-w-2xl bg-[#121212] border border-[#1F1F1F] rounded-lg p-2 flex items-center justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#888888]" size={14} />
          <input 
            type="text"
            placeholder="Search directory by name, phone and statuses..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-transparent border-none text-xs pl-9 pr-4 py-1.5 text-white placeholder-[#888888] focus:outline-none"
          />
        </div>
      </div>

      {/* Customers Cards list */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredCustomers.map(c => {
          const isOverdue = c.khataBalance < -1000 || c.status === 'Overdue';
          const isFrequent = c.status === 'Frequent';

          return (
            <div 
              key={c.id} 
              className={`bg-[#121212] border rounded-md p-5 flex flex-col justify-between h-full hover:border-[#353534] transition-all relative overflow-hidden ${
                isOverdue ? 'border-red-500/20' : 'border-[#1F1F1F]'
              }`}
            >
              {isOverdue && (
                <div className="absolute top-0 left-0 right-0 h-1 bg-red-400"></div>
              )}

              {/* Head stats */}
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-[#1C1B1B] border border-[#1F1F1F] flex items-center justify-center text-white font-semibold text-sm">
                    {c.name.charAt(0)}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">{c.name}</h4>
                    <p className="text-[10px] text-[#888888] mt-0.5">{c.phone}</p>
                  </div>
                </div>

                {isFrequent && (
                  <span className="bg-[#10B981]/15 text-[#4edea3] text-[10px] uppercase font-bold py-0.5 px-2 rounded-sm border border-[#10B981]/25 flex items-center gap-1">
                    <Star size={10} /> Frequent
                  </span>
                )}
                {isOverdue && (
                  <span className="bg-red-400/10 text-red-400 text-[10px] uppercase font-bold py-0.5 px-2 rounded-sm border border-red-500/20 flex items-center gap-1">
                    <AlertTriangle size={10} /> Overdue
                  </span>
                )}
              </div>

              {/* Balances details */}
              <div className="grid grid-cols-2 gap-3 mb-5 text-xs">
                <div className={`p-2.5 rounded-sm border ${
                  isOverdue ? 'bg-red-500/5 border-red-500/10' : 'bg-[#0F0F0F] border-[#1F1F1F]'
                }`}>
                  <p className="text-[9px] text-[#888888] uppercase font-bold tracking-wider">Khata Balance</p>
                  <p className={`font-semibold font-mono text-xs mt-1 ${
                    c.khataBalance < 0 ? 'text-red-400' : c.khataBalance > 0 ? 'text-[#4edea3]' : 'text-gray-400'
                  }`}>
                    ₹ {c.khataBalance.toLocaleString('en-IN')}
                  </p>
                </div>

                <div className="bg-[#0F0F0F] border border-[#1F1F1F] p-2.5 rounded-sm">
                  <p className="text-[9px] text-[#888888] uppercase font-bold tracking-wider">Avg Basket</p>
                  <p className="font-semibold text-white font-mono text-xs mt-1">₹ {c.avgBasket}</p>
                </div>

                <div className="col-span-2 bg-[#0F0F0F] border border-[#1F1F1F] p-2.5 rounded-sm flex justify-between items-center text-xs">
                  <p className="text-[9px] text-[#888888] uppercase font-bold tracking-wider">LIFETIME REVENUE</p>
                  <p className="font-semibold text-white font-mono">₹ {c.lifetimeSpend.toLocaleString('en-IN')}</p>
                </div>
              </div>

              {/* Action togglers */}
              <div className="flex gap-2">
                <button 
                  onClick={() => {
                    const message = `Namaste ${c.name}, this is Suresh Sharma's Kirana store. Kindly settle your outstanding Khata balance of ₹${Math.abs(c.khataBalance)}. Thank you!`;
                    navigator.clipboard.writeText(message);
                    alert("WhatsApp notification templates copied to your clipboard!");
                  }}
                  className="flex-1 bg-transparent border border-[#1F1F1F] hover:border-white text-xs font-semibold py-1.5 px-3 rounded-sm text-[#888888] hover:text-white flex items-center justify-center gap-1 transition-colors cursor-pointer"
                >
                  <Send size={12} /> WhatsApp
                </button>
                <button 
                  onClick={() => setSettleCustomer(c)}
                  className="flex-1 bg-[#1C1B1B] hover:bg-white hover:text-black border border-[#1F1F1F] text-xs font-semibold py-1.5 px-3 rounded-sm text-white flex items-center justify-center gap-1 transition-all cursor-pointer"
                >
                  <ScrollText size={12} /> Settle Khata
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Settle Khata Dialogue overlay */}
      {settleCustomer && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <form onSubmit={handleRecordPayment} className="bg-[#121212] border border-[#1F1F1F] rounded-md p-5 w-full max-w-sm space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-[#1F1F1F]">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-white">Record Khata Payback</h3>
              <button type="button" onClick={() => setSettleCustomer(null)} className="text-[#888888] hover:text-white">
                <span className="text-base">✕</span>
              </button>
            </div>

            <p className="text-xs text-[#888888]">
              Recording a payment reduces <b className="text-white">{settleCustomer.name}</b>'s open credit balance of ₹{Math.abs(settleCustomer.khataBalance)}.
            </p>

            <div className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-[#888888]">Payment Amount Received (₹)</label>
                <input 
                  type="number"
                  value={settleAmount}
                  onChange={(e) => setSettleAmount(e.target.value)}
                  placeholder="e.g. 1000"
                  className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white font-mono"
                  required
                  min="1"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[#888888]">Transaction Notes</label>
                <input 
                  type="text"
                  value={settleDesc}
                  onChange={(e) => setSettleDesc(e.target.value)}
                  className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white"
                  required
                />
              </div>
            </div>

            <button 
              type="submit"
              disabled={settleLoading}
              className="w-full bg-[#10B981] text-black font-semibold text-xs py-2 rounded-sm cursor-pointer"
            >
              {settleLoading ? "Recording payment..." : "Approve Settlement Receipt"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
