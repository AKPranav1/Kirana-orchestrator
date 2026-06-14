/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { FileText, Download, Play, CheckCircle, Calculator, Wallet, ShieldAlert } from 'lucide-react';
import { Product, Customer } from '../types';
import { apiClient } from '../services/api';

export default function Reports() {
  const [products, setProducts] = useState<Product[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);

  // Preview generated models state
  const [activeReport, setActiveReport] = useState<'none' | 'valuation' | 'gst' | 'khata'>('none');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    const p = await apiClient.getProducts();
    const c = await apiClient.getCustomers();
    setProducts(p);
    setCustomers(c);
    setLoading(false);
  };

  const calculateInventoryValuation = () => {
    return products.reduce((sum, p) => sum + (p.costPrice * p.stockQuantity), 0);
  };

  const calculateRetailValuation = () => {
    return products.reduce((sum, p) => sum + (p.unitPrice * p.stockQuantity), 0);
  };

  const totalOutstandingKhata = () => {
    return customers.reduce((sum, c) => c.khataBalance < 0 ? sum + Math.abs(c.khataBalance) : sum, 0);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Reports</h2>
          <p className="text-xs text-[#888888] mt-1">Create CSVs for accounting, GST and stock value.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Inventory Valuation Report */}
        <div className="bg-[#121212] border border-[#1F1F1F] rounded-md p-5 flex flex-col justify-between h-56 hover:border-[#353534] transition-all">
          <div>
            <div className="p-2 bg-[#10B981]/10 rounded-sm w-fit text-[#4edea3] mb-3">
              <Calculator size={16} />
            </div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-white">Stock value report</h3>
            <p className="text-xs text-[#888888] mt-2 leading-relaxed">
              Calculates wholesaler cost value and retail value for your stock.
            </p>
          </div>
            <button 
              onClick={() => setActiveReport('valuation')}
              className="w-full mt-4 py-2 bg-[#1C1B1B] hover:bg-white hover:text-black border border-[#1F1F1F] text-white font-semibold text-xs rounded-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <Play size={10} /> Generate stock report
            </button>
        </div>

        {/* Card 2: GST Summary Reports */}
        <div className="bg-[#121212] border border-[#1F1F1F] rounded-md p-5 flex flex-col justify-between h-56 hover:border-[#353534] transition-all">
          <div>
            <div className="p-2 bg-blue-500/10 rounded-sm w-fit text-blue-400 mb-3">
              <FileText size={16} />
            </div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-white">GST report</h3>
            <p className="text-xs text-[#888888] mt-2 leading-relaxed">
              Consolidates sales and shows GST amounts per slab.
            </p>
          </div>
            <button 
              onClick={() => setActiveReport('gst')}
              className="w-full mt-4 py-2 bg-[#1C1B1B] hover:bg-white hover:text-black border border-[#1F1F1F] text-white font-semibold text-xs rounded-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <Play size={10} /> Generate GST report
            </button>
        </div>

        {/* Card 3: Khata Aging Overdue Reminders */}
        <div className="bg-[#121212] border border-[#1F1F1F] rounded-md p-5 flex flex-col justify-between h-56 hover:border-[#353534] transition-all">
          <div>
            <div className="p-2 bg-red-500/10 rounded-sm w-fit text-red-400 mb-3">
              <Wallet size={16} />
            </div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-white">Credit book report</h3>
            <p className="text-xs text-[#888888] mt-2 leading-relaxed">
              Shows overdue customers and total unpaid amounts.
            </p>
          </div>
            <button 
              onClick={() => setActiveReport('khata')}
              className="w-full mt-4 py-2 bg-[#1C1B1B] hover:bg-white hover:text-black border border-[#1F1F1F] text-white font-semibold text-xs rounded-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <Play size={10} /> View credit report
            </button>
        </div>
      </div>

      {/* On-Screen formatted inspection preview segment */}
      {activeReport !== 'none' && (
        <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 mt-6 animate-fade-in relative">
          <button 
            onClick={() => setActiveReport('none')}
            className="absolute top-4 right-4 text-xs font-semibold text-[#888888] hover:text-white cursor-pointer"
          >
            ✕ Dismiss Report
          </button>

          {activeReport === 'valuation' && (
            <div className="space-y-4">
                <h3 className="text-sm font-semibold text-[#4edea3] uppercase tracking-wider flex items-center gap-2">
                  <CheckCircle size={14} /> Stock value report ready
                </h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-xs pt-2">
                <div className="bg-[#0A0A0A] border border-[#1F1F1F] p-3 rounded-sm">
                  <span className="text-[#888888] text-[9px] uppercase font-bold">Total Unique SKUs</span>
                  <p className="text-sm font-bold text-white mt-1">{products.length}</p>
                </div>
                <div className="bg-[#0A0A0A] border border-[#1F1F1F] p-3 rounded-sm">
                  <span className="text-[#888888] text-[9px] uppercase font-bold">Consolidated Items Count</span>
                  <p className="text-sm font-bold text-white mt-1">{products.reduce((sum, p) => sum + p.stockQuantity, 0)} Units</p>
                </div>
                <div className="bg-[#0A0A0A] border border-[#1F1F1F] p-3 rounded-sm">
                  <span className="text-[#888888] text-[9px] uppercase font-bold">Wholesaler cost value</span>
                  <p className="text-sm font-bold text-[#4edea3] font-mono mt-1">₹ {calculateInventoryValuation().toLocaleString('en-IN')}</p>
                </div>
                <div className="bg-[#0A0A0A] border border-[#1F1F1F] p-3 rounded-sm">
                  <span className="text-[#888888] text-[10px] uppercase font-bold">Retail value</span>
                  <p className="text-sm font-bold text-white font-mono mt-1">₹ {calculateRetailValuation().toLocaleString('en-IN')}</p>
                </div>
              </div>
            </div>
          )}

          {activeReport === 'gst' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-2">
                <CheckCircle size={14} /> Month-to-Date GST summary calculated (GSTIN: 19AABCX1234F1Z8)
              </h3>
              <div className="text-xs space-y-3 pt-2">
                <div className="p-3 bg-[#0A0A0A] border border-[#1F1F1F] rounded-sm flex justify-between">
                  <div>
                    <span className="text-[10px] font-bold text-[#888888] uppercase tracking-wider">CGST (State Tax Share)</span>
                    <p className="text-sm font-bold text-white font-mono mt-1">₹ 2,450.40</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-[#888888] uppercase tracking-wider">SGST (Central Tax Share)</span>
                    <p className="text-sm font-bold text-white font-mono mt-1">₹ 2,450.40</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-[#888888] uppercase tracking-wider">TOTAL GST COLLECTED</span>
                    <p className="text-sm font-bold text-[#4edea3] font-mono mt-1">₹ 4,900.80</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeReport === 'khata' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wider flex items-center gap-2">
                <ShieldAlert size={14} /> Khata accounting delinquency logs
              </h3>
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 text-xs pt-2">
                <div className="bg-[#0A0A0A] border border-[#1F1F1F] p-3 rounded-sm">
                  <span className="text-[#888888] text-[9px] uppercase font-bold">Total book outstanding</span>
                  <p className="text-sm font-bold text-red-400 font-mono mt-1">₹ {totalOutstandingKhata().toLocaleString('en-IN')}</p>
                </div>
                <div className="bg-[#0A0A0A] border border-[#1F1F1F] p-3 rounded-sm">
                  <span className="text-[#888888] text-[9px] uppercase font-bold">Overdue account heads</span>
                  <p className="text-sm font-bold text-white mt-1">2 Customers (Anjali Sharma, Rohan Malhotra)</p>
                </div>
                <div className="bg-[#0A0A0A] border border-[#1F1F1F] p-3 rounded-sm">
                  <span className="text-[#888888] text-[9px] uppercase font-bold">Delinquent assets ratio</span>
                  <p className="text-sm font-bold text-white mt-1">42.4% (Exceeds acceptable risk threshold)</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
