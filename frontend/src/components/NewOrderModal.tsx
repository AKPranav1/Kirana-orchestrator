/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { X, Search, Plus, Minus, Check, ShoppingCart, UserPlus } from 'lucide-react';
import { Product, Customer } from '../types';
import { inventoryService } from '../services/inventory';
import { customersService } from '../services/customers';
import { ordersService } from '../services/orders';

interface NewOrderModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export default function NewOrderModal({ onClose, onSuccess }: NewOrderModalProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [search, setSearch] = useState("");
  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [cart, setCart] = useState<{ [productId: string]: number }>({});
  const [paymentMethod, setPaymentMethod] = useState<'cash' | 'khata'>('cash');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const p = await inventoryService.getInventory();
    const c = await customersService.getCustomers();
    setProducts(p);
    setCustomers(c);
  };

  const updateCart = (productId: string, delta: number) => {
    const prod = products.find(p => p.id === productId);
    if (!prod) return;

    setCart(prev => {
      const current = prev[productId] || 0;
      const next = current + delta;
      
      if (next <= 0) {
        const copy = { ...prev };
        delete copy[productId];
        return copy;
      }

      // Check stock limit
      if (delta > 0 && next > prod.stockQuantity) {
        alert(`Cannot add more. Only ${prod.stockQuantity} units left in stock.`);
        return prev;
      }

      return { ...prev, [productId]: next };
    });
  };

  const getCartTotal = () => {
    return Object.entries(cart).reduce((total, [id, qty]) => {
      const prod = products.find(p => p.id === id);
      const qtyNum = qty as number;
      return total + (prod ? prod.unitPrice * qtyNum : 0);
    }, 0);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const totalAmount = getCartTotal();
    if (totalAmount === 0) {
      alert("Please add at least one product to the cart.");
      return;
    }

    if (paymentMethod === 'khata' && !selectedCustomerId) {
      alert("Please select a customer to charge to Khata.");
      return;
    }

    setLoading(true);
    try {
      const selectedCustomer = customers.find(c => c.id === selectedCustomerId);
      const items = Object.entries(cart).map(([id, qty]) => {
        const p = products.find(prod => prod.id === id)!;
        const qtyNum = qty as number;
        return {
          productId: id,
          productName: p.name,
          quantity: qtyNum,
          price: p.unitPrice
        };
      });

      // 1. Create order
      await ordersService.createOrder({
        customerId: selectedCustomerId || undefined,
        customerName: selectedCustomer ? selectedCustomer.name : 'Walk-in Customer',
        customerPhone: selectedCustomer ? selectedCustomer.phone : '',   // add this line
        items,
        totalAmount,
        status: 'Processed',
        source: 'In-Store'
      });

      // 2. If charged to Khata, record credit transaction
      if (paymentMethod === 'khata' && selectedCustomerId) {
        await customersService.addKhataTransaction(
          selectedCustomerId,
          'credit',
          totalAmount,
          `In-store purchase of ${items.map(i => `${i.quantity}x ${i.productName}`).join(', ')}`
        );
      }

      setMessage("Order placed and processed successfully!");
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1000);
    } catch (err: any) {
      alert(err.message || "Something went wrong placing the order.");
    } finally {
      setLoading(false);
    }
  };

  const filteredProducts = products.filter(p => 
    p.name.toLowerCase().includes(search.toLowerCase()) || 
    p.sku.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-[#121212] border border-[#1F1F1F] w-full max-w-4xl max-h-[90vh] rounded-md flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-[#1F1F1F] flex justify-between items-center bg-[#161616]">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-white flex items-center gap-2">
            <ShoppingCart size={16} className="text-[#4edea3]" /> Create Sale
          </h3>
          <button onClick={onClose} className="text-[#888888] hover:text-white cursor-pointer p-1">
            <X size={18} />
          </button>
        </div>

        {message ? (
          <div className="p-10 text-center flex flex-col items-center justify-center gap-3">
            <div className="h-12 w-12 rounded-full bg-[#10B981]/20 flex items-center justify-center text-[#4edea3]">
              <Check size={28} />
            </div>
            <p className="text-white font-medium text-lg">{message}</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
            {/* Catalog list section (Left) */}
            <div className="flex-1 p-5 border-r border-[#1F1F1F] flex flex-col overflow-y-auto">
              {/* Search */}
              <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#888888]" size={14} />
                <input 
                  type="text"
                  placeholder="Search catalog by product name or SKU..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm text-xs pl-9 pr-4 py-2 text-white placeholder-[#888888] focus:border-white focus:outline-none"
                />
              </div>

              {/* Product Grid */}
              <div className="flex-1 space-y-2 overflow-y-auto pr-1">
                {filteredProducts.map(p => {
                  const currentQtyInCart = cart[p.id] || 0;
                  const isOutOfStock = p.stockQuantity === 0;

                  return (
                    <div 
                      key={p.id} 
                      className={`p-3 rounded-sm border flex justify-between items-center transition-colors ${
                        isOutOfStock 
                          ? 'border-[#1F1F1F] bg-[#0E0E0E] opacity-50' 
                          : 'border-[#1F1F1F] bg-[#0F0F0F] hover:border-[#353534]'
                      }`}
                    >
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-white truncate">{p.name}</p>
                        <p className="text-[10px] text-[#888888] font-mono mt-0.5">
                          {p.sku} • {p.category} • <span className="text-[#4edea3]">₹{p.unitPrice}</span>
                        </p>
                        <p className={`text-[10px] font-medium mt-1 ${p.stockQuantity < 5 ? 'text-red-400' : 'text-[#888888]'}`}>
                          Stock: {p.stockQuantity} units
                        </p>
                      </div>

                      {/* Add controls */}
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {currentQtyInCart > 0 ? (
                          <div className="flex items-center gap-2 border border-[#1F1F1F] bg-[#121212] rounded-sm py-0.5 px-2">
                            <button 
                              type="button"
                              onClick={() => updateCart(p.id, -1)}
                              className="text-[#888888] hover:text-white p-1"
                            >
                              <Minus size={12} />
                            </button>
                            <span className="text-xs font-mono font-bold text-white min-w-[12px] text-center">
                              {currentQtyInCart}
                            </span>
                            <button 
                              type="button"
                              onClick={() => updateCart(p.id, 1)}
                              className="text-[#888888] hover:text-white p-1"
                            >
                              <Plus size={12} />
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            disabled={isOutOfStock}
                            onClick={() => updateCart(p.id, 1)}
                            className="bg-[#1C1B1B] hover:bg-white hover:text-black border border-[#1F1F1F] rounded-sm py-1 px-3 text-xs font-medium text-white transition-all disabled:opacity-50 disabled:hover:bg-[#1C1B1B] disabled:hover:text-white cursor-pointer"
                          >
                            Add
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Customer bind and summary section (Right) */}
            <form onSubmit={handleSubmit} className="w-full md:w-80 p-5 bg-[#0A0A0A] flex flex-col justify-between overflow-y-auto border-t md:border-t-0 border-[#1F1F1F]">
              <div className="space-y-4">
                 <h4 className="text-xs font-semibold text-[#888888] uppercase tracking-wider">Checkout Options</h4>

                {/* Bind to customer */}
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-[#888888]">Customer (optional)</label>
                  <select 
                    value={selectedCustomerId}
                    onChange={(e) => setSelectedCustomerId(e.target.value)}
                    className="w-full bg-[#121212] border border-[#1F1F1F] rounded-sm text-xs p-2 text-white placeholder-[#888888] focus:border-white focus:outline-none cursor-pointer"
                  >
                        <option value="">Walk-In Customer (No Khata)</option>
                    {customers.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.phone}) - Bal: ₹{c.khataBalance}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Payment Options */}
                {selectedCustomerId && (
                  <div className="space-y-2">
                    <label className="block text-xs font-medium text-[#888888]">Payment Mode</label>
                    <div className="grid grid-cols-2 gap-2">
                        <button
                          type="button"
                          onClick={() => setPaymentMethod('cash')}
                          className={`py-1.5 px-3 rounded-sm border text-xs font-medium cursor-pointer ${
                            paymentMethod === 'cash' 
                              ? 'bg-white text-black border-white' 
                              : 'bg-[#121212] text-[#888888] border-[#1F1F1F] hover:text-white'
                          }`}
                        >
                          Paid
                        </button>
                        <button
                          type="button"
                          onClick={() => setPaymentMethod('khata')}
                          className={`py-1.5 px-3 rounded-sm border text-xs font-medium cursor-pointer ${
                            paymentMethod === 'khata' 
                              ? 'bg-[#93000a]/20 text-red-400 border-red-500/50' 
                              : 'bg-[#121212] text-[#888888] border-[#1F1F1F] hover:text-white'
                          }`}
                        >
                          Add to Credit Book
                        </button>
                    </div>
                  </div>
                )}

                {/* Cart summary */}
                <div className="border-t border-[#1F1F1F] pt-4 mt-4 space-y-2">
                  <span className="text-xs font-semibold text-[#888888] uppercase tracking-wider block">Cart Summary</span>
                  <div className="max-h-40 overflow-y-auto space-y-1.5">
                    {Object.entries(cart).length === 0 ? (
                      <p className="text-xs text-[#888888] italic">Cart is empty</p>
                    ) : (
                      Object.entries(cart).map(([id, qty]) => {
                        const prod = products.find(p => p.id === id);
                        const qtyNum = qty as number;
                        if (!prod) return null;
                        return (
                          <div key={id} className="flex justify-between items-center text-xs">
                            <span className="text-[#888888] truncate max-w-[150px]">{prod.name} x{qtyNum}</span>
                            <span className="font-mono text-white">₹{prod.unitPrice * qtyNum}</span>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>

              {/* Total and Submit */}
                 <div className="pt-4 border-t border-[#1F1F1F] mt-4 space-y-3">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-[#888888]">Grand Total:</span>
                  <span className="text-xl font-bold font-mono text-white">₹{getCartTotal()}</span>
                </div>

                 <button
                   type="submit"
                   disabled={loading || Object.keys(cart).length === 0}
                   className="w-full bg-[#10B981] hover:bg-[#4edea3] text-black font-semibold py-2 px-4 rounded-sm text-xs transition-colors cursor-pointer disabled:opacity-50"
                 >
                   {loading ? "Processing..." : "Complete Sale"}
                 </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
