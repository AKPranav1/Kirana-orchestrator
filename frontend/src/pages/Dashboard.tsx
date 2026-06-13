/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  ShoppingBag, 
  Wallet, 
  AlertTriangle, 
  Truck, 
  CreditCard, 
  CheckCircle,
  Sparkles,
  ClipboardList,
  MessageSquare,
  ArrowRight,
  RefreshCw,
  Plus,
  Send
} from 'lucide-react';
import { dashboardService } from '../services/dashboard';
import { ordersService } from '../services/orders';
import { DashboardMetrics, Order } from '../types';
import MetricCard from '../components/MetricCard';
import { mockRecentActivity } from '../data/dashboard';

interface DashboardProps {
  onNavigate: (tab: string) => void;
  onOpenNewOrder: () => void;
}

export default function Dashboard({ onNavigate, onOpenNewOrder }: DashboardProps) {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [activities, setActivities] = useState(mockRecentActivity);
  
  // WhatsApp Simulated Parsing states
  const [whatsappText, setWhatsappText] = useState("Aashirvaad Atta 2, Amul Milk 5, Tata Salt 1, please send fast to Rajesh Kumar");
  const [parseLoading, setParseLoading] = useState(false);
  const [parseSuccess, setParseSuccess] = useState<any>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const data = await dashboardService.getDashboard();
      setMetrics(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleExtractOrder = async () => {
    if (!whatsappText.trim()) return;
    setParseLoading(true);
    setParseSuccess(null);
    try {
      const res = await ordersService.extractOrderFromWhatsApp(whatsappText);
      if (res.order) {
        setParseSuccess(res.order);
        // Prepend to activities
        setActivities(prev => [
          {
            id: `act-${Date.now()}`,
            type: "whatsapp_order",
            description: `Order #${res.order!.id} extracted from WhatsApp`,
            timeLabel: "Just now",
            user: res.order!.customerName,
            status: "Processed"
          },
          ...prev
        ]);
        // Update metrics
        loadDashboard();
      } else {
        alert(res.error || "No matching items found.");
      }
    } catch (err) {
      alert("Error parsing WhatsApp message");
    } finally {
      setParseLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and top banner actions */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">OS Overview</h2>
          <p className="text-xs text-[#888888] mt-1">Real-time pulse of your autonomous commerce engine.</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={onOpenNewOrder}
            className="px-4 py-2 bg-transparent border border-[#1F1F1F] hover:bg-[#121212] font-semibold text-xs rounded-sm text-white flex items-center gap-2 cursor-pointer transition-colors"
          >
            <Plus size={14} /> Add Product
          </button>
          <button 
            onClick={onOpenNewOrder}
            className="px-4 py-2 bg-white text-black hover:bg-[#e2e2e2] font-semibold text-xs rounded-sm flex items-center gap-2 cursor-pointer transition-colors"
          >
            <Plus size={14} /> New Order
          </button>
        </div>
      </div>

      {/* KPI Bento Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <MetricCard 
          title="Today's Revenue" 
          value={`₹${metrics?.todaysRevenue?.toLocaleString('en-IN') || '12,450'}`} 
          icon={TrendingUp} 
          iconColor="text-[#10B981]"
          trend="+14.2% demand"
          trendDirection="up"
          loading={loading}
        />
        <MetricCard 
          title="Today's Orders" 
          value={metrics?.todaysOrdersCount || '42'} 
          icon={ShoppingBag} 
          trend="WhatsApp engine busy"
          loading={loading}
        />
        <MetricCard 
          title="Outstanding Khata" 
          value={`₹${metrics?.outstandingKhata?.toLocaleString('en-IN') || '8,200'}`} 
          icon={Wallet} 
          iconColor="text-red-400"
          trend="Needs recovery action"
          trendDirection="down"
          loading={loading}
        />
        <MetricCard 
          title="Low Stock Warning" 
          value={metrics?.lowStockItemsCount ?? 3} 
          icon={AlertTriangle} 
          iconColor="text-red-400"
          trend="ML replenishment ready"
          loading={loading}
        />
        <MetricCard 
          title="Pending Deliveries" 
          value={metrics?.pendingDeliveriesCount || 5} 
          icon={Truck} 
          trend="3 In Transit"
          loading={loading}
        />
        <MetricCard 
          title="Pending Supplier Pay" 
          value={`₹${metrics?.pendingSupplierPay?.toLocaleString('en-IN') || '15,000'}`} 
          icon={CreditCard} 
          trend="Awaiting approval"
          loading={loading}
        />
      </div>

      {/* Center layout split */}
      <div className="grid grid-cols-1 lg:grid-cols-1 home-view gap-6">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* WhatsApp order pilot (Left) */}
          <div className="flex-1 bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2.5 mb-3 border-b border-[#1F1F1F] pb-3">
                <span className="p-1 px-1.5 bg-[#25D366]/10 text-[#25D366] rounded-sm text-xs font-semibold flex items-center gap-1">
                  <MessageSquare size={14} /> LIVE PIPELINE
                </span>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-white">WhatsApp Order Extractor (LLM parser)</h3>
              </div>
              <p className="text-xs text-[#888888] mb-4">
                Kirana AI automatically catches natural text orders via WhatsApp, matches them to catalog products or price structures, and reserves stock instantly. Try it below:
              </p>

              {/* Text area input code */}
              <div className="space-y-3">
                <label className="block text-[11px] font-semibold text-[#888888] uppercase tracking-wider">Paste Chat Message Transcript</label>
                <textarea 
                  value={whatsappText}
                  onChange={(e) => setWhatsappText(e.target.value)}
                  placeholder="e.g., 2 packets of atta and 5 bags milk please send fast from Aarav Malhotra"
                  className="w-full bg-[#0F0F0F] border border-[#1F1F1F] rounded-sm text-xs p-3 text-white placeholder-[#888888] focus:border-white focus:outline-none min-h-[100px] resize-none"
                />
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-[#1F1F1F] flex flex-col sm:flex-row justify-between items-center gap-3">
              <span className="text-[10px] text-[#888888] flex items-center gap-1 font-mono">
                Powered by Gemini-3.5-Flash
              </span>
              <button 
                onClick={handleExtractOrder}
                disabled={parseLoading}
                className="w-full sm:w-auto px-4 py-2 bg-[#10B981] hover:bg-[#4edea3] text-black font-semibold text-xs rounded-sm flex items-center justify-center gap-1 transition-all cursor-pointer disabled:opacity-50"
              >
                {parseLoading ? "Processing Stream..." : "Extract & Process Order"}
                <ArrowRight size={14} />
              </button>
            </div>

            {/* Parse Result Feedback */}
            {parseSuccess && (
              <div className="mt-4 p-3 bg-[#162D20] border border-[#214F33] rounded-sm animate-pulse-soft">
                <p className="text-xs font-semibold text-[#4edea3] flex items-center gap-1">
                  <CheckCircle size={14} /> Extraction Success! Order #{parseSuccess.id} Processed
                </p>
                <div className="mt-2 text-[11px] text-[#888888] space-y-1 font-mono">
                  <div>Customer: <b className="text-white">{parseSuccess.customerName}</b></div>
                  <div>Items: {parseSuccess.items.map((i: any) => `${i.quantity}x ${i.productName}`).join(', ')}</div>
                  <div>Total Cost Charged: <b className="text-white">₹{parseSuccess.totalAmount}</b></div>
                </div>
              </div>
            )}
          </div>

          {/* Store Health & AI Insights (Right) */}
          <div className="w-full lg:w-96 flex flex-col gap-6">
            {/* Health Score Circular dial wrapper */}
            <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 flex flex-col items-center justify-center relative overflow-hidden h-52">
              <span className="text-[10px] font-semibold text-[#888888] uppercase tracking-wider absolute top-4 left-4 block">Store Health Indicator</span>
              <div className="relative w-28 h-28 mt-4 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="42" fill="none" stroke="#1F1F1F" strokeWidth="5"></circle>
                  <circle 
                    cx="50" 
                    cy="50" 
                    r="42" 
                    fill="none" 
                    stroke="#10B981" 
                    strokeWidth="5" 
                    strokeDasharray="263.8" 
                    strokeDashoffset="15" // ~94%
                    strokeLinecap="round"
                    className="transition-all duration-1000"
                  ></circle>
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold font-mono text-white">94%</span>
                </div>
              </div>
              <p className="text-[10px] font-bold text-[#4edea3] uppercase tracking-wide mt-3 flex items-center gap-1">
                <CheckCircle size={12} /> Operational Efficiency High
              </p>
            </div>

            {/* AI Insights list card */}
            <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 flex-1 select-none">
              <div className="flex items-center gap-2 mb-3 pb-3 border-b border-[#1F1F1F]">
                <Sparkles size={14} className="text-[#4edea3]" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-white">Active AI Insights</h3>
              </div>
              <div className="space-y-3">
                <div className="p-3 bg-[#1A1A1A] border border-[#1F1F1F] rounded-sm text-xs">
                  <div className="font-semibold text-white">Amul Milk stock falling critical</div>
                  <p className="text-[11px] text-[#888888] mt-1">Under 4 units left. Out-of-stock expected in 4 hours due to fast weekend checkout velocity.</p>
                  <button 
                    onClick={() => onNavigate('forecasts')}
                    className="mt-2 text-[10px] text-[#4edea3] hover:underline hover:text-white font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    View ML recommendation <ArrowRight size={10} />
                  </button>
                </div>

                <div className="p-3 bg-[#1A1A1A] border border-[#1F1F1F] rounded-sm text-xs font-sans">
                  <div className="font-semibold text-white">Anjali Sharma Khata overdue alert</div>
                  <p className="text-[11px] text-[#888888] mt-1">Outstanding credit balance of ₹4,250 remains uncollected for more than 15 days.</p>
                  <button 
                    onClick={() => onNavigate('customers')}
                    className="mt-2 text-[10px] text-red-400 hover:underline hover:text-white font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    Ping WhatsApp reminder <ArrowRight size={10} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity Section */}
      <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg overflow-hidden">
        <div className="p-4 border-b border-[#1F1F1F] flex justify-between items-center bg-[#161616]">
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider">Recent Activity Feed</h3>
          <button 
            onClick={() => onNavigate('orders')}
            className="text-xs font-semibold text-[#888888] hover:text-white cursor-pointer"
          >
            Go to Live Orders
          </button>
        </div>

        <div className="divide-y divide-[#1F1F1F]">
          {activities.map((act) => (
            <div 
              key={act.id} 
              className="p-4 flex items-center justify-between hover:bg-[#151515] transition-colors"
            >
              <div className="flex items-center gap-4 min-w-0">
                <div className="w-8 h-8 rounded-sm bg-[#1C1B1B] border border-[#1F1F1F] flex items-center justify-center text-[#888888] flex-shrink-0">
                  <ClipboardList size={14} />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-white truncate">{act.description}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-[#888888]">{act.timeLabel}</span>
                    {act.user && (
                      <>
                        <div className="w-1 h-1 bg-[#1F1F1F] rounded-full"></div>
                        <span className="text-[10px] text-[#888888]">{act.user}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {act.status && (
                <span className="text-[10px] font-bold bg-[#10B981]/10 text-[#4edea3] px-2 py-0.5 rounded-sm uppercase tracking-wide">
                  {act.status}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
