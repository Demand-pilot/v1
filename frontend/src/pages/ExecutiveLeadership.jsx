import React, { useState, useEffect } from 'react';
import { 
  Globe, 
  TrendingUp, 
  DollarSign, 
  AlertTriangle, 
  PieChart, 
  MapPin, 
  Sparkles, 
  ShieldCheck,
  BarChart3,
  Layers,
  ArrowUpDown,
  Building2,
  RefreshCw,
  Search
} from 'lucide-react';
import { api } from '../services/api';

export default function ExecutiveLeadership({ onOpenAICopilot }) {
  const [macroData, setMacroData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRegion, setSelectedRegion] = useState('ALL');
  const [sortBy, setSortBy] = useState('profit'); // 'profit', 'revenue', 'margin', 'volume'
  const [searchQuery, setSearchQuery] = useState('');
  const [activeStoreDetail, setActiveStoreDetail] = useState(14);

  const fetchMacro = async () => {
    setIsLoading(true);
    try {
      const data = await api.getMacroAnalytics();
      setMacroData(data);
    } catch (err) {
      console.error('Error fetching macro analytics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMacro();
  }, []);

  const stores = macroData?.stores || [];

  // Filter & Sort stores
  const filteredStores = stores
    .filter((s) => {
      if (selectedRegion !== 'ALL' && s.region?.toUpperCase() !== selectedRegion) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          s.city?.toLowerCase().includes(q) ||
          s.state?.toLowerCase().includes(q) ||
          s.store_nbr?.toString().includes(q)
        );
      }
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'profit') return b.return_profit_usd - a.return_profit_usd;
      if (sortBy === 'revenue') return b.gross_revenue_usd - a.gross_revenue_usd;
      if (sortBy === 'margin') return b.net_margin_pct - a.net_margin_pct;
      if (sortBy === 'volume') return b.forecast_16d_volume - a.forecast_16d_volume;
      return 0;
    });

  const activeStore = stores.find((s) => s.store_nbr === activeStoreDetail) || stores[0] || {
    store_nbr: 14,
    city: 'Quito',
    state: 'Pichincha',
    region: 'Sierra',
    forecast_16d_volume: 84120,
    gross_revenue_usd: 521544,
    return_profit_usd: 146032,
    net_margin_pct: 0.2800,
    holding_cost_savings_usd: 21904,
    stockout_risk_score: 0.85,
    reorder_status: 'CRITICAL',
    primary_surge_driver: 'Sierra Academic Surge (+145%)'
  };

  return (
    <div className="app-container" style={{ padding: '36px var(--space-5) 112px' }}>
      
      {/* Header & National Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '36px' }}>
        <div>
          <div className="eyebrow" style={{ marginBottom: '6px' }}>
            Executive Strategic Cockpit • 54 Stores Nationwide
          </div>
          <h1 style={{ fontSize: '2.4rem', fontFamily: 'var(--font-serif)', fontWeight: '700', marginBottom: '8px' }}>
            National Store Return Profits & Financial Portfolio
          </h1>
          <p className="body-text" style={{ maxWidth: '780px' }}>
            Comprehensive visibility across all 54 retail stores in Ecuador. Tracks 16-day forecast revenues, store return profits, net margins, and regional holding cost optimizations.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={fetchMacro}
            disabled={isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '10px 18px',
              borderRadius: 'var(--radius-pill)',
              backgroundColor: 'var(--surface-elevated)',
              border: '1px solid var(--border-subtle)',
              fontSize: '0.82rem',
              fontWeight: '600',
              color: 'var(--text-secondary)',
              cursor: 'pointer'
            }}
          >
            <RefreshCw size={14} className={isLoading ? 'spin' : ''} />
            <span>Refresh Financials</span>
          </button>

          <button
            onClick={onOpenAICopilot}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '12px 22px',
              borderRadius: 'var(--radius-pill)',
              backgroundColor: 'var(--accent-terracotta)',
              color: '#ffffff',
              border: 'none',
              fontWeight: '700',
              fontSize: '0.88rem',
              cursor: 'pointer',
              boxShadow: '0 4px 14px rgba(196, 93, 62, 0.3)'
            }}
          >
            <Sparkles size={16} />
            <span>Strategic Portfolio ROI Copilot</span>
          </button>
        </div>
      </div>

      {/* 4 Macro Financial KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '24px', marginBottom: '48px' }}>
        
        <div style={{ backgroundColor: 'var(--surface-elevated)', padding: '26px', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700', marginBottom: '6px' }}>
            National Forecast Volume
          </div>
          <div style={{ fontSize: '2.2rem', fontFamily: 'var(--font-serif)', fontWeight: '700', color: 'var(--text-primary)' }}>
            {(macroData?.national_volume || 2674850).toLocaleString()} <span style={{ fontSize: '0.85rem', fontFamily: 'var(--font-sans)', color: 'var(--text-muted)' }}>units</span>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--accent-terracotta)', fontWeight: '600', marginTop: '8px' }}>
            Across 54 Retail Stores
          </div>
        </div>

        <div style={{ backgroundColor: 'var(--surface-elevated)', padding: '26px', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700', marginBottom: '6px' }}>
            Projected Gross Revenue
          </div>
          <div style={{ fontSize: '2.2rem', fontFamily: 'var(--font-serif)', fontWeight: '700', color: 'var(--text-primary)' }}>
            ${((macroData?.gross_revenue_usd || 16526470) / 1000000).toFixed(2)}M <span style={{ fontSize: '0.85rem', fontFamily: 'var(--font-sans)', color: 'var(--text-muted)' }}>USD</span>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--state-info)', fontWeight: '600', marginTop: '8px' }}>
            Avg ${( (macroData?.gross_revenue_usd || 16526470) / 54 ).toLocaleString(undefined, {maximumFractionDigits:0})} / Store
          </div>
        </div>

        <div style={{ backgroundColor: 'var(--surface-elevated)', padding: '26px', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700', marginBottom: '6px' }}>
            Projected Store Return Profit
          </div>
          <div style={{ fontSize: '2.2rem', fontFamily: 'var(--font-serif)', fontWeight: '700', color: 'var(--state-success)' }}>
            ${((macroData?.return_profit_usd || 4703580) / 1000000).toFixed(2)}M <span style={{ fontSize: '0.85rem', fontFamily: 'var(--font-sans)', color: 'var(--text-muted)' }}>USD</span>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--state-success)', fontWeight: '600', marginTop: '8px' }}>
            {((macroData?.avg_net_margin_pct || 0.2846) * 100).toFixed(2)}% Net Margin Rate
          </div>
        </div>

        <div style={{ backgroundColor: 'var(--surface-elevated)', padding: '26px', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700', marginBottom: '6px' }}>
            Holding Cost Savings
          </div>
          <div style={{ fontSize: '2.2rem', fontFamily: 'var(--font-serif)', fontWeight: '700', color: 'var(--state-success)' }}>
            ${((macroData?.holding_cost_savings_usd || 694110) / 1000).toFixed(0)}k <span style={{ fontSize: '0.85rem', fontFamily: 'var(--font-sans)', color: 'var(--text-muted)' }}>USD</span>
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--state-success)', fontWeight: '600', marginTop: '8px' }}>
            -14.2% Inventory Capital Waste
          </div>
        </div>

      </div>

      {/* Regional Summary Bar */}
      {macroData?.regional_summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '48px' }}>
          <div style={{ backgroundColor: 'var(--surface-card)', padding: '20px 24px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>Sierra Region ({macroData.regional_summary.sierra.count} Stores)</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: '4px' }}>
              <span style={{ fontSize: '1.3rem', fontWeight: '700', fontFamily: 'var(--font-serif)' }}>${(macroData.regional_summary.sierra.revenue_usd / 1000000).toFixed(2)}M Rev</span>
              <span style={{ fontSize: '0.9rem', color: 'var(--state-success)', fontWeight: '700' }}>${(macroData.regional_summary.sierra.profit_usd / 1000000).toFixed(2)}M Profit</span>
            </div>
            <div style={{ fontSize: '0.76rem', color: 'var(--accent-terracotta)', marginTop: '4px' }}>{macroData.regional_summary.sierra.surge_driver}</div>
          </div>

          <div style={{ backgroundColor: 'var(--surface-card)', padding: '20px 24px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>Coast Region ({macroData.regional_summary.coast.count} Stores)</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: '4px' }}>
              <span style={{ fontSize: '1.3rem', fontWeight: '700', fontFamily: 'var(--font-serif)' }}>${(macroData.regional_summary.coast.revenue_usd / 1000000).toFixed(2)}M Rev</span>
              <span style={{ fontSize: '0.9rem', color: 'var(--state-success)', fontWeight: '700' }}>${(macroData.regional_summary.coast.profit_usd / 1000000).toFixed(2)}M Profit</span>
            </div>
            <div style={{ fontSize: '0.76rem', color: 'var(--accent-terracotta)', marginTop: '4px' }}>{macroData.regional_summary.coast.surge_driver}</div>
          </div>

          <div style={{ backgroundColor: 'var(--surface-card)', padding: '20px 24px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>Oriente Region ({macroData.regional_summary.oriente.count} Stores)</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: '4px' }}>
              <span style={{ fontSize: '1.3rem', fontWeight: '700', fontFamily: 'var(--font-serif)' }}>${(macroData.regional_summary.oriente.revenue_usd / 1000000).toFixed(2)}M Rev</span>
              <span style={{ fontSize: '0.9rem', color: 'var(--state-success)', fontWeight: '700' }}>${(macroData.regional_summary.oriente.profit_usd / 1000000).toFixed(2)}M Profit</span>
            </div>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '4px' }}>{macroData.regional_summary.oriente.surge_driver}</div>
          </div>
        </div>
      )}

      {/* 54-Store Return Profits & Margin Matrix Section */}
      <section style={{ marginBottom: '48px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div className="eyebrow" style={{ marginBottom: '4px' }}>
              Financial Performance Matrix
            </div>
            <h2 style={{ fontSize: '1.85rem', fontFamily: 'var(--font-serif)', fontWeight: '700' }}>
              54 Stores Return Profit & Margin Table
            </h2>
          </div>

          {/* Controls: Search, Region Filter, Sort */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            
            {/* Search */}
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Search size={14} style={{ position: 'absolute', left: '12px', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search city, store #..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  padding: '8px 12px 8px 34px',
                  borderRadius: 'var(--radius-pill)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--surface-elevated)',
                  fontSize: '0.82rem',
                  color: 'var(--text-primary)'
                }}
              />
            </div>

            {/* Region Pills */}
            <div style={{ display: 'flex', gap: '4px', backgroundColor: 'rgba(45, 42, 38, 0.05)', padding: '4px', borderRadius: 'var(--radius-pill)' }}>
              {['ALL', 'SIERRA', 'COAST', 'ORIENTE'].map((r) => (
                <button
                  key={r}
                  onClick={() => setSelectedRegion(r)}
                  style={{
                    padding: '5px 12px',
                    borderRadius: 'var(--radius-pill)',
                    border: 'none',
                    backgroundColor: selectedRegion === r ? 'var(--text-primary)' : 'transparent',
                    color: selectedRegion === r ? '#ffffff' : 'var(--text-secondary)',
                    fontSize: '0.76rem',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  {r}
                </button>
              ))}
            </div>

            {/* Sort Dropdown */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              <ArrowUpDown size={14} />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                style={{
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-pill)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--surface-elevated)',
                  fontSize: '0.8rem',
                  fontWeight: '600',
                  color: 'var(--text-primary)',
                  cursor: 'pointer'
                }}
              >
                <option value="profit">Sort by Return Profit ($)</option>
                <option value="revenue">Sort by Gross Revenue ($)</option>
                <option value="margin">Sort by Net Margin (%)</option>
                <option value="volume">Sort by Demand Volume</option>
              </select>
            </div>

          </div>
        </div>

        {/* Table View */}
        <div style={{ backgroundColor: 'var(--surface-elevated)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ overflowX: 'auto', maxHeight: '520px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.86rem' }}>
              <thead style={{ position: 'sticky', top: 0, backgroundColor: 'var(--surface-card)', borderBottom: '1px solid var(--border-subtle)', zIndex: 10 }}>
                <tr>
                  <th style={{ padding: '16px 20px', fontWeight: '700', color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Store</th>
                  <th style={{ padding: '16px 20px', fontWeight: '700', color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Location & Region</th>
                  <th style={{ padding: '16px 20px', fontWeight: '700', color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>16D Forecast Units</th>
                  <th style={{ padding: '16px 20px', fontWeight: '700', color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Gross Revenue</th>
                  <th style={{ padding: '16px 20px', fontWeight: '700', color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Return Profit ($)</th>
                  <th style={{ padding: '16px 20px', fontWeight: '700', color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Net Margin</th>
                  <th style={{ padding: '16px 20px', fontWeight: '700', color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Holding Savings</th>
                  <th style={{ padding: '16px 20px', fontWeight: '700', color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Risk Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredStores.map((s, idx) => {
                  const isSelected = s.store_nbr === activeStoreDetail;
                  return (
                    <tr
                      key={s.store_nbr}
                      onClick={() => setActiveStoreDetail(s.store_nbr)}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        backgroundColor: isSelected ? 'rgba(196, 93, 62, 0.06)' : (idx % 2 === 0 ? 'transparent' : 'rgba(45, 42, 38, 0.015)'),
                        cursor: 'pointer',
                        transition: 'background-color var(--transition-fast)'
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected) e.currentTarget.style.backgroundColor = 'rgba(45, 42, 38, 0.03)';
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) e.currentTarget.style.backgroundColor = idx % 2 === 0 ? 'transparent' : 'rgba(45, 42, 38, 0.015)';
                      }}
                    >
                      <td style={{ padding: '16px 20px', fontWeight: '700', color: 'var(--text-primary)' }}>
                        Store {s.store_nbr}
                      </td>
                      <td style={{ padding: '16px 20px', color: 'var(--text-secondary)' }}>
                        <div>{s.city}, {s.state}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--accent-terracotta)', fontWeight: '600' }}>{s.region} • Type {s.store_type} (Cluster {s.cluster})</div>
                      </td>
                      <td style={{ padding: '16px 20px', fontFamily: 'var(--font-mono)', fontWeight: '600' }}>
                        {s.forecast_16d_volume.toLocaleString()}
                      </td>
                      <td style={{ padding: '16px 20px', fontFamily: 'var(--font-mono)', fontWeight: '600' }}>
                        ${s.gross_revenue_usd.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}
                      </td>
                      <td style={{ padding: '16px 20px', fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--state-success)' }}>
                        ${s.return_profit_usd.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}
                      </td>
                      <td style={{ padding: '16px 20px', fontFamily: 'var(--font-mono)', fontWeight: '600' }}>
                        {(s.net_margin_pct * 100).toFixed(1)}%
                      </td>
                      <td style={{ padding: '16px 20px', fontFamily: 'var(--font-mono)', color: 'var(--state-info)' }}>
                        ${s.holding_cost_savings_usd.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}
                      </td>
                      <td style={{ padding: '16px 20px' }}>
                        <span
                          style={{
                            fontSize: '0.72rem',
                            fontWeight: '700',
                            padding: '3px 10px',
                            borderRadius: 'var(--radius-pill)',
                            backgroundColor: s.reorder_status === 'CRITICAL' ? 'var(--state-danger-bg)' : (s.reorder_status === 'WARNING' ? 'var(--state-warning-bg)' : 'var(--state-success-bg)'),
                            color: s.reorder_status === 'CRITICAL' ? 'var(--state-danger)' : (s.reorder_status === 'WARNING' ? 'var(--state-warning)' : 'var(--state-success)')
                          }}
                        >
                          {s.reorder_status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Selected Store Deep Dive Card */}
      {activeStore && (
        <section style={{ backgroundColor: 'var(--surface-card)', padding: '32px', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
            <div>
              <div className="eyebrow" style={{ marginBottom: '4px' }}>Store Deep Dive</div>
              <h3 style={{ fontSize: '1.6rem', fontFamily: 'var(--font-serif)', fontWeight: '700' }}>
                Store {activeStore.store_nbr} — {activeStore.city} ({activeStore.region} Region)
              </h3>
            </div>

            <span style={{ fontSize: '0.8rem', fontWeight: '700', color: 'var(--accent-terracotta)' }}>
              Primary Driver: {activeStore.primary_surge_driver}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
            <div>
              <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>16-Day Forecast Volume</div>
              <div style={{ fontSize: '1.4rem', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>{activeStore.forecast_16d_volume.toLocaleString()} units</div>
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>Gross Store Revenue</div>
              <div style={{ fontSize: '1.4rem', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>${activeStore.gross_revenue_usd.toLocaleString()}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>Store Return Profit</div>
              <div style={{ fontSize: '1.4rem', fontWeight: '700', fontFamily: 'var(--font-mono)', color: 'var(--state-success)' }}>${activeStore.return_profit_usd.toLocaleString()}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>Capital Waste Savings</div>
              <div style={{ fontSize: '1.4rem', fontWeight: '700', fontFamily: 'var(--font-mono)', color: 'var(--state-info)' }}>${activeStore.holding_cost_savings_usd.toLocaleString()}</div>
            </div>
          </div>
        </section>
      )}

    </div>
  );
}
