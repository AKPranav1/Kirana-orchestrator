/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';

// Pages import
import Dashboard from './pages/Dashboard';
import LiveOrders from './pages/LiveOrders';
import Customers from './pages/Customers';
import KhataLedger from './pages/KhataLedger';
import Inventory from './pages/Inventory';
import Analytics from './pages/Analytics';
// import Forecasts from './pages/Forecasts'; // Replaced by MLDashboard
import Reports from './pages/Reports';
import Settings from './pages/Settings';

// The new ML Dashboard component
import MLDashboard from './components/MLDashboard';

// Reusable action dialogs
import NewOrderModal from './components/NewOrderModal';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showNewOrder, setShowNewOrder] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Success handler for placed orders (triggers reload on active pages if needed)
  const handleOrderSuccess = () => {
    // Optional refresh trigger, React key updates can act as forced re-mount
    // Just force state remount logic if needed. Our localStorage makes it work perfectly anyway!
  };

  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <Dashboard 
            onNavigate={(tab) => setActiveTab(tab)} 
            onOpenNewOrder={() => setShowNewOrder(true)} 
          />
        );
      case 'orders':
        return (
          <LiveOrders 
            onOpenNewOrder={() => setShowNewOrder(true)} 
          />
        );
      case 'customers':
        return <Customers />;
      case 'khata':
        return <KhataLedger />;
      case 'inventory':
        return <Inventory />;
      case 'analytics':
        return <Analytics />;
      case 'forecasts':
        // Here is where we inject your new Machine Learning Chart Dashboard!
        return <MLDashboard />;
      case 'reports':
        return <Reports />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard onNavigate={(tab) => setActiveTab(tab)} onOpenNewOrder={() => setShowNewOrder(true)} />;
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-[#e5e2e1] overflow-x-hidden">
      {/* Sidebar navigation frame code */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={(tab) => {
          setActiveTab(tab);
          setMobileMenuOpen(false);
        }} 
        onNewOrder={() => setShowNewOrder(true)}
      />

      {/* Mobile Drawer (Visible ONLY on mobile when burger menu clicked) */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden bg-black/80">
          <div className="w-64 bg-[#121212] border-r border-[#1F1F1F] flex flex-col pt-6 pb-4 px-3 h-full animate-[slideRight_0.2s_ease-out]">
            <div className="mb-6 px-3 flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-md bg-white flex items-center justify-center text-black font-semibold text-lg font-mono">
                  K
                </div>
                <h1 className="text-md font-bold text-white uppercase tracking-wider">Kirana AI</h1>
              </div>
              <button 
                onClick={() => setMobileMenuOpen(false)}
                className="text-[#888888] hover:text-white"
              >
                ✕
              </button>
            </div>

            {/* Menu Links */}
            <div className="flex-1 overflow-y-auto space-y-1">
               {[
                 { id: 'dashboard', name: 'Home' },
                 { id: 'orders', name: 'Incoming Orders' },
                 { id: 'customers', name: 'Customers' },
                 { id: 'khata', name: 'Credit Book' },
                 { id: 'inventory', name: 'Products' },
                 { id: 'analytics', name: 'Sales Insights' },
                 { id: 'forecasts', name: 'Stock Suggestions' },
                 { id: 'reports', name: 'Reports' },
                 { id: 'settings', name: 'Settings' }
               ].map((item) => {
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setActiveTab(item.id);
                      setMobileMenuOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 rounded-sm text-xs font-semibold ${
                      isActive 
                        ? 'bg-[#1D2E26] text-[#4edea3]' 
                        : 'text-[#888888] hover:text-white'
                    }`}
                  >
                    {item.name}
                  </button>
                );
              })}
            </div>
            
            <button
              onClick={() => {
                setShowNewOrder(true);
                setMobileMenuOpen(false);
              }}
              className="mt-4 bg-white text-[#0A0A0A] font-semibold text-xs py-2 px-4 rounded-sm"
            >
              + New Order
            </button>
          </div>
        </div>
      )}

      {/* Main Top Header and Main Area Content Frames */}
      <div className="md:pl-64 min-h-screen flex flex-col pt-16">
        <Topbar 
          onSearchChange={() => {}} 
          onMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)}
        />
        
        {/* Viewport Core Render Frame */}
        <main className="flex-1 p-4 md:p-10 select-none pb-20 max-w-7xl mx-auto w-full">
          {renderActivePage()}
        </main>
      </div>

      {/* Central Interactive Checkout Dialog */}
      {showNewOrder && (
        <NewOrderModal 
          onClose={() => setShowNewOrder(false)} 
          onSuccess={handleOrderSuccess}
        />
      )}
    </div>
  );
}