-- ============================================================================
-- DemandPilot Production Database Migration (Supabase PostgreSQL + pgvector)
-- Migration: 20260814000001_initial_schema.sql
-- Description: Core operational data, forecasting, ordering workflow, AI & RBAC
-- ============================================================================

-- 0. Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- 1. CORE OPERATIONAL TABLES
-- ============================================================================

-- Stores Master Table (54 Stores in Ecuador)
CREATE TABLE IF NOT EXISTS stores (
    store_nbr INTEGER PRIMARY KEY,
    city VARCHAR(64) NOT NULL,
    state VARCHAR(64) NOT NULL,
    region VARCHAR(32) NOT NULL CHECK (region IN ('Sierra', 'Coast', 'Oriente')),
    store_type VARCHAR(8) NOT NULL,
    cluster INTEGER NOT NULL,
    revenue_tier VARCHAR(16) NOT NULL DEFAULT 'TIER_1',
    target_margin_pct NUMERIC(5,4) NOT NULL DEFAULT 0.2500,
    lead_time_days INTEGER NOT NULL DEFAULT 7,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Product Families Master Table (33 Competition Categories)
CREATE TABLE IF NOT EXISTS product_families (
    family VARCHAR(64) PRIMARY KEY,
    avg_unit_price_usd NUMERIC(10,2) NOT NULL DEFAULT 3.50,
    gross_margin_pct NUMERIC(5,4) NOT NULL DEFAULT 0.2800,
    holding_cost_factor NUMERIC(5,4) NOT NULL DEFAULT 0.0500,
    promo_elasticity NUMERIC(5,4) NOT NULL DEFAULT 0.2500,
    category_classification VARCHAR(32) NOT NULL DEFAULT 'SMOOTH_STAPLE',
    surge_risk_tier VARCHAR(16) NOT NULL DEFAULT 'LOW',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Daily Sales History (Historical Actuals for 28D/56D/90D Timeline)
CREATE TABLE IF NOT EXISTS daily_sales (
    id BIGSERIAL PRIMARY KEY,
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    family VARCHAR(64) NOT NULL REFERENCES product_families(family) ON DELETE CASCADE,
    date DATE NOT NULL,
    sales_units NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    onpromotion_units INTEGER NOT NULL DEFAULT 0,
    is_payday BOOLEAN NOT NULL DEFAULT FALSE,
    is_holiday BOOLEAN NOT NULL DEFAULT FALSE,
    is_earthquake_affected BOOLEAN NOT NULL DEFAULT FALSE,
    oil_dcoil_price NUMERIC(8,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_daily_sales_store_fam_date UNIQUE (store_nbr, family, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_sales_lookup ON daily_sales(store_nbr, family, date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_sales_date ON daily_sales(date DESC);

-- Inventory Snapshots (Current stock on hand, labeled if demo seed)
CREATE TABLE IF NOT EXISTS inventory_snapshots (
    id BIGSERIAL PRIMARY KEY,
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    family VARCHAR(64) NOT NULL REFERENCES product_families(family) ON DELETE CASCADE,
    snapshot_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    on_hand_units NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    reserved_units NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    in_transit_units NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    is_demo_seed BOOLEAN NOT NULL DEFAULT FALSE,
    integration_source VARCHAR(64) NOT NULL DEFAULT 'MANUAL_OR_DEMO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inventory_store_fam ON inventory_snapshots(store_nbr, family, snapshot_timestamp DESC);

-- Inventory Movements Audit Log
CREATE TABLE IF NOT EXISTS inventory_movements (
    id BIGSERIAL PRIMARY KEY,
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    family VARCHAR(64) NOT NULL REFERENCES product_families(family) ON DELETE CASCADE,
    movement_type VARCHAR(32) NOT NULL CHECK (movement_type IN ('SALE', 'RECEIPT', 'ADJUSTMENT', 'TRANSFER', 'WASTE')),
    units NUMERIC(12,2) NOT NULL,
    reference_id VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_movements_store_fam ON inventory_movements(store_nbr, family, created_at DESC);

-- Supplier Lead Times
CREATE TABLE IF NOT EXISTS supplier_lead_times (
    id BIGSERIAL PRIMARY KEY,
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    family VARCHAR(64) NOT NULL REFERENCES product_families(family) ON DELETE CASCADE,
    lead_time_days INTEGER NOT NULL DEFAULT 7,
    supplier_name VARCHAR(128) NOT NULL DEFAULT 'Corporación Favorita Central Distribution',
    supplier_reliability_pct NUMERIC(5,2) NOT NULL DEFAULT 96.50,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_supplier_store_fam UNIQUE (store_nbr, family)
);

-- Promotions Calendar
CREATE TABLE IF NOT EXISTS promotions (
    id BIGSERIAL PRIMARY KEY,
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    family VARCHAR(64) NOT NULL REFERENCES product_families(family) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    promo_type VARCHAR(64) NOT NULL DEFAULT 'PRICE_CUT',
    discount_pct NUMERIC(5,2) NOT NULL DEFAULT 15.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_promos_store_fam_dates ON promotions(store_nbr, family, start_date, end_date);

-- Holiday & Event Calendar
CREATE TABLE IF NOT EXISTS holiday_events (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    event_name VARCHAR(128) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    locale VARCHAR(32) NOT NULL DEFAULT 'National',
    locale_name VARCHAR(64) NOT NULL DEFAULT 'Ecuador',
    transferred BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_holidays_date ON holiday_events(date);

-- Inbound Shipments
CREATE TABLE IF NOT EXISTS inbound_shipments (
    id BIGSERIAL PRIMARY KEY,
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    family VARCHAR(64) NOT NULL REFERENCES product_families(family) ON DELETE CASCADE,
    purchase_order_id VARCHAR(64),
    expected_arrival_date DATE NOT NULL,
    units NUMERIC(12,2) NOT NULL,
    carrier VARCHAR(64) NOT NULL DEFAULT 'Favorita Logistics Fleet',
    shipment_status VARCHAR(32) NOT NULL DEFAULT 'IN_TRANSIT' CHECK (shipment_status IN ('SCHEDULED', 'IN_TRANSIT', 'RECEIVED', 'DELAYED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inbound_store_date ON inbound_shipments(store_nbr, expected_arrival_date);

-- ============================================================================
-- 2. FORECASTING & MODEL METRICS TABLES
-- ============================================================================

-- Forecast Runs (Immutable Model Inference Execution Runs)
CREATE TABLE IF NOT EXISTS forecast_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    cutoff_date DATE NOT NULL,
    horizon_days INTEGER NOT NULL DEFAULT 16,
    selected_model VARCHAR(64) NOT NULL,
    overall_rmsle NUMERIC(7,4) NOT NULL,
    is_active_approved BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_forecast_runs_active ON forecast_runs(is_active_approved, cutoff_date DESC);

-- Forecast Predictions (1,782 Series × 16-Day Daily Forecast Values)
CREATE TABLE IF NOT EXISTS forecast_predictions (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES forecast_runs(run_id) ON DELETE CASCADE,
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    family VARCHAR(64) NOT NULL REFERENCES product_families(family) ON DELETE CASCADE,
    forecast_date DATE NOT NULL,
    horizon_step INTEGER NOT NULL CHECK (horizon_step BETWEEN 1 AND 16),
    predicted_units NUMERIC(12,2) NOT NULL,
    lower_p10 NUMERIC(12,2) NOT NULL,
    upper_p90 NUMERIC(12,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_forecast_step UNIQUE (run_id, store_nbr, family, forecast_date)
);

CREATE INDEX IF NOT EXISTS idx_forecast_pred_lookup ON forecast_predictions(run_id, store_nbr, family, forecast_date);

-- Model Tournament Scorecard & Segment Metrics
CREATE TABLE IF NOT EXISTS model_metrics (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES forecast_runs(run_id) ON DELETE CASCADE,
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    family VARCHAR(64) NOT NULL REFERENCES product_families(family) ON DELETE CASCADE,
    model_engine VARCHAR(64) NOT NULL, -- 'LightGBM_GBDT', 'PyTorch_LSTM', 'Zero_Mask_Rule'
    backtest_rmsle NUMERIC(7,4) NOT NULL,
    baseline_rmsle NUMERIC(7,4) NOT NULL,
    lift_pct NUMERIC(6,2) NOT NULL,
    tournament_rank INTEGER NOT NULL DEFAULT 1,
    decision_rationale TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_metrics_lookup ON model_metrics(run_id, store_nbr, family);

-- Forecast Recommendations (Daily Reorder & Safety Buffer Calculations)
CREATE TABLE IF NOT EXISTS forecast_recommendations (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES forecast_runs(run_id) ON DELETE CASCADE,
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    family VARCHAR(64) NOT NULL REFERENCES product_families(family) ON DELETE CASCADE,
    safety_stock NUMERIC(12,2) NOT NULL,
    reorder_point NUMERIC(12,2) NOT NULL,
    recommended_order_qty NUMERIC(12,2) NOT NULL,
    days_of_cover NUMERIC(6,2) NOT NULL,
    projected_stockout_date DATE,
    urgency VARCHAR(16) NOT NULL CHECK (urgency IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    reason TEXT NOT NULL,
    impact TEXT NOT NULL,
    confidence_pct NUMERIC(5,2) NOT NULL DEFAULT 94.20,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommendations_store_urgency ON forecast_recommendations(store_nbr, urgency, created_at DESC);

-- ============================================================================
-- 3. ORDERING WORKFLOW & PURCHASE ORDER TABLES
-- ============================================================================

-- Order Plans (Active Store Manager Replenishment Drafts)
CREATE TABLE IF NOT EXISTS order_plans (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default_tenant',
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'SUBMITTED', 'CANCELLED', 'APPROVED')),
    created_by_user_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_plans_store ON order_plans(store_nbr, status);

-- Order Plan Lines
CREATE TABLE IF NOT EXISTS order_plan_lines (
    id VARCHAR(64) PRIMARY KEY,
    order_plan_id VARCHAR(64) NOT NULL REFERENCES order_plans(id) ON DELETE CASCADE,
    family VARCHAR(64) NOT NULL REFERENCES product_families(family) ON DELETE CASCADE,
    recommended_qty NUMERIC(12,2) NOT NULL,
    adjusted_qty NUMERIC(12,2) NOT NULL,
    reason TEXT,
    is_approved BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_plan_family UNIQUE (order_plan_id, family)
);

CREATE INDEX IF NOT EXISTS idx_order_plan_lines_plan ON order_plan_lines(order_plan_id);

-- Purchase Orders (Official Submitted & Persisted Purchase Orders)
CREATE TABLE IF NOT EXISTS purchase_orders (
    id VARCHAR(64) PRIMARY KEY,
    order_plan_id VARCHAR(64) REFERENCES order_plans(id) ON DELETE SET NULL,
    po_number VARCHAR(64) NOT NULL UNIQUE,
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    supplier_name VARCHAR(128) NOT NULL DEFAULT 'Corporación Favorita Central Hub',
    total_units NUMERIC(12,2) NOT NULL,
    total_cost_usd NUMERIC(12,2) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'TRANSMITTED' CHECK (status IN ('TRANSMITTED', 'CONFIRMED', 'IN_TRANSIT', 'RECEIVED', 'CANCELLED')),
    submitted_by_user_id VARCHAR(64) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    estimated_delivery_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_purchase_orders_store ON purchase_orders(store_nbr, submitted_at DESC);

-- Purchase Order Lines
CREATE TABLE IF NOT EXISTS purchase_order_lines (
    id VARCHAR(64) PRIMARY KEY,
    purchase_order_id VARCHAR(64) NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    family VARCHAR(64) NOT NULL REFERENCES product_families(family) ON DELETE CASCADE,
    units NUMERIC(12,2) NOT NULL,
    unit_price_usd NUMERIC(10,2) NOT NULL,
    line_total_usd NUMERIC(12,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_po_lines_po ON purchase_order_lines(purchase_order_id);

-- Order Audit Events Log (Immutable User Action Trail)
CREATE TABLE IF NOT EXISTS order_audit_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL, -- 'PLAN_CREATED', 'LINE_UPDATED', 'PLAN_SUBMITTED', 'PO_GENERATED'
    entity_type VARCHAR(32) NOT NULL, -- 'ORDER_PLAN', 'PURCHASE_ORDER'
    entity_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    user_role VARCHAR(32) NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_audit_entity ON order_audit_events(entity_type, entity_id, created_at DESC);

-- ============================================================================
-- 4. ACCESS CONTROL, AI RAG & MEMORY TABLES
-- ============================================================================

-- User Profiles (Mirrors Supabase Auth Users)
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default_tenant',
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(128) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'STORE_MANAGER' CHECK (role IN ('STORE_MANAGER', 'SUPPLY_CHAIN_PLANNER', 'EXECUTIVE_LEADERSHIP', 'ADMIN')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User Store Authorization (Defines Store-Level RBAC Access)
CREATE TABLE IF NOT EXISTS user_store_access (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    store_nbr INTEGER NOT NULL REFERENCES stores(store_nbr) ON DELETE CASCADE,
    access_level VARCHAR(32) NOT NULL DEFAULT 'READ_WRITE' CHECK (access_level IN ('READ_ONLY', 'READ_WRITE', 'ADMIN')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_store UNIQUE (user_id, store_nbr)
);

CREATE INDEX IF NOT EXISTS idx_user_store_access ON user_store_access(user_id, store_nbr);

-- Knowledge Documents Master (Approved Operational Material Only)
CREATE TABLE IF NOT EXISTS knowledge_documents (
    doc_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default_tenant',
    store_nbr INTEGER REFERENCES stores(store_nbr) ON DELETE SET NULL,
    family VARCHAR(64) REFERENCES product_families(family) ON DELETE SET NULL,
    doc_type VARCHAR(32) NOT NULL CHECK (doc_type IN ('PROMO_PLAN', 'OPERATIONAL_NOTE', 'HOLIDAY_EVENT', 'MODEL_EXPLANATION', 'SUPPLIER_POLICY')),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    approved_status BOOLEAN NOT NULL DEFAULT TRUE,
    valid_from DATE,
    valid_to DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_docs_store ON knowledge_documents(store_nbr, family, approved_status);

-- Knowledge Document Chunks (Hybrid RRF Vector + Lexical Search)
CREATE TABLE IF NOT EXISTS knowledge_document_chunks (
    chunk_id VARCHAR(64) PRIMARY KEY,
    doc_id VARCHAR(64) NOT NULL REFERENCES knowledge_documents(doc_id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding vector(384), -- pgvector embeddings
    search_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON knowledge_document_chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_tsv ON knowledge_document_chunks USING gin(search_tsv);
CREATE INDEX IF NOT EXISTS idx_chunks_vector ON knowledge_document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Chat Sessions (Scoped by User and Selected Store)
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default_tenant',
    user_id VARCHAR(64) NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    store_nbr INTEGER REFERENCES stores(store_nbr) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL DEFAULT 'Demand Intelligence Consultation',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id, store_nbr, updated_at DESC);

-- Chat Turns (Messages & Grounding Sources)
CREATE TABLE IF NOT EXISTS chat_turns (
    turn_id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    message TEXT NOT NULL,
    cited_sources JSONB DEFAULT '[]'::jsonb,
    grounded_verified BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_turns_session ON chat_turns(session_id, created_at ASC);

-- Conversation Summaries (Layer 2 Memory Storage)
CREATE TABLE IF NOT EXISTS conversation_summaries (
    summary_id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    turn_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_summaries_session ON conversation_summaries(session_id);

-- User Preferences (Layer 3 Durable Memory Storage)
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id VARCHAR(64) PRIMARY KEY REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default_tenant',
    default_store_nbr INTEGER REFERENCES stores(store_nbr) ON DELETE SET NULL,
    preferred_theme VARCHAR(32) NOT NULL DEFAULT 'WARM_MINIMAL',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 5. ROW-LEVEL SECURITY (RLS) POLICIES ON ALL TABLES
-- ============================================================================

-- Enable RLS on Every Table
ALTER TABLE stores ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_families ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE supplier_lead_times ENABLE ROW LEVEL SECURITY;
ALTER TABLE promotions ENABLE ROW LEVEL SECURITY;
ALTER TABLE holiday_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE inbound_shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecast_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecast_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecast_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_plan_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_order_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_store_access ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Base Public / Read Policies (Master Catalogs)
CREATE POLICY "Public Read Stores" ON stores FOR SELECT USING (true);
CREATE POLICY "Public Read Product Families" ON product_families FOR SELECT USING (true);
CREATE POLICY "Public Read Holiday Events" ON holiday_events FOR SELECT USING (true);
CREATE POLICY "Public Read Forecast Runs" ON forecast_runs FOR SELECT USING (true);

-- Store-Scoped Policies for Authenticated Operations
CREATE POLICY "User Store Read Daily Sales" ON daily_sales FOR SELECT USING (
    EXISTS (SELECT 1 FROM user_store_access usa WHERE usa.user_id = auth.uid()::text AND usa.store_nbr = daily_sales.store_nbr)
    OR auth.role() = 'service_role'
);

CREATE POLICY "User Store Read Inventory" ON inventory_snapshots FOR SELECT USING (
    EXISTS (SELECT 1 FROM user_store_access usa WHERE usa.user_id = auth.uid()::text AND usa.store_nbr = inventory_snapshots.store_nbr)
    OR auth.role() = 'service_role'
);

CREATE POLICY "User Store Read Forecasts" ON forecast_predictions FOR SELECT USING (
    EXISTS (SELECT 1 FROM user_store_access usa WHERE usa.user_id = auth.uid()::text AND usa.store_nbr = forecast_predictions.store_nbr)
    OR auth.role() = 'service_role'
);

CREATE POLICY "User Store Order Plans" ON order_plans FOR ALL USING (
    created_by_user_id = auth.uid()::text 
    OR EXISTS (SELECT 1 FROM user_store_access usa WHERE usa.user_id = auth.uid()::text AND usa.store_nbr = order_plans.store_nbr)
    OR auth.role() = 'service_role'
);

CREATE POLICY "User Store Purchase Orders" ON purchase_orders FOR ALL USING (
    submitted_by_user_id = auth.uid()::text 
    OR EXISTS (SELECT 1 FROM user_store_access usa WHERE usa.user_id = auth.uid()::text AND usa.store_nbr = purchase_orders.store_nbr)
    OR auth.role() = 'service_role'
);

CREATE POLICY "User Chat Sessions" ON chat_sessions FOR ALL USING (
    user_id = auth.uid()::text OR auth.role() = 'service_role'
);

CREATE POLICY "User Chat Turns" ON chat_turns FOR ALL USING (
    EXISTS (SELECT 1 FROM chat_sessions cs WHERE cs.session_id = chat_turns.session_id AND (cs.user_id = auth.uid()::text OR auth.role() = 'service_role'))
);

CREATE POLICY "User Preferences Policy" ON user_preferences FOR ALL USING (
    user_id = auth.uid()::text OR auth.role() = 'service_role'
);
