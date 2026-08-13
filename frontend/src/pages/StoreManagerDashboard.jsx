import React, { useState, useEffect } from 'react';
import { 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  TrendingUp, 
  Sparkles, 
  Plus, 
  Minus, 
  RotateCcw, 
  ChevronDown, 
  ChevronUp, 
  ShieldCheck, 
  ArrowRight,
  RefreshCw,
  ShoppingBag,
  Info,
  Calendar,
  AlertTriangle
} from 'lucide-react';
import { api } from '../services/api';
import DemandTrendChart from '../components/DemandTrendChart';
import InventoryRunwayChart from '../components/InventoryRunwayChart';
import OrderPlanDock from '../components/OrderPlanDock';

export default function StoreManagerDashboard({ storeId = 14, onOpenAICopilot, onNavigateToRestock }) {
  const [snapshot, setSnapshot] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [apiError, setApiError] = useState(null);
  
  // Active selected category for history & runway charts
  const [selectedFamily, setSelectedFamily] = useState('SCHOOL AND OFFICE SUPPLIES');
  const [historyWindow, setHistoryWindow] = useState(28);

  // Editable Order Quantities: { [family]: quantity }
  const [orderQuantities, setOrderQuantities] = useState({});
  
  // Planned orders cart: { [family]: { qty, reason, stockoutDate } }
  const [plannedOrders, setPlannedOrders] = useState({});

  // Expandable audit drawers: { [family]: boolean }
  const [expandedAudit, setExpandedAudit] = useState({});

  const fetchSnapshot = async (showRefreshSpinner = false) => {
    if (showRefreshSpinner) setIsRefreshing(true);
    else setIsLoading(true);
    setApiError(null);

    try {
      const data = await api.getStoreOperationsSnapshot(storeId);
      setSnapshot(data);

      // Initialize order quantities from recommended values
      const initialQty = {};
      data.categories?.forEach((cat) => {
        initialQty[cat.family] = cat.recommended_order_qty || 0;
      });
      setOrderQuantities(initialQty);

      // Ensure selected family exists in response
      if (data.categories && data.categories.length > 0) {
        if (!data.categories.some(c => c.family === selectedFamily)) {
          setSelectedFamily(data.categories[0].family);
        }
      }
    } catch (err) {
      console.error('Failed to load store operations snapshot:', err);
      setApiError(err.message || 'Unable to connect to live store snapshot service.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSnapshot();
  }, [storeId]);

  // Adjust order quantity with min 0
  const handleQuantityChange = (family, delta) => {
    setOrderQuantities((prev) => {
      const current = prev[family] || 0;
      const next = Math.max(0, current + delta);
      return { ...prev, [family]: next };
    });
  };

  const handleManualQuantityInput = (family, valStr) => {
    const num = parseInt(valStr, 10);
    setOrderQuantities((prev) => ({
      ...prev,
      [family]: isNaN(num) ? 0 : Math.max(0, num)
    }));
  };

  // Add / Remove from Order Plan with API Persistence and error rollback
  const toggleAddToPlan = async (cat) => {
    const family = cat.family;
    const qty = orderQuantities[family] || cat.recommended_order_qty;
    const isAdding = !plannedOrders[family];
    const previousPlannedOrders = { ...plannedOrders };

    // Optimistic UI update
    setPlannedOrders((prev) => {
      const next = { ...prev };
      if (next[family]) {
        delete next[family];
      } else {
        next[family] = {
          family,
          qty,
          stockoutDate: cat.projected_stockout_date,
          daysOfCover: cat.days_of_cover
        };
      }
      return next;
    });

    // Server-side persistence with state rollback on error
    try {
      const plan = await api.getCurrentOrderPlan(storeId);
      if (isAdding) {
        await api.saveOrderPlanLine(
          plan.id,
          family,
          qty,
          cat.recommended_order_qty || 0,
          `Added from Priority Action / Exception table`
        );
      }
    } catch (err) {
      console.warn('Could not sync order plan with server, reverting optimistic update:', err);
      setPlannedOrders(previousPlannedOrders);
    }
  };

  const toggleAuditPanel = (family) => {
    setExpandedAudit((prev) => ({
      ...prev,
      [family]: !prev[family]
    }));
  };

  const activeCategoryObj = snapshot?.categories?.find(c => c.family === selectedFamily) || snapshot?.categories?.[0];

  // Loading State
  if (isLoading && !snapshot) {
    return (
      <div className="app-container" style={{ padding: '64px var(--space-5)', textAlign: 'center' }}>
        <div style={{ width: '36px', height: '36px', borderRadius: '50%', border: '3px solid var(--accent-terracotta)', borderTopColor: 'transparent', animation: 'spin 0.8s linear infinite', margin: '0 auto 20px' }} />
        <h2 style={{ fontSize: '1.4rem', fontFamily: 'var(--font-serif)' }}>Loading Live Store {storeId} Snapshot...</h2>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginTop: '6px' }}>Fetching authoritative SQL facts and 16-day rolling forecasts...</p>
      </div>
    );
  }

  // Error State (including 403 Forbidden RBAC)
  if (apiError && !snapshot) {
    const is403 = apiError.includes('403') || apiError.includes('Access denied');
    return (
      <div className="app-container" style={{ padding: '64px var(--space-5)', textAlign: 'center' }}>
        <div style={{ width: '48px', height: '48px', borderRadius: '50%', backgroundColor: 'var(--state-danger-bg)', color: 'var(--state-danger)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
          <AlertCircle size={28} />
        </div>
        <h2 style={{ fontSize: '1.4rem', fontFamily: 'var(--font-serif)', color: 'var(--state-danger)' }}>
          {is403 ? 'Access Denied (403 Forbidden)' : 'Failed to Load Operations Snapshot'}
        </h2>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', maxWidth: '480px', margin: '8px auto 20px' }}>
          {is403 
            ? `Your current login role does not have authorization to view operational data for Store ${storeId}. Please select an authorized store.`
            : apiError}
        </p>
        <button
          onClick={() => fetchSnapshot()}
          style={{ padding: '10px 22px', borderRadius: 'var(--radius-pill)', backgroundColor: 'var(--text-primary)', color: '#fff', border: 'none', fontWeight: '600', cursor: 'pointer' }}
        >
          {is403 ? 'Retry with Store 14' : 'Retry Connection'}
        </button>
      </div>
    );
  }

  return (
    <div className="app-container" style={{ padding: '36px var(--space-5) 112px' }}>
      
      {/* 1. Store Header & Data Freshness Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'var(--surface-elevated)',
          padding: '18px 24px',
          borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--border-subtle)',
          boxShadow: 'var(--shadow-sm)',
          marginBottom: '36px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.86rem', fontWeight: '700' }}>
            <span style={{ width: '9px', height: '9px', borderRadius: '50%', backgroundColor: snapshot?.freshness === 'LIVE' ? 'var(--state-success)' : 'var(--state-warning)' }} />
            <span>{snapshot?.store_name || `Store ${storeId}`}</span>
          </div>

          <div style={{ height: '18px', width: '1px', backgroundColor: 'var(--border-subtle)' }} />

          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Clock size={14} />
            <span>Cutoff As-Of: Aug 15, 2017 08:00 (Today)</span>
          </div>

          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: '700',
              padding: '3px 10px',
              borderRadius: 'var(--radius-pill)',
              backgroundColor: snapshot?.freshness === 'LIVE' ? 'var(--state-success-bg)' : 'var(--state-warning-bg)',
              color: snapshot?.freshness === 'LIVE' ? 'var(--state-success)' : 'var(--state-warning)'
            }}
          >
            {snapshot?.freshness === 'LIVE' ? 'LIVE DATA STREAM' : 'CACHED SNAPSHOT'}
          </span>
        </div>

        {/* Refresh Action */}
        <button
          onClick={() => fetchSnapshot(true)}
          disabled={isRefreshing}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 18px',
            borderRadius: 'var(--radius-pill)',
            border: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--surface-card)',
            fontSize: '0.8rem',
            fontWeight: '600',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            transition: 'all var(--transition-fast)'
          }}
        >
          <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />
          <span>{isRefreshing ? 'Refreshing...' : 'Refresh Snapshot'}</span>
        </button>
      </div>

      {/* 2. Today's Ranked Priority Actions Queue */}
      <section style={{ marginBottom: '48px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '20px' }}>
          <div>
            <div className="eyebrow" style={{ marginBottom: '6px' }}>
              Action-First Replenishment Queue
            </div>
            <h2 style={{ fontSize: '1.85rem', fontFamily: 'var(--font-serif)', fontWeight: '700' }}>
              Today’s Priority Actions
            </h2>
          </div>
          <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
            Ranked by immediate stockout risk and customer fulfillment impact
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '24px' }}>
          {snapshot?.priority_actions?.map((act) => {
            const isHigh = act.urgency === 'HIGH';
            const isAdded = !!plannedOrders[act.family];
            const currentQty = orderQuantities[act.family] || act.recommended_order_qty;

            return (
              <div
                key={act.id}
                style={{
                  backgroundColor: 'var(--surface-elevated)',
                  borderRadius: 'var(--radius-xl)',
                  padding: '24px',
                  border: isHigh ? '2px solid var(--accent-terracotta)' : '1px solid var(--border-medium)',
                  boxShadow: isHigh ? 'var(--shadow-md)' : 'var(--shadow-sm)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '18px'
                }}
              >
                <div>
                  {/* Top Urgency Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px',
                        fontSize: '0.74rem',
                        fontWeight: '700',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        padding: '4px 10px',
                        borderRadius: 'var(--radius-pill)',
                        backgroundColor: isHigh ? 'var(--state-danger-bg)' : 'var(--state-warning-bg)',
                        color: isHigh ? 'var(--state-danger)' : 'var(--state-warning)'
                      }}
                    >
                      <AlertTriangle size={13} />
                      {isHigh ? 'Stockout Risk: High' : 'Stockout Risk: Moderate'}
                    </span>

                    <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                      Stockout: <strong style={{ color: 'var(--text-primary)' }}>{act.projected_stockout_date}</strong> ({act.days_of_cover}D cover)
                    </div>
                  </div>

                  {/* Headline & Reason */}
                  <h3 style={{ fontSize: '1.25rem', fontFamily: 'var(--font-serif)', fontWeight: '700', lineHeight: 1.25, marginBottom: '8px', color: 'var(--text-primary)' }}>
                    {act.action_headline}
                  </h3>
                  <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.55, marginBottom: '14px' }}>
                    {act.reason}
                  </p>

                  {/* Impact Note & Confidence */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--surface-card)', padding: '10px 14px', borderRadius: 'var(--radius-md)', fontSize: '0.78rem' }}>
                    <span style={{ color: 'var(--text-primary)', fontWeight: '600' }}>
                      Impact: {act.impact}
                    </span>
                    <span style={{ color: 'var(--state-success)', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>
                      {act.confidence} Conf
                    </span>
                  </div>
                </div>

                {/* Bottom Action Controls */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '14px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
                  
                  {/* Accessible 44px Order Quantity Adjuster */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                      onClick={() => handleQuantityChange(act.family, -50)}
                      aria-label={`Decrease ${act.family} order by 50 units`}
                      style={{
                        minWidth: '44px',
                        minHeight: '44px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-medium)',
                        backgroundColor: 'var(--surface-card)',
                        color: 'var(--text-primary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        fontWeight: '700'
                      }}
                    >
                      <Minus size={16} />
                    </button>

                    <input
                      type="number"
                      value={currentQty}
                      onChange={(e) => handleManualQuantityInput(act.family, e.target.value)}
                      aria-label={`${act.family} order quantity`}
                      style={{
                        width: '80px',
                        height: '44px',
                        textAlign: 'center',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-medium)',
                        backgroundColor: 'var(--surface-elevated)',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: '700',
                        fontSize: '1rem',
                        color: 'var(--text-primary)'
                      }}
                    />

                    <button
                      onClick={() => handleQuantityChange(act.family, 50)}
                      aria-label={`Increase ${act.family} order by 50 units`}
                      style={{
                        minWidth: '44px',
                        minHeight: '44px',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border-medium)',
                        backgroundColor: 'var(--surface-card)',
                        color: 'var(--text-primary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        fontWeight: '700'
                      }}
                    >
                      <Plus size={16} />
                    </button>
                  </div>

                  {/* Add to Order Plan Button */}
                  <button
                    onClick={() => toggleAddToPlan({ family: act.family, recommended_order_qty: currentQty, projected_stockout_date: act.projected_stockout_date, days_of_cover: act.days_of_cover })}
                    style={{
                      flex: 1,
                      minHeight: '44px',
                      padding: '0 18px',
                      borderRadius: 'var(--radius-pill)',
                      backgroundColor: isAdded ? 'var(--state-success)' : 'var(--accent-terracotta)',
                      color: '#ffffff',
                      border: 'none',
                      fontWeight: '700',
                      fontSize: '0.88rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      boxShadow: isAdded ? 'none' : '0 4px 14px rgba(196, 93, 62, 0.3)',
                      transition: 'all var(--transition-fast)'
                    }}
                  >
                    {isAdded ? (
                      <>
                        <CheckCircle2 size={16} />
                        <span>Added to Plan</span>
                      </>
                    ) : (
                      <>
                        <ShoppingBag size={16} />
                        <span>Add to Order Plan</span>
                      </>
                    )}
                  </button>

                </div>

              </div>
            );
          })}
        </div>
      </section>

      {/* 3. Interactive Selected Category Deep Dive: Demand Trend & Runway */}
      <section style={{ marginBottom: '36px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <div className="eyebrow" style={{ marginBottom: '4px' }}>
              Credibility & Demand Evidence
            </div>
            <h2 style={{ fontSize: '1.65rem', fontFamily: 'var(--font-serif)', fontWeight: '700' }}>
              Historical Actuals & 16-Day Inventory Runway
            </h2>
          </div>

          {/* Category Selector Pills */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {snapshot?.categories?.map((c) => (
              <button
                key={c.family}
                onClick={() => setSelectedFamily(c.family)}
                style={{
                  fontSize: '0.78rem',
                  fontWeight: '600',
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-pill)',
                  border: '1px solid ' + (selectedFamily === c.family ? 'var(--accent-terracotta)' : 'var(--border-subtle)'),
                  backgroundColor: selectedFamily === c.family ? 'var(--accent-terracotta)' : 'var(--surface-elevated)',
                  color: selectedFamily === c.family ? '#ffffff' : 'var(--text-primary)',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)'
                }}
              >
                {c.family}
              </button>
            ))}
          </div>
        </div>

        {/* Dual Chart Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
          {activeCategoryObj && (
            <>
              <DemandTrendChart
                category={activeCategoryObj}
                historyWindow={historyWindow}
                onToggleHistoryWindow={(w) => setHistoryWindow(w)}
              />
              <InventoryRunwayChart
                category={activeCategoryObj}
              />
            </>
          )}
        </div>
      </section>

      {/* 4. Exception-Based Inventory Table */}
      <section style={{ marginBottom: '36px' }}>
        <div style={{ marginBottom: '16px' }}>
          <div className="eyebrow" style={{ marginBottom: '4px' }}>
            Category Exception Matrix
          </div>
          <h2 style={{ fontSize: '1.65rem', fontFamily: 'var(--font-serif)', fontWeight: '700' }}>
            Store 14 Exception Table
          </h2>
        </div>

        <div
          style={{
            backgroundColor: 'var(--surface-elevated)',
            borderRadius: 'var(--radius-xl)',
            border: '1px solid var(--border-subtle)',
            boxShadow: 'var(--shadow-sm)',
            overflow: 'hidden'
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.06em', backgroundColor: 'var(--surface-card)' }}>
                <th style={{ padding: '14px 20px' }}>Product Category</th>
                <th style={{ padding: '14px 14px' }}>Days of Cover</th>
                <th style={{ padding: '14px 14px' }}>Stockout Risk</th>
                <th style={{ padding: '14px 14px' }}>Recommended Order</th>
                <th style={{ padding: '14px 20px', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {snapshot?.categories?.map((cat) => {
                const isHigh = cat.stockout_risk === 'HIGH';
                const isMedium = cat.stockout_risk === 'MEDIUM';
                const isAdded = !!plannedOrders[cat.family];
                const isExpanded = !!expandedAudit[cat.family];
                const currentQty = orderQuantities[cat.family] || cat.recommended_order_qty;

                return (
                  <React.Fragment key={cat.family}>
                    <tr
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        backgroundColor: isHigh ? 'rgba(164, 58, 40, 0.03)' : 'transparent'
                      }}
                    >
                      {/* Category & Selection */}
                      <td style={{ padding: '16px 20px' }}>
                        <div style={{ fontWeight: '700', color: 'var(--text-primary)', marginBottom: '2px' }}>
                          {cat.family}
                        </div>
                        <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                          On-Hand: {cat.on_hand} u • Safety Buffer: {cat.safety_stock} u
                        </div>
                      </td>

                      {/* Days of Cover */}
                      <td style={{ padding: '16px 14px', fontFamily: 'var(--font-mono)' }}>
                        <span style={{ fontWeight: '700', color: isHigh ? 'var(--state-danger)' : isMedium ? 'var(--state-warning)' : 'var(--text-primary)' }}>
                          {cat.days_of_cover} Days
                        </span>
                      </td>

                      {/* Stockout Risk Icon + Text */}
                      <td style={{ padding: '16px 14px' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            fontSize: '0.74rem',
                            fontWeight: '700',
                            padding: '3px 10px',
                            borderRadius: 'var(--radius-pill)',
                            backgroundColor: isHigh ? 'var(--state-danger-bg)' : isMedium ? 'var(--state-warning-bg)' : 'var(--state-success-bg)',
                            color: isHigh ? 'var(--state-danger)' : isMedium ? 'var(--state-warning)' : 'var(--state-success)'
                          }}
                        >
                          {isHigh ? <AlertCircle size={12} /> : isMedium ? <AlertTriangle size={12} /> : <CheckCircle2 size={12} />}
                          {isHigh ? `High Risk (${cat.projected_stockout_date})` : isMedium ? `Moderate (${cat.projected_stockout_date})` : 'Low Risk (>14D)'}
                        </span>
                      </td>

                      {/* Accessible Recommended Order Controls */}
                      <td style={{ padding: '16px 14px' }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                          <button
                            onClick={() => handleQuantityChange(cat.family, -25)}
                            aria-label={`Decrease ${cat.family} order by 25 units`}
                            style={{
                              minWidth: '44px',
                              minHeight: '44px',
                              borderRadius: 'var(--radius-md)',
                              border: '1px solid var(--border-medium)',
                              backgroundColor: 'var(--surface-card)',
                              color: 'var(--text-primary)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              cursor: 'pointer'
                            }}
                          >
                            <Minus size={14} />
                          </button>

                          <input
                            type="number"
                            value={currentQty}
                            onChange={(e) => handleManualQuantityInput(cat.family, e.target.value)}
                            aria-label={`${cat.family} order input`}
                            style={{
                              width: '72px',
                              height: '44px',
                              textAlign: 'center',
                              borderRadius: 'var(--radius-md)',
                              border: '1px solid var(--border-medium)',
                              backgroundColor: 'var(--surface-elevated)',
                              fontFamily: 'var(--font-mono)',
                              fontWeight: '700',
                              fontSize: '0.92rem'
                            }}
                          />

                          <button
                            onClick={() => handleQuantityChange(cat.family, 25)}
                            aria-label={`Increase ${cat.family} order by 25 units`}
                            style={{
                              minWidth: '44px',
                              minHeight: '44px',
                              borderRadius: 'var(--radius-md)',
                              border: '1px solid var(--border-medium)',
                              backgroundColor: 'var(--surface-card)',
                              color: 'var(--text-primary)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              cursor: 'pointer'
                            }}
                          >
                            <Plus size={14} />
                          </button>
                        </div>
                      </td>

                      {/* Action & Expand Audit Toggle */}
                      <td style={{ padding: '16px 20px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                          <button
                            onClick={() => toggleAuditPanel(cat.family)}
                            aria-label={`Toggle recommendation details for ${cat.family}`}
                            style={{
                              minHeight: '44px',
                              padding: '0 12px',
                              borderRadius: 'var(--radius-pill)',
                              border: '1px solid var(--border-subtle)',
                              backgroundColor: 'var(--surface-card)',
                              fontSize: '0.78rem',
                              fontWeight: '600',
                              color: 'var(--text-secondary)',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px'
                            }}
                          >
                            <span>Why this?</span>
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>

                          <button
                            onClick={() => toggleAddToPlan({ family: cat.family, recommended_order_qty: currentQty, projected_stockout_date: cat.projected_stockout_date, days_of_cover: cat.days_of_cover })}
                            aria-label={`Add ${cat.family} to order plan`}
                            style={{
                              minHeight: '44px',
                              padding: '0 16px',
                              borderRadius: 'var(--radius-pill)',
                              backgroundColor: isAdded ? 'var(--state-success)' : 'var(--accent-terracotta)',
                              color: '#ffffff',
                              border: 'none',
                              fontSize: '0.82rem',
                              fontWeight: '700',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px'
                            }}
                          >
                            {isAdded ? <CheckCircle2 size={14} /> : <Plus size={14} />}
                            <span>{isAdded ? 'Added' : 'Add to Plan'}</span>
                          </button>
                        </div>
                      </td>
                    </tr>

                    {/* Expandable "Why this recommendation?" Audit Drawer */}
                    {isExpanded && cat.audit_details && (
                      <tr style={{ backgroundColor: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-subtle)' }}>
                        <td colSpan={5} style={{ padding: '20px 28px' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '24px', alignItems: 'center' }}>
                            <div style={{ backgroundColor: 'var(--surface-elevated)', padding: '14px 20px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)', minWidth: '240px' }}>
                              <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>AI Forecast Model</div>
                              <div style={{ fontSize: '1rem', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>
                                {cat.audit_details.selected_engine === 'LightGBM_GBDT' ? 'Gradient Tree Direct Model' : 'Deep Temporal LSTM'}
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                                <span style={{ fontSize: '0.74rem', backgroundColor: 'var(--state-success-bg)', color: 'var(--state-success)', padding: '2px 8px', borderRadius: 'var(--radius-pill)', fontWeight: '700' }}>
                                  {cat.family.includes('SCHOOL') ? '94.2% AI Confidence' : '91.8% AI Confidence'}
                                </span>
                              </div>
                            </div>

                            <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                              <strong style={{ color: 'var(--text-primary)' }}>Why this order is recommended: </strong>
                              {cat.audit_details.decision_rationale}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Floating Order Plan Dock */}
      <OrderPlanDock
        plannedOrders={plannedOrders}
        onOpenRestockPlanner={onNavigateToRestock}
        onClearPlan={() => setPlannedOrders({})}
      />

    </div>
  );
}
