import React, { useState, useEffect } from 'react';
import { 
  Store, 
  Layers, 
  Globe, 
  ArrowRight, 
  Sparkles, 
  ShieldCheck, 
  TrendingUp, 
  Boxes,
  Zap,
  Move3d,
  ChevronDown,
  Truck,
  CheckCircle2
} from 'lucide-react';
import AutoAnimatedPointer from '../components/AutoAnimatedPointer';
import SupermarketWebGLHero from '../components/SupermarketWebGLHero';

export default function LoginPage({ onSelectPersona }) {
  const [isUserInteracting, setIsUserInteracting] = useState(false);
  const [hoveredCard, setHoveredCard] = useState(null);
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const height = document.documentElement.scrollHeight - window.innerHeight;
      if (height > 0) {
        setScrollProgress(scrollY / height);
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const personas = [
    {
      id: 'store_manager',
      role: 'Store Manager',
      subtitle: 'Operational Day-to-Day Console',
      icon: Store,
      badge: 'Interactive Demo • Store 14 (Quito Sierra)',
      highlightColor: 'var(--accent-terracotta)',
      description: 'Daily stockout risk mitigation, payday rush planning (+8.0%), Sierra back-to-school surges (+145%), and grounded AI copilot.',
      capabilities: [
        'Priority Action Queue with Stockout Warnings',
        'Historical Actuals vs 16-Day Forecast Timeline',
        'Dynamic Restock Planner & Purchase Order Transmission',
        'Grounded AI Copilot with 94.2% ML Confidence'
      ],
      actionText: 'Launch Store Manager Suite'
    },
    {
      id: 'supply_chain',
      role: 'Supply Chain Planner',
      subtitle: 'Tactical Horizon Distribution',
      icon: Layers,
      badge: '1,782 Series Matrix',
      highlightColor: '#355e7a',
      description: 'Multi-origin 16-day forecast grid across Ecuador, lead-time safety stock tuning, and automated model tournament selection.',
      capabilities: [
        '16-Day Forecast Grid across 54 Stores',
        'Safety Stock & Lead Time (95% Service Level)',
        'Model Tournament Scorecard (0.4239 Pooled RMSLE)',
        'Permanent Zero Series Detection (53 series)'
      ],
      actionText: 'Access Tactical Planner Grid'
    },
    {
      id: 'executive',
      role: 'Executive Leadership',
      subtitle: 'Strategic Macro Performance',
      icon: Globe,
      badge: '54 Stores Nationwide',
      highlightColor: '#2d6a4f',
      description: 'Macro retail footprint analytics, promotional lift ROI (20.4% → 44.1%), and national holding cost optimization.',
      capabilities: [
        '3D Ecuador Store Visualizer & Risk Scores',
        'National Forecast Volume: 685,000 Units',
        'Projected Holding Savings: $142,500 USD',
        'Macro Promotion Elasticity Analytics'
      ],
      actionText: 'Enter Executive Overview'
    }
  ];

  return (
    <div
      onMouseMove={() => setIsUserInteracting(true)}
      style={{
        minHeight: '100vh',
        backgroundColor: '#faf8f5',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        overflowX: 'hidden'
      }}
    >
      {/* Background Ambient Glow */}
      <div
        style={{
          position: 'fixed',
          top: '-15%',
          right: '-10%',
          width: '800px',
          height: '800px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(196, 93, 62, 0.05) 0%, rgba(250, 248, 245, 0) 70%)',
          pointerEvents: 'none',
          zIndex: 0
        }}
      />

      {/* Auto Animated Guide Cursor */}
      <AutoAnimatedPointer isUserInteracting={isUserInteracting} />

      {/* Top Header */}
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 40,
          backgroundColor: 'rgba(250, 248, 245, 0.9)',
          backdropFilter: 'blur(16px)',
          borderBottom: '1px solid rgba(45, 42, 38, 0.05)',
          padding: '18px 0'
        }}
      >
        <div className="app-container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: 'var(--accent-terracotta)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
                boxShadow: '0 2px 8px rgba(196, 93, 62, 0.25)'
              }}
            >
              <Boxes size={18} />
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: '1.35rem', fontWeight: '700', letterSpacing: '-0.02em', lineHeight: 1 }}>
                Demand<span style={{ color: 'var(--accent-terracotta)' }}>Pilot</span>
              </div>
              <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--text-muted)', fontWeight: '600' }}>
                Retail Operating System
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: 'rgba(45, 42, 38, 0.04)',
                padding: '6px 14px',
                borderRadius: 'var(--radius-pill)',
                fontSize: '0.78rem',
                color: 'var(--text-secondary)',
                fontWeight: '600'
              }}
            >
              <ShieldCheck size={14} color="var(--state-success)" />
              <span>0.4239 Pooled RMSLE (+27.65% Lift)</span>
            </span>

            <a
              href="#personas"
              style={{
                fontSize: '0.82rem',
                fontWeight: '600',
                color: 'var(--accent-terracotta)',
                padding: '6px 14px',
                borderRadius: 'var(--radius-pill)',
                transition: 'all var(--transition-fast)'
              }}
            >
              Skip to Workspaces ↓
            </a>
          </div>
        </div>
      </header>

      {/* Chapter 1: Hero & 3D WebGL Supermarket Elevator */}
      <section style={{ padding: '64px 0 96px', position: 'relative' }}>
        <div className="app-container">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '48px', alignItems: 'center' }}>
            
            <div>
              <div className="eyebrow" style={{ marginBottom: '14px' }}>
                Chapter 01 • The Retail Reality
              </div>
              <h1 style={{ fontSize: 'clamp(2.4rem, 2rem + 2vw, 3.6rem)', lineHeight: 1.12, marginBottom: '22px' }}>
                What if your grocery shelves predicted tomorrow’s surge before it happened?
              </h1>
              <p className="body-text" style={{ fontSize: '1.1rem', lineHeight: 1.65, marginBottom: '32px', maxWidth: '580px' }}>
                Every August in Quito Sierra, School Supplies surge by <strong>+145%</strong>. On the 15th and 30th nationwide, salary paydays spike grocery foot traffic by <strong>+8.0%</strong>. DemandPilot grounds replenishment on real transaction physics.
              </p>

              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <a
                  href="#personas"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '14px 28px',
                    borderRadius: 'var(--radius-pill)',
                    backgroundColor: 'var(--accent-terracotta)',
                    color: '#ffffff',
                    fontWeight: '700',
                    fontSize: '0.92rem',
                    boxShadow: '0 4px 16px rgba(196, 93, 62, 0.35)',
                    transition: 'all var(--transition-fast)'
                  }}
                >
                  <span>Explore Workspaces</span>
                  <ArrowRight size={16} />
                </a>

                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  Scroll down to elevate the store ↓
                </div>
              </div>
            </div>

            {/* Interactive 3D WebGL Supermarket Canvas */}
            <div style={{ position: 'relative' }}>
              <SupermarketWebGLHero scrollProgress={scrollProgress} />
            </div>

          </div>
        </div>
      </section>

      {/* Chapter 2: The Neural Engine (3,000,888 Real Transactions) */}
      <section style={{ padding: '80px 0', backgroundColor: 'rgba(238, 232, 223, 0.45)', borderTop: '1px solid rgba(45, 42, 38, 0.05)', borderBottom: '1px solid rgba(45, 42, 38, 0.05)' }}>
        <div className="app-container">
          <div style={{ maxWidth: '720px', margin: '0 auto 56px', textAlign: 'center' }}>
            <div className="eyebrow" style={{ marginBottom: '10px' }}>
              Chapter 02 • Production Validation
            </div>
            <h2 style={{ fontSize: '2.2rem', fontFamily: 'var(--font-serif)', fontWeight: '700', marginBottom: '16px' }}>
              Grounded in 3,000,888 Real Grocery Transactions.
            </h2>
            <p className="body-text" style={{ fontSize: '1.05rem', lineHeight: 1.6 }}>
              Evaluated across 8 rolling 16-day forecast origins covering 54 stores and 33 product families in Ecuador with zero future data leakage.
            </p>
          </div>

          {/* 3 Metric Pillars */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '32px' }}>
            
            <div style={{ backgroundColor: 'var(--surface-elevated)', padding: '32px', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-sm)' }}>
              <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', fontWeight: '700', marginBottom: '8px' }}>
                Forecast Precision
              </div>
              <div style={{ fontSize: '2.4rem', fontFamily: 'var(--font-serif)', fontWeight: '700', color: 'var(--state-success)', lineHeight: 1 }}>
                0.4239
              </div>
              <div style={{ fontSize: '0.84rem', color: 'var(--state-success)', fontWeight: '600', marginTop: '8px' }}>
                +27.65% Lift vs 56-Day Baseline
              </div>
              <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginTop: '12px', lineHeight: 1.55 }}>
                Direct LightGBM model captures promotion density shifts from 20.4% baseline up to 44.1% test coverage.
              </p>
            </div>

            <div style={{ backgroundColor: 'var(--surface-elevated)', padding: '32px', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-sm)' }}>
              <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', fontWeight: '700', marginBottom: '8px' }}>
                AI Model Confidence
              </div>
              <div style={{ fontSize: '2.4rem', fontFamily: 'var(--font-serif)', fontWeight: '700', color: 'var(--text-primary)', lineHeight: 1 }}>
                94.2%
              </div>
              <div style={{ fontSize: '0.84rem', color: 'var(--accent-terracotta)', fontWeight: '600', marginTop: '8px' }}>
                High-Accuracy SLA Guarantee
              </div>
              <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginTop: '12px', lineHeight: 1.55 }}>
                Deep temporal LSTM auto-regressively predicts high-turnover smooth staples during bi-weekly salary cycles.
              </p>
            </div>

            <div style={{ backgroundColor: 'var(--surface-elevated)', padding: '32px', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-sm)' }}>
              <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', fontWeight: '700', marginBottom: '8px' }}>
                Capital Efficiency
              </div>
              <div style={{ fontSize: '2.4rem', fontFamily: 'var(--font-serif)', fontWeight: '700', color: 'var(--state-info)', lineHeight: 1 }}>
                $142.5k
              </div>
              <div style={{ fontSize: '0.84rem', color: 'var(--state-info)', fontWeight: '600', marginTop: '8px' }}>
                -14.2% Inventory Holding Waste
              </div>
              <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginTop: '12px', lineHeight: 1.55 }}>
                Optimized safety buffers and lead-time reorder points prevent both shelf stockouts and over-ordering.
              </p>
            </div>

          </div>
        </div>
      </section>

      {/* Chapter 3: Interactive Persona Workspace Cards */}
      <section id="personas" style={{ padding: '96px 0 112px' }}>
        <div className="app-container">
          
          <div style={{ textAlign: 'center', maxWidth: '640px', margin: '0 auto 48px' }}>
            <div className="eyebrow" style={{ marginBottom: '8px' }}>
              Chapter 03 • Step into Your Role
            </div>
            <h2 style={{ fontSize: '2.4rem', fontFamily: 'var(--font-serif)', fontWeight: '700', marginBottom: '12px' }}>
              Select Operational Workspace
            </h2>
            <p className="body-text" style={{ fontSize: '1rem' }}>
              Choose a tailored perspective to inspect daily operations, tactical distribution grids, or macro strategy.
            </p>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: '32px',
              position: 'relative'
            }}
          >
            {personas.map((p) => {
              const IconComp = p.icon;
              const isHovered = hoveredCard === p.id;
              const isStoreMgr = p.id === 'store_manager';

              return (
                <div
                  key={p.id}
                  onMouseEnter={() => setHoveredCard(p.id)}
                  onMouseLeave={() => setHoveredCard(null)}
                  style={{
                    backgroundColor: isStoreMgr ? 'var(--surface-elevated)' : 'rgba(238, 232, 223, 0.5)',
                    borderRadius: 'var(--radius-xl)',
                    padding: '36px 32px',
                    border: isStoreMgr 
                      ? '2px solid var(--accent-terracotta)' 
                      : '1px solid rgba(45, 42, 38, 0.08)',
                    boxShadow: isStoreMgr 
                      ? 'var(--shadow-lg)' 
                      : isHovered 
                      ? 'var(--shadow-md)' 
                      : 'var(--shadow-sm)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '28px',
                    position: 'relative',
                    transition: 'all var(--transition-normal)',
                    transform: isHovered ? 'translateY(-6px)' : 'none'
                  }}
                >
                  {/* Featured Badge */}
                  {isStoreMgr && (
                    <div
                      style={{
                        position: 'absolute',
                        top: '-12px',
                        right: '24px',
                        backgroundColor: 'var(--accent-terracotta)',
                        color: '#ffffff',
                        fontSize: '0.72rem',
                        fontWeight: '700',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        padding: '4px 14px',
                        borderRadius: 'var(--radius-pill)',
                        boxShadow: '0 2px 8px rgba(196, 93, 62, 0.4)'
                      }}
                    >
                      Store Manager Console
                    </div>
                  )}

                  <div>
                    {/* Icon & Badge */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
                      <div
                        style={{
                          width: '46px',
                          height: '46px',
                          borderRadius: '12px',
                          backgroundColor: isStoreMgr ? 'var(--accent-terracotta)' : 'var(--surface-elevated)',
                          color: isStoreMgr ? '#ffffff' : p.highlightColor,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          boxShadow: 'var(--shadow-sm)'
                        }}
                      >
                        <IconComp size={22} />
                      </div>

                      <span
                        style={{
                          fontSize: '0.74rem',
                          fontWeight: '600',
                          padding: '4px 12px',
                          borderRadius: 'var(--radius-pill)',
                          backgroundColor: isStoreMgr ? 'var(--accent-terracotta-subtle)' : 'rgba(45, 42, 38, 0.05)',
                          color: isStoreMgr ? 'var(--accent-terracotta)' : 'var(--text-secondary)'
                        }}
                      >
                        {p.badge}
                      </span>
                    </div>

                    {/* Titles */}
                    <h3 style={{ fontSize: '1.55rem', marginBottom: '6px', fontFamily: 'var(--font-serif)', fontWeight: '700' }}>
                      {p.role}
                    </h3>
                    <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', fontWeight: '500', marginBottom: '16px' }}>
                      {p.subtitle}
                    </div>
                    <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '24px' }}>
                      {p.description}
                    </p>

                    {/* Capabilities */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {p.capabilities.map((cap, cIdx) => (
                        <div key={cIdx} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                          <CheckCircle2 size={14} color="var(--accent-terracotta)" />
                          <span>{cap}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Launch CTA */}
                  <button
                    onClick={() => onSelectPersona(p.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '10px',
                      width: '100%',
                      padding: '14px 20px',
                      borderRadius: 'var(--radius-pill)',
                      backgroundColor: isStoreMgr ? 'var(--accent-terracotta)' : 'var(--text-primary)',
                      color: '#ffffff',
                      border: 'none',
                      fontSize: '0.92rem',
                      fontWeight: '700',
                      cursor: 'pointer',
                      boxShadow: isStoreMgr ? '0 4px 16px rgba(196, 93, 62, 0.35)' : 'none',
                      transition: 'all var(--transition-fast)'
                    }}
                    onMouseEnter={(e) => {
                      if (!isStoreMgr) e.currentTarget.style.backgroundColor = 'var(--accent-terracotta)';
                    }}
                    onMouseLeave={(e) => {
                      if (!isStoreMgr) e.currentTarget.style.backgroundColor = 'var(--text-primary)';
                    }}
                  >
                    <span>{p.actionText}</span>
                    <ArrowRight size={16} />
                  </button>
                </div>
              );
            })}
          </div>

        </div>
      </section>

      {/* Clean Footer */}
      <footer style={{ padding: '24px 0', borderTop: '1px solid rgba(45, 42, 38, 0.06)', backgroundColor: '#faf8f5' }}>
        <div className="app-container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          <div>DemandPilot • Grounded Retail AI for Corporación Favorita Ecuador Data</div>
          <div>Strict Leakage-Safe Multi-Origin Evaluation Architecture</div>
        </div>
      </footer>
    </div>
  );
}
