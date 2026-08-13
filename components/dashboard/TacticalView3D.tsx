'use client';

import React, { useRef, useState, useMemo } from 'react';
import * as THREE from 'three';
import { Canvas, useFrame } from '@react-three/fiber';
import { CameraControls, ContactShadows } from '@react-three/drei';

// ==========================================
// Types & Interfaces
// ==========================================
export interface WarehouseNode {
  id: number;
  name: string;
  code: string;
  type: 'Central DC' | 'Regional Hub' | 'Crossdock';
  x: number;
  z: number;
  capacity: number;
  safetyStockLimit: number;
  dailyStockLevels: number[];
  dailyInbound: number[];
  dailyOutbound: number[];
}

// ==========================================
// Soft Pastel & Editorial Color Palette
// ==========================================
const PASTEL_COLORS = {
  bg: '#FEF9F4',
  floor: '#F7EFE8',
  groundContour: '#EAE0D5',
  nodeMetal: '#3B2F52',
  nodeGlass: '#52436A',
  dockTrim: '#D5C3B5',
  
  // Status Colors
  safetyPlane: '#36B37E', // Mint Green Safety Stock Plane
  optimalStock: '#36B37E', // Green
  warningStock: '#F39C12', // Amber
  criticalStock: '#E74C3C', // Red Pulse
};

// Helper function for deterministic string number formatting
const formatNumber = (num: number): string => {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

// 16-Day Horizon Dates (Aug 16 - Aug 31)
const TIMELINE_DATES = [
  'Aug 16', 'Aug 17', 'Aug 18', 'Aug 19', 'Aug 20',
  'Aug 21', 'Aug 22', 'Aug 23', 'Aug 24', 'Aug 25',
  'Aug 26', 'Aug 27', 'Aug 28', 'Aug 29', 'Aug 30', 'Aug 31'
];

// ==========================================
// 5 Major Warehouse/Depot Nodes Data
// ==========================================
const WAREHOUSE_NODES: WarehouseNode[] = [
  {
    id: 1,
    name: 'Quito Central DC',
    code: 'DC-UIO-01',
    type: 'Central DC',
    x: -3.8,
    z: -2.2,
    capacity: 4500,
    safetyStockLimit: 1400,
    dailyStockLevels: [2400, 2250, 2080, 1850, 1620, 1450, 1310, 1150, 980, 890, 950, 1120, 1380, 1650, 1920, 2150],
    dailyInbound: [150, 120, 100, 80, 90, 110, 120, 140, 380, 420, 450, 400, 350, 300, 280, 250],
    dailyOutbound: [300, 270, 270, 310, 320, 280, 260, 300, 470, 360, 280, 170, 80, 30, 10, 20],
  },
  {
    id: 2,
    name: 'Guayaquil Port Hub',
    code: 'HUB-GYE-02',
    type: 'Regional Hub',
    x: 4.0,
    z: 2.8,
    capacity: 6000,
    safetyStockLimit: 1500,
    dailyStockLevels: [3800, 3750, 3680, 3600, 3520, 3450, 3380, 3300, 3210, 3100, 2980, 2890, 2800, 2720, 2650, 2580],
    dailyInbound: [450, 400, 380, 350, 360, 340, 320, 300, 280, 250, 260, 240, 220, 200, 190, 180],
    dailyOutbound: [500, 450, 450, 430, 440, 410, 390, 380, 370, 360, 380, 330, 300, 270, 260, 250],
  },
  {
    id: 3,
    name: 'Cuenca Regional Depot',
    code: 'DEP-CUE-03',
    type: 'Regional Hub',
    x: -4.2,
    z: 3.8,
    capacity: 3500,
    safetyStockLimit: 1100,
    dailyStockLevels: [1850, 1820, 1790, 1750, 1710, 1680, 1640, 1600, 1550, 1510, 1480, 1450, 1420, 1400, 1380, 1360],
    dailyInbound: [120, 110, 100, 90, 90, 80, 80, 70, 60, 70, 70, 60, 60, 50, 50, 40],
    dailyOutbound: [150, 140, 130, 130, 130, 110, 120, 120, 100, 100, 90, 90, 80, 70, 70, 60],
  },
  {
    id: 4,
    name: 'Manta Coastal Depot',
    code: 'DEP-MEC-04',
    type: 'Regional Hub',
    x: -7.0,
    z: -0.8,
    capacity: 3200,
    safetyStockLimit: 1000,
    dailyStockLevels: [1950, 1900, 1840, 1780, 1710, 1640, 1580, 1500, 1420, 1350, 1280, 1220, 1170, 1120, 1080, 1040],
    dailyInbound: [90, 80, 80, 70, 70, 60, 60, 50, 50, 50, 40, 40, 40, 30, 30, 30],
    dailyOutbound: [140, 140, 140, 140, 140, 120, 120, 130, 120, 120, 100, 90, 90, 80, 70, 70],
  },
  {
    id: 5,
    name: 'Santo Domingo Crossdock',
    code: 'XD-SDQ-05',
    type: 'Crossdock',
    x: 1.5,
    z: -3.8,
    capacity: 3800,
    safetyStockLimit: 1200,
    dailyStockLevels: [2100, 2050, 1980, 1920, 1850, 1790, 1720, 1660, 1600, 1540, 1490, 1430, 1380, 1330, 1290, 1250],
    dailyInbound: [110, 100, 100, 90, 90, 80, 80, 70, 70, 60, 60, 50, 50, 50, 40, 40],
    dailyOutbound: [160, 150, 160, 160, 160, 140, 140, 130, 130, 110, 110, 100, 100, 90, 80, 80],
  },
];

// ==========================================
// High-End Architectural Logistics Warehouse Node
// ==========================================
const WarehouseNode3D: React.FC<{
  node: WarehouseNode;
  dayIndex: number;
  isSelected: boolean;
  onSelect: (node: WarehouseNode) => void;
}> = ({ node, dayIndex, isSelected, onSelect }) => {
  const inventoryStackRef = useRef<THREE.Group>(null!);
  const currentStock = node.dailyStockLevels[dayIndex] || node.dailyStockLevels[0];
  const isBelowSafety = currentStock < node.safetyStockLimit;

  // Dynamic inventory height based on stock level (0.4 to 3.2 units)
  const targetHeight = useMemo(() => {
    return Math.max(0.4, (currentStock / node.capacity) * 3.2);
  }, [currentStock, node.capacity]);

  // Smooth lerping scale animation on timeline scrub
  useFrame((_, delta) => {
    if (inventoryStackRef.current) {
      inventoryStackRef.current.scale.y = THREE.MathUtils.lerp(
        inventoryStackRef.current.scale.y,
        targetHeight,
        delta * 8
      );
    }
  });

  const statusColor = isBelowSafety
    ? PASTEL_COLORS.criticalStock
    : isSelected
    ? '#6B5B8A'
    : PASTEL_COLORS.optimalStock;

  return (
    <group
      position={[node.x, 0, node.z]}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(node);
      }}
    >
      {/* 1. Base Concrete Logistics Apron / Foundation Pad */}
      <mesh position={[0, 0.04, 0]} receiveShadow>
        <boxGeometry args={[2.5, 0.08, 2.5]} />
        <meshStandardMaterial color="#D5C3B5" roughness={0.5} metalness={0.2} />
      </mesh>

      {/* 2. Elevated Loading Bay Platform with Roller Dock Gates */}
      <mesh position={[0, 0.16, 1.15]} castShadow receiveShadow>
        <boxGeometry args={[2.1, 0.16, 0.35]} />
        <meshStandardMaterial color="#8C7A6B" roughness={0.6} />
      </mesh>
      {[-0.6, 0, 0.6].map((dx, i) => (
        <mesh key={i} position={[dx, 0.38, 1.3]}>
          <boxGeometry args={[0.38, 0.32, 0.04]} />
          <meshStandardMaterial color="#3B2F52" roughness={0.3} metalness={0.7} />
        </mesh>
      ))}

      {/* 3. Structural Steel Columns (4 Corner Posts) */}
      {[-1.05, 1.05].map((cx, i) =>
        [-1.05, 1.05].map((cz, j) => (
          <mesh key={`${i}-${j}`} position={[cx, 1.7, cz]} castShadow>
            <boxGeometry args={[0.08, 3.4, 0.08]} />
            <meshStandardMaterial color="#3B2F52" roughness={0.3} metalness={0.6} />
          </mesh>
        ))
      )}

      {/* 4. Architectural Modern Roof Truss & Parapet Cap */}
      <mesh position={[0, 3.45, 0]}>
        <boxGeometry args={[2.3, 0.12, 2.3]} />
        <meshStandardMaterial color="#3B2F52" roughness={0.3} metalness={0.5} />
      </mesh>

      {/* 5. Translucent Glass Curtain-Wall Facade Shell */}
      <mesh position={[0, 1.7, 0]} receiveShadow>
        <boxGeometry args={[2.1, 3.3, 2.1]} />
        <meshStandardMaterial
          color="#52436A"
          transparent
          opacity={0.22}
          roughness={0.1}
          metalness={0.7}
        />
      </mesh>

      {/* 6. Dynamic Internal Inventory Pallet Stack (Scales with scrubber) */}
      <group ref={inventoryStackRef} position={[0, 0.1, 0]}>
        <mesh position={[0, 0.5, 0]} castShadow receiveShadow>
          <boxGeometry args={[1.75, 1.0, 1.75]} />
          <meshStandardMaterial
            color={isBelowSafety ? PASTEL_COLORS.criticalStock : '#6B5B8A'}
            emissive={isBelowSafety ? PASTEL_COLORS.criticalStock : '#3B2F52'}
            emissiveIntensity={isBelowSafety ? 0.9 : 0.25}
            roughness={0.3}
            metalness={0.4}
          />
        </mesh>
      </group>

      {/* 7. Glowing Architectural Status Crown Beacon */}
      <mesh position={[0, 3.62, 0]}>
        <cylinderGeometry args={[0.18, 0.18, 0.14, 16]} />
        <meshStandardMaterial
          color={statusColor}
          emissive={statusColor}
          emissiveIntensity={1.4}
          roughness={0.2}
        />
      </mesh>
    </group>
  );
};

// ==========================================
// Translucent Safety Stock (SS) Plane
// ==========================================
const SafetyStockPlane: React.FC = () => {
  return (
    <group position={[0, 1.25, 0]}>
      {/* Translucent Green/Mint Safety Stock Plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[22, 18]} />
        <meshStandardMaterial
          color="#36B37E"
          transparent
          opacity={0.15}
          side={THREE.DoubleSide}
          roughness={0.1}
          metalness={0.2}
        />
      </mesh>

      {/* Subtle Border Rim around Safety Plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <planeGeometry args={[22.1, 18.1]} />
        <meshBasicMaterial color="#36B37E" wireframe transparent opacity={0.3} />
      </mesh>
    </group>
  );
};

// ==========================================
// Main Tactical View 3D Component
// ==========================================
export default function TacticalView3D() {
  const [nodes] = useState<WarehouseNode[]>(WAREHOUSE_NODES);
  const [dayIndex, setDayIndex] = useState<number>(8); // Default to Aug 24 (Payday surge peak)
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(1); // Default to Quito DC
  const [isRebalanced, setIsRebalanced] = useState<boolean>(false);

  const [chatMessages, setChatMessages] = useState<
    { sender: 'user' | 'agent'; text: string; time: string; action?: string }[]
  >([
    {
      sender: 'user',
      text: 'Simulate Quito Central DC inventory buffer across the Aug 16-31 Payday horizon.',
      time: '11:05 AM',
    },
    {
      sender: 'agent',
      text: 'Tactical AI Planner: On Day 8 (Aug 24), Quito Central DC (DC-UIO-01) dips below Safety Stock (1,400 units) to 980 units (-30% buffer breach). Recommended action: Dispatch 350 units rebalancing transfer from Guayaquil Port Hub (surplus: +1,700 units).',
      time: '11:05 AM',
      action: 'transfer',
    },
  ]);
  const [chatInput, setChatInput] = useState('');

  const cameraControlsRef = useRef<CameraControls>(null!);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) || nodes[0],
    [nodes, selectedNodeId]
  );

  // Smooth camera zoom to specific node
  const zoomToNode = (node: WarehouseNode) => {
    setSelectedNodeId(node.id);
    if (cameraControlsRef.current) {
      cameraControlsRef.current.setLookAt(
        node.x + 3.2,
        4.0,
        node.z + 3.5,
        node.x,
        1.2,
        node.z,
        true
      );
    }
  };

  const resetCamera = () => {
    setSelectedNodeId(null);
    if (cameraControlsRef.current) {
      cameraControlsRef.current.setLookAt(0, 14, 16, 0, 0, 0, true);
    }
  };

  const handleDispatchTransfer = () => {
    setIsRebalanced(true);
    setChatMessages((prev) => [
      ...prev,
      {
        sender: 'agent',
        text: '✅ ERP Transfer Order #TR-8821 Dispatched: 350 units in transit via E35 Pan-American corridor (Guayaquil Hub -> Quito Central DC). Arrival ETA: 6.5 hrs.',
        time: '11:06 AM',
      },
    ]);
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput.trim();
    setChatMessages((prev) => [
      ...prev,
      { sender: 'user', text: userMsg, time: '11:07 AM' },
      {
        sender: 'agent',
        text: `Tactical AI: Analyzing network stock simulation on ${TIMELINE_DATES[dayIndex]} for "${userMsg}". Safety stock Z=1.65 coverage is active.`,
        time: '11:07 AM',
      },
    ]);
    setChatInput('');
  };

  return (
    <div className="relative w-full h-full bg-[#FEF9F4] text-[#3B2F52] flex flex-col font-sans overflow-hidden select-none">
      {/* ------------------------------------------------------------- */}
      {/* Top Header Bar                                                */}
      {/* ------------------------------------------------------------- */}
      <header className="z-10 glass-pastel-panel border-b border-purple-200/50 px-6 py-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="h-3.5 w-3.5 rounded-full bg-[#6B5B8A] shadow-[0_0_8px_#6B5B8A]" />
          <h1 className="heading-pastel text-xl font-bold tracking-tight text-[#3B2F52]">
            Supply Chain Tactical Planner — 16-Day Network Simulation
          </h1>
        </div>

        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            onClick={() => zoomToNode(nodes[0])}
            className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-[#E74C3C] text-white shadow-sm hover:bg-rose-700 transition-all flex items-center gap-2"
          >
            <span>🚨 Inspect Quito Breach (Day 8)</span>
          </button>
          <button
            onClick={resetCamera}
            className="px-3.5 py-1.5 rounded-xl text-xs font-bold glass-pastel-card text-purple-900 hover:bg-purple-50 transition-all"
          >
            Reset Overview
          </button>
        </div>
      </header>

      {/* ------------------------------------------------------------- */}
      {/* Main Integrated Layout (Left Rail + 3D Viewport + Right AI)   */}
      {/* ------------------------------------------------------------- */}
      <div className="relative flex-1 w-full h-full flex flex-col md:flex-row overflow-hidden">
        
        {/* ----------------------------------------------------------- */}
        {/* Left Rail: 5 Node Network Stock Status                      */}
        {/* ----------------------------------------------------------- */}
        <aside className="w-full md:w-72 glass-pastel-panel border-r border-purple-200/50 p-4 flex flex-col justify-between overflow-y-auto z-10">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="label-mono-pastel text-[10px] font-bold text-purple-900">
                NETWORK NODES (5)
              </span>
              <span className="text-[9px] font-mono text-purple-800 font-bold bg-purple-100 px-2 py-0.5 rounded">
                {TIMELINE_DATES[dayIndex]}
              </span>
            </div>

            {/* Nodes Scroll List */}
            <div className="flex flex-col gap-2 max-h-[calc(100vh-320px)] overflow-y-auto pr-1">
              {nodes.map((node) => {
                const stock = node.dailyStockLevels[dayIndex];
                const isBreached = stock < node.safetyStockLimit;

                return (
                  <button
                    key={node.id}
                    onClick={() => zoomToNode(node)}
                    className={`p-2.5 rounded-xl text-left text-xs transition-all flex flex-col gap-1 border ${
                      selectedNodeId === node.id
                        ? 'bg-purple-100/90 border-purple-400 shadow-sm'
                        : 'glass-pastel-card hover:bg-purple-50/60 border-purple-200/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-purple-950 text-[11px]">{node.name}</span>
                      <span
                        className={`text-[8px] font-bold px-1.5 py-0.2 rounded uppercase ${
                          isBreached
                            ? 'bg-red-100 text-red-700 animate-pulse'
                            : 'bg-emerald-100 text-emerald-700'
                        }`}
                      >
                        {isBreached ? 'BELOW SS' : 'BUFFER OK'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-[10px] text-slate-500">
                      <span>Stock: <strong className="text-purple-950 font-mono">{formatNumber(stock)}</strong></span>
                      <span>Safety: <span className="font-mono">{formatNumber(node.safetyStockLimit)}</span></span>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Active Rebalance Telemetry */}
            <div className="glass-pastel-card p-3 rounded-2xl border border-purple-300 bg-purple-50/50">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="h-2 w-2 rounded-full bg-[#6B5B8A] animate-pulse" />
                <span className="text-[10px] font-bold text-purple-950 uppercase">
                  Rebalance Strategy
                </span>
              </div>
              <p className="text-[11px] text-purple-900 leading-tight">
                <strong>Guayaquil Port</strong> ➔ <strong>Quito Central DC</strong>: Transfer 350 units to prevent stockout.
              </p>
              <div className="mt-2 flex items-center justify-between text-[10px]">
                <span className="text-slate-600 font-semibold">Lead Time:</span>
                <span className="font-mono font-bold text-purple-950">6.5 Hours (Pan-Am E35)</span>
              </div>
            </div>
          </div>
        </aside>

        {/* ----------------------------------------------------------- */}
        {/* Center: 3D Warehouse Network Viewport (Clean, No Lines)     */}
        {/* ----------------------------------------------------------- */}
        <div className="relative flex-1 h-full bg-[#FEF9F4]">
          <Canvas
            camera={{ position: [0, 14, 16], fov: 40 }}
            shadows
            className="w-full h-full cursor-grab active:cursor-grabbing"
          >
            <fog attach="fog" args={['#FEF9F4', 16, 38]} />

            <ambientLight intensity={0.9} color="#FFF5EB" />
            <directionalLight
              position={[25, 35, 20]}
              intensity={1.3}
              color="#FFE8D6"
              castShadow
              shadow-mapSize-width={2048}
              shadow-mapSize-height={2048}
            />

            <ContactShadows
              position={[0, 0.01, 0]}
              opacity={0.35}
              scale={35}
              blur={2.2}
              color="#4A3E5D"
            />

            {/* Translucent Glowing Safety Stock Buffer Plane */}
            <SafetyStockPlane />

            {/* 5 Architectural 3D Logistics Warehouses */}
            {nodes.map((node) => (
              <WarehouseNode3D
                key={node.id}
                node={node}
                dayIndex={dayIndex}
                isSelected={selectedNodeId === node.id}
                onSelect={(n) => zoomToNode(n)}
              />
            ))}

            <CameraControls ref={cameraControlsRef} makeDefault />
          </Canvas>

          {/* Selected Node Telemetry Card (Bottom Left Dock) */}
          <div className="absolute bottom-20 left-4 glass-pastel-panel p-3.5 rounded-2xl text-xs flex flex-col gap-1.5 shadow-xl pointer-events-auto border border-purple-200/50 min-w-[260px]">
            <div className="flex items-center justify-between gap-2 border-b border-purple-200/50 pb-1.5">
              <span className="label-mono-pastel text-[10px] font-bold text-purple-900">
                {selectedNode.name} ({selectedNode.code})
              </span>
              <span
                className={`text-[8px] px-1.5 py-0.5 rounded font-bold uppercase ${
                  selectedNode.dailyStockLevels[dayIndex] < selectedNode.safetyStockLimit
                    ? 'bg-red-100 text-red-700'
                    : 'bg-emerald-100 text-emerald-700'
                }`}
              >
                {selectedNode.dailyStockLevels[dayIndex] < selectedNode.safetyStockLimit
                  ? 'CRITICAL DEFICIT'
                  : 'BUFFER HEALTHY'}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
              <div>
                <span className="text-slate-500 block text-[10px]">Projected Stock:</span>
                <span className="font-mono font-bold text-purple-950">{formatNumber(selectedNode.dailyStockLevels[dayIndex])} units</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">Safety Limit:</span>
                <span className="font-mono font-bold text-emerald-700">{formatNumber(selectedNode.safetyStockLimit)} units</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">Daily Outbound:</span>
                <span className="font-mono font-semibold text-purple-900">{selectedNode.dailyOutbound[dayIndex]} units/day</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">Total Capacity:</span>
                <span className="font-mono text-purple-900">{formatNumber(selectedNode.capacity)}</span>
              </div>
            </div>
          </div>

          {/* --------------------------------------------------------- */}
          {/* 16-Day Interactive Time-Scrubber (Bottom Viewport Dock)    */}
          {/* --------------------------------------------------------- */}
          <div className="absolute bottom-3 left-4 right-4 glass-pastel-panel px-5 py-3 rounded-2xl shadow-xl flex flex-col gap-1.5 pointer-events-auto border border-purple-200/60 z-10">
            <div className="flex items-center justify-between text-xs">
              <span className="label-mono-pastel text-[10px] font-bold text-purple-900">
                16-DAY REPLENISHMENT HORIZON (AUG 16 - AUG 31)
              </span>
              <span className="font-mono font-extrabold text-purple-950 bg-purple-100 px-2 py-0.5 rounded text-xs">
                SIMULATION DAY: {TIMELINE_DATES[dayIndex]}
              </span>
            </div>

            <input
              type="range"
              min="0"
              max="15"
              step="1"
              value={dayIndex}
              onChange={(e) => setDayIndex(parseInt(e.target.value))}
              className="w-full accent-[#6B5B8A] cursor-pointer h-2 bg-purple-200/60 rounded-lg appearance-none"
            />

            <div className="flex justify-between text-[9px] font-mono text-slate-500 pt-0.5">
              {TIMELINE_DATES.map((date, idx) => (
                <span
                  key={idx}
                  onClick={() => setDayIndex(idx)}
                  className={`cursor-pointer hover:text-purple-950 ${
                    dayIndex === idx ? 'font-black text-purple-900 underline' : ''
                  }`}
                >
                  {date.replace('Aug ', '')}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* ----------------------------------------------------------- */}
        {/* Right Sidebar: Tactical Conversational AI Planner           */}
        {/* ----------------------------------------------------------- */}
        <aside className="w-full md:w-96 glass-pastel-panel border-l border-purple-200/60 p-4 flex flex-col justify-between z-20 shadow-xl overflow-hidden">
          <div className="flex flex-col h-full overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-purple-200/60 pb-2.5 mb-2.5">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="label-mono-pastel text-xs font-bold text-purple-900">
                  TACTICAL AI PLANNER
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[9px] font-mono text-purple-700 bg-purple-100/80 px-2 py-0.5 rounded-md">
                <span>⚡ 40ms</span>
                <span>•</span>
                <span>Z=1.65</span>
              </div>
            </div>

            {/* Quick Action Suggestion Chips */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              <button
                onClick={() => setChatInput('Calculate rebalancing transfer cost between Guayaquil and Quito')}
                className="text-[10px] px-2.5 py-1 rounded-lg bg-purple-100/80 text-purple-900 font-semibold border border-purple-200 hover:bg-purple-200 transition-all text-left"
              >
                🚚 Rebalance Transfer Cost
              </button>
              <button
                onClick={() => setChatInput('What is the projected stockout probability for Quito DC?')}
                className="text-[10px] px-2.5 py-1 rounded-lg bg-red-100/80 text-red-900 font-semibold border border-red-200 hover:bg-red-200 transition-all text-left"
              >
                🚨 Quito Stockout Risk
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

                    {msg.action === 'transfer' && !isRebalanced && (
                      <button
                        onClick={handleDispatchTransfer}
                        className="mt-2 w-full py-1.5 bg-[#6B5B8A] hover:bg-purple-900 text-white rounded-lg font-bold text-[10px] shadow-sm transition-all flex items-center justify-center gap-1"
                      >
                        <span>✓ Dispatch 350 Units Transfer (TR-8821)</span>
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
                placeholder="Ask Tactical AI about rebalancing..."
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
