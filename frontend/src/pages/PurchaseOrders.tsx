/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { ShoppingBag, Eye, CheckCircle, Truck, PackageCheck, AlertTriangle, Play, RefreshCw } from 'lucide-react';
import { PurchaseOrder } from '../types';
import { suppliersService } from '../services/suppliers';

export default function PurchaseOrders() {
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [activePO, setActivePO] = useState<PurchaseOrder | null>(null);

  useEffect(() => {
    loadPOs();
  }, []);

  const loadPOs = async () => {
    setLoading(true);
    const list = await suppliersService.getPurchaseOrders();
    setPurchaseOrders(list);
    setLoading(false);
  };

  const handleApprovePO = async (poId: string) => {
    const originalText = activePO;
    try {
      const updated = await suppliersService.approvePurchaseOrder(poId);
      if (activePO && activePO.id === poId) {
        setActivePO(updated);
      }
      loadPOs();
    } catch (err) {
      alert("Error approving purchase order.");
    }
  };

  const handleReceivePO = async (poId: string) => {
    try {
      const updated = await suppliersService.receivePurchaseOrder(poId);
      if (activePO && activePO.id === poId) {
        setActivePO(updated);
      }
      loadPOs();
    } catch (err) {
      alert("Error receiving stock from purchase order.");
    }
  };

  const getStatusColor = (status: PurchaseOrder['status']) => {
    switch (status) {
      case 'Delivered':
        return 'bg-[#10B981]/15 text-[#4edea3] border-[#10B981]/20';
      case 'In Transit':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'Awaiting Approval':
        return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      default:
        return 'bg-[#1F1F1F] text-[#888888] border-[#353534]';
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Purchase Procurement Orders</h2>
          <p className="text-xs text-[#888888] mt-1">Submit B2B restocking requests to suppliers and clear incoming warehouse cargo.</p>
        </div>
        <button 
          onClick={loadPOs}
          className="px-3.5 py-1.5 bg-[#121212] hover:bg-white hover:text-black border border-[#1F1F1F] text-xs font-semibold text-white rounded-sm flex items-center gap-1.5 cursor-pointer transition-all"
        >
          <RefreshCw size={12} /> Reload Procurement Stream
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Main Orders Table (Cols 1-8) */}
        <div className="lg:col-span-8 bg-[#121212] border border-[#1F1F1F] rounded-lg overflow-hidden flex flex-col">
          <div className="p-4 border-b border-[#1F1F1F] flex justify-between items-center bg-[#161616]">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-white">B2B Purchase Orders</h3>
          </div>

          <div className="overflow-x-auto">
            {loading ? (
              <p className="text-xs text-[#888888] p-10 text-center">Loading purchase logs...</p>
            ) : purchaseOrders.length === 0 ? (
              <p className="text-xs text-[#888888] p-10 text-center">No purchase orders placed.</p>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#1F1F1F] text-[#888888] text-[10px] uppercase font-bold tracking-wider bg-[#0F0F0F]">
                    <th className="p-4 font-semibold">PO Reference</th>
                    <th className="p-4 font-semibold">B2B Wholesaler</th>
                    <th className="p-4 font-semibold">Consolidated Value</th>
                    <th className="p-4 font-semibold">Fulfillment status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1F1F1F] text-xs">
                  {purchaseOrders.map(po => (
                    <tr 
                      key={po.id} 
                      onClick={() => setActivePO(po)}
                      className="table-row-hover transition-colors cursor-pointer"
                    >
                      <td className="p-4 font-semibold text-white">{po.id}</td>
                      <td className="p-4">
                        <div className="text-white font-semibold">{po.supplierName}</div>
                        <div className="text-[10px] text-[#888888] mt-0.5">Date: {new Date(po.createdAt).toLocaleDateString()}</div>
                      </td>
                      <td className="p-4 text-white font-mono">₹{po.totalAmount.toLocaleString('en-IN')}</td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 border rounded-sm text-[10px] font-bold uppercase tracking-wider ${getStatusColor(po.status)}`}>
                          {po.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Purchase Order Details Inspection Panel (Cols 9-12) */}
        <div className="lg:col-span-4 bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 flex flex-col justify-between">
          {activePO ? (
            <div className="space-y-4">
              <div className="flex justify-between items-start pb-3 border-b border-[#1F1F1F]">
                <div>
                  <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Inspect B2B PO</h3>
                  <p className="text-[10px] text-[#888888] font-mono mt-0.5">{activePO.id}</p>
                </div>
                <span className={`px-2 py-0.5 rounded-sm border text-[10px] font-bold uppercase tracking-wider ${getStatusColor(activePO.status)}`}>
                  {activePO.status}
                </span>
              </div>

              {/* Specs */}
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#888888]">Supplier Wholesaler:</span>
                  <span className="text-white font-semibold">{activePO.supplierName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#888888]">Order Created:</span>
                  <span className="text-white font-mono text-[10px]">{new Date(activePO.createdAt).toLocaleString()}</span>
                </div>
                {activePO.estimatedDelivery && (
                  <div className="flex justify-between">
                    <span className="text-[#888888]">Awaited Delivery:</span>
                    <span className="text-white font-semibold text-amber-500">{activePO.estimatedDelivery}</span>
                  </div>
                )}
              </div>

              {/* Progress visualizer for delivery */}
              {activePO.status === 'In Transit' && activePO.deliveryProgress !== undefined && (
                <div className="space-y-1.5 pb-2">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#888888]">Delivery Progress</span>
                    <span className="text-white font-bold font-mono">{activePO.deliveryProgress}%</span>
                  </div>
                  <div className="w-full bg-[#1F1F1F] h-1.5 rounded-sm overflow-hidden">
                    <div 
                      style={{ width: `${activePO.deliveryProgress}%` }}
                      className="bg-blue-500 h-full transition-all duration-500"
                    ></div>
                  </div>
                </div>
              )}

              {/* Items Detail */}
              <div className="border-t border-b border-[#1F1F1F] py-3 my-2 space-y-1.5">
                <span className="text-[10px] font-semibold text-[#888888] uppercase tracking-wider block">Line Cargo Breakdown</span>
                {activePO.items.map((it, i) => (
                  <div key={i} className="flex justify-between items-center text-xs">
                    <span className="text-[#888888]">{it.productName} <b className="text-white">x{it.quantity}</b></span>
                    <span className="font-mono text-white">₹{it.costPrice * it.quantity}</span>
                  </div>
                ))}
              </div>

              <div className="flex justify-between items-baseline pt-2">
                <span className="text-xs text-[#888888]">Total Cost Payable:</span>
                <span className="text-lg font-bold font-mono text-white">₹{activePO.totalAmount.toLocaleString('en-IN')}</span>
              </div>

              {/* Contextual RESTOCK action handlers */}
              <div className="pt-4 border-t border-[#1F1F1F]">
                {activePO.status === 'Awaiting Approval' && (
                  <button 
                    onClick={() => handleApprovePO(activePO.id)}
                    className="w-full py-2 bg-[#10B981] hover:bg-[#4edea3] text-black font-semibold text-xs rounded-sm transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <CheckCircle size={14} /> Approve & Dispatch PO
                  </button>
                )}

                {activePO.status === 'In Transit' && (
                  <button 
                    onClick={() => handleReceivePO(activePO.id)}
                    className="w-full py-2 bg-blue-500 hover:bg-blue-400 text-white font-semibold text-xs rounded-sm transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <PackageCheck size={14} /> Receive & Intake Stock Cargo
                  </button>
                )}

                {activePO.status === 'Delivered' && (
                  <div className="p-3 bg-[#162D20]/80 border border-[#214F33] text-xs text-[#4edea3] rounded-sm text-center font-bold flex items-center justify-center gap-1.5 select-none">
                    <CheckCircle size={14} /> RESTOCKING INTEGRATION COMPLETE
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-10 flex flex-col items-center justify-center text-[#888888] flex-1">
              <Eye size={28} className="mb-2" />
              <p className="text-xs">Select any purchase document from B2B ledger to process restocking channels.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
