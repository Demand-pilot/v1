import React, { useMemo } from 'react';
import { AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react';

export default function InventoryRunwayChart({ category }) {
  if (!category) return null;

  const onHand = category.on_hand || 480;
  const safetyStock = category.safety_stock || 320;
  const rop = category.reorder_point || 1345;
  const forecasts = category.forecast_16d || [];

  // Compute daily inventory decay over 16 days
  const runwayTimeline = useMemo(() => {
    let running = onHand;
    let stockoutDay = null;

    const days = forecasts.map((dailyDemand, idx) => {
      running = Math.max(0, running - dailyDemand);
      if (running <= safetyStock && stockoutDay === null) {
        stockoutDay = idx + 1;
      }
      return {
        day: idx + 1,
        date: `Aug ${16 + idx}`,
        demand: dailyDemand,
        stock: running,
        isBelowSafety: running <= safetyStock
      };
    });

    return { days, stockoutDay };
  }, [onHand, safetyStock, forecasts]);

  const maxVal = Math.max(onHand, rop, safetyStock * 1.5, 100) * 1.15;
  const minVal = 0;

  const svgWidth = 840;
  const svgHeight = 220;
  const padding = { top: 25, right: 30, bottom: 40, left: 55 };
  const plotWidth = svgWidth - padding.left - padding.right;
  const plotHeight = svgHeight - padding.top - padding.bottom;

  const getX = (index) => padding.left + (index / (forecasts.length - 1)) * plotWidth;
  const getY = (val) => padding.top + plotHeight - ((val - minVal) / (maxVal - minVal)) * plotHeight;

  // Runway stock decay curve path
  const stockCurvePath = useMemo(() => {
    if (runwayTimeline.days.length === 0) return '';
    return runwayTimeline.days.map((d, idx) => `${idx === 0 ? 'M' : 'L'} ${getX(idx).toFixed(1)} ${getY(d.stock).toFixed(1)}`).join(' ');
  }, [runwayTimeline, maxVal]);

  const ropY = getY(rop);
  const ssY = getY(safetyStock);

  return (
    <div style={{ backgroundColor: 'var(--surface-elevated)', padding: '24px', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)' }}>
      
      {/* Header & Stockout Alert Pill */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', fontWeight: '700', marginBottom: '2px' }}>
            16-Day Inventory Runway & Stockout Prediction
          </div>
          <h3 style={{ fontSize: '1.25rem', fontFamily: 'var(--font-serif)', fontWeight: '700' }}>
            Stock Decay vs Safety Buffer Thresholds
          </h3>
        </div>

        {/* Stockout Callout Badge */}
        {runwayTimeline.stockoutDay ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'var(--state-danger-bg)',
              color: 'var(--state-danger)',
              padding: '6px 14px',
              borderRadius: 'var(--radius-pill)',
              fontSize: '0.82rem',
              fontWeight: '700',
              border: '1px solid rgba(164, 58, 40, 0.2)'
            }}
          >
            <ShieldAlert size={15} />
            <span>Stockout Projected: Aug {15 + runwayTimeline.stockoutDay} (Day +{runwayTimeline.stockoutDay})</span>
          </div>
        ) : (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'var(--state-success-bg)',
              color: 'var(--state-success)',
              padding: '6px 14px',
              borderRadius: 'var(--radius-pill)',
              fontSize: '0.82rem',
              fontWeight: '600'
            }}
          >
            <CheckCircle2 size={15} />
            <span>Buffer Secure Across 16 Days</span>
          </div>
        )}
      </div>

      {/* SVG Canvas */}
      <div style={{ position: 'relative', width: '100%', overflowX: 'auto' }}>
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: '100%', height: 'auto', minWidth: '600px' }}>
          
          {/* Reorder Point (ROP) Threshold */}
          {rop <= maxVal && (
            <g>
              <line
                x1={padding.left}
                y1={ropY}
                x2={svgWidth - padding.right}
                y2={ropY}
                stroke="var(--state-warning)"
                strokeDasharray="5 3"
                strokeWidth="1.5"
              />
              <text x={svgWidth - padding.right} y={ropY - 4} textAnchor="end" fontSize="10" fontWeight="700" fill="var(--state-warning)">
                Reorder Point (ROP: {rop} u)
              </text>
            </g>
          )}

          {/* Safety Stock (SS) Threshold */}
          <line
            x1={padding.left}
            y1={ssY}
            x2={svgWidth - padding.right}
            y2={ssY}
            stroke="var(--state-danger)"
            strokeDasharray="4 3"
            strokeWidth="1.5"
          />
          <text x={svgWidth - padding.right} y={ssY - 4} textAnchor="end" fontSize="10" fontWeight="700" fill="var(--state-danger)">
            Safety Stock Buffer (SS: {safetyStock} u)
          </text>

          {/* Runway Stock Decay Curve */}
          <path
            d={stockCurvePath}
            fill="none"
            stroke="var(--text-primary)"
            strokeWidth="2.8"
            strokeLinecap="round"
          />

          {/* Daily Points */}
          {runwayTimeline.days.map((d, idx) => {
            const x = getX(idx);
            const y = getY(d.stock);
            const isStockoutPoint = idx + 1 === runwayTimeline.stockoutDay;

            return (
              <g key={idx}>
                <circle
                  cx={x}
                  cy={y}
                  r={isStockoutPoint ? '7' : '4'}
                  fill={isStockoutPoint ? 'var(--state-danger)' : d.isBelowSafety ? 'var(--state-warning)' : 'var(--surface-elevated)'}
                  stroke={isStockoutPoint ? 'var(--surface-elevated)' : 'var(--text-primary)'}
                  strokeWidth="2"
                />
                {isStockoutPoint && (
                  <text x={x} y={y - 12} textAnchor="middle" fontSize="10" fontWeight="700" fill="var(--state-danger)">
                    Stockout Breach
                  </text>
                )}
              </g>
            );
          })}

          {/* X Axis Date Labels */}
          {runwayTimeline.days.map((d, idx) => {
            if (idx % 2 === 0 || idx === runwayTimeline.days.length - 1) {
              return (
                <text key={idx} x={getX(idx)} y={svgHeight - 12} textAnchor="middle" fontSize="10" fill="var(--text-muted)">
                  {d.date}
                </text>
              );
            }
            return null;
          })}

          {/* Y Axis Zero Line */}
          <line
            x1={padding.left}
            y1={getY(0)}
            x2={svgWidth - padding.right}
            y2={getY(0)}
            stroke="var(--border-medium)"
            strokeWidth="1"
          />
          <text x={padding.left - 8} y={getY(0) + 4} textAnchor="end" fontSize="10" fill="var(--text-muted)" fontFamily="var(--font-mono)">
            0 u
          </text>
        </svg>
      </div>

    </div>
  );
}
