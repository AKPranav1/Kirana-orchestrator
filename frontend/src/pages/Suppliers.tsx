/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Truck, Plus, Search, Phone, ShieldCheck, CreditCard, ChevronRight } from 'lucide-react';
import { Supplier } from '../types';
import { suppliersService } from '../services/suppliers';

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  // Form states to create supply links
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("FMCG Goods");
  const [contactName, setContactName] = useState("");
  const [phone, setPhone] = useState("");
  const [avgDeliveryDays, setAvgDeliveryDays] = useState("");

  useEffect(() => {
    loadSuppliers();
  }, []);

  const loadSuppliers = async () => {
    setLoading(true);
    const list = await suppliersService.getSuppliers();
    setSuppliers(list);
    setLoading(false);
  };

  const handleAddSupplier = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !contactName || !phone || !avgDeliveryDays) return;

    try {
      await suppliersService.addSupplier({
        name,
        category,
        contactName,
        phone,
        avgDeliveryDays: parseFloat(avgDeliveryDays)
      });
      setName("");
      setCategory("FMCG Goods");
      setContactName("");
      setPhone("");
      setAvgDeliveryDays("");
      setShowForm(false);
      loadSuppliers();
    } catch (err) {
      alert("Error registering supplier.");
    }
  };

  const filteredSuppliers = suppliers.filter(s => 
    s.name.toLowerCase().includes(search.toLowerCase()) || 
    s.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Wholesalers</h2>
          <p className="text-xs text-[#888888] mt-1">Manage wholesalers, delivery times and amounts due.</p>
        </div>
        <button 
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-white text-black hover:bg-[#e2e2e2] font-semibold text-xs rounded-sm flex items-center gap-2 cursor-pointer transition-colors"
        >
          <Plus size={14} /> Add Wholesaler
        </button>
      </div>

      {/* Add Supplier Form */}
        {showForm && (
        <form onSubmit={handleAddSupplier} className="bg-[#121212] border border-[#10B981]/25 p-5 rounded-md space-y-4 max-w-2xl">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-white">Add Wholesaler</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1">
               <label className="text-[#888888]">Wholesaler name</label>
              <input 
                type="text" 
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="ITC Limited Distributor"
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none"
                required
              />
            </div>
            <div className="space-y-1">
               <label className="text-[#888888]">Category</label>
              <select 
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none"
              >
                <option value="FMCG Goods">FMCG Goods</option>
                <option value="Dairy Products">Dairy Products</option>
                <option value="Beverages & Staples">Beverages & Staples</option>
                <option value="Spices & Seasoning">Spices & Seasoning</option>
              </select>
            </div>
            <div className="space-y-1">
               <label className="text-[#888888]">Contact person</label>
              <input 
                type="text" 
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                placeholder="Rohan Shinde"
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none"
                required
              />
            </div>
            <div className="space-y-1">
               <label className="text-[#888888]">Phone</label>
              <input 
                type="text" 
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 99887 70000"
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none"
                required
              />
            </div>
            <div className="col-span-2 space-y-1">
               <label className="text-[#888888]">Delivery days (avg)</label>
              <input 
                type="number" 
                step="0.1"
                value={avgDeliveryDays}
                onChange={(e) => setAvgDeliveryDays(e.target.value)}
                placeholder="1.5"
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none"
                required
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 text-xs">
            <button 
              type="button" 
              onClick={() => setShowForm(false)}
              className="px-3 py-1.5 bg-transparent border border-[#1F1F1F] text-[#888888]"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="px-3 py-1.5 bg-[#10B981] text-black font-semibold rounded-sm"
            >
              Add wholesaler
            </button>
          </div>
        </form>
      )}

      {/* Search Filter */}
      <div className="relative w-full max-w-xl bg-[#121212] border border-[#1F1F1F] px-3 py-2 rounded-lg">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#888888]" size={14} />
            <input 
              type="text"
              placeholder="Search wholesalers..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-transparent border-none text-xs pl-8 pr-4 text-white placeholder-[#888888] focus:outline-none"
            />
        </div>
      </div>

      {/* Grid of B2B Wholesale Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {loading ? (
          <p className="text-xs text-[#888888] p-4 text-center">Loading linked wholesalers register...</p>
        ) : filteredSuppliers.length === 0 ? (
          <p className="text-xs text-[#888888] p-4 text-center">No linked merchants match criteria.</p>
        ) : (
          filteredSuppliers.map(s => (
            <div 
              key={s.id} 
              className="bg-[#121212] border border-[#1F1F1F] hover:border-[#353534] rounded-lg p-5 flex flex-col justify-between h-52 transition-all relative overflow-hidden"
            >
              <div>
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="text-xs font-bold text-white flex items-center gap-2">
                      <Truck size={14} className="text-[#4edea3]" /> {s.name}
                    </h3>
                    <p className="text-[10px] text-[#888888] mt-1">{s.category}</p>
                  </div>
                  <span className="bg-[#1F1F1F] border border-[#353534] text-[9px] text-[#888888] font-bold uppercase tracking-wider py-0.5 px-1.5 rounded-sm">
                    {s.id}
                  </span>
                </div>

                {/* Substats */}
                <div className="grid grid-cols-2 gap-4 mt-4 text-xs">
                  <div className="space-y-1">
                    <span className="text-[9px] text-[#888888] font-bold uppercase tracking-wider">Primary Sales contact</span>
                    <p className="text-white font-semibold flex items-center gap-1">
                      <Phone size={10} className="text-[#888888]" /> {s.contactName} ({s.phone})
                    </p>
                  </div>

                  <div className="space-y-1 text-right">
                    <span className="text-[9px] text-[#888888] font-bold uppercase tracking-wider">Avg Delivery Speed</span>
                    <p className="text-[#4edea3] font-bold font-mono">
                      {s.avgDeliveryDays} Days
                    </p>
                  </div>
                </div>
              </div>

              {/* Outstanding metrics payable */}
              <div className="mt-4 pt-3 border-t border-[#1F1F1F] flex justify-between items-center text-xs">
                <div className="flex items-center gap-2">
                  <CreditCard size={14} className="text-[#888888]" />
                  <span className="text-[#888888]">Pending Payable Invoice:</span>
                  <span className="font-semibold text-white font-mono">₹{s.outstandingBalance.toLocaleString('en-IN')}</span>
                </div>

                <div className="flex items-center gap-1 text-[10px] text-[#888888] group cursor-pointer hover:text-white">
                  <span>Audit transactions</span>
                  <ChevronRight size={12} />
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
