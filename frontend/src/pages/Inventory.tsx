/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Package, Search, Filter, Plus, Save, Edit, RefreshCw } from 'lucide-react';
import { Product, Supplier } from '../types';
import { inventoryService } from '../services/inventory';
import { suppliersService } from '../services/suppliers';

export default function Inventory() {
  const [products, setProducts] = useState<Product[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [loading, setLoading] = useState(true);

  // Stock edit states
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editQty, setEditQty] = useState("");

  // Add Product form states
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [sku, setSku] = useState("");
  const [category, setCategory] = useState("Grains");
  const [unitPrice, setUnitPrice] = useState("");
  const [costPrice, setCostPrice] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [stockQuantity, setStockQuantity] = useState("");

  useEffect(() => {
    loadInventory();
  }, []);

  const loadInventory = async () => {
    setLoading(true);
    const p = await inventoryService.getInventory();
    const s = await suppliersService.getSuppliers();
    setProducts(p);
    setSuppliers(s);
    setLoading(false);
  };

  const handleUpdateStock = async (id: string) => {
    if (!editQty || isNaN(parseInt(editQty))) return;
    try {
      await inventoryService.updateProductStock(id, parseInt(editQty));
      setEditingId(null);
      setEditQty("");
      loadInventory();
    } catch (err) {
      alert("Error updating stock quantity.");
    }
  };

  const handleAddProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !sku || !unitPrice || !costPrice || !supplierId || !stockQuantity) return;

    try {
      const selectedSupplier = suppliers.find(s => s.id === supplierId);
      await inventoryService.addProduct({
        name,
        sku,
        category,
        unitPrice: parseFloat(unitPrice),
        costPrice: parseFloat(costPrice),
        supplierId,
        supplierName: selectedSupplier ? selectedSupplier.name : "Hindustan Unilever",
        stockQuantity: parseInt(stockQuantity),
        status: parseInt(stockQuantity) === 0 ? 'Out of Stock' : parseInt(stockQuantity) < 5 ? 'Low Stock' : 'In Stock'
      });

      // Clear states & Reload
      setName("");
      setSku("");
      setCategory("Grains");
      setUnitPrice("");
      setCostPrice("");
      setSupplierId("");
      setStockQuantity("");
      setShowForm(false);
      loadInventory();
    } catch (err) {
      alert("Error adding product");
    }
  };

  const getStatusStyle = (status: Product['status']) => {
    switch (status) {
      case 'In Stock':
        return 'bg-[#10B981]/10 text-[#4edea3] border-[#10B981]/20';
      case 'Low Stock':
        return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      default:
        return 'bg-red-400/10 text-red-400 border-red-500/20';
    }
  };

  const categories = ["All", ...Array.from(new Set(products.map(p => p.category)))];

  const filteredProducts = products.filter(p => {
    const matchesCategory = categoryFilter === 'All' || p.category === categoryFilter;
    const matchesSearch = p.name.toLowerCase().includes(search.toLowerCase()) || 
                          p.sku.toLowerCase().includes(search.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Products & Stock</h2>
          <p className="text-xs text-[#888888] mt-1">Set prices and manage stock.</p>
        </div>
        <button 
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-white text-black hover:bg-[#e2e2e2] font-semibold text-xs rounded-sm flex items-center gap-2 cursor-pointer transition-colors"
        >
          <Plus size={14} /> Add New Product
        </button>
      </div>

      {/* Add Product standard form block */}
        {showForm && (
        <form onSubmit={handleAddProduct} className="bg-[#121212] border border-[#10B981]/20 p-5 rounded-md space-y-4 max-w-2xl">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-white">Add Product</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="space-y-1">
              <label className="text-[#888888]">Product Name</label>
              <input 
                type="text" 
                value={name} 
                onChange={(e) => setName(e.target.value)}
                placeholder="Aashirvaad Atta 10kg"
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none"
                required
              />
            </div>
            <div className="space-y-1">
               <label className="text-[#888888]">SKU / Barcode</label>
              <input 
                type="text" 
                value={sku} 
                onChange={(e) => setSku(e.target.value)}
                placeholder="SKU-ASH-505"
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
                <option value="Grains">Grains</option>
                <option value="Dairy">Dairy</option>
                <option value="Beverages">Beverages</option>
                <option value="Snacks">Snacks</option>
                <option value="Oils">Oils</option>
                <option value="Spices">Spices</option>
              </select>
            </div>
            <div className="space-y-1">
               <label className="text-[#888888]">Selling price (₹)</label>
              <input 
                type="number" 
                value={unitPrice} 
                onChange={(e) => setUnitPrice(e.target.value)}
                placeholder="245"
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none"
                required
              />
            </div>
            <div className="space-y-1">
               <label className="text-[#888888]">Wholesaler cost (₹)</label>
              <input 
                type="number" 
                value={costPrice} 
                onChange={(e) => setCostPrice(e.target.value)}
                placeholder="210"
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none"
                required
              />
            </div>
            <div className="space-y-1">
               <label className="text-[#888888]">Wholesaler</label>
              <select 
                value={supplierId} 
                onChange={(e) => setSupplierId(e.target.value)}
                className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none"
                required
              >
                <option value="">Select Supplier</option>
                {suppliers.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1 md:col-span-3">
               <label className="text-[#888888]">Initial stock quantity</label>
              <input 
                type="number" 
                value={stockQuantity} 
                onChange={(e) => setStockQuantity(e.target.value)}
                placeholder="50"
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
              Add product
            </button>
          </div>
        </form>
      )}

      {/* Filters bar */}
      <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-3 flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#888888]" size={14} />
            <input 
              type="text"
              placeholder="Search product name or SKU..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm text-xs pl-9 pr-4 py-2 text-white"
            />
        </div>

        <div className="flex gap-1 overflow-x-auto">
          {categories.map(c => (
            <button
              key={c}
              onClick={() => setCategoryFilter(c)}
              className={`px-3 py-1.5 rounded-sm text-xs font-semibold cursor-pointer whitespace-nowrap transition-colors ${
                categoryFilter === c 
                  ? 'bg-white text-black' 
                  : 'bg-[#0F0F0F] text-[#888888] hover:text-white hover:bg-[#1C1B1B]'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Catalog Table */}
      <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          {loading ? (
            <p className="text-xs p-10 text-center text-[#888888]">Loading catalog inventory...</p>
          ) : filteredProducts.length === 0 ? (
            <p className="text-xs p-10 text-center text-[#888888]">No matching products in database.</p>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#1F1F1F] text-[#888888] text-[10px] uppercase font-bold tracking-wider bg-[#0F0F0F]">
                  <th className="p-4 font-semibold">SKU / Item Details</th>
                  <th className="p-4 font-semibold">Category</th>
                  <th className="p-4 font-semibold">B2B Wholesaler Cost</th>
                  <th className="p-4 font-semibold">Checkout Price</th>
                  <th className="p-4 font-semibold">Profit Margin</th>
                  <th className="p-4 font-semibold text-center">Stock Count</th>
                  <th className="p-4 font-semibold text-right">FMCG Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F1F1F] text-xs">
                {filteredProducts.map(p => (
                  <tr key={p.id} className="table-row-hover transition-colors">
                    <td className="p-4">
                      <div className="font-semibold text-white">{p.name}</div>
                      <div className="text-[10px] text-[#888888] font-mono mt-0.5">{p.sku}</div>
                    </td>
                    <td className="p-4 text-[#888888]">{p.category}</td>
                    <td className="p-4 text-white font-mono">₹{p.costPrice}</td>
                    <td className="p-4 text-white font-mono">₹{p.unitPrice}</td>
                    <td className="p-4">
                      <span className="text-[#4edea3] font-mono bg-[#10B981]/10 px-1.5 py-0.5 rounded-sm">
                        {p.margin}%
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      {editingId === p.id ? (
                        <div className="flex items-center justify-center gap-1">
                          <input 
                            type="number" 
                            value={editQty}
                            onChange={(e) => setEditQty(e.target.value)}
                            className="bg-[#0F0F0F] border border-[#1F1F1F] text-center w-14 rounded-sm p-1 text-white text-xs font-mono"
                          />
                          <button 
                            onClick={() => handleUpdateStock(p.id)}
                            className="p-1.5 bg-[#10B981] rounded-sm text-black cursor-pointer"
                          >
                            <Save size={12} />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-center gap-2 group/btn">
                          <span className="font-mono font-semibold text-white leading-none">{p.stockQuantity}</span>
                          <button 
                            onClick={() => {
                              setEditingId(p.id);
                              setEditQty(p.stockQuantity.toString());
                            }}
                            className="text-[#888888] hover:text-white p-0.5 opacity-0 group-hover/btn:opacity-100 transition-opacity cursor-pointer"
                          >
                            <Edit size={11} />
                          </button>
                        </div>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <span className={`px-2 py-0.5 border rounded-sm text-[10px] font-bold uppercase tracking-wider ${getStatusStyle(p.status)}`}>
                        {p.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
