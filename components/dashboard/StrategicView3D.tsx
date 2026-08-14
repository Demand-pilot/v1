'use client';

import React, { useRef, useMemo, useState } from 'react';
import * as THREE from 'three';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, ContactShadows } from '@react-three/drei';

// ==========================================
// Types & Interfaces
// ==========================================
export type StockoutRisk = 'optimal' | 'overstock' | 'high_risk';

export interface StoreData {
  id: number;
  name: string;
  city: string;
  regionCluster: string;
  x: number;
  z: number;
  forecastVolume: number; // Units (800 - 5000)
  stockoutRisk: StockoutRisk;
  categorySurge: string;
  rmsle: number;
}

// ==========================================
// Soft Pastel & Editorial Color Palette
// ==========================================
const EDITORIAL_PALETTE = {
  bgVoid: '#FEF9F4',        // Warm Cream Background
  groundPlane: '#F7EFE8',   // Seamless Warm Ground Floor
  mapContour: '#EAE0D5',    // Soft Ecuador Landmass Fill
  outlinePlum: '#C8B8AA',   // Soft Plum/Taupe Border Line
  textPlum: '#3B2F52',      // Deep Plum Text
  subtextPlum: '#6B5B8A',   // Muted Lavender Text
  mauveAccent: '#E8B4C8',   // Soft Mauve Accent
  
  // Status Accents
  optimal: '#36B37E',      // Emerald Green
  overstock: '#F39C12',    // Amber
  highRisk: '#E74C3C',     // Rose Red
};

// Helper function for deterministic string number formatting
const formatNumber = (num: number): string => {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

// ==========================================
// 54 Ecuador Stores Data Generator
// ==========================================
const REGIONS = [
  { name: 'Quito North', cluster: 'Pichincha Sierra', x: -1.5, z: -4.5 },
  { name: 'Quito Central', cluster: 'Pichincha Sierra', x: -1.0, z: -3.5 },
  { name: 'Quito South', cluster: 'Pichincha Sierra', x: -0.5, z: -2.5 },
  { name: 'Guayaquil Metro', cluster: 'Guayas Coast', x: -6.5, z: 2.5 },
  { name: 'Guayaquil Port', cluster: 'Guayas Coast', x: -7.5, z: 4.0 },
  { name: 'Cuenca Highland', cluster: 'Azuay Sierra', x: -3.0, z: 6.5 },
  { name: 'Santo Domingo', cluster: 'Tsáchilas', x: -4.0, z: -1.0 },
  { name: 'Manta Coast', cluster: 'Manabí Coast', x: -10.5, z: 0.5 },
  { name: 'Portoviejo Valley', cluster: 'Manabí Coast', x: -9.0, z: 1.5 },
  { name: 'Machala South', cluster: 'El Oro Coast', x: -7.5, z: 8.5 },
  { name: 'Ambato Plateau', cluster: 'Tungurahua', x: -1.5, z: 1.0 },
  { name: 'Loja Far South', cluster: 'Loja Sierra', x: -3.5, z: 9.5 },
  { name: 'Esmeraldas Coast', cluster: 'Esmeraldas Coast', x: -6.0, z: -7.5 },
  { name: 'Ibarra North', cluster: 'Imbabura', x: 1.5, z: -6.5 },
  { name: 'Riobamba Central', cluster: 'Chimborazo', x: -1.8, z: 3.5 },
  { name: 'Tulcán Border', cluster: 'Carchi Border', x: 2.5, z: -8.0 },
  { name: 'Latacunga Sierra', cluster: 'Cotopaxi', x: -1.2, z: -0.5 },
  { name: 'Quevedo Lowlands', cluster: 'Los Ríos', x: -5.5, z: 0.5 },
  { name: 'Babahoyo Plains', cluster: 'Los Ríos', x: -5.8, z: 3.0 },
  { name: 'Santa Elena Coast', cluster: 'Santa Elena', x: -11.0, z: 3.5 },
  { name: 'Salinas Peninsula', cluster: 'Santa Elena', x: -12.5, z: 4.5 },
];

const generate54SeparatedStores = (): StoreData[] => {
  const stores: StoreData[] = [];
  const positions: THREE.Vector3[] = [];
  let currentId = 1;
  let seed = 999;

  const pseudoRandom = () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };

  const MIN_DIST = 1.30;

  let attempts = 0;
  while (stores.length < 54 && attempts < 5000) {
    attempts++;
    const region = REGIONS[attempts % REGIONS.length];

    const x = Math.max(-13.5, Math.min(12.5, region.x + (pseudoRandom() - 0.5) * 2.4));
    const z = Math.max(-8.5, Math.min(9.5, region.z + (pseudoRandom() - 0.5) * 2.4));

    const pos = new THREE.Vector3(x, 0, z);

    let tooClose = false;
    for (const existingPos of positions) {
      if (pos.distanceTo(existingPos) < MIN_DIST) {
        tooClose = true;
        break;
      }
    }

    if (!tooClose) {
      positions.push(pos);

      const volume = Math.floor(1100 + pseudoRandom() * 3700);
      const riskRand = pseudoRandom();
      let risk: StockoutRisk = 'optimal';
      if (riskRand < 0.18) risk = 'high_risk';
      else if (riskRand < 0.38) risk = 'overstock';

      const categories = [
        'GROCERY I',
        'BEVERAGES',
        'CLEANING',
        'PERSONAL CARE',
        'POULTRY',
        'SCHOOL SUPPLIES',
      ];

      stores.push({
        id: currentId,
        name: `Store #${currentId} - ${region.name}`,
        city: region.name,
        regionCluster: region.cluster,
        x: parseFloat(x.toFixed(2)),
        z: parseFloat(z.toFixed(2)),
        forecastVolume: volume,
        stockoutRisk: risk,
        categorySurge: categories[Math.floor(pseudoRandom() * categories.length)],
        rmsle: parseFloat((0.30 + pseudoRandom() * 0.15).toFixed(2)),
      });

      currentId++;
    }
  }

  return stores;
};

const STORES_DATA = generate54SeparatedStores();

// ==========================================
// Detailed Architectural Skyscraper Building
// ==========================================
const DetailedSkyscraper3D: React.FC<{
  store: StoreData;
  isHovered: boolean;
  isSelected: boolean;
  onHover: (id: number | null) => void;
  onClick: (id: number) => void;
}> = ({ store, isHovered, isSelected, onHover, onClick }) => {
  const groupRef = useRef<THREE.Group>(null!);

  const buildingHeight = useMemo(
    () => (store.forecastVolume / 5000) * 4.6 + 0.8,
    [store.forecastVolume]
  );

  const statusColor = useMemo(() => {
    if (store.stockoutRisk === 'high_risk') return EDITORIAL_PALETTE.highRisk;
    if (store.stockoutRisk === 'overstock') return EDITORIAL_PALETTE.overstock;
    return EDITORIAL_PALETTE.optimal;
  }, [store.stockoutRisk]);

  useFrame(({ clock }) => {
    if (groupRef.current && (isHovered || isSelected || store.stockoutRisk === 'high_risk')) {
      const time = clock.getElapsedTime();
      const pulse = 1 + Math.sin(time * 4 + store.id) * 0.04;
      groupRef.current.scale.set(pulse, 1, pulse);
    } else if (groupRef.current) {
      groupRef.current.scale.set(1, 1, 1);
    }
  });

  return (
    <group
      ref={groupRef}
      position={[store.x, 0, store.z]}
      onPointerOver={(e) => {
        e.stopPropagation();
        onHover(store.id);
      }}
      onPointerOut={() => onHover(null)}
      onClick={(e) => {
        e.stopPropagation();
        onClick(store.id);
      }}
    >
      {/* 1. Base Stepped Foundation Slab */}
      <mesh position={[0, 0.04, 0]} receiveShadow>
        <boxGeometry args={[0.76, 0.08, 0.76]} />
        <meshStandardMaterial color="#D5C3B5" roughness={0.4} metalness={0.2} />
      </mesh>

      {/* 2. Status Accent Collar */}
      <mesh position={[0, 0.1, 0]}>
        <boxGeometry args={[0.64, 0.04, 0.64]} />
        <meshStandardMaterial
          color={statusColor}
          emissive={statusColor}
          emissiveIntensity={isHovered ? 1.2 : 0.6}
        />
      </mesh>

      {/* 3. Main Skyscraper Body */}
      <mesh position={[0, buildingHeight / 2 + 0.12, 0]} castShadow receiveShadow>
        <boxGeometry args={[0.54, buildingHeight, 0.54]} />
        <meshStandardMaterial
          color={isHovered || isSelected ? '#6B5B8A' : '#3B2F52'}
          roughness={0.25}
          metalness={0.45}
        />
      </mesh>

      {/* 4. Glass Curtain-Wall Facade Insets */}
      <mesh position={[0, buildingHeight / 2 + 0.12, 0.28]}>
        <boxGeometry args={[0.42, buildingHeight * 0.88, 0.02]} />
        <meshStandardMaterial
          color={statusColor}
          emissive={statusColor}
          emissiveIntensity={0.3}
          roughness={0.1}
          metalness={0.8}
        />
      </mesh>

      {/* 5. Architectural Top Roof Crown */}
      <mesh position={[0, buildingHeight + 0.18, 0]}>
        <boxGeometry args={[0.58, 0.12, 0.58]} />
        <meshStandardMaterial
          color={statusColor}
          emissive={statusColor}
          emissiveIntensity={isHovered || isSelected ? 1.5 : 0.8}
          roughness={0.2}
        />
      </mesh>

      {/* 6. Glowing Top Spire Pin */}
      <mesh position={[0, buildingHeight + 0.28, 0]}>
        <cylinderGeometry args={[0.06, 0.14, 0.12, 16]} />
        <meshStandardMaterial color={statusColor} emissive={statusColor} emissiveIntensity={0.9} />
      </mesh>
    </group>
  );
};

// ==========================================
// Stylized 2D Architectural Ecuador Map Floor
// ==========================================
const EditorialEcuadorMap: React.FC = () => {
  const ecuadorShape = useMemo(() => {
    const shape = new THREE.Shape();
    shape.moveTo(-13, -8);
    shape.lineTo(-14, -2);
    shape.lineTo(-11, 4);
    shape.lineTo(-6, 8.5);
    shape.lineTo(2, 7.5);
    shape.lineTo(7.5, 3.5);
    shape.lineTo(11.5, -2);
    shape.lineTo(13, -7.5);
    shape.lineTo(4, -9.5);
    shape.lineTo(-4, -9.5);
    shape.closePath();

    return new THREE.ShapeGeometry(shape);
  }, []);

  const ecuadorBorderLine = useMemo(() => {
    const points: THREE.Vector3[] = [
      new THREE.Vector3(-13, 0.015, -8),
      new THREE.Vector3(-14, 0.015, -2),
      new THREE.Vector3(-11, 0.015, 4),
      new THREE.Vector3(-6, 0.015, 8.5),
      new THREE.Vector3(2, 0.015, 7.5),
      new THREE.Vector3(7.5, 0.015, 3.5),
      new THREE.Vector3(11.5, 0.015, -2),
      new THREE.Vector3(13, 0.015, -7.5),
      new THREE.Vector3(4, 0.015, -9.5),
      new THREE.Vector3(-4, 0.015, -9.5),
      new THREE.Vector3(-13, 0.015, -8),
    ];
    return new THREE.BufferGeometry().setFromPoints(points);
  }, []);

  const borderLineObj = useMemo(() => {
    const mat = new THREE.LineBasicMaterial({
      color: EDITORIAL_PALETTE.outlinePlum,
      linewidth: 2,
      transparent: true,
      opacity: 0.85,
    });
    return new THREE.Line(ecuadorBorderLine, mat);
  }, [ecuadorBorderLine]);

  return (
    <group>
      {/* 1. Seamless Infinite Warm Ground Floor */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <planeGeometry args={[140, 140]} />
        <meshStandardMaterial
          color={EDITORIAL_PALETTE.groundPlane}
          roughness={0.95}
          metalness={0.05}
        />
      </mesh>

      {/* 2. Stylized Ecuador Territory Surface Fill */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]} receiveShadow>
        <primitive object={ecuadorShape} attach="geometry" />
        <meshStandardMaterial
          color={EDITORIAL_PALETTE.mapContour}
          roughness={0.8}
          metalness={0.1}
        />
      </mesh>

      {/* 3. Stylized Soft Plum Boundary Outline */}
      <primitive object={borderLineObj} />
    </group>
  );
};

// ==========================================
// Main Strategic Dashboard Page Component
// ==========================================
export default function StrategicView3D() {
  const [stores] = useState<StoreData[]>(STORES_DATA);
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [macroEvent, setMacroEvent] = useState<string>('payday');
  const [searchFilter, setSearchFilter] = useState<string>('');

  const [chatMessages, setChatMessages] = useState<
    { sender: 'user' | 'agent'; text: string; time: string; highlight?: string }[]
  >([
    {
      sender: 'user',
      text: 'What is the national stockout risk during the upcoming Payday surge?',
      time: '10:45 AM',
    },
    {
      sender: 'agent',
      text: 'DemandPilot AI: Nationwide demand volume is projected at 171,092 units (+14.2% YoY). 18.5% of outlets (10 stores) are flagged for stockout risk (< 2 days buffer), concentrated primarily in Quito and Guayaquil metro corridors.',
      time: '10:45 AM',
      highlight: '10 Stores at Risk',
    },
  ]);
  const [chatInput, setChatInput] = useState('');

  // Filtered stores for left rail
  const filteredStores = useMemo(() => {
    return stores.filter(
      (s) =>
        s.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
        s.city.toLowerCase().includes(searchFilter.toLowerCase()) ||
        s.regionCluster.toLowerCase().includes(searchFilter.toLowerCase())
    );
  }, [stores, searchFilter]);

  const activeStore = useMemo(
    () => stores.find((s) => s.id === (hoveredId || selectedId)),
    [stores, hoveredId, selectedId]
  );

  // Compute Macro KPIs
  const kpis = useMemo(() => {
    let totalVolume = 0;
    let highRiskCount = 0;
    let overstockCount = 0;
    let optimalCount = 0;

    stores.forEach((s) => {
      totalVolume += s.forecastVolume;
      if (s.stockoutRisk === 'high_risk') highRiskCount++;
      else if (s.stockoutRisk === 'overstock') overstockCount++;
      else optimalCount++;
    });

    const stockoutRiskPct = ((highRiskCount / stores.length) * 100).toFixed(1);

    return {
      totalVolume,
      highRiskCount,
      overstockCount,
      optimalCount,
      stockoutRiskPct,
      totalStores: stores.length,
    };
  }, [stores]);

  const handleQuickPrompt = (text: string) => {
    setChatInput(text);
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput.trim();
    setChatMessages((prev) => [
      ...prev,
      { sender: 'user', text: userMsg, time: '10:46 AM' },
      {
        sender: 'agent',
        text: `DemandPilot AI: Analyzing 1,782 multi-model time series for "${userMsg}". Multi-model arbitration selected LightGBM GBDT (RMSLE: 0.38). Regional safety stock allocation is fully verified.`,
        time: '10:46 AM',
      },
    ]);
    setChatInput('');
  };

  return (
    <div className="relative w-full h-full bg-[#FEF9F4] text-[#3B2F52] flex flex-col font-sans overflow-hidden select-none">
      {/* ------------------------------------------------------------- */}
      {/* Top Header Navigation                                         */}
      {/* ------------------------------------------------------------- */}
      <header className="z-10 glass-pastel-panel border-b border-purple-200/50 px-6 py-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="h-3.5 w-3.5 rounded-full bg-[#E8B4C8] shadow-[0_0_8px_#E8B4C8]" />
          <h1 className="heading-pastel text-xl font-bold tracking-tight text-[#3B2F52]">
            DemandPilot — Executive Strategic View
          </h1>
        </div>

        {/* Macro Event Selector Buttons */}
        <div className="flex items-center glass-pastel-card p-1 rounded-xl border border-purple-200/60 pointer-events-auto">
          <button
            onClick={() => setMacroEvent('payday')}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
              macroEvent === 'payday'
                ? 'bg-[#6B5B8A] text-white shadow-sm'
                : 'text-purple-900 hover:bg-purple-50'
            }`}
          >
            Payday Surge
          </button>
          <button
            onClick={() => setMacroEvent('earthquake')}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
              macroEvent === 'earthquake'
                ? 'bg-[#E74C3C] text-white shadow-sm'
                : 'text-purple-900 hover:bg-purple-50'
            }`}
          >
            2016 Earthquake Shockwave
          </button>
          <button
            onClick={() => setMacroEvent('school')}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
              macroEvent === 'school'
                ? 'bg-[#F39C12] text-white shadow-sm'
                : 'text-purple-900 hover:bg-purple-50'
            }`}
          >
            Back-to-School Season
          </button>
        </div>
      </header>

      {/* ------------------------------------------------------------- */}
      {/* Macro KPI Banner Cards                                        */}
      {/* ------------------------------------------------------------- */}
      <div className="z-10 grid grid-cols-2 md:grid-cols-4 gap-3 px-6 py-2.5 bg-[#FEF9F4]/70 backdrop-blur-md border-b border-purple-100">
        <div className="glass-pastel-card p-3 rounded-2xl flex flex-col justify-between">
          <span className="label-mono-pastel text-[9px]">16-Day Forecast Demand</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl font-black text-purple-950 font-mono tracking-tight">
              {formatNumber(kpis.totalVolume)}
            </span>
            <span className="text-[10px] font-bold text-emerald-600">+14.2% YoY</span>
          </div>
        </div>

        <div className="glass-pastel-card p-3 rounded-2xl flex flex-col justify-between">
          <span className="label-mono-pastel text-[9px]">National Stockout Risk</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl font-black text-rose-600 font-mono tracking-tight">
              {kpis.stockoutRiskPct}%
            </span>
            <span className="text-[10px] font-bold text-slate-500">({kpis.highRiskCount} Outlets)</span>
          </div>
        </div>

        <div className="glass-pastel-card p-3 rounded-2xl flex flex-col justify-between">
          <span className="label-mono-pastel text-[9px]">Optimal Buffer Outlets</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl font-black text-emerald-600 font-mono tracking-tight">
              {kpis.optimalCount}
            </span>
            <span className="text-[10px] font-bold text-slate-500">/ {kpis.totalStores} Outlets</span>
          </div>
        </div>

        <div className="glass-pastel-card p-3 rounded-2xl flex flex-col justify-between">
          <span className="label-mono-pastel text-[9px]">Overstock Warnings</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl font-black text-amber-600 font-mono tracking-tight">
              {kpis.overstockCount}
            </span>
            <span className="text-[10px] font-bold text-slate-500">Outlets</span>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* Main Integrated Layout (Left Rail + 3D Map + Right AI)        */}
      {/* ------------------------------------------------------------- */}
      <div className="relative flex-1 w-full h-full flex flex-col md:flex-row overflow-hidden">
        
        {/* ----------------------------------------------------------- */}
        {/* Left Rail: Outlets List & Risk Rankings                     */}
        {/* ----------------------------------------------------------- */}
        <aside className="w-full md:w-72 glass-pastel-panel border-r border-purple-200/50 p-4 flex flex-col justify-between overflow-y-auto z-10">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="label-mono-pastel text-[10px] font-bold text-purple-900">
                54 OUTLETS NETWORK
              </span>
              <span className="text-[9px] text-slate-500">{filteredStores.length} stores</span>
            </div>

            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Search store, city, or cluster..."
              className="w-full bg-white/90 border border-purple-200 rounded-xl px-3 py-1.5 text-xs text-purple-950 focus:outline-none focus:ring-2 focus:ring-purple-400"
            />

            {/* Outlets Scroll List */}
            <div className="flex flex-col gap-1.5 max-h-[calc(100vh-320px)] overflow-y-auto pr-1">
              {filteredStores.map((store) => (
                <button
                  key={store.id}
                  onClick={() => setSelectedId(store.id)}
                  onMouseEnter={() => setHoveredId(store.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  className={`p-2 rounded-xl text-left text-xs transition-all flex items-center justify-between border ${
                    selectedId === store.id || hoveredId === store.id
                      ? 'bg-purple-100/90 border-purple-400 shadow-sm'
                      : 'glass-pastel-card hover:bg-purple-50/60 border-purple-200/40'
                  }`}
                >
                  <div>
                    <div className="font-bold text-purple-950 text-[11px]">{store.name}</div>
                    <div className="text-[9px] text-slate-500">{store.regionCluster}</div>
                  </div>
                  <div className="text-right">
                    <span className="font-mono font-bold text-purple-950 text-[10px] block">
                      {formatNumber(store.forecastVolume)}
                    </span>
                    <span
                      className={`text-[8px] font-bold px-1.5 py-0.2 rounded uppercase ${
                        store.stockoutRisk === 'high_risk'
                          ? 'bg-red-100 text-red-700'
                          : store.stockoutRisk === 'overstock'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-emerald-100 text-emerald-700'
                      }`}
                    >
                      {store.stockoutRisk === 'high_risk'
                        ? 'RISK'
                        : store.stockoutRisk === 'overstock'
                        ? 'OVER'
                        : 'OPT'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* ----------------------------------------------------------- */}
        {/* Center: 3D Map Viewport (Framed properly)                   */}
        {/* ----------------------------------------------------------- */}
        <div className="relative flex-1 h-full bg-[#FEF9F4]">
          <Canvas
            camera={{ position: [0, 15, 16], fov: 40 }}
            shadows
            className="w-full h-full cursor-grab active:cursor-grabbing"
          >
            <fog attach="fog" args={['#FEF9F4', 16, 38]} />

            <ambientLight intensity={0.85} color="#FFF5EB" />
            <directionalLight
              position={[25, 35, 20]}
              intensity={1.2}
              color="#FFE8D6"
              castShadow
              shadow-mapSize-width={2048}
              shadow-mapSize-height={2048}
              shadow-bias={-0.0001}
            />
            <directionalLight position={[-25, -20, -10]} intensity={0.35} color="#E8B4C8" />

            <ContactShadows
              position={[0, 0.012, 0]}
              opacity={0.35}
              scale={45}
              blur={2.2}
              far={10}
              color="#4A3E5D"
            />

            <EditorialEcuadorMap />
            {stores.map((store) => (
              <DetailedSkyscraper3D
                key={store.id}
                store={store}
                isHovered={hoveredId === store.id}
                isSelected={selectedId === store.id}
                onHover={setHoveredId}
                onClick={(id) => setSelectedId(selectedId === id ? null : id)}
              />
            ))}

            <OrbitControls
              maxPolarAngle={Math.PI / 2.5}
              minPolarAngle={Math.PI / 6}
              minDistance={8}
              maxDistance={24}
              enablePan={true}
              target={[0, 1, 0]}
            />
          </Canvas>

          {/* Active Store Telemetry Card (Bottom Left Dock) */}
          {activeStore && (
            <div className="absolute bottom-4 left-4 glass-pastel-panel p-3.5 rounded-2xl text-xs flex flex-col gap-1.5 shadow-xl pointer-events-auto border border-purple-200/50 min-w-[260px]">
              <div className="flex items-center justify-between gap-2 border-b border-purple-200/50 pb-1.5">
                <span className="label-mono-pastel text-[10px] font-bold text-purple-900">
                  {activeStore.name}
                </span>
                <span
                  className={`text-[8px] px-1.5 py-0.5 rounded font-bold uppercase ${
                    activeStore.stockoutRisk === 'high_risk'
                      ? 'bg-red-100 text-red-700'
                      : activeStore.stockoutRisk === 'overstock'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-emerald-100 text-emerald-700'
                  }`}
                >
                  {activeStore.stockoutRisk === 'high_risk'
                    ? 'HIGH STOCKOUT RISK'
                    : activeStore.stockoutRisk === 'overstock'
                    ? 'OVERSTOCK WARNING'
                    : 'OPTIMAL BUFFER'}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                <div>
                  <span className="text-slate-500 block text-[10px]">16-Day Forecast:</span>
                  <span className="font-mono font-bold text-purple-950">{formatNumber(activeStore.forecastVolume)} units</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">Top Surge Category:</span>
                  <span className="font-semibold text-purple-900">{activeStore.categorySurge}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">Region Cluster:</span>
                  <span className="font-bold text-purple-900 text-[10px]">{activeStore.regionCluster}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">Model RMSLE:</span>
                  <span className="font-mono font-bold text-emerald-700">{activeStore.rmsle}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ----------------------------------------------------------- */}
        {/* Right Sidebar: Strategic Conversational AI Agent Panel      */}
        {/* ----------------------------------------------------------- */}
        <aside className="w-full md:w-96 glass-pastel-panel border-l border-purple-200/60 p-4 flex flex-col justify-between z-20 shadow-xl overflow-hidden">
          <div className="flex flex-col h-full overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-purple-200/60 pb-2.5 mb-2.5">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="label-mono-pastel text-xs font-bold text-purple-900">
                  STRATEGIC AI ADVISOR
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[9px] font-mono text-purple-700 bg-purple-100/80 px-2 py-0.5 rounded-md">
                <span>⚡ 42ms</span>
                <span>•</span>
                <span>1,782 Series</span>
              </div>
            </div>

            {/* Quick Action Suggestion Chips */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              <button
                onClick={() => handleQuickPrompt('Which regional cluster has the highest stockout risk?')}
                className="text-[10px] px-2.5 py-1 rounded-lg bg-red-100/80 text-red-900 font-semibold border border-red-200 hover:bg-red-200 transition-all text-left"
              >
                🚨 Highest Risk Cluster
              </button>
              <button
                onClick={() => handleQuickPrompt('Simulate impact of 2016 Earthquake shockwave on supply chains')}
                className="text-[10px] px-2.5 py-1 rounded-lg bg-amber-100/80 text-amber-900 font-semibold border border-amber-200 hover:bg-amber-200 transition-all text-left"
              >
                ⚡ Earthquake Impact
              </button>
              <button
                onClick={() => handleQuickPrompt('Recommend safety stock buffer multiplier for payday')}
                className="text-[10px] px-2.5 py-1 rounded-lg bg-purple-100/80 text-purple-900 font-semibold border border-purple-200 hover:bg-purple-200 transition-all text-left"
              >
                📊 Payday Buffer Multiplier
              </button>
            </div>

            {/* Chat History */}
            <div className="flex-1 flex flex-col gap-3 overflow-y-auto pr-1 pb-2">
              {chatMessages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col ${
                    msg.sender === 'user' ? 'items-end' : 'items-start'
                  }`}
                >
                  <div
                    className={`p-3 rounded-2xl text-xs max-w-[95%] transition-all ${
                      msg.sender === 'user'
                        ? 'bg-[#6B5B8A] text-white rounded-br-none shadow-sm'
                        : 'glass-pastel-card text-purple-950 rounded-bl-none border border-purple-200/80 shadow-sm'
                    }`}
                  >
                    <p className="leading-relaxed text-[11px]">{msg.text}</p>
                    <span className="text-[8px] opacity-70 mt-1 block text-right">
                      {msg.time}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Chat Input Form */}
          <form onSubmit={handleSendMessage} className="mt-2 pt-2.5 border-t border-purple-200/60">
            <div className="flex gap-1.5">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask Strategic AI about nationwide demand..."
                className="flex-1 bg-white/90 border border-purple-200 rounded-xl px-3 py-2 text-xs text-purple-950 focus:outline-none focus:ring-2 focus:ring-purple-400"
              />
              <button
                type="submit"
                className="px-3.5 py-2 bg-[#6B5B8A] text-white rounded-xl text-xs font-bold hover:bg-purple-900 transition-all shadow-sm"
              >
                Send
              </button>
            </div>
          </form>
        </aside>
      </div>
    </div>
  );
}
