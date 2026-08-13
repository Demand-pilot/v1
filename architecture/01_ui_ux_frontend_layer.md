# DemandPilot Architecture — Layer 1: UI/UX & Frontend Layer

**System Layer**: Presentation & User Experience  
**Technologies**: Next.js 14 (App Router), React 18, Three.js (WebGL), Chart.js, Tailwind CSS  
**Design System**: Warm Minimal (`#faf8f5` Cream, `#eee8df` Beige, `#2d2a26` Charcoal, `#c45d3e` Terracotta)

---

## 1. Persona-Based User Interfaces

DemandPilot serves three distinct retail user personas, tailoring information density, visual formats, and interaction models to each role:

```
                                  ┌─────────────────────────────────────────┐
                                  │       NEXT.JS 14 FRONTEND LAYER         │
                                  └────────────────────┬────────────────────┘
                                                       │
         ┌─────────────────────────────────────────────┼─────────────────────────────────────────────┐
         ▼                                             ▼                                             ▼
┌───────────────────────────┐             ┌───────────────────────────┐             ┌───────────────────────────┐
│   STORE MANAGERS          │             │   SUPPLY CHAIN PLANNERS   │             │   EXECUTIVE LEADERSHIP    │
│   (Operational Role)      │             │   (Tactical Role)         │             │   (Strategic Role)        │
├───────────────────────────┤             ├───────────────────────────┤             ├───────────────────────────┤
│ • Natural Language AI Q&A │             │ • 16-Day Forecast Grid    │             │ • Three.js 3D Store Map   │
│ • Daily Order Adjustments │             │ • Reorder Point (ROP) Logs│             │ • Macro Ecuador Map       │
│ • Payday Stockout Alerts  │             │ • Safety Stock Variations │             │ • Category Revenue KPIs   │
└───────────────────────────┘             └───────────────────────────┘             └───────────────────────────┘
```

### A. Persona 1: Store Managers (Operational Interface)
* **Objective**: Rapid daily decision-making, stockout prevention during payday surges, and natural language explanation.
* **UI Components**:
  * **Conversational AI Widget**: Chat interface allowing store managers to ask plain-English questions (*"Why is School Supplies spiking at Store 14?"*).
  * **Payday Alert Cards**: Highlights upcoming payday peaks (16th & 1st of month) with recommended order increases.
  * **Quick Adjust Controls**: Instant +/– button overrides for daily stock orders.
* **Frontend Protocol**: Connects via Server-Sent Events (SSE) / WebSocket to FastAPI `/api/v1/agent/chat` for streaming LLM explanations.

### B. Persona 2: Supply Chain Planners (Tactical Interface)
* **Objective**: Managing regional warehouse distribution, monitoring model accuracy (RMSLE), and setting Safety Stock parameters.
* **UI Components**:
  * **16-Day Forecast Grid**: Interactive tabular view of all 1,782 series across the 16-day forecast horizon (Aug 16 – Aug 31).
  * **ROP & Safety Stock Panel**: Live inputs for supplier lead times ($L$) and service factors ($Z=1.65$ for 95% confidence).
  * **Model Performance Matrix**: Comparative view showing whether LightGBM, PyTorch LSTM, or Baseline was selected per category.
* **Frontend Protocol**: REST API fetch calls to `/api/v1/forecast/grid` with client-side sorting and filter caching.

### C. Persona 3: Executive Leadership (Strategic Interface)
* **Objective**: Macro-level visibility across 54 stores in Ecuador, category performance analytics, and promotion ROI.
* **UI Components**:
  * **Three.js 3D Store Visualizer**: Interactive 3D Ecuador map with extruded store pillars reflecting regional inventory health and forecast demand volume.
  * **Category Doughnut Charts**: Visual promo density breakdown (Train 20.4% vs. Test 44.1%).
  * **Macro KPI Cards**: Total national demand volume, stockout risk percentage, and projected holding cost savings.
* **Frontend Protocol**: WebGL canvas rendering fed by lightweight GeoJSON and aggregate store endpoints (`/api/v1/analytics/macro`).

---

## 2. Frontend Architecture & Protocols

### A. Next.js 14 App Router & Server Components
* **React Server Components (RSC)**: Server-renders initial dashboard data on the server edge, delivering sub-100ms Page Load Times (First Contentful Paint < 80ms).
* **Client Boundary Hydration**: Only interactive widgets (Three.js canvas, Chart.js instances, Chat input) use `'use client'` hydration, keeping client bundle size under 85 KB gzipped.

### B. State Management Protocol
* **Server State**: Managed via TanStack Query (React Query v5) for automatic background re-fetching, cache invalidation, and optimistic UI updates.
* **Local UI State**: Zustand light store for active slide index, selected store filters, and slide presentation controls.

### C. Responsive Design Token System
```css
:root {
  --bg-primary: #faf8f5;        /* Warm Cream */
  --bg-secondary: #eee8df;      /* Soft Beige Card background */
  --bg-card: #ffffff;           /* Clean Card fill */
  --text-primary: #2d2a26;      /* Charcoal headings */
  --text-secondary: #635e58;    /* Muted body text */
  --accent-terracotta: #c45d3e; /* Terracotta brand accent */
  --font-heading: 'Playfair Display', Georgia, serif;
  --font-body: 'Plus Jakarta Sans', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```
