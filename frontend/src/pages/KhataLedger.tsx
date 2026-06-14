/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Wallet, Search, Filter, MessageSquare, Download, AlertCircle, ArrowUpRight, ArrowDownLeft } from 'lucide-react';
import { KhataTransaction, Customer } from '../types';
import { apiClient } from '../services/api';

export default function KhataLedger() {
  const [txns, setTxns] = useState<KhataTransaction[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<'all' | 'credit' | 'payment'>('all');
  const [loading, setLoading] = useState(true);
  const [ageing, setAgeing] = useState<any[]>([]);

  useEffect(() => {
    loadLedger();
  }, []);

  const loadLedger = async () => {
    setLoading(true);
    try {
      const custs = await apiClient.getCustomers();
      setCustomers(custs);
      
      // Load transactions for each customer or get all khata entries
      const allTxns: KhataTransaction[] = [];
      for (const customer of custs) {
        const customerTxns = await apiClient.getKhataTransactions(customer.id);
        allTxns.push(...customerTxns);
      }
      setTxns(allTxns.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()));
      
      try {
        const analytics = await apiClient.getAnalytics();
        setAgeing((analytics as any).khata_ageing || []);
      } catch (e) {
        // Mock ageing data if none exists
        setAgeing([
          { range: "0-7 days", amount: 0 },
          { range: "8-15 days", amount: 0 },
          { range: "16-30 days", amount: 0 },
          { range: ">30 days", amount: 0 }
        ]);
      }
    } catch (error) {
      console.error('Failed to load ledger:', error);
    } finally {
      setLoading(false);
    }
  };

  const getOutstandingTotal = () => {
    // khataBalance is negative (e.g., -180), so convert to positive for display
    return customers.reduce((sum, c) => {
      const balance = c.khataBalance || 0;
      // If balance is negative, add its absolute value
      return sum + (balance < 0 ? Math.abs(balance) : balance);
    }, 0);
  };
  const filteredTxns = txns.filter(t => {
    const matchesSearch = t.customerName?.toLowerCase().includes(search.toLowerCase()) || 
                          t.description?.toLowerCase().includes(search.toLowerCase());
    const matchesType = typeFilter === 'all' || t.type === typeFilter;
    return matchesSearch && matchesType;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Khata Credit Ledger</h2>
          <p className="text-xs text-[#888888] mt-1">Settle outstanding customer book credit accounts and view chronological ageing cycles.</p>
        </div>
        <button 
          onClick={() => {
            if (txns.length === 0) return;
            const keys = ["Date", "Customer", "Type", "Amount", "Notes"];
            const csvContent = "data:text/csv;charset=utf-8," 
              + keys.join(",") + "\n"
              + txns.map(t => `"${t.date}","${t.customerName}","${t.type}","${t.amount}","${t.description || ''}"`).join("\n");
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `Khata_Ledger_Export_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }}
          className="px-4 py-2 bg-[#1C1B1B] hover:bg-white hover:text-black border border-[#1F1F1F] font-semibold text-xs rounded-sm text-white flex items-center gap-2 cursor-pointer transition-all"
        >
          <Download size={14} /> Export CSV Ledger
        </button>
      </div>

      {/* Top Ledger Aggregations Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Sum details panel (Cols 1-4) */}
        <div className="lg:col-span-4 bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 flex flex-col justify-between h-52">
          <div>
            <span className="text-[10px] font-bold text-[#888888] uppercase tracking-wider block">Total Book Outstanding Credit</span>
            <div className="text-3xl font-extrabold text-red-400 mt-2 font-mono tracking-tight">
              ₹ {getOutstandingTotal().toLocaleString('en-IN')}
            </div>
            <p className="text-xs text-[#888888] mt-3">
              Total credit owed by customers across {customers.length} active records.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs bg-red-500/5 text-red-400 p-2.5 rounded border border-red-500/10">
            <AlertCircle size={14} />
            <span>Needs immediate WhatsApp reminder recovery!</span>
          </div>
        </div>

        {/* CSS Ageing Analysis panel (Cols 5-12) */}
        <div className="lg:col-span-8 bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 flex flex-col justify-between h-52">
          <div>
            <span className="text-[10px] font-bold text-[#888888] uppercase tracking-wider block">Credit Ageing Cohort Analysis (Overdue)</span>
            <div className="grid grid-cols-4 gap-4 mt-6 text-xs">
              {ageing.length > 0 ? ageing.map((co, idx) => {
                const maxAmt = Math.max(...ageing.map(c => c.amount || 0), 1);
                const heightPercentage = maxAmt > 0 ? ((co.amount || 0) / maxAmt) * 100 : 0;
                return (
                  <div key={idx} className="flex flex-col items-center justify-end h-24">
                    <span className="text-[10px] font-semibold text-white font-mono">₹{(co.amount || 0).toLocaleString()}</span>
                    <div 
                      style={{ height: `${Math.max(heightPercentage, 4)}%` }}
                      className={`w-full max-w-[28px] mt-1.5 rounded-t-sm transition-all duration-700 ${
                        idx === 0 ? 'bg-[#10B981]/20' : idx === 1 ? 'bg-amber-500/20' : 'bg-red-400/40'
                      }`}
                    ></div>
                    <span className="text-[9px] text-[#888888] font-bold uppercase tracking-wide mt-2">{co.range}</span>
                  </div>
                );
              }) : (
                <div className="col-span-4 text-center text-[#888888] text-xs">No ageing data available</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Filter and Streams */}
      <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg overflow-hidden">
        {/* Filter controls headers */}
        <div className="p-4 border-b border-[#1F1F1F] flex flex-wrap gap-4 justify-between items-center bg-[#161616]">
          <div className="relative w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#888888]" size={14} />
            <input 
              type="text"
              placeholder="Filter ledger stream by comments..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm text-xs pl-9 pr-4 py-2 text-white focus:outline-none focus:border-[#333]"
            />
          </div>

          <div className="flex gap-1">
            {(['all', 'credit', 'payment'] as const).map(f => (
              <button
                key={f}
                onClick={() => setTypeFilter(f)}
                className={`px-3 py-1.5 rounded-sm text-xs font-semibold cursor-pointer transition-colors capitalize ${
                  typeFilter === f 
                    ? 'bg-white text-black' 
                    : 'bg-[#0F0F0F] text-[#888888] hover:text-white hover:bg-[#1C1B1B]'
                }`}
              >
                {f === 'all' ? 'All Ledger Streams' : f}
              </button>
            ))}
          </div>
        </div>

        {/* Transactions list */}
        <div className="overflow-x-auto">
          {loading ? (
            <p className="text-xs p-10 text-center text-[#888888]">Loading credit transactions stream...</p>
          ) : filteredTxns.length === 0 ? (
            <p className="text-xs p-10 text-center text-[#888888]">No matching ledger entry found.</p>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#1F1F1F] text-[#888888] text-[10px] uppercase font-bold bg-[#0F0F0F]">
                  <th className="p-4">Timestamp</th>
                  <th className="p-4">Customer</th>
                  <th className="p-4">Description of Transaction</th>
                  <th className="p-4 text-right">Adjustment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F1F1F] text-xs">
                {filteredTxns.map((t, idx) => {
                  const isPayment = t.type === 'payment';
                  return (
                    <tr key={idx} className="hover:bg-[#1a1a1a] transition-colors">
                      <td className="p-4 font-mono text-[10px] text-[#888888]">
                        {new Date(t.date).toLocaleString()}
                      </td>
                      <td className="p-4 text-white font-semibold">{t.customerName}</td>
                      <td className="p-4 text-[#888888]">{t.description || 'No description'}</td>
                      <td className="p-4 text-right">
                        <span className={`inline-flex items-center gap-1 font-semibold font-mono ${
                          isPayment ? 'text-[#4edea3]' : 'text-red-400'
                        }`}>
                          {isPayment ? <ArrowDownLeft size={12} /> : <ArrowUpRight size={12} />}
                          ₹ {t.amount.toLocaleString()}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}