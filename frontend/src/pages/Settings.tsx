/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Save, Sparkles, MessageSquare, BellRing } from 'lucide-react';
import { StoreSettings } from '../types';
import { apiClient } from '../services/api';

export default function Settings() {
  const [settings, setSettings] = useState<StoreSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    const data = await apiClient.getSettings();
    setSettings(data);
    setLoading(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;

    try {
      await apiClient.saveSettings(settings);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      alert("Error saving settings.");
    }
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">System Settings & Interfaces</h2>
        <p className="text-xs text-[#888888] mt-1">Configure artificial intelligence parsers, notification rules, and B2B WhatsApp automation APIs.</p>
      </div>

      {loading || !settings ? (
        <p className="text-xs text-[#888888] p-10 text-center font-mono">Loading settings profiles...</p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Main Info Box */}
          <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-white border-b border-[#1F1F1F] pb-2">Kirana Shop Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-sans">
              <div className="space-y-1.5">
                <label className="text-[#888888]">Store Display Name</label>
                <input 
                  type="text" 
                  value={settings.storeName}
                  onChange={(e) => setSettings({ ...settings, storeName: e.target.value })}
                  className="w-full bg-[#0A0A0A] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none focus:border-white"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[#888888]">Owner Name</label>
                <input 
                  type="text" 
                  value={settings.ownerName}
                  onChange={(e) => setSettings({ ...settings, ownerName: e.target.value })}
                  className="w-full bg-[#0A0A0A] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none focus:border-white"
                  required
                />
              </div>

              <div className="space-y-1.5 md:col-span-2">
                <label className="text-[#888888]">Official Mobile Number (+91 for WhatsApp bindings)</label>
                <input 
                  type="text" 
                  value={settings.phone}
                  onChange={(e) => setSettings({ ...settings, phone: e.target.value })}
                  className="w-full bg-[#0A0A0A] border border-[#1F1F1F] rounded-sm p-2 text-white focus:outline-none focus:border-white font-mono"
                  required
                />
              </div>
            </div>
          </div>

          {/* AI Integrations Configuration info */}
          <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-white border-b border-[#1F1F1F] pb-2 flex items-center gap-2">
              <Sparkles size={14} className="text-[#10B981]" /> WhatsApp Pipeline Automation
            </h3>
            
            <div className="space-y-4 text-xs">
              <div className="flex justify-between items-center transition-all bg-[#0A0A0A] border border-[#1F1F1F] p-3 rounded-sm">
                <div>
                  <span className="font-semibold text-white">Enable Kirana AI WhatsApp Receiver</span>
                  <p className="text-[10px] text-[#888888] mt-1">Intercept client order texts directly, queuing processed transactions automatically.</p>
                </div>
                <button
                  type="button"
                  onClick={() => setSettings({ ...settings, whatsappEnabled: !settings.whatsappEnabled })}
                  className={`px-3 py-1.5 rounded-sm font-semibold transition-all cursor-pointer ${
                    settings.whatsappEnabled 
                      ? 'bg-[#10B981]/15 text-[#4edea3] border border-[#10B981]/30' 
                      : 'bg-transparent border border-[#1F1F1F] text-[#888888]'
                  }`}
                >
                  {settings.whatsappEnabled ? "ACTIVE" : "INACTIVE"}
                </button>
              </div>

              <div className="flex justify-between items-center transition-all bg-[#0A0A0A] border border-[#1F1F1F] p-3 rounded-sm">
                <div>
                  <span className="font-semibold text-white">Auto-Extract Line Items via Gemini LLM</span>
                  <p className="text-[10px] text-[#888888] mt-1">Run text transcripts through AI models instantly without waiting for shopkeeper's approval.</p>
                </div>
                <button
                  type="button"
                  onClick={() => setSettings({ ...settings, autoExtractWhatsapp: !settings.autoExtractWhatsapp })}
                  className={`px-3 py-1.5 rounded-sm font-semibold transition-all cursor-pointer ${
                    settings.autoExtractWhatsapp 
                      ? 'bg-[#10B981]/15 text-[#4edea3] border border-[#10B981]/30' 
                      : 'bg-transparent border border-[#1F1F1F] text-[#888888]'
                  }`}
                >
                  {settings.autoExtractWhatsapp ? "AUTO-PROCESS ENABLED" : "MANUAL REVIEW REQUIRED"}
                </button>
              </div>
            </div>
          </div>

          {/* Low Stock Alerts Parameters */}
          <div className="bg-[#121212] border border-[#1F1F1F] rounded-lg p-5 space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-white border-b border-[#1F1F1F] pb-2 flex items-center gap-2">
              <BellRing size={14} className="text-amber-500" /> Replenishment Alerts Settings
            </h3>
            <div className="text-xs space-y-3">
              <div className="space-y-1.5 max-w-sm">
                <label className="text-[#888888]">Minimum stock warnings trigger limit (Units)</label>
                <input 
                  type="number" 
                  value={settings.lowStockThreshold}
                  onChange={(e) => setSettings({ ...settings, lowStockThreshold: parseInt(e.target.value) })}
                  className="w-full bg-[#0A0A0A] border border-[#1F1F1F] rounded-sm p-2 text-white font-mono focus:outline-none"
                  required
                />
                <span className="text-[10px] text-[#888888] block text-[11px] leading-relaxed mt-1">
                  Alert indicators are shown in the Topbar bell and active OS dashboards when catalog item totals fall under this point.
                </span>
              </div>
            </div>
          </div>

          {/* Action Trigger Save buttons */}
          <div className="flex items-center gap-4">
            <button 
              type="submit"
              className="py-2.5 px-6 bg-white text-[#0A0A0A] font-semibold text-xs rounded-sm transition-all hover:bg-[#e2e2e2] active:scale-[0.98] flex items-center gap-2 cursor-pointer"
            >
              <Save size={14} /> Commit Changes
            </button>

            {success && (
              <span className="text-xs text-[#4edea3] font-bold uppercase tracking-wider flex items-center gap-1 leading-none animate-pulse-soft">
                ✓ Settings profiles updated successfully!
              </span>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
