import React, { useState } from 'react';
import LoginPage from './pages/LoginPage';
import StoreManagerDashboard from './pages/StoreManagerDashboard';
import StoreManagerRestockPlanner from './pages/StoreManagerRestockPlanner';
import SupplyChainPlanner from './pages/SupplyChainPlanner';
import ExecutiveLeadership from './pages/ExecutiveLeadership';
import Navbar from './components/Navbar';
import AICopilotDrawer from './components/AICopilotDrawer';
import { setAuthToken } from './services/api';

export default function App() {
  const [currentPersona, setCurrentPersona] = useState('login'); // 'login', 'store_manager', 'supply_chain', 'executive'
  const [activePage, setActivePage] = useState('dashboard'); // 'dashboard', 'restock'
  const [selectedStore, setSelectedStore] = useState(14);
  const [aiCopilotOpen, setAiCopilotOpen] = useState(false);

  const handleSelectPersona = (personaId) => {
    setCurrentPersona(personaId);
    if (personaId === 'store_manager') {
      setAuthToken('demo-token-store_manager');
    } else if (personaId === 'supply_chain') {
      setAuthToken('demo-token-supply_chain_planner');
    } else if (personaId === 'executive') {
      setAuthToken('demo-token-executive_leadership');
    }
    setActivePage('dashboard');
  };

  const handleLogout = () => {
    setCurrentPersona('login');
    setAiCopilotOpen(false);
    setAuthToken(null);
  };

  if (currentPersona === 'login') {
    return <LoginPage onSelectPersona={handleSelectPersona} />;
  }

  return (
    <div className="page-wrapper">
      {/* Top Navigation */}
      <Navbar
        selectedStore={selectedStore}
        onSelectStore={setSelectedStore}
        activePage={activePage}
        setActivePage={setActivePage}
        onToggleAICopilot={() => setAiCopilotOpen(!aiCopilotOpen)}
        aiCopilotOpen={aiCopilotOpen}
        onLogout={handleLogout}
      />

      {/* Main Content Pages */}
      <main style={{ flex: 1 }}>
        {currentPersona === 'store_manager' && (
          activePage === 'dashboard' ? (
            <StoreManagerDashboard
              storeId={selectedStore}
              onOpenAICopilot={() => setAiCopilotOpen(true)}
              onNavigateToRestock={() => setActivePage('restock')}
            />
          ) : (
            <StoreManagerRestockPlanner
              storeId={selectedStore}
              onOpenAICopilot={() => setAiCopilotOpen(true)}
            />
          )
        )}

        {currentPersona === 'supply_chain' && (
          <SupplyChainPlanner
            onOpenAICopilot={() => setAiCopilotOpen(true)}
          />
        )}

        {currentPersona === 'executive' && (
          <ExecutiveLeadership
            onOpenAICopilot={() => setAiCopilotOpen(true)}
          />
        )}
      </main>

      {/* Grounded AI Copilot Side Drawer with dynamic store context */}
      <AICopilotDrawer
        isOpen={aiCopilotOpen}
        onClose={() => setAiCopilotOpen(false)}
        storeId={selectedStore}
      />

      {/* Clean Manager-First Footer */}
      <footer style={{ padding: '20px 0', borderTop: '1px solid var(--border-subtle)', backgroundColor: 'var(--bg-primary)' }}>
        <div className="app-container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          <div>DemandPilot • Ecuador Retail Operations & Replenishment Console</div>
          <div>As-Of Cutoff: Aug 15, 2017 08:00 • 16-Day Forecast Horizon (Aug 16 – Aug 31)</div>
        </div>
      </footer>
    </div>
  );
}

