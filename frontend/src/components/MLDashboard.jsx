import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { AlertTriangle, TrendingUp, Package, Brain, Zap } from 'lucide-react';

export default function MLDashboard() {
  const [forecastData, setForecastData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchForecasts = async () => {
      try {
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8002';
        const response = await fetch(`${baseUrl}/forecast`);
        const data = await response.json();
        
        const sortedData = data.sort((a, b) => b.recommended_reorder_quantity - a.recommended_reorder_quantity);
        setForecastData(sortedData);
        setLoading(false);
      } catch (error) {
        console.error("Failed to fetch ML data:", error);
        setLoading(false);
      }
    };

    fetchForecasts();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#10B981] mx-auto mb-4"></div>
          <p className="text-[#888888] text-sm">Loading AI Engine predictions...</p>
        </div>
      </div>
    );
  }

  // REMOVED :any types here
  const totalItems = forecastData.length;
  const itemsToReorder = forecastData.filter((item) => item.recommended_reorder_quantity > 0).length;
  const criticalStockouts = forecastData.filter((item) => item.predicted_stockout_days <= 3).length;
  const chartData = forecastData.slice(0, 10);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">AI Demand Forecasting Engine</h2>
          <p className="text-xs text-[#888888] mt-1">Machine learning predictions for inventory replenishment and stockout risks.</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-[#10B981] bg-[#10B981]/10 px-3 py-1.5 rounded-full">
          <Brain size={14} />
          <span>XGBoost Model Active</span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Tile 1 */}
        <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Package className="text-blue-400 w-5 h-5" />
            </div>
            <div>
              <p className="text-[10px] text-[#888888] font-semibold uppercase tracking-wider">Products Monitored</p>
              <p className="text-2xl font-bold text-white mt-1">{totalItems}</p>
            </div>
          </div>
        </div>

        {/* Tile 2 */}
        <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-500/10 rounded-lg">
              <TrendingUp className="text-yellow-400 w-5 h-5" />
            </div>
            <div>
              <p className="text-[10px] text-[#888888] font-semibold uppercase tracking-wider">Action Needed (Reorder)</p>
              <p className="text-2xl font-bold text-white mt-1">{itemsToReorder}</p>
            </div>
          </div>
        </div>

        {/* Tile 3 */}
        <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-500/10 rounded-lg">
              <AlertTriangle className="text-red-400 w-5 h-5" />
            </div>
            <div>
              <p className="text-[10px] text-[#888888] font-semibold uppercase tracking-wider">Stockout Risk (&lt;3 days)</p>
              <p className="text-2xl font-bold text-red-400 mt-1">{criticalStockouts}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <Zap size={16} className="text-[#10B981]" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-white">Inventory Gap Analysis (Top 10 Priorities)</h3>
        </div>
        
        <div className="h-96 w-full">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
                <CartesianGrid stroke="#1F1F1F" vertical={false} />
                <XAxis 
                  dataKey="product_name" 
                  angle={-45} 
                  textAnchor="end" 
                  height={80} 
                  interval={0}
                  tick={{ fontSize: 11, fill: '#888888' }}
                  stroke="#1F1F1F"
                />
                <YAxis tick={{ fontSize: 11, fill: '#888888' }} stroke="#1F1F1F" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#121212', borderColor: '#1F1F1F', borderRadius: '8px' }}
                  labelStyle={{ color: '#888888', fontSize: '11px' }}
                  itemStyle={{ fontSize: '12px' }}
                />
                <Legend 
                  verticalAlign="top" 
                  height={36}
                  wrapperStyle={{ fontSize: '11px', color: '#888888' }}
                />
                <Bar dataKey="current_stock" name="Current Stock" fill="#475569" radius={[4, 4, 0, 0]} />
                <Bar dataKey="recommended_reorder_quantity" name="AI Reorder Quantity" fill="#10B981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-[#888888] text-sm">
              No forecast data available. Run ML training script first.
            </div>
          )}
        </div>
      </div>

      {/* Insights Table */}
      {forecastData.length > 0 && (
        <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg overflow-hidden">
          <div className="p-4 border-b border-[#1F1F1F] bg-[#161616]">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-white">Detailed Forecasts</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-[#1F1F1F] text-[#888888] text-[10px] uppercase font-bold bg-[#0F0F0F]">
                  <th className="p-4">Product</th>
                  <th className="p-4">Current Stock</th>
                  <th className="p-4">Predicted Stockout (days)</th>
                  <th className="p-4">Recommended Reorder Qty</th>
                  <th className="p-4">Confidence Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F1F1F]">
                {forecastData.slice(0, 15).map((item, idx) => (
                  <tr key={idx} className="hover:bg-[#1a1a1a] transition-colors">
                    <td className="p-4 text-white text-xs font-medium">{item.product_name}</td>
                    <td className="p-4 text-[#888888] text-xs">{item.current_stock}</td>
                    <td className="p-4">
                      <span className={`text-xs font-mono ${
                        item.predicted_stockout_days <= 3 ? 'text-red-400' : 
                        item.predicted_stockout_days <= 7 ? 'text-yellow-400' : 'text-[#888888]'
                      }`}>
                        {item.predicted_stockout_days} days
                      </span>
                    </td>
                    <td className="p-4 text-[#10B981] text-xs font-mono font-bold">
                      {item.recommended_reorder_quantity > 0 ? `+${item.recommended_reorder_quantity}` : '-'}
                    </td>
                    <td className="p-4 text-[#888888] text-xs">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-[#1F1F1F] rounded-full h-1.5">
                          <div 
                            className="bg-[#10B981] h-1.5 rounded-full" 
                            style={{ width: `${Math.round((item.confidence_score || 0.85) * 100)}%` }}
                          />
                        </div>
                        <span>{Math.round((item.confidence_score || 0.85) * 100)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}