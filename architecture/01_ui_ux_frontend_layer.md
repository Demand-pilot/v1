# DemandPilot: UI/UX & 3D Visualization Architecture

## 1. Executive Summary & Tech Stack Alignment
DemandPilot features a responsive, low-latency presentation layer built using **Next.js 14 (App Router)**, **Tailwind CSS**, and **Three.js** via **React Three Fiber (`@react-three/fiber`)** and **Drei (`@react-three/drei`)**. The visualization engine translates complex multi-model forecasts (LSTM, LightGBM, Baselines) across 1,782 series into role-tailored, interactive 3D environments operating at sub-100ms dashboard speeds.

---

## 2. User Hierarchy & Role-Based UI/UX Specifications

The UI dynamically adapts based on three operational user levels:

### A. Strategic Level: Executive Leadership
* **Core Objective**: Macro demand visibility across Ecuador (22 cities, 54 stores), promotional ROI analysis, and macro-shock impact tracking (e.g., 2016 Earthquake sales surges, national payday peaks).
* **Primary Interface**: Dark-mode Executive Command Dashboard with an interactive **3D Ecuador Regional Demand Map**.
* **Key UI Components**:
  * National KPI Header Cards (Total Forecast Volume, National Stockout Risk %, Category Growth).
  * 3D Regional Demand Map Viewport with interactive city/store beacons.
  * Macro Event Filter Toggle (Earthquake Shock Wave, Bi-weekly Payday Surge, Back-to-School Season).

### B. Tactical Level: Supply Chain & Distribution Planners
* **Core Objective**: Inter-store inventory distribution, warehouse safety stock (SS) calculations, Reorder Point (ROP) monitoring, and 16-day horizon timeline scrubbing.
* **Primary Interface**: Multi-pane Supply Chain Operations Dashboard with a **3D Inter-Store Network Topology Graph**.
* **Key UI Components**:
  * 16-Day Interactive Time-Scrubber Timeline (Aug 16 - Aug 31).
  * Reorder Point (ROP) & Safety Stock (SS) threshold visualizers.
  * Store Rebalancing Recommendations Table with automated ERP webhook triggers.

### C. Operational Level: Dark Store & Warehouse Managers
* **Core Objective**: Daily SKU-level order adjustments, zero out-of-stock during payday surges, and instant actionability.
* **Primary Interface**: Streamlined Operational Dashboard featuring a **3D Isometric Store Floorplan** and an integrated Conversational AI Agent.
* **Key UI Components**:
  * 3D Aisle Demand Heatmap (33 Product Families).
  * Daily Urgent Reorder List (Action items prioritized by stockout risk).
  * Grounded RAG Conversational AI Panel (Natural language queries with zero numerical hallucination).

---

## 3. Dynamic Three.js Animation & Visual Mechanics

### A. Strategic Map Animations (`EcuadorMap3D.tsx`)
1. **Dynamic Store Beacons (54 Pillars)**:
   * **Height Scaling**: 3D cylinder/hexagonal mesh heights dynamically animate based on predicted 16-day sales volume.
   * **Color Shader Dynamics**:
     * 🟢 `Emerald Green (#10B981)`: Optimal Inventory Buffer.
     * 🔴 `Neon Red (#EF4444)`: High Stockout Risk (< 2 Days Coverage).
     * 🟠 `Amber Orange (#F59E0B)`: Overstock Warning (> 15 Days Buffer).
2. **Macro Shock Wave Effect**:
   * Toggling macro events (e.g., 2016 Earthquake) triggers an expanding translucent 3D ring shader originating from the epicenter, lighting up affected store pillars (+40% surge in Grocery 1 / Personal Care).
3. **Particle Supply Lines**:
   * Animated Bezier curve particle streams connect distribution centers (Quito/Guayaquil) to store pillars, representing real-time stock transfer velocity.

### B. Tactical Network Graph Animations (`InventoryNetwork3D.tsx`)
1. **Interactive 16-Day Time-Scrubber**:
   * Dragging the timeline slider smoothly interpolates 3D stock rack height vectors across all 54 stores using GSAP/framer-motion.
2. **Reorder Point (ROP) Plane**:
   * Translucent horizontal 3D threshold planes represent Safety Stock limits. When inventory dips below the plane, the rack mesh triggers a pulsing red outline pass.
3. **Inter-Store Rebalancing Arcs**:
   * Animated glowing arcs curve between overstocked stores and stockout-prone stores to visualize suggested inventory rebalancing routes.

### C. Operational Floorplan & AI Camera Focus (`StoreFloorplan3D.tsx`)
1. **3D Aisle Demand Heatmap**:
   * The isometric 3D store floorplan renders 33 product aisles. Aisles glow in real time based on demand profiling (e.g., School Supplies glowing bright yellow during late-August Sierra season).
2. **AI Agent Camera Interpolation**:
   * When a Store Manager asks a question (e.g., *"Why is School Supplies spiking by +145% at Store 14?"*), the Three.js camera uses `CameraControls` smoothly to pan, tilt, and zoom into the **School Supplies** aisle mesh.
3. **3D Floating HTML Callout Badges**:
   * HTML badges anchor above the focused 3D aisle displaying model metadata:
     * `+145% Demand Surge`
     * `Promo Elasticity: 0.67`
     * `Engine Selected: LightGBM GBDT (RMSLE: 0.38)`

---

## 4. Performance & Rendering Optimization Strategy
* **Instanced Rendering (`InstancedMesh`)**: Combines all 54 store pillars and floorplan items into single GPU draw calls, maintaining 60 FPS performance.
* **Level of Detail (LOD)**: Simplifies 3D mesh complexity when zooming out to macro views.
* **Sub-100ms Dashboard Integration**: Pre-computed model forecasts served via Redis cache with WebGL canvas state persistent across Next.js route transitions.
