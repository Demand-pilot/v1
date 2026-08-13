'use client';

import React, { useRef, useState, useMemo } from 'react';
import * as THREE from 'three';
import { Canvas } from '@react-three/fiber';
import { CameraControls, ContactShadows, Float } from '@react-three/drei';

// ==========================================
// Types & Interfaces
// ==========================================
export interface AisleData {
  id: number;
  name: string;
  category: string;
  x: number;
  z: number;
  demandSurgePct: number;
  isSpiking: boolean;
  elasticity: number;
  engine: string;
  rmsle: number;
  currentStock: number;
  recommendedOrder: number;
}

// ==========================================
// Soft Pastel & Editorial Color Palette
// ==========================================
const PASTEL_COLORS = {
  bg: '#FEF9F4',
  floor: '#F4ECE6',
  floorTile: '#EAE0D5',
  wall: '#D5C3B5',
  aisleMetal: '#4A3E5D',
  shelfWood: '#C8B8AA',
  
  // Status Glow Colors
  spikeEmissive: '#F39C12', // Amber Yellow Glow
  spikeRed: '#E74C3C',
  optimalGreen: '#36B37E',
  accentPurple: '#6B5B8A',
};

// Helper function for deterministic string number formatting
const formatNumber = (num: number): string => {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

// ==========================================
// Detailed Store 14 Product Family Aisles
// ==========================================
const STORE_14_AISLES: AisleData[] = [
  { id: 1, name: 'Aisle 01', category: 'Grocery I', x: -4.2, z: -3.8, demandSurgePct: 12, isSpiking: false, elasticity: 0.42, engine: 'LightGBM GBDT', rmsle: 0.35, currentStock: 1420, recommendedOrder: 180 },
  { id: 2, name: 'Aisle 02', category: 'Grocery II', x: -1.4, z: -3.8, demandSurgePct: 8, isSpiking: false, elasticity: 0.38, engine: 'LightGBM GBDT', rmsle: 0.36, currentStock: 980, recommendedOrder: 90 },
  { id: 3, name: 'Aisle 03', category: 'Beverages', x: 1.4, z: -3.8, demandSurgePct: 24, isSpiking: false, elasticity: 0.51, engine: 'PyTorch LSTM', rmsle: 0.40, currentStock: 1210, recommendedOrder: 220 },
  { id: 4, name: 'Aisle 04', category: 'Liquor & Wine', x: 4.2, z: -3.8, demandSurgePct: 5, isSpiking: false, elasticity: 0.30, engine: 'LightGBM GBDT', rmsle: 0.34, currentStock: 490, recommendedOrder: 40 },
  
  { id: 5, name: 'Aisle 05', category: 'School Supplies', x: 2.2, z: -1.0, demandSurgePct: 145, isSpiking: true, elasticity: 0.67, engine: 'LightGBM GBDT', rmsle: 0.38, currentStock: 340, recommendedOrder: 680 },
  { id: 6, name: 'Aisle 06', category: 'Personal Care', x: -4.2, z: -1.0, demandSurgePct: 18, isSpiking: false, elasticity: 0.45, engine: 'LightGBM GBDT', rmsle: 0.33, currentStock: 840, recommendedOrder: 150 },
  { id: 7, name: 'Aisle 07', category: 'Cleaning', x: -1.4, z: -1.0, demandSurgePct: 14, isSpiking: false, elasticity: 0.40, engine: 'Baseline Moving Avg', rmsle: 0.42, currentStock: 680, recommendedOrder: 110 },
  { id: 8, name: 'Aisle 08', category: 'Deli & Prepared', x: 4.2, z: -1.0, demandSurgePct: 16, isSpiking: false, elasticity: 0.43, engine: 'LightGBM GBDT', rmsle: 0.35, currentStock: 310, recommendedOrder: 130 },

  { id: 9, name: 'Aisle 09', category: 'Poultry & Meat', x: -4.2, z: 1.8, demandSurgePct: 22, isSpiking: false, elasticity: 0.48, engine: 'PyTorch LSTM', rmsle: 0.39, currentStock: 460, recommendedOrder: 190 },
  { id: 10, name: 'Aisle 10', category: 'Frozen Foods', x: -1.4, z: 1.8, demandSurgePct: 9, isSpiking: false, elasticity: 0.35, engine: 'LightGBM GBDT', rmsle: 0.32, currentStock: 790, recommendedOrder: 80 },
  { id: 11, name: 'Aisle 11', category: 'Dairy & Eggs', x: 1.4, z: 1.8, demandSurgePct: 15, isSpiking: false, elasticity: 0.44, engine: 'LightGBM GBDT', rmsle: 0.31, currentStock: 920, recommendedOrder: 140 },
  { id: 12, name: 'Aisle 12', category: 'Bakery', x: 4.2, z: 1.8, demandSurgePct: 11, isSpiking: false, elasticity: 0.39, engine: 'Baseline Moving Avg', rmsle: 0.37, currentStock: 260, recommendedOrder: 95 },
];

// ==========================================
// Detailed 3D Store Aisle Mesh
// ==========================================
const DetailedAisle3D: React.FC<{
  aisle: AisleData;
  isSelected: boolean;
  onSelect: (aisle: AisleData) => void;
}> = ({ aisle, isSelected, onSelect }) => {
  const groupRef = useRef<THREE.Group>(null!);

  const accentColor = aisle.isSpiking
    ? PASTEL_COLORS.spikeEmissive
    : isSelected
    ? '#6B5B8A'
    : PASTEL_COLORS.aisleMetal;

  return (
    <group
      ref={groupRef}
      position={[aisle.x, 0, aisle.z]}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(aisle);
      }}
    >
      {/* 1. Base Architectural Floor Plinth */}
      <mesh position={[0, 0.04, 0]} receiveShadow>
        <boxGeometry args={[1.9, 0.08, 1.3]} />
        <meshStandardMaterial color="#D5C3B5" roughness={0.4} />
      </mesh>

      {/* 2. Vertical Endcap Columns */}
      <mesh position={[-0.85, 0.7, 0]} castShadow>
        <boxGeometry args={[0.08, 1.3, 1.1]} />
        <meshStandardMaterial color="#3B2F52" roughness={0.3} metalness={0.5} />
      </mesh>
      <mesh position={[0.85, 0.7, 0]} castShadow>
        <boxGeometry args={[0.08, 1.3, 1.1]} />
        <meshStandardMaterial color="#3B2F52" roughness={0.3} metalness={0.5} />
      </mesh>

      {/* 3. Three Tiered Shelves */}
      {[0.3, 0.7, 1.1].map((yHeight, idx) => (
        <mesh key={idx} position={[0, yHeight, 0]} castShadow receiveShadow>
          <boxGeometry args={[1.7, 0.04, 1.05]} />
          <meshStandardMaterial
            color={aisle.isSpiking ? '#52436A' : '#4A3E5D'}
            roughness={0.3}
            metalness={0.4}
          />
        </mesh>
      ))}

      {/* 4. Mini 3D Product Packages stacked on shelves */}
      {[-0.5, 0, 0.5].map((xOffset, i) => (
        <group key={i}>
          {/* Bottom Shelf Packages */}
          <mesh position={[xOffset, 0.45, -0.25]} castShadow>
            <boxGeometry args={[0.3, 0.24, 0.35]} />
            <meshStandardMaterial
              color={aisle.isSpiking ? '#F39C12' : i % 2 === 0 ? '#36B37E' : '#E8B4C8'}
              roughness={0.2}
            />
          </mesh>
          <mesh position={[xOffset, 0.45, 0.25]} castShadow>
            <boxGeometry args={[0.3, 0.24, 0.35]} />
            <meshStandardMaterial
              color={aisle.isSpiking ? '#F39C12' : i % 2 === 0 ? '#58A6FF' : '#F59E0B'}
              roughness={0.2}
            />
          </mesh>

          {/* Top Shelf Packages */}
          <mesh position={[xOffset, 0.85, -0.2]} castShadow>
            <boxGeometry args={[0.26, 0.24, 0.3]} />
            <meshStandardMaterial
              color={aisle.isSpiking ? '#F1C40F' : i % 2 === 0 ? '#E74C3C' : '#36B37E'}
              roughness={0.2}
            />
          </mesh>
        </group>
      ))}

      {/* 5. Overhead Glowing LED Category Sign */}
      <mesh position={[0, 1.45, 0]}>
        <boxGeometry args={[1.72, 0.16, 0.35]} />
        <meshStandardMaterial
          color={accentColor}
          emissive={accentColor}
          emissiveIntensity={aisle.isSpiking ? 1.5 : isSelected ? 0.9 : 0.3}
          roughness={0.1}
        />
      </mesh>

      {/* Floating 3D Crystal Beacon above Spiking Aisle */}
      {aisle.isSpiking && (
        <Float speed={2.5} rotationIntensity={0.6} floatIntensity={0.6}>
          <mesh position={[0, 2.2, 0]}>
            <octahedronGeometry args={[0.28]} />
            <meshStandardMaterial
              color={PASTEL_COLORS.spikeEmissive}
              emissive={PASTEL_COLORS.spikeEmissive}
              emissiveIntensity={1.8}
            />
          </mesh>
        </Float>
      )}

      {/* Pulsing Base Glow Ring for Spiking Aisle */}
      {aisle.isSpiking && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
          <ringGeometry args={[1.1, 1.4, 32]} />
          <meshBasicMaterial color={PASTEL_COLORS.spikeEmissive} transparent opacity={0.6} side={THREE.DoubleSide} />
        </mesh>
      )}
    </group>
  );
};

// ==========================================
// 3D Store Floorplan Surface
// ==========================================
const StoreFloorplan3D: React.FC<{
  aisles: AisleData[];
  selectedAisleId: number | null;
  onSelectAisle: (aisle: AisleData) => void;
}> = ({ aisles, selectedAisleId, onSelectAisle }) => {
  return (
    <group>
      {/* 1. Store Outer Foundation Base */}
      <mesh position={[0, 0.01, 0]} receiveShadow>
        <boxGeometry args={[13.6, 0.02, 11.6]} />
        <meshStandardMaterial color={PASTEL_COLORS.floor} roughness={0.9} />
      </mesh>

      {/* 2. Store Interior Floor Surface with Walkway Lines */}
      <mesh position={[0, 0.02, 0]} receiveShadow>
        <boxGeometry args={[13.2, 0.01, 11.2]} />
        <meshStandardMaterial color={PASTEL_COLORS.floorTile} roughness={0.8} />
      </mesh>

      {/* 3. Aisles Grid */}
      {aisles.map((aisle) => (
        <DetailedAisle3D
          key={aisle.id}
          aisle={aisle}
          isSelected={selectedAisleId === aisle.id}
          onSelect={onSelectAisle}
        />
      ))}
    </group>
  );
};

// ==========================================
// Main Operational View 3D Component
// ==========================================
export default function OperationalView3D() {
  const [aisles, setAisles] = useState<AisleData[]>(STORE_14_AISLES);
  const [selectedAisleId, setSelectedAisleId] = useState<number | null>(5); // Default School Supplies
  const [orderApplied, setOrderApplied] = useState<boolean>(false);

  const [chatMessages, setChatMessages] = useState<
    {
      id: string;
      sender: 'user' | 'agent';
      text: string;
      time: string;
      metrics?: { surge: string; elasticity: string; engine: string; rmsle: string; orderIncrease: string };
      showAction?: boolean;
    }[]
  >([
    {
      id: '1',
      sender: 'user',
      text: 'Why is School Supplies spiking by +145% at Store 14 in late August?',
      time: '10:42 AM',
    },
    {
      id: '2',
      sender: 'agent',
      text: 'DemandPilot AI Engine analysis for Store 14 (Quito North): Annual Sierra back-to-school season coincides with national bi-weekly payday liquidity (Aug 15). Multi-model arbitration selected LightGBM GBDT over LSTM.',
      time: '10:42 AM',
      metrics: {
        surge: '+145% Peak',
        elasticity: '0.67 (High)',
        engine: 'LightGBM GBDT',
        rmsle: '0.38 (Optimal)',
        orderIncrease: '+240 Units',
      },
      showAction: true,
    },
  ]);
  const [chatInput, setChatInput] = useState('');

  const cameraControlsRef = useRef<CameraControls>(null!);

  const selectedAisle = useMemo(
    () => aisles.find((a) => a.id === selectedAisleId),
    [aisles, selectedAisleId]
  );

  // Focus camera directly on School Supplies aisle
  const zoomToSchoolSupplies = () => {
    setSelectedAisleId(5);
    if (cameraControlsRef.current) {
      cameraControlsRef.current.setLookAt(4.8, 3.8, 1.8, 2.2, 0.8, -1.0, true);
    }
  };

  // Focus on specific aisle
  const zoomToAisle = (aisle: AisleData) => {
    setSelectedAisleId(aisle.id);
    if (cameraControlsRef.current) {
      cameraControlsRef.current.setLookAt(
        aisle.x + 2.5,
        3.5,
        aisle.z + 2.8,
        aisle.x,
        0.8,
        aisle.z,
        true
      );
    }
  };

  // Reset overview camera angle
  const resetCamera = () => {
    setSelectedAisleId(null);
    if (cameraControlsRef.current) {
      cameraControlsRef.current.setLookAt(0, 11, 12, 0, 0, 0, true);
    }
  };

  const handleApplyOrder = () => {
    setOrderApplied(true);
    setAisles((prev) =>
      prev.map((a) => (a.id === 5 ? { ...a, currentStock: a.currentStock + 240 } : a))
    );
    setChatMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        sender: 'agent',
        text: '✅ ERP Webhook Dispatched: Order adjustment +240 Units confirmed for Store 14 (School Supplies). Projected stockout probability reduced from 18.2% to < 0.8%.',
        time: '10:44 AM',
      },
    ]);
  };

  const handleQuickPrompt = (promptText: string) => {
    setChatInput(promptText);
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput.trim();
    const newMsgId = Date.now().toString();

    let replyText = `DemandPilot AI: Analyzing Store 14 telemetry for "${userMsg}". Current inventory safety buffer is Z=1.65 (95% Confidence Level).`;
    let metrics = undefined;

    if (userMsg.toLowerCase().includes('school') || userMsg.toLowerCase().includes('supplies')) {
      zoomToSchoolSupplies();
      replyText = `DemandPilot AI: Focused on School Supplies (Aisle 05). Volume spike of +145% driven by Sierra back-to-school peak and promo density of 44.1%.`;
      metrics = {
        surge: '+145% Peak',
        elasticity: '0.67',
        engine: 'LightGBM GBDT',
        rmsle: '0.38',
        orderIncrease: '+240 Units',
      };
    } else if (userMsg.toLowerCase().includes('reorder') || userMsg.toLowerCase().includes('order')) {
      replyText = `DemandPilot AI: Reorder recommendations computed across 12 product aisles. Priority 1 is School Supplies (+240 units), Priority 2 is Beverages (+80 units).`;
    }

    setChatMessages((prev) => [
      ...prev,
      { id: newMsgId, sender: 'user', text: userMsg, time: '10:45 AM' },
      {
        id: (Date.now() + 1).toString(),
        sender: 'agent',
        text: replyText,
        time: '10:45 AM',
        metrics,
      },
    ]);
    setChatInput('');
  };

  return (
    <div className="relative w-full h-full bg-[#FEF9F4] text-[#3B2F52] flex flex-col font-sans overflow-hidden select-none">
      {/* ------------------------------------------------------------- */}
      {/* Top Header Action Bar                                         */}
      {/* ------------------------------------------------------------- */}
      <header className="z-10 glass-pastel-panel border-b border-purple-200/50 px-6 py-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="h-3.5 w-3.5 rounded-full bg-[#F39C12] shadow-[0_0_8px_#F39C12] animate-pulse" />
          <h1 className="heading-pastel text-xl font-bold tracking-tight text-[#3B2F52]">
            Store 14 — Operational Floorplan
          </h1>
          <span className="label-mono-pastel text-[9px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
            QUITO NORTH · SIERRA HORIZON
          </span>
        </div>

        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            onClick={zoomToSchoolSupplies}
            className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-[#F39C12] text-white shadow-sm hover:bg-amber-600 transition-all flex items-center gap-2"
          >
            <span>🚨 Focus Spiking Aisle (+145%)</span>
          </button>
          <button
            onClick={resetCamera}
            className="px-3.5 py-1.5 rounded-xl text-xs font-bold glass-pastel-card text-purple-900 hover:bg-purple-50 transition-all"
          >
            Reset Camera
          </button>
        </div>
      </header>

      {/* ------------------------------------------------------------- */}
      {/* Main Integrated Layout (Left Rail + 3D Canvas + Right AI)     */}
      {/* ------------------------------------------------------------- */}
      <div className="relative flex-1 w-full h-full flex flex-col md:flex-row overflow-hidden">
        
        {/* ----------------------------------------------------------- */}
        {/* Left Rail: Live Inventory & Aisle Health Telemetry          */}
        {/* ----------------------------------------------------------- */}
        <aside className="w-full md:w-72 glass-pastel-panel border-r border-purple-200/50 p-4 flex flex-col justify-between overflow-y-auto z-10">
          <div className="flex flex-col gap-4">
            <div>
              <span className="label-mono-pastel text-[10px] font-bold text-purple-900">
                DAILY STORE HEALTH (AUG 16 - 31)
              </span>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <div className="glass-pastel-card p-2.5 rounded-xl flex flex-col">
                  <span className="text-[9px] text-slate-500 font-semibold">Today Forecast</span>
                  <span className="text-base font-extrabold text-purple-950 font-mono">4,850</span>
                  <span className="text-[9px] font-bold text-emerald-700">+18.4% YoY</span>
                </div>
                <div className="glass-pastel-card p-2.5 rounded-xl flex flex-col">
                  <span className="text-[9px] text-slate-500 font-semibold">Stockout Risk</span>
                  <span className="text-base font-extrabold text-amber-700 font-mono">3.2%</span>
                  <span className="text-[9px] text-slate-500">1 Urgent Aisle</span>
                </div>
              </div>
            </div>

            {/* Aisle Inventory Status List */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="label-mono-pastel text-[10px] font-bold text-purple-900">
                  PRODUCT AISLES (12)
                </span>
                <span className="text-[9px] text-slate-500">Click to Inspect</span>
              </div>
              <div className="flex flex-col gap-1.5 max-h-64 overflow-y-auto pr-1">
                {aisles.map((aisle) => (
                  <button
                    key={aisle.id}
                    onClick={() => zoomToAisle(aisle)}
                    className={`p-2 rounded-xl text-left text-xs transition-all flex items-center justify-between border ${
                      selectedAisleId === aisle.id
                        ? 'bg-purple-100/90 border-purple-400 shadow-sm'
                        : 'glass-pastel-card hover:bg-purple-50/60 border-purple-200/40'
                    }`}
                  >
                    <div>
                      <div className="font-bold text-purple-950 text-[11px]">
                        {aisle.name} — {aisle.category}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        Stock: <span className="font-mono font-semibold text-purple-900">{formatNumber(aisle.currentStock)}</span>
                      </div>
                    </div>
                    {aisle.isSpiking ? (
                      <span className="text-[8px] font-extrabold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 animate-pulse">
                        +145%
                      </span>
                    ) : (
                      <span className="text-[8px] font-semibold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                        +{aisle.demandSurgePct}%
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Reorder Recommendation Box */}
            <div className="glass-pastel-card p-3 rounded-2xl border border-amber-300/80 bg-amber-50/40">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                <span className="text-[10px] font-bold text-amber-900 uppercase">
                  Payday Surge Alert
                </span>
              </div>
              <p className="text-[11px] text-amber-950 leading-tight">
                School Supplies inventory will stock out in 1.4 days without order replenishment.
              </p>
              <div className="mt-2 flex items-center justify-between text-[10px]">
                <span className="text-slate-600 font-semibold">Suggested Add:</span>
                <span className="font-mono font-bold text-purple-950">+240 Units</span>
              </div>
            </div>
          </div>
        </aside>

        {/* ----------------------------------------------------------- */}
        {/* Center: 3D Store Floorplan Viewport (Fills screen nicely)   */}
        {/* ----------------------------------------------------------- */}
        <div className="relative flex-1 h-full bg-[#FEF9F4]">
          <Canvas
            camera={{ position: [0, 11, 12], fov: 38 }}
            shadows
            className="w-full h-full cursor-grab active:cursor-grabbing"
          >
            <fog attach="fog" args={['#FEF9F4', 16, 38]} />

            {/* Studio Lighting */}
            <ambientLight intensity={0.9} color="#FFF5EB" />
            <directionalLight
              position={[20, 30, 20]}
              intensity={1.3}
              color="#FFE8D6"
              castShadow
              shadow-mapSize-width={2048}
              shadow-mapSize-height={2048}
            />

            {/* Soft Contact Shadows */}
            <ContactShadows
              position={[0, 0.01, 0]}
              opacity={0.35}
              scale={32}
              blur={2.0}
              color="#4A3E5D"
            />

            {/* 3D Floorplan & Product Family Aisles */}
            <StoreFloorplan3D
              aisles={aisles}
              selectedAisleId={selectedAisleId}
              onSelectAisle={(aisle) => zoomToAisle(aisle)}
            />

            <CameraControls ref={cameraControlsRef} makeDefault />
          </Canvas>

          {/* Selected Aisle Telemetry Card (Bottom Center/Left) */}
          {selectedAisle && (
            <div className="absolute bottom-4 left-4 glass-pastel-panel p-3.5 rounded-2xl text-xs flex flex-col gap-1.5 shadow-xl pointer-events-auto border border-purple-200/50 min-w-[260px]">
              <div className="flex items-center justify-between gap-2 border-b border-purple-200/50 pb-1.5">
                <span className="label-mono-pastel text-[10px] font-bold text-purple-900">
                  {selectedAisle.name} — {selectedAisle.category}
                </span>
                {selectedAisle.isSpiking ? (
                  <span className="text-[8px] px-1.5 py-0.5 rounded font-bold uppercase bg-amber-100 text-amber-800 border border-amber-300">
                    +145% SURGE
                  </span>
                ) : (
                  <span className="text-[8px] px-1.5 py-0.5 rounded font-bold uppercase bg-emerald-100 text-emerald-800">
                    BUFFER OPTIMAL
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                <div>
                  <span className="text-slate-500 block text-[10px]">Current Stock:</span>
                  <span className="font-mono font-bold text-purple-950">{formatNumber(selectedAisle.currentStock)} units</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">Promo Elasticity:</span>
                  <span className="font-mono font-bold text-purple-950">{selectedAisle.elasticity}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">Selected Engine:</span>
                  <span className="font-bold text-purple-900 text-[10px]">{selectedAisle.engine}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">Model RMSLE:</span>
                  <span className="font-mono font-bold text-emerald-700">{selectedAisle.rmsle}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ----------------------------------------------------------- */}
        {/* Right Sidebar: Rich DemandPilot Conversational AI Panel     */}
        {/* ----------------------------------------------------------- */}
        <aside className="w-full md:w-96 glass-pastel-panel border-l border-purple-200/60 p-4 flex flex-col justify-between z-20 shadow-xl overflow-hidden">
          <div className="flex flex-col h-full overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-purple-200/60 pb-2.5 mb-2.5">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="label-mono-pastel text-xs font-bold text-purple-900">
                  DEMANDPILOT AI AGENT
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[9px] font-mono text-purple-700 bg-purple-100/80 px-2 py-0.5 rounded-md">
                <span>⚡ 38ms</span>
                <span>•</span>
                <span>RAG</span>
              </div>
            </div>

            {/* Quick Action Suggestion Chips */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              <button
                onClick={() => handleQuickPrompt('Why is School Supplies spiking by +145%?')}
                className="text-[10px] px-2.5 py-1 rounded-lg bg-amber-100/90 text-amber-900 font-semibold border border-amber-200 hover:bg-amber-200 transition-all text-left"
              >
                🚨 School Supplies Spike (+145%)
              </button>
              <button
                onClick={() => handleQuickPrompt('Generate ERP Reorder Recommendations for Store 14')}
                className="text-[10px] px-2.5 py-1 rounded-lg bg-purple-100/80 text-purple-900 font-semibold border border-purple-200 hover:bg-purple-200 transition-all text-left"
              >
                📦 Reorder Suggestions
              </button>
              <button
                onClick={() => handleQuickPrompt('Compare LightGBM vs LSTM accuracy for beverages')}
                className="text-[10px] px-2.5 py-1 rounded-lg bg-emerald-100/80 text-emerald-900 font-semibold border border-emerald-200 hover:bg-emerald-200 transition-all text-left"
              >
                ⚡ Model RMSLE Compare
              </button>
            </div>

            {/* Chat History & Interactive AI Cards */}
            <div className="flex-1 flex flex-col gap-3 overflow-y-auto pr-1 pb-2">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
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

                    {/* AI Structured Metrics Box */}
                    {msg.metrics && (
                      <div className="mt-2.5 p-2 rounded-xl bg-purple-50/80 border border-purple-200/70 text-[10px] flex flex-col gap-1">
                        <div className="flex justify-between">
                          <span className="text-slate-500 font-medium">Demand Surge:</span>
                          <span className="font-bold text-amber-800">{msg.metrics.surge}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500 font-medium">Promo Elasticity:</span>
                          <span className="font-mono font-bold text-purple-950">{msg.metrics.elasticity}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500 font-medium">Selected Engine:</span>
                          <span className="font-bold text-purple-900">{msg.metrics.engine}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500 font-medium">Model RMSLE:</span>
                          <span className="font-mono font-bold text-emerald-700">{msg.metrics.rmsle}</span>
                        </div>
                        <div className="flex justify-between border-t border-purple-200/60 pt-1 mt-0.5">
                          <span className="text-purple-900 font-bold">Suggested Add:</span>
                          <span className="font-mono font-extrabold text-purple-950">{msg.metrics.orderIncrease}</span>
                        </div>
                      </div>
                    )}

                    {/* Actionable Button */}
                    {msg.showAction && !orderApplied && (
                      <button
                        onClick={handleApplyOrder}
                        className="mt-2 w-full py-1.5 bg-[#F39C12] hover:bg-amber-600 text-white rounded-lg font-bold text-[10px] shadow-sm transition-all flex items-center justify-center gap-1"
                      >
                        <span>✓ Apply +240 Units Order Override</span>
                      </button>
                    )}

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
                placeholder="Ask AI about Store 14 inventory..."
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
