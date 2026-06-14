/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar 
} from 'recharts';
import { BarChart3, TrendingUp, DollarSign, Calendar, Sliders } from 'lucide-react';
import { Analytics } from '../types';
import { analyticsService } from '../services/analytics';

export default function AnalyticsView() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState<'7d' | '30d'>('7d');

  useEffect(() => {
    loadAnalytics();
  }, [timeframe]); // Reload when timeframe changes

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const res = await analyticsService.getAnalytics(timeframe); // Pass timeframe to API
      setData(res);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const COLORS = ['#10B981', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6'];

  // Add fallback/empty data to prevent undefined errors
  const safeData = {
    trendData: data?.trendData || [],
    categoryDistribution: data?.categoryDistribution || [],
    topProducts: data?.topProducts || []
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Business Intelligence Analytics</h2>
          <p className="text-xs text-[#888888] mt-1">Configure parameters, view product velocities, and track daily business trends.</p>
        </div>

        {/* Timeframe selector */}
        <div className="flex bg-[#121212] border border-[#1F1F1F] rounded p-1 gap-1">
          <button 
            onClick={() => setTimeframe('7d')}
            className={`px-3 py-1 text-xs font-semibold rounded-sm transition-colors cursor-pointer ${
              timeframe === '7d' 
                ? 'bg-white text-black' 
                : 'text-[#888888] hover:text-white'
            }`}
          >
            Last 7 Days
          </button>
          <button 
            onClick={() => setTimeframe('30d')}
            className={`px-3 py-1 text-xs font-semibold rounded-sm transition-colors cursor-pointer ${
              timeframe === '30d' 
                ? 'bg-white text-black' 
                : 'text-[#888888] hover:text-white'
            }`}
          >
            Last 30 Days
          </button>
        </div>
      </div>

      {loading || !data ? (
        <p className="text-xs text-[#888888] p-10 text-center font-mono animate-pulse">Running data aggregation streams...</p>
      ) : (
        <div className="space-y-6">
          {/* Charts Row 1: Area stream of Daily Revenue & Volume */}
          <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={16} className="text-[#10B981]" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-white">Daily Revenue Velocity & Order Volume</h3>
            </div>

            <div className="h-72 w-full">
              {safeData.trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={safeData.trendData}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10B981" stopOpacity={0.1}/>
                        <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#1F1F1F" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#888888" 
                      fontSize={10} 
                      tickLine={false} 
                      axisLine={false}
                    />
                    <YAxis 
                      stroke="#888888" 
                      fontSize={10} 
                      tickLine={false} 
                      axisLine={false}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#121212', borderColor: '#1F1F1F', borderRadius: '4px' }}
                      labelStyle={{ color: '#888888', fontSize: '11px' }}
                      itemStyle={{ color: 'white', fontSize: '12px' }}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="revenue" 
                      stroke="#10B981" 
                      fillOpacity={1} 
                      fill="url(#colorRevenue)" 
                      strokeWidth={2}
                      name="Revenue (₹)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-[#888888] text-sm">
                  No revenue data available
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Pie Chart: category share */}
            <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 flex flex-col justify-between h-80">
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 size={16} className="text-blue-400" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-white">FMCG Sales Distribution share</h3>
              </div>

              <div className="flex-1 flex items-center justify-center gap-4">
                {safeData.categoryDistribution.length > 0 ? (
                  <>
                    <div className="w-40 h-40">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={safeData.categoryDistribution}
                            cx="50%"
                            cy="50%"
                            innerRadius={50}
                            outerRadius={70}
                            paddingAngle={3}
                            dataKey="value"
                            nameKey="name"
                          >
                            {safeData.categoryDistribution.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#121212', borderColor: '#1F1F1F' }}
                            itemStyle={{ color: 'white', fontSize: '11px' }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Legend list */}
                    <div className="space-y-2 text-xs">
                      {safeData.categoryDistribution.map((entry, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></div>
                          <span className="text-[#888888]">{entry.name}</span>
                          <span className="text-white font-semibold font-mono">{entry.value}%</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="text-[#888888] text-sm text-center w-full">
                    No category data available
                  </div>
                )}
              </div>
            </div>

            {/* Bar Chart: top selling items list */}
            <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 flex flex-col justify-between h-80">
              <div className="flex items-center gap-2 mb-3">
                <Sliders size={16} className="text-amber-500" />
                <h3 className="text-xs font-semibold uppercase tracking-wider text-white">Revenue Leaders (Top FMCG items)</h3>
              </div>

              <div className="w-full h-[300px] mt-2">
                {safeData.topProducts.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={safeData.topProducts}
                      margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
                      layout="vertical"
                    >
                      <CartesianGrid stroke="#1F1F1F" horizontal={false} />
                      <XAxis 
                        type="number"
                        stroke="#888888" 
                        fontSize={10} 
                        tickLine={false} 
                        axisLine={false}
                      />
                      <YAxis 
                        type="category"
                        dataKey="name" 
                        stroke="#888888" 
                        fontSize={8} 
                        tickLine={false} 
                        axisLine={false}
                        width={80}
                      />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#121212', borderColor: '#1F1F1F' }}
                        itemStyle={{ color: 'white', fontSize: '11px' }}
                      />
                      <Bar dataKey="revenue" fill="#10B981" radius={[0, 2, 2, 0]} name="Revenue Collected (₹)" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-[#888888] text-sm">
                    No product data available
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}