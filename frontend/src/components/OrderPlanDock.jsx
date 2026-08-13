import React from 'react';
import { ShoppingBag, ArrowRight, CheckCircle2, X } from 'lucide-react';

export default function OrderPlanDock({ plannedOrders, onOpenRestockPlanner, onClearPlan }) {
  const orderList = Object.values(plannedOrders || {});
  if (orderList.length === 0) return null;

  const totalUnits = orderList.reduce((sum, item) => sum + (item.qty || 0), 0);

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 80,
        width: 'min(780px, 94vw)',
        backgroundColor: 'var(--text-primary)',
        color: '#ffffff',
        padding: '16px 24px',
        borderRadius: 'var(--radius-pill)',
        boxShadow: '0 8px 32px rgba(45, 42, 38, 0.35)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        animation: 'fadeIn 250ms ease-out'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div
          style={{
            width: '38px',
            height: '38px',
            borderRadius: '50%',
            backgroundColor: 'var(--accent-terracotta)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ffffff'
          }}
        >
          <ShoppingBag size={18} />
        </div>
        <div>
          <div style={{ fontSize: '0.92rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>{orderList.length} Categories Queued</span>
            <span style={{ fontSize: '0.74rem', backgroundColor: 'rgba(255,255,255,0.2)', padding: '2px 8px', borderRadius: 'var(--radius-pill)' }}>
              {totalUnits.toLocaleString()} Total Units
            </span>
          </div>
          <div style={{ fontSize: '0.74rem', color: 'rgba(255,255,255,0.7)', marginTop: '2px' }}>
            Ready for warehouse dispatch manifest transmission
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <button
          onClick={onClearPlan}
          title="Clear order plan"
          style={{
            background: 'none',
            border: 'none',
            color: 'rgba(255,255,255,0.6)',
            cursor: 'pointer',
            padding: '6px'
          }}
        >
          <X size={16} />
        </button>

        <button
          onClick={onOpenRestockPlanner}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 20px',
            borderRadius: 'var(--radius-pill)',
            backgroundColor: 'var(--accent-terracotta)',
            color: '#ffffff',
            border: 'none',
            fontWeight: '700',
            fontSize: '0.86rem',
            cursor: 'pointer',
            boxShadow: '0 4px 14px rgba(196, 93, 62, 0.4)',
            transition: 'all var(--transition-fast)'
          }}
        >
          <span>Transmit in Restock Planner</span>
          <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
}
