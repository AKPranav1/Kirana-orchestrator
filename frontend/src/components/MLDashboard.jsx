import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { AlertTriangle, TrendingUp, Package } from 'lucide-react';

export default function MLDashboard() {
  const [forecastData, setForecastData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Fetch data from your Python backend
    const fetchForecasts = async () => {
      try {
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8002';
        const response = await fetch(`${baseUrl}/forecast`);
        const data = await response.json();
        
        // 2. Sort data so the items needing the most urgent reorders are at the top
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

  if (loading) return <div className="p-10 text-center font-bold text-gray-500">Loading AI Engine...</div>;

  // 3. Calculate Math for the Top Tiles
  const totalItems = forecastData.length;
  const itemsToReorder = forecastData.filter(item => item.recommended_reorder_quantity > 0).length;
  const criticalStockouts = forecastData.filter(item => item.predicted_stockout_days <= 3).length;

  // 4. Prepare Chart Data (Top 10 items so the chart isn't overcrowded)
  const chartData = forecastData.slice(0, 10);

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-extrabold text-gray-900 mb-6">AI Demand Forecasting</h1>

      {/* --- TOP TILES SECTION --- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        
        {/* Tile 1: Total Products */}
        <div className="bg-white rounded-lg shadow p-6 flex items-center border-l-4 border-blue-500">
          <div className="p-3 bg-blue-100 rounded-full mr-4">
            <Package className="text-blue-600 w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-gray-500 font-semibold uppercase">Products Monitored</p>
            <p className="text-2xl font-bold text-gray-900">{totalItems}</p>
          </div>
        </div>

        {/* Tile 2: Items Needing Reorder */}
        <div className="bg-white rounded-lg shadow p-6 flex items-center border-l-4 border-yellow-500">
          <div className="p-3 bg-yellow-100 rounded-full mr-4">
            <TrendingUp className="text-yellow-600 w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-gray-500 font-semibold uppercase">Action Needed</p>
            <p className="text-2xl font-bold text-gray-900">{itemsToReorder}</p>
          </div>
        </div>

        {/* Tile 3: Critical Risk */}
        <div className="bg-white rounded-lg shadow p-6 flex items-center border-l-4 border-red-500">
          <div className="p-3 bg-red-100 rounded-full mr-4">
            <AlertTriangle className="text-red-600 w-6 h-6" />
          </div>
          <div>
            <p className="text-sm text-gray-500 font-semibold uppercase">Stockout Risk (&lt; 3 days)</p>
            <p className="text-2xl font-bold text-red-600">{criticalStockouts}</p>
          </div>
        </div>
      </div>

      {/* --- CHART SECTION --- */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-4">Inventory Gap Analysis (Top 10 Priorities)</h2>
        <div className="h-96 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              
              {/* XAxis rotates the product names so they are readable */}
              <XAxis 
                dataKey="product_name" 
                angle={-45} 
                textAnchor="end" 
                height={80} 
                interval={0}
                tick={{fontSize: 12}}
              />
              <YAxis />
              <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
              <Legend verticalAlign="top" height={36}/>
              
              {/* The Two Bars */}
              <Bar dataKey="current_stock" name="Current Stock" fill="#94a3b8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="recommended_reorder_quantity" name="AI Reorder Quantity" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
}