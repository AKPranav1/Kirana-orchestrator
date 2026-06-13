/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon?: LucideIcon;
  iconColor?: string;
  trend?: string;
  trendDirection?: 'up' | 'down' | 'neutral';
  loading?: boolean;
}

export default function MetricCard({ 
  title, 
  value, 
  icon: Icon, 
  iconColor = "text-[#888888]", 
  trend, 
  trendDirection = 'neutral',
  loading = false
}: MetricCardProps) {
  return (
    <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 flex flex-col justify-between h-32 hover:border-[#353534] transition-all">
      {loading ? (
        <div className="space-y-4 animate-pulse w-full">
          <div className="h-4 bg-[#1F1F1F] rounded w-1/3"></div>
          <div className="h-8 bg-[#1F1F1F] rounded w-1/2"></div>
        </div>
      ) : (
        <>
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-[#888888] uppercase tracking-wider">{title}</span>
            {Icon && (
              <span className={`${iconColor}`}>
                <Icon size={18} />
              </span>
            )}
          </div>
          <div className="flex justify-between items-baseline mt-2">
            <div className="text-2xl font-bold font-mono text-white tracking-tight">{value}</div>
            {trend && (
              <span className={`text-[10px] font-semibold flex items-center gap-0.5 rounded px-1.5 py-0.5 ${
                trendDirection === 'up' 
                  ? 'bg-[#10B981]/10 text-[#4edea3]' 
                  : trendDirection === 'down' 
                  ? 'bg-red-500/10 text-red-400' 
                  : 'bg-[#1F1F1F] text-[#888888]'
              }`}>
                {trend}
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
