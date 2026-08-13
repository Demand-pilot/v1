import React, { useState, useMemo } from 'react';
import { Calendar, Tag, Info } from 'lucide-react';

export default function DemandTrendChart({ category, historyWindow = 28, onToggleHistoryWindow }) {
  const [hoveredIndex, setHoveredIndex] = useState(null);

  if (!category) return null;

  const actuals = historyWindow === 56 ? (category.actual_history_56d || []) : (category.actual_history_28d || []);
  const forecasts = category.forecast_16d || [];
  const lowerBand = category.forecast_lower_p10 || forecasts.map(v => v * 0.85);
  const upperBand = category.forecast_upper_p90 || forecasts.map(v => v * 1.15);
  const events = category.event_annotations || [];

  const totalPoints = actuals.length + forecasts.length;
  const maxVal = Math.max(...actuals, ...forecasts, ...upperBand, 50) * 1.15;
  const minVal = 0;

  // Chart dimensions
  const svgWidth = 840;
  const svgHeight = 260;
  const padding = { top: 20, right: 30, bottom: 40, left: 45 };
  const plotWidth = svgWidth - padding.left - padding.right;
  const plotHeight = svgHeight - padding.top - padding.bottom;

  const getX = (index) => padding.left + (index / (totalPoints - 1)) * plotWidth;
  const getY = (val) => padding.top + plotHeight - ((val - minVal) / (maxVal - minVal)) * plotHeight;

  // Actuals path
  const actualsPath = useMemo(() => {
    if (actuals.length === 0) return '';
    return actuals.map((val, idx) => `${idx === 0 ? 'M' : 'L'} ${getX(idx).toFixed(1)} ${getY(val).toFixed(1)}`).join(' ');
  }, [actuals, maxVal]);

  // Forecast path (starts at last actual point)
  const forecastPath = useMemo(() => {
    if (forecasts.length === 0 || actuals.length === 0) return '';
    const lastActualX = getX(actuals.length - 1);
    const lastActualY = getY(actuals[actuals.length - 1]);
    const fPoints = forecasts.map((val, idx) => `L ${getX(actuals.length + idx).toFixed(1)} ${getY(val).toFixed(1)}`).join(' ');
    return `M ${lastActualX.toFixed(1)} ${lastActualY.toFixed(1)} ${fPoints}`;
  }, [actuals, forecasts, maxVal]);

  // Confidence ribbon polygon path
  const confidenceBandPath = useMemo(() => {
    if (forecasts.length === 0 || actuals.length === 0) return '';
    const topPoints = upperBand.map((val, idx) => `${getX(actuals.length + idx).toFixed(1)},${getY(val).toFixed(1)}`);
    const bottomPoints = lowerBand.map((val, idx) => `${getX(actuals.length + idx).toFixed(1)},${getY(val).toFixed(1)}`).reverse();
    return `M ${topPoints.join(' L ')} L ${bottomPoints.join(' L ')} Z`;
  }, [actuals, upperBand, lowerBand, maxVal]);

  const cutoffX = getX(actuals.length - 1);

  // Hover data point calculation
  const hoverData = useMemo(() => {
    if (hoveredIndex === null) return null;
    const isActual = hoveredIndex < actuals.length;
    const val = isActual ? actuals[hoveredIndex] : forecasts[hoveredIndex - actuals.length];
    const x = getX(hoveredIndex);
    const y = getY(val);
    
    // Check if event annotation exists near this point
    const fcDay = hoveredIndex - actuals.length + 1;
    let eventLabel = null;
    if (fcDay === 1) eventLabel = 'Aug 16 Bi-Weekly Payday Peak';
    if (fcDay === 10 && category.family.includes('SCHOOL')) eventLabel = 'Aug 25 Sierra School Promo Ramp';

    return {
      index: hoveredIndex,
      isActual,
      val,
      x,
      y,
      eventLabel,
      dateLabel: isActual ? `Past Day -${actuals.length - hoveredIndex}` : `Horizon Day +${fcDay} (Aug ${15 + fcDay})`
    };
  }, [hoveredIndex, actuals, forecasts, category]);

  return (
    <div style={{ backgroundColor: 'var(--surface-elevated)', padding: '24px', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)' }}>
      
      {/* Chart Header & History Range Switcher */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', fontWeight: '700', marginBottom: '2px' }}>
            Historical Actuals vs 16-Day Forecast Timeline
          </div>
          <h3 style={{ fontSize: '1.25rem', fontFamily: 'var(--font-serif)', fontWeight: '700' }}>
            {category.family}
          </h3>
        </div>

        {/* History Window Toggle & Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '12px', height: '3px', backgroundColor: 'var(--accent-terracotta)', borderRadius: '2px' }} />
              Actuals (Solid)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '12px', height: '3px', borderTop: '2px dashed var(--accent-terracotta)' }} />
              Forecast (Dashed)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '10px', height: '8px', backgroundColor: 'rgba(196, 93, 62, 0.15)', borderRadius: '2px' }} />
              90% CI Band
            </span>
          </div>

          <div style={{ display: 'flex', backgroundColor: 'var(--surface-card)', padding: '3px', borderRadius: 'var(--radius-pill)', border: '1px solid var(--border-subtle)' }}>
            <button
              onClick={() => onToggleHistoryWindow && onToggleHistoryWindow(28)}
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--radius-pill)',
                border: 'none',
                backgroundColor: historyWindow === 28 ? 'var(--text-primary)' : 'transparent',
                color: historyWindow === 28 ? 'var(--text-inverse)' : 'var(--text-secondary)',
                fontSize: '0.74rem',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              28D History
            </button>
            <button
              onClick={() => onToggleHistoryWindow && onToggleHistoryWindow(56)}
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--radius-pill)',
                border: 'none',
                backgroundColor: historyWindow === 56 ? 'var(--text-primary)' : 'transparent',
                color: historyWindow === 56 ? 'var(--text-inverse)' : 'var(--text-secondary)',
                fontSize: '0.74rem',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              56D History
            </button>
          </div>
        </div>
      </div>

      {/* SVG Plot Canvas */}
      <div style={{ position: 'relative', width: '100%', overflowX: 'auto' }}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          style={{ width: '100%', height: 'auto', minWidth: '600px', overflow: 'visible' }}
          onMouseLeave={() => setHoveredIndex(null)}
        >
          {/* Grid Lines */}
          {[0.25, 0.5, 0.75, 1].map((p, i) => {
            const y = padding.top + plotHeight * (1 - p);
            const val = Math.round(minVal + (maxVal - minVal) * p);
            return (
              <g key={i}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={svgWidth - padding.right}
                  y2={y}
                  stroke="var(--border-subtle)"
                  strokeDasharray="4 4"
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 8}
                  y={y + 4}
                  textAnchor="end"
                  fontSize="10"
                  fill="var(--text-muted)"
                  fontFamily="var(--font-mono)"
                >
                  {val}
                </text>
              </g>
            );
          })}

          {/* As-Of Today Cutoff Line */}
          <line
            x1={cutoffX}
            y1={padding.top}
            x2={cutoffX}
            y2={svgHeight - padding.bottom}
            stroke="var(--text-muted)"
            strokeWidth="1.5"
            strokeDasharray="3 3"
          />
          <text
            x={cutoffX}
            y={padding.top - 6}
            textAnchor="middle"
            fontSize="10"
            fontWeight="700"
            fill="var(--text-secondary)"
            letterSpacing="0.04em"
          >
            Cutoff: Aug 15 (Now)
          </text>

          {/* Confidence Band Polygon */}
          <path
            d={confidenceBandPath}
            fill="rgba(196, 93, 62, 0.14)"
            stroke="none"
          />

          {/* Solid Actuals Line */}
          <path
            d={actualsPath}
            fill="none"
            stroke="var(--accent-terracotta)"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Dashed Forecast Line */}
          <path
            d={forecastPath}
            fill="none"
            stroke="var(--accent-terracotta)"
            strokeWidth="2.4"
            strokeDasharray="6 4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Event Pins on Forecast Horizon */}
          {category.event_annotations?.map((ev, eIdx) => {
            const isPayday = ev.type === 'PAYDAY';
            const targetIdx = actuals.length + (isPayday ? 0 : 9);
            const x = getX(targetIdx);
            const y = getY(forecasts[isPayday ? 0 : 9] || 100);

            return (
              <g key={eIdx} transform={`translate(${x}, ${y - 12})`}>
                <circle r="5" fill={isPayday ? 'var(--state-warning)' : 'var(--accent-terracotta)'} />
                <circle r="9" fill={isPayday ? 'var(--state-warning-bg)' : 'var(--accent-terracotta-subtle)'} />
              </g>
            );
          })}

          {/* Interactive Transparent Hit Columns for Hover */}
          {Array.from({ length: totalPoints }).map((_, idx) => (
            <rect
              key={idx}
              x={getX(idx) - (plotWidth / totalPoints) / 2}
              y={padding.top}
              width={plotWidth / totalPoints}
              height={plotHeight}
              fill="transparent"
              style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHoveredIndex(idx)}
            />
          ))}

          {/* Hover Crosshair & Point Indicator */}
          {hoverData && (
            <g>
              <line
                x1={hoverData.x}
                y1={padding.top}
                x2={hoverData.x}
                y2={svgHeight - padding.bottom}
                stroke="var(--text-primary)"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <circle
                cx={hoverData.x}
                cy={hoverData.y}
                r="6"
                fill="var(--surface-elevated)"
                stroke="var(--accent-terracotta)"
                strokeWidth="2.5"
              />
            </g>
          )}

          {/* X Axis Labels */}
          <text x={padding.left} y={svgHeight - 12} fontSize="10" fill="var(--text-muted)">
            -{historyWindow}D Past
          </text>
          <text x={cutoffX} y={svgHeight - 12} textAnchor="middle" fontSize="10" fontWeight="600" fill="var(--text-primary)">
            Aug 15 (As-Of)
          </text>
          <text x={svgWidth - padding.right} y={svgHeight - 12} textAnchor="end" fontSize="10" fill="var(--text-muted)">
            +16D Horizon (Aug 31)
          </text>
        </svg>

        {/* Floating Tooltip */}
        {hoverData && (
          <div
            style={{
              position: 'absolute',
              top: `${Math.max(10, hoverData.y - 65)}px`,
              left: `${Math.min(svgWidth - 180, Math.max(10, hoverData.x - 75))}px`,
              backgroundColor: 'var(--text-primary)',
              color: '#ffffff',
              padding: '8px 12px',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.78rem',
              boxShadow: 'var(--shadow-md)',
              pointerEvents: 'none',
              zIndex: 30,
              display: 'flex',
              flexDirection: 'column',
              gap: '2px'
            }}
          >
            <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.7)', fontWeight: '500' }}>
              {hoverData.dateLabel}
            </div>
            <div style={{ fontWeight: '700', fontSize: '0.92rem', fontFamily: 'var(--font-mono)' }}>
              {hoverData.val.toFixed(1)} units <span style={{ fontSize: '0.72rem', fontWeight: '400' }}>({hoverData.isActual ? 'Actual' : 'Forecast'})</span>
            </div>
            {hoverData.eventLabel && (
              <div style={{ fontSize: '0.68rem', color: '#ffb703', fontWeight: '600', marginTop: '2px' }}>
                ★ {hoverData.eventLabel}
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
