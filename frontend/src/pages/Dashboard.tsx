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
import { customersService } from '../services/customers'; 
import { inventoryService } from '../services/inventory';
import { DashboardMetrics, Order } from '../types';
import MetricCard from '../components/MetricCard';
// Recent activity will be populated from live events; no local mocks

interface DashboardProps {
  onNavigate: (tab: string) => void;
  onOpenNewOrder: () => void;
}

interface Insight {
  id: string;
  title: string;
  body: string;
  ctaLabel: string;
  ctaColor: string;
  target: string;
}

const formatRelativeTime = (dateStr: string): string => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '';
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
};

export default function Dashboard({ onNavigate, onOpenNewOrder }: DashboardProps) {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [creditOutstanding, setCreditOutstanding] = useState<number>(0);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [activities, setActivities] = useState<any[]>([]);
  const [parseLoading, setParseLoading] = useState(false);
  const [parseSuccess, setParseSuccess] = useState<any>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [data, customers, products, orders] = await Promise.all([
        dashboardService.getDashboard(),
        customersService.getCustomers(),
        inventoryService.getInventory(),
        ordersService.getOrders(),
      ]);

      setMetrics(data);

      // Credit Outstanding — same logic as the Customer Directory, so the
      // two pages always agree.
      const totalOutstanding = customers.reduce(
        (sum, c) => (c.khataBalance < 0 ? sum + Math.abs(c.khataBalance) : sum),
        0
      );
      setCreditOutstanding(totalOutstanding);

      // --- Active AI Insights, built from real data ---
      const newInsights: Insight[] = [];

      const lowStockProducts = [...products]
        .filter((p: any) => (p.stockQuantity ?? p.stock_quantity ?? 0) < 5)
        .sort((a: any, b: any) => (a.stockQuantity ?? a.stock_quantity ?? 0) - (b.stockQuantity ?? b.stock_quantity ?? 0));

      if (lowStockProducts.length > 0) {
        const top: any = lowStockProducts[0];
        const stock = top.stockQuantity ?? top.stock_quantity ?? 0;
        const pname = top.name ?? top.product_name ?? 'A product';
        const others = lowStockProducts.length - 1;
        newInsights.push({
          id: 'low-stock',
          title: `${pname} stock running low`,
          body: `Only ${stock} unit${stock === 1 ? '' : 's'} left.${others > 0 ? ` ${others} other item${others === 1 ? '' : 's'} also below the reorder threshold.` : ''}`,
          ctaLabel: 'View stock suggestions',
          ctaColor: 'text-[#4edea3]',
          target: 'forecasts',
        });
      } else {
        newInsights.push({
          id: 'low-stock',
          title: 'Stock levels look healthy',
          body: 'No products are currently below the low-stock threshold.',
          ctaLabel: 'View products',
          ctaColor: 'text-[#4edea3]',
          target: 'inventory',
        });
      }

      const overdueCustomers = customers
        .filter((c) => c.khataBalance < 0)
        .sort((a, b) => a.khataBalance - b.khataBalance);

      if (overdueCustomers.length > 0) {
        const top = overdueCustomers[0];
        const amount = Math.abs(top.khataBalance);
        const others = overdueCustomers.length - 1;
        newInsights.push({
          id: 'khata-overdue',
          title: `${top.name} Khata balance outstanding`,
          body: `Outstanding credit balance of ₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })} is pending recovery.${others > 0 ? ` ${others} other customer${others === 1 ? '' : 's'} also have open balances.` : ''}`,
          ctaLabel: 'Ping WhatsApp reminder',
          ctaColor: 'text-red-400',
          target: 'customers',
        });
      } else {
        newInsights.push({
          id: 'khata-overdue',
          title: 'No overdue credit balances',
          body: 'All customer Khata balances are currently settled.',
          ctaLabel: 'View credit book',
          ctaColor: 'text-[#4edea3]',
          target: 'khata',
        });
      }

      setInsights(newInsights);

      // --- Recent Activity Feed, from real recent orders ---
      const recentActivities = orders.slice(0, 6).map((o: any) => {
        const orderId = o.id ?? o.order_id ?? '';
        const name = o.customerName ?? o.customer_name ?? o.customer ?? 'Unknown Customer';
        const amount = o.totalAmount ?? o.total_amount ?? o.bill_amount ?? 0;
        const status = o.status ?? 'Processed';
        const createdAt = o.createdAt ?? o.created_at ?? '';
        return {
          id: `order-${orderId}`,
          type: 'order',
          description: `Order #${orderId} — ₹${Number(amount).toLocaleString('en-IN')}`,
          timeLabel: formatRelativeTime(createdAt),
          user: name,
          status,
        };
      });
      setActivities(recentActivities);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and top banner actions */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Shop Summary</h2>
          <p className="text-xs text-[#888888] mt-1">Live view of sales, stock and alerts.</p>
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
            title="Today's Sales" 
          value={`₹${(metrics?.todaysRevenue ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`} 
          icon={TrendingUp} 
          iconColor="text-[#10B981]"
          trend={(metrics?.todaysOrdersCount ?? 0) > 0 ? `${metrics?.todaysOrdersCount} orders so far` : "No sales yet today"}
          trendDirection="up"
          loading={loading}
        />
        <MetricCard 
            title="Orders Today" 
          value={metrics?.todaysOrdersCount ?? 0} 
          icon={ShoppingBag} 
          trend={(metrics?.todaysOrdersCount ?? 0) > 0 ? "WhatsApp engine busy" : "No orders yet today"}
          loading={loading}
        />
        <MetricCard 
            title="Credit Outstanding" 
          value={`₹${creditOutstanding.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`} 
          icon={Wallet} 
          iconColor="text-red-400"
          trend="Needs recovery action"
          trendDirection="down"
          loading={loading}
        />
        <MetricCard 
            title="Low Stock" 
          value={metrics?.lowStockItemsCount ?? 0} 
          icon={AlertTriangle} 
          iconColor="text-red-400"
          trend={(metrics?.lowStockItemsCount ?? 0) > 0 ? "ML replenishment ready" : "All stock levels healthy"}
          loading={loading}
        />
        <MetricCard 
            title="Pending Deliveries" 
          value={metrics?.pendingDeliveriesCount ?? 0} 
          icon={Truck} 
          trend={(metrics?.pendingDeliveriesCount ?? 0) > 0 ? `${metrics?.pendingDeliveriesCount} in transit` : "No deliveries pending"}
          loading={loading}
        />
        <MetricCard 
            title="Amount Due to Wholesalers" 
          value={`₹${(metrics?.pendingSupplierPay ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`} 
          icon={CreditCard} 
          trend={(metrics?.pendingSupplierPay ?? 0) > 0 ? "Awaiting approval" : "All settled"}
          loading={loading}
        />
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
