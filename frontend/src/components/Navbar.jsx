import React from 'react';
import { 
  Store, 
  Sparkles, 
  Layers, 
  Boxes, 
  ShoppingCart, 
  LogOut, 
  ChevronDown 
} from 'lucide-react';

export default function Navbar({ 
  selectedStore = 14,
  onSelectStore,
  activePage, 
  setActivePage, 
  onToggleAICopilot, 
  aiCopilotOpen,
  onLogout 
}) {
  return (
    <header
      style={{
        backgroundColor: 'rgba(250, 248, 245, 0.92)',
        borderBottom: '1px solid rgba(45, 42, 38, 0.05)',
        position: 'sticky',
        top: 0,
        zIndex: 40,
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        transition: 'all var(--transition-normal)'
      }}
    >
      <div className="app-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '64px' }}>
        
        {/* Brand & Store Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div 
            onClick={() => setActivePage('dashboard')}
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '10px' }}
          >
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'var(--accent-terracotta)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
                boxShadow: '0 2px 8px rgba(196, 93, 62, 0.25)'
              }}
            >
              <Boxes size={16} />
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: '1.2rem', fontWeight: '700', letterSpacing: '-0.02em', lineHeight: 1 }}>
                Demand<span style={{ color: 'var(--accent-terracotta)' }}>Pilot</span>
              </div>
            </div>
          </div>

          <div style={{ height: '18px', width: '1px', backgroundColor: 'rgba(45, 42, 38, 0.08)' }} />

          {/* Organic Borderless Store Dropdown */}
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <select
              value={selectedStore}
              onChange={(e) => onSelectStore && onSelectStore(parseInt(e.target.value, 10))}
              aria-label="Select retail store location"
              style={{
                appearance: 'none',
                WebkitAppearance: 'none',
                backgroundColor: 'transparent',
                border: 'none',
                borderRadius: 'var(--radius-pill)',
                padding: '6px 26px 6px 8px',
                fontSize: '0.84rem',
                fontWeight: '600',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                transition: 'background-color var(--transition-fast)'
              }}
              onMouseEnter={(e) => e.target.style.backgroundColor = 'rgba(45, 42, 38, 0.04)'}
              onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
            >
              <option value="14">Store 14 • Quito (Sierra)</option>
              <option value="25">Store 25 • Guayaquil (Coast)</option>
              <option value="52">Store 52 • Manta (Coast)</option>
              <option value="1">Store 1 • Quito (Sierra)</option>
              <option value="44">Store 44 • Quito (Sierra)</option>
            </select>
            <ChevronDown size={13} style={{ position: 'absolute', right: '8px', pointerEvents: 'none', color: 'var(--text-muted)' }} />
          </div>
        </div>

        {/* Center Sleek Tab Navigation with Smooth Underline Transition */}
        <nav style={{ display: 'flex', alignItems: 'center', position: 'relative', gap: '32px' }}>
          
          <button
            onClick={() => setActivePage('dashboard')}
            style={{
              position: 'relative',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.88rem',
              fontWeight: activePage === 'dashboard' ? '700' : '500',
              color: activePage === 'dashboard' ? 'var(--text-primary)' : 'var(--text-muted)',
              padding: '8px 0',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'color var(--transition-normal)'
            }}
          >
            <Layers size={14} color={activePage === 'dashboard' ? 'var(--accent-terracotta)' : 'currentColor'} />
            <span>Store Dashboard</span>
            {activePage === 'dashboard' && (
              <span
                style={{
                  position: 'absolute',
                  bottom: '0px',
                  left: 0,
                  right: 0,
                  height: '2px',
                  backgroundColor: 'var(--accent-terracotta)',
                  borderRadius: '2px',
                  animation: 'fadeIn 200ms ease-out'
                }}
              />
            )}
          </button>

          <button
            onClick={() => setActivePage('restock')}
            style={{
              position: 'relative',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.88rem',
              fontWeight: activePage === 'restock' ? '700' : '500',
              color: activePage === 'restock' ? 'var(--text-primary)' : 'var(--text-muted)',
              padding: '8px 0',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'color var(--transition-normal)'
            }}
          >
            <ShoppingCart size={14} color={activePage === 'restock' ? 'var(--accent-terracotta)' : 'currentColor'} />
            <span>Restock Planner</span>
            {activePage === 'restock' && (
              <span
                style={{
                  position: 'absolute',
                  bottom: '0px',
                  left: 0,
                  right: 0,
                  height: '2px',
                  backgroundColor: 'var(--accent-terracotta)',
                  borderRadius: '2px',
                  animation: 'fadeIn 200ms ease-out'
                }}
              />
            )}
          </button>

        </nav>

        {/* Right Actions: Floating AI Copilot & Subtle Logout */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={onToggleAICopilot}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 16px',
              borderRadius: 'var(--radius-pill)',
              backgroundColor: aiCopilotOpen ? 'var(--accent-terracotta)' : 'transparent',
              color: aiCopilotOpen ? '#ffffff' : 'var(--text-primary)',
              border: aiCopilotOpen ? 'none' : '1px solid rgba(45, 42, 38, 0.1)',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '0.82rem',
              boxShadow: aiCopilotOpen ? '0 2px 10px rgba(196, 93, 62, 0.3)' : 'none',
              transition: 'all var(--transition-normal)'
            }}
            onMouseEnter={(e) => {
              if (!aiCopilotOpen) e.currentTarget.style.backgroundColor = 'rgba(45, 42, 38, 0.04)';
            }}
            onMouseLeave={(e) => {
              if (!aiCopilotOpen) e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <Sparkles size={13} color={aiCopilotOpen ? '#ffffff' : 'var(--accent-terracotta)'} />
            <span>AI Copilot</span>
          </button>

          <button
            onClick={onLogout}
            title="Switch Workspace Persona"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: '500',
              transition: 'color var(--transition-fast)'
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-primary)'}
            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            <LogOut size={13} />
            <span>Switch</span>
          </button>
        </div>

      </div>
    </header>
  );
}
