-- DemandPilot Production Database Schema — PostgreSQL & SQLite Compatible

-- 1. Store Master Metadata (54 Stores across Ecuador)
CREATE TABLE IF NOT EXISTS store_metadata (
    store_nbr INTEGER PRIMARY KEY,
    city VARCHAR(64) NOT NULL,
    state VARCHAR(64) NOT NULL,
    region VARCHAR(32) NOT NULL, -- 'Sierra', 'Coast', 'Oriente'
    store_type VARCHAR(8) NOT NULL, -- 'A', 'B', 'C', 'D', 'E'
    cluster INTEGER NOT NULL,
    revenue_tier VARCHAR(16) NOT NULL DEFAULT 'TIER_1',
    target_margin_pct FLOAT NOT NULL DEFAULT 0.25,
    lead_time_days INTEGER NOT NULL DEFAULT 7
);

-- 2. Category Economics & Margin Metadata (33 Families)
CREATE TABLE IF NOT EXISTS category_economics (
    family VARCHAR(64) PRIMARY KEY,
    avg_unit_price_usd FLOAT NOT NULL DEFAULT 3.50,
    gross_margin_pct FLOAT NOT NULL DEFAULT 0.28,
    holding_cost_factor FLOAT NOT NULL DEFAULT 0.05,
    promo_elasticity FLOAT NOT NULL DEFAULT 0.25,
    category_classification VARCHAR(32) NOT NULL DEFAULT 'SMOOTH_STAPLE',
    surge_risk_tier VARCHAR(16) NOT NULL DEFAULT 'LOW'
);

-- 3. Forecast Runs & Metrics
CREATE TABLE IF NOT EXISTS forecast_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    cutoff_date DATE NOT NULL,
    horizon_days INTEGER NOT NULL DEFAULT 16,
    selected_model VARCHAR(64) NOT NULL,
    overall_rmsle FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Forecast Structured Facts (1,782 Series Authoritative)
CREATE TABLE IF NOT EXISTS forecast_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id VARCHAR(64) NOT NULL,
    store_nbr INTEGER NOT NULL,
    family VARCHAR(64) NOT NULL,
    selected_engine VARCHAR(64) NOT NULL,
    backtest_rmsle FLOAT NOT NULL,
    forecast_16d_sum FLOAT NOT NULL,
    forecast_avg_daily FLOAT NOT NULL,
    reorder_point FLOAT NOT NULL,
    safety_stock FLOAT NOT NULL,
    surge_percentage FLOAT DEFAULT 0.0,
    promo_density_train FLOAT DEFAULT 0.0,
    promo_density_test FLOAT DEFAULT 0.0,
    projected_revenue_usd FLOAT DEFAULT 0.0,
    projected_profit_usd FLOAT DEFAULT 0.0,
    daily_forecasts_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES forecast_runs(run_id),
    FOREIGN KEY (store_nbr) REFERENCES store_metadata(store_nbr),
    FOREIGN KEY (family) REFERENCES category_economics(family)
);

CREATE INDEX IF NOT EXISTS idx_forecast_store_fam ON forecast_facts(store_nbr, family);

-- 5. Store Financial Returns (54 Stores Aggregate Return Profits)
CREATE TABLE IF NOT EXISTS store_financial_returns (
    store_nbr INTEGER PRIMARY KEY,
    city VARCHAR(64) NOT NULL,
    state VARCHAR(64) NOT NULL,
    region VARCHAR(32) NOT NULL,
    store_type VARCHAR(8) NOT NULL,
    cluster INTEGER NOT NULL,
    forecast_16d_volume FLOAT NOT NULL,
    gross_revenue_usd FLOAT NOT NULL,
    return_profit_usd FLOAT NOT NULL,
    net_margin_pct FLOAT NOT NULL,
    holding_cost_savings_usd FLOAT NOT NULL,
    stockout_risk_score FLOAT NOT NULL,
    reorder_status VARCHAR(16) NOT NULL, -- 'OK', 'WARNING', 'CRITICAL'
    primary_surge_driver VARCHAR(128),
    FOREIGN KEY (store_nbr) REFERENCES store_metadata(store_nbr)
);

-- 6. Store Knowledge & Operational Documents
CREATE TABLE IF NOT EXISTS store_knowledge_docs (
    doc_id VARCHAR(64) PRIMARY KEY,
    store_nbr INTEGER NOT NULL,
    family VARCHAR(64) NOT NULL,
    doc_type VARCHAR(32) NOT NULL, -- 'PROMO_PLAN', 'OPERATIONAL_NOTE', 'HOLIDAY_EVENT', 'MODEL_EXPLANATION'
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    approved_status BOOLEAN NOT NULL DEFAULT 1,
    valid_from DATE,
    valid_to DATE,
    embedding_json TEXT, -- Serialized vector embedding
    -- Provenance. 'SEED_EXAMPLE' rows are illustrative fixtures shipped with the repo and
    -- are NOT operator-authored notes; the agent must be able to tell them apart from
    -- 'OPERATOR' rows before citing them as evidence.
    source VARCHAR(32) NOT NULL DEFAULT 'OPERATOR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_doc_store_fam ON store_knowledge_docs(store_nbr, family);

-- 7. Chat Sessions & 3-Layer Memory Storage
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default_tenant',
    user_id VARCHAR(64) NOT NULL,
    user_role VARCHAR(32) NOT NULL DEFAULT 'STORE_MANAGER',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_turns (
    turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(64) NOT NULL,
    role VARCHAR(16) NOT NULL, -- 'user', 'assistant', 'system'
    message TEXT NOT NULL,
    cited_source_ids TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS conversation_summaries (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(64) NOT NULL,
    summary_text TEXT NOT NULL,
    turn_count INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default_tenant',
    user_role VARCHAR(32) NOT NULL DEFAULT 'STORE_MANAGER',
    authorized_stores_json TEXT NOT NULL, -- JSON list of store numbers e.g. [1, 14, 25, 52]
    default_store_nbr INTEGER DEFAULT 14,
    default_family VARCHAR(64) DEFAULT 'SCHOOL AND OFFICE SUPPLIES',
    preferred_unit VARCHAR(16) DEFAULT 'units',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Promotional Elasticity Table
CREATE TABLE IF NOT EXISTS promo_elasticity (
    family VARCHAR(64) PRIMARY KEY,
    elasticity_score FLOAT NOT NULL,
    category_classification VARCHAR(32) NOT NULL,
    surge_risk_tier VARCHAR(16) NOT NULL
);

-- 8b. Observed inventory positions.
-- The store operations snapshot previously invented on-hand quantities in code
-- (480.0 for Sierra school supplies, 1240.0 for beverages, forecast_avg * 8 otherwise)
-- because no table held them. It now reads this table and reports NULL when a position
-- is unknown, because an unknown stock level is not a zero and is not a guess.
CREATE TABLE IF NOT EXISTS inventory_positions (
    store_nbr INTEGER NOT NULL,
    family VARCHAR(64) NOT NULL,
    on_hand_units FLOAT NOT NULL,
    observed_at TIMESTAMP NOT NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'WMS',
    PRIMARY KEY (store_nbr, family),
    FOREIGN KEY (store_nbr) REFERENCES store_metadata(store_nbr)
);

-- 8c. Observed daily sales history.
-- Previously the snapshot "reconstructed" 28-day and 56-day actual history from the
-- forecast's own average velocity and returned it as `actual_history_28d`. That is
-- forecast echoed back as observation. Real observations live here or nowhere.
CREATE TABLE IF NOT EXISTS sales_history (
    store_nbr INTEGER NOT NULL,
    family VARCHAR(64) NOT NULL,
    date DATE NOT NULL,
    units FLOAT NOT NULL,
    PRIMARY KEY (store_nbr, family, date)
);

CREATE INDEX IF NOT EXISTS idx_sales_hist_store_fam_date
    ON sales_history(store_nbr, family, date);

-- 9. Order Plans & Replenishment Drafts
CREATE TABLE IF NOT EXISTS order_plans (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default_tenant',
    store_nbr INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT', -- 'DRAFT', 'SUBMITTED', 'CANCELLED'
    created_by_user_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_plan_lines (
    id VARCHAR(64) PRIMARY KEY,
    order_plan_id VARCHAR(64) NOT NULL,
    family VARCHAR(64) NOT NULL,
    recommended_qty FLOAT NOT NULL DEFAULT 0.0,
    adjusted_qty FLOAT NOT NULL DEFAULT 0.0,
    reason TEXT,
    is_approved BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_plan_id, family),
    FOREIGN KEY (order_plan_id) REFERENCES order_plans(id)
);

CREATE INDEX IF NOT EXISTS idx_order_plan_lines_plan ON order_plan_lines(order_plan_id);

-- 10. Purchase Orders & Submission Records
CREATE TABLE IF NOT EXISTS purchase_orders (
    id VARCHAR(64) PRIMARY KEY,
    order_plan_id VARCHAR(64),
    po_number VARCHAR(64) NOT NULL UNIQUE,
    store_nbr INTEGER NOT NULL,
    supplier_name VARCHAR(128) NOT NULL DEFAULT 'Corporación Favorita Central Distribution Hub',
    total_units FLOAT NOT NULL,
    total_cost_usd FLOAT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'TRANSMITTED',
    submitted_by_user_id VARCHAR(64) NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estimated_delivery_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_purchase_orders_store ON purchase_orders(store_nbr);

CREATE TABLE IF NOT EXISTS purchase_order_lines (
    id VARCHAR(64) PRIMARY KEY,
    purchase_order_id VARCHAR(64) NOT NULL,
    family VARCHAR(64) NOT NULL,
    units FLOAT NOT NULL,
    unit_price_usd FLOAT NOT NULL DEFAULT 3.50,
    line_total_usd FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id)
);

CREATE INDEX IF NOT EXISTS idx_po_lines_po ON purchase_order_lines(purchase_order_id);

-- 11. Order Audit Events Trail
CREATE TABLE IF NOT EXISTS order_audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type VARCHAR(64) NOT NULL,
    entity_type VARCHAR(32) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    user_role VARCHAR(32) NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON order_audit_events(entity_id);
CREATE INDEX IF NOT EXISTS idx_chat_turns_session ON chat_turns(session_id);
CREATE INDEX IF NOT EXISTS idx_conv_summaries_session ON conversation_summaries(session_id);
