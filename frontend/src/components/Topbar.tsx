/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Search, Bell, HelpCircle, X, Check, Menu } from 'lucide-react';
import { Notification } from '../types';
import { apiClient } from '../services/api';

interface TopbarProps {
  onSearchChange?: (val: string) => void;
  searchPlaceholder?: string;
  onMenuToggle?: () => void;
}

export default function Topbar({ onSearchChange, searchPlaceholder = "Search catalog, orders...", onMenuToggle }: TopbarProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    loadNotifs();
  }, []);

  const loadNotifs = async () => {
    const list = await apiClient.getNotifications();
    setNotifications(list);
  };

  const markAllRead = async () => {
    await apiClient.markNotificationsAsRead();
    loadNotifs();
  };

  const getUnreadCount = () => {
    return notifications.filter(n => !n.isRead).length;
  };

  return (
    <header className="fixed top-0 right-0 left-0 md:left-64 h-16 bg-[#0A0A0A] border-b border-[#1F1F1F] flex justify-between items-center px-4 md:px-10 z-30">
      {/* Search Input / Burger Menu */}
      <div className="flex items-center gap-4 flex-1 max-w-md">
        {onMenuToggle && (
          <button 
            onClick={onMenuToggle}
            className="md:hidden text-[#888888] hover:text-[#FFFFFF] cursor-pointer"
          >
            <Menu size={20} />
          </button>
        )}
        <div className="relative w-full hidden sm:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#888888]" size={16} />
          <input 
            type="text"
            placeholder={searchPlaceholder}
            onChange={(e) => onSearchChange?.(e.target.value)}
            className="w-full bg-[#121212] border border-[#1F1F1F] rounded-sm text-sm pl-10 pr-4 py-1.5 text-white placeholder-[#888888] focus:border-white focus:outline-none transition-colors"
          />
        </div>
      </div>

      {/* Right side controls */}
      <div className="flex items-center gap-4">
        {/* Store Active indicator */}
        <div className="flex items-center gap-2 px-3 py-1 rounded bg-[#121212] border border-[#1F1F1F]">
          <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse-soft"></span>
          <span className="text-xs font-medium text-[#888888]">Store: Online</span>
        </div>

        {/* Notif bell with Popover */}
        <div className="relative">
          <button 
            onClick={() => setShowDropdown(!showDropdown)}
            className="text-[#888888] hover:text-white p-1 rounded-full hover:bg-[#121212] transition-colors relative cursor-pointer"
          >
            <Bell size={18} />
            {getUnreadCount() > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-[#10B981] rounded-full border border-[#0A0A0A]"></span>
            )}
          </button>

          {showDropdown && (
            <div className="absolute right-0 mt-3 w-80 bg-[#121212] border border-[#1F1F1F] rounded-sm shadow-2xl p-4 z-50">
              <div className="flex justify-between items-center mb-3 pb-2 border-b border-[#1F1F1F]">
                <h4 className="text-xs font-semibold text-white uppercase tracking-wider">Alerts & Insights</h4>
                {getUnreadCount() > 0 && (
                  <button 
                    onClick={markAllRead}
                    className="text-[10px] text-[#4edea3] hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    <Check size={10} /> Mark all read
                  </button>
                )}
              </div>
              <div className="space-y-2.5 max-h-60 overflow-y-auto">
                {notifications.length === 0 ? (
                  <p className="text-xs text-[#888888] text-center py-4">No new notifications</p>
                ) : (
                  notifications.map(n => (
                    <div 
                      key={n.id} 
                      className={`p-2 rounded-sm border text-xs transition-colors ${
                        n.isRead 
                          ? 'bg-[#121212] border-[#1F1F1F] text-[#888888]' 
                          : 'bg-[#161D1A] border-[#1C2C23] text-white'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <span className="font-semibold text-white">{n.title}</span>
                        {!n.isRead && <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]"></span>}
                      </div>
                      <p className="mt-0.5 text-[11px] text-[#888888]">{n.description}</p>
                    </div>
                  ))
                )}
              </div>
              <div className="mt-3 text-center border-t border-[#1F1F1F] pt-2">
                <button 
                  onClick={() => setShowDropdown(false)}
                  className="text-[10px] text-[#888888] hover:text-white"
                >
                  Dismiss Menu
                </button>
              </div>
            </div>
          )}
        </div>

        <button className="text-[#888888] hover:text-white p-1 rounded-full hover:bg-[#121212] transition-colors hidden sm:block">
          <HelpCircle size={18} />
        </button>

        {/* Small avatar for profile view */}
        <div className="w-8 h-8 rounded-sm bg-[#121212] border border-[#1F1F1F] overflow-hidden">
          <img 
            alt="Owner portrait" 
            className="w-full h-full object-cover" 
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuAtu6ukQUsCZq-CumtrPz0nfkwIymJdUdgU4Onbwu2cg5pKf9JosUHzmiSryc1sJLN6qo6S1sDusdH5vbk1UScYe6bE2pxrrrHEJSecxw-CJ7Uy28vwe0tJQApYcQzuju6gqMizyxMSaol4nxT6J7cL7iqNeJw5ZsyEzg0btLeIBdXyt9es4pwdrW-wCcUE9pyaSZNQ5soq8-uXcw5coVwgs3LNk0C95qE_bGxlGbkwNmaULBiYAI2lzDJQHz-_gVTIOGnJxRlRi24H"
          />
        </div>
      </div>
    </header>
  );
}
