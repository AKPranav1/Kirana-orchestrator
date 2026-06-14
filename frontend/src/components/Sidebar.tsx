/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { 
  LayoutDashboard, 
  ShoppingCart, 
  Users, 
  Wallet, 
  Package, 
  ShoppingBag, 
  Truck, 
  BarChart3, 
  TrendingUp, 
  FileText, 
  Settings, 
  Bell, 
  Store,
  Plus
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onNewOrder: () => void;
}

export default function Sidebar({ activeTab, setActiveTab, onNewOrder }: SidebarProps) {
  const menuItems = [
    { id: 'dashboard', name: 'Home', icon: LayoutDashboard },
    { id: 'orders', name: 'Incoming Orders', icon: ShoppingCart },
    { id: 'customers', name: 'Customers', icon: Users },
    { id: 'khata', name: 'Credit Book', icon: Wallet },
    { id: 'inventory', name: 'Products', icon: Package },
    { id: 'analytics', name: 'Sales Insights', icon: BarChart3 },
    { id: 'forecasts', name: 'Stock Suggestions', icon: TrendingUp }
  ];

  return (
    <nav className="fixed left-0 top-0 bottom-0 w-64 bg-[#121212] border-r border-[#1F1F1F] flex flex-col pt-6 pb-4 px-3 z-40 hidden md:flex">
      {/* Brand Header */}
      <div className="mb-6 px-3 flex items-center gap-3">
        <div className="h-9 w-9 rounded-md bg-white flex items-center justify-center text-black font-semibold text-xl font-mono tracking-tight">
          K
        </div>
        <div>
          <h1 className="text-lg font-semibold text-white tracking-tight leading-none">Kirana AI</h1>
          <p className="text-[10px] text-[#888888] font-medium tracking-wider mt-1 uppercase">Store OS v2.4</p>
        </div>
      </div>

      {/* Primary Call to Action */}
      <button 
        onClick={onNewOrder}
        className="mx-2 mb-6 bg-white text-[#0A0A0A] font-medium text-sm py-2 px-4 rounded-sm flex items-center justify-center gap-2 hover:bg-[#e2e2e2] active:scale-[0.98] transition-all cursor-pointer"
      >
        <Plus size={16} />
        + New Sale
      </button>

      {/* Navigation List */}
      <div className="flex-1 overflow-y-auto space-y-1 pr-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-sm text-sm transition-colors duration-150 text-left cursor-pointer ${
                isActive 
                  ? 'bg-[#1D2E26] text-[#4edea3] font-medium border-l-2 border-[#10B981]' 
                  : 'text-[#888888] hover:text-[#FFFFFF] hover:bg-[#1A1A1A]'
              }`}
            >
              <Icon size={18} className={isActive ? 'text-[#4edea3]' : 'text-[#888888]'} />
              <span>{item.name}</span>
            </button>
          );
        })}
      </div>

      {/* Bottom Profile Details */}
      <div className="mt-auto pt-4 border-t border-[#1F1F1F] px-2 flex items-center gap-3">
        <div className="w-8 h-8 rounded-sm bg-[#1C1B1B] border border-[#1F1F1F] overflow-hidden flex-shrink-0">
          <img 
            alt="Shopkeeper Avatar" 
            className="w-full h-full object-cover" 
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuAtu6ukQUsCZq-CumtrPz0nfkwIymJdUdgU4Onbwu2cg5pKf9JosUHzmiSryc1sJLN6qo6S1sDusdH5vbk1UScYe6bE2pxrrrHEJSecxw-CJ7Uy28vwe0tJQApYcQzuju6gqMizyxMSaol4nxT6J7cL7iqNeJw5ZsyEzg0btLeIBdXyt9es4pwdrW-wCcUE9pyaSZNQ5soq8-uXcw5coVwgs3LNk0C95qE_bGxlGbkwNmaULBiYAI2lzDJQHz-_gVTIOGnJxRlRi24H"
          />
        </div>
        <div className="flex flex-col min-w-0">
          <span className="text-xs font-semibold text-[#FFFFFF] truncate">Suresh Sharma</span>
          <span className="text-[10px] text-[#888888] font-medium tracking-wide">Store Owner</span>
        </div>
      </div>
    </nav>
  );
}
