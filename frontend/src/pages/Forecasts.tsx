/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { TrendingUp, Sparkles, AlertTriangle, ShieldCheck, ShoppingCart, ArrowRight, CheckCircle, RefreshCw } from 'lucide-react';
import { Forecast } from '../types';
import { forecastService } from '../services/forecast';
import { suppliersService } from '../services/suppliers';

export default function Forecasts() {
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const [loading, setLoading] = useState(true);
  const [procuredIdList, setProcuredIdList] = useState<string[]>([]);
  const [procureSuccessId, setProcureSuccessId] = useState<string | null>(null);

  useEffect(() => {
    loadForecasts();
  }, []);

  const loadForecasts = async () => {
    setLoading(true);
    const list = await forecastService.getForecasts();
    setForecasts(list);
    setLoading(false);
  };

  const handleProcureDraft = async (forecast: Forecast) => {
    setProcureSuccessId(null);
    try {
      // Create draft Purchase Order
      // Prefer canonicalProductId if provided by the ML payload. Otherwise use forecast.productId.
      const prodId = (forecast as any).canonicalProductId || forecast.productId;
      const usedProductId = prodId || forecast.productId;

      await suppliersService.createPurchaseOrder({
        supplierId: "sup-1", // Hind Unilever default
        supplierName: "Hindustan Unilever",
        items: [
          {
            productId: usedProductId,
            productName: forecast.product_name,
            quantity: forecast.recommended_reorder_quantity,
            costPrice: 210.00
          }
        ],
        totalAmount: forecast.recommended_reorder_quantity * 160 // approximate B2B rate
      });

      setProcuredIdList(prev => [...prev, forecast.productId]);
      setProcureSuccessId(forecast.productId);
      
      setTimeout(() => {
        setProcureSuccessId(null);
      }, 3000);
    } catch (err) {
      alert("Error generating replenishment PO.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
  <h2 className="text-xl font-bold text-white tracking-tight">Stock Suggestions</h2>
          <p className="text-xs text-[#888888] mt-1">Automatic suggestions: what to reorder and how fast items sell.</p>
        </div>

        <div className="flex items-center gap-2">
            <span className="text-[10px] bg-[#10B981]/15 text-[#4edea3] font-bold border border-[#10B981]/30 py-1 px-2.5 rounded-sm flex items-center gap-1 leading-none uppercase">
              <Sparkles size={11} /> Model active
            </span>
        </div>
      </div>

      {/* Main Grid Forecast items */}
      <div className="space-y-4">
          {loading ? (
           <p className="text-xs text-[#888888] p-10 text-center font-mono animate-pulse">Calculating stock suggestions...</p>
         ) : forecasts.length === 0 ? (
           <p className="text-xs text-[#888888] p-10 text-center font-mono">No stock suggestions.</p>
         ) : (
          forecasts.map((f, idx) => {
            const isStockoutImminent = f.predicted_stockout_days <= 1;
            const hasProcured = procuredIdList.includes(f.productId);
            const isJustProcured = procureSuccessId === f.productId;

            return (
              <div 
                key={f.productId}
                className={`bg-[#121212] border rounded-lg p-5 flex flex-col justify-between hover:border-[#353534] transition-all relative overflow-hidden ${
                  isStockoutImminent ? 'border-red-500/20' : 'border-[#1F1F1F]'
                }`}
              >
                {/* Imminent stockout indicator bar */}
                {isStockoutImminent && (
                  <div className="absolute top-0 bottom-0 left-0 w-1 bg-red-400"></div>
                )}

                <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                  {/* Left Column: Product status details */}
                  <div className="space-y-3 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-bold text-white leading-none truncate">{f.product_name}</h3>
                      <span className="text-[10px] font-mono text-[#888888] bg-[#0A0A0A] px-2 py-0.5 rounded border border-[#1F1F1F]">
                        ID: {f.productId}
                      </span>
                    </div>

                    <p className="text-xs text-[#888888] leading-relaxed max-w-2xl">
                      {f.recommendation_text}
                    </p>

                    {/* Numeric stats display grids */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-1">
                      <div className="bg-[#0A0A0A] border border-[#1F1F1F] p-2 rounded-sm">
                        <span className="text-[9px] text-[#888888] font-bold uppercase tracking-wider block">Current Shelved</span>
                        <span className={`font-mono font-semibold block mt-1 ${isStockoutImminent ? 'text-red-400' : 'text-white'}`}>
                          {f.current_stock} Units
                        </span>
                      </div>

                      <div className="bg-[#0A0A0A] border border-[#1F1F1F] p-2 rounded-sm">
                        <span className="text-[9px] text-[#888888] font-bold uppercase tracking-wider block">Predicted Sales velocity</span>
                        <span className="font-mono text-white font-semibold block mt-1">
                          {f.predicted_daily_demand}/Day
                        </span>
                      </div>

                      <div className="bg-[#0A0A0A] border border-[#1F1F1F] p-2 rounded-sm">
                        <span className="text-[9px] text-[#888888] font-bold uppercase tracking-wider block">Predicted Stockout Period</span>
                        <span className={`font-mono font-semibold block mt-1 ${isStockoutImminent ? 'text-red-400 font-bold' : 'text-white'}`}>
                          {f.predicted_stockout_days <= 0 ? "OUT OF STOCK" : `${f.predicted_stockout_days} Days`}
                        </span>
                      </div>

                      <div className="bg-[#0A0A0A] border border-[#1F1F1F] p-2 rounded-sm">
                        <span className="text-[9px] text-[#888888] font-bold uppercase tracking-wider block">ML Confidence Metric</span>
                        <span className="font-mono text-[#10B981] font-semibold block mt-1">
                          {(f.confidence * 100).toFixed(0)}% Match
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Restocking automation trigger section */}
                  <div className="lg:w-60 bg-[#0F0F0F] border border-[#1F1F1F] rounded-lg p-4 flex flex-col justify-between h-full space-y-4 flex-shrink-0">
                    <div className="space-y-1">
                      <span className="text-[9px] text-[#888888] font-bold uppercase tracking-wider block">Suggested Cargo Order</span>
                      <div className="text-xl font-bold font-mono text-white mt-1">
                        {f.recommended_reorder_quantity} Packets
                      </div>
                    </div>

                    {isJustProcured ? (
                      <div className="p-2 bg-[#162D20] text-center border border-[#214F33] rounded-sm text-[#4edea3] text-[10px] font-bold flex items-center justify-center gap-1">
                        <CheckCircle size={12} /> Restock draft PO Submitted!
                      </div>
                    ) : hasProcured ? (
                      <button 
                        type="button" 
                        disabled 
                        className="w-full py-2 bg-[#1C1B1B] text-[#555555] font-semibold text-xs rounded-sm cursor-not-allowed border border-[#1F1F1F]"
                      >
                        Procured Draft Created
                      </button>
                    ) : (
                      <button
                        onClick={() => handleProcureDraft(f)}
                        className="w-full py-2 bg-white text-black hover:bg-[#e2e2e2] font-semibold text-xs rounded-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <ShoppingCart size={13} /> Restock Cargo
                        <ArrowRight size={13} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
