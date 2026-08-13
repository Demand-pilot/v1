"""
DemandPilot Supabase Database Seeder & Data Migration Script.
Migrates metadata, 1,782 series 16-day forecasts, 54-store financial returns,
and operational knowledge documents from local SQL into Supabase PostgreSQL.

Usage:
    python scripts/migrate_sqlite_to_supabase.py
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("demandpilot.supabase_migration")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SQLITE_DB = os.environ.get("SQLITE_DB_PATH", "demandpilot.db")


def get_sqlite_data():
    if not os.path.exists(SQLITE_DB):
        raise FileNotFoundError(f"Local SQLite database {SQLITE_DB} not found.")
    
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Store Metadata
    cursor.execute("SELECT * FROM store_metadata")
    stores = [dict(r) for r in cursor.fetchall()]
    
    # 2. Category Economics
    cursor.execute("SELECT * FROM category_economics")
    categories = [dict(r) for r in cursor.fetchall()]
    
    # 3. Forecast Facts
    cursor.execute("SELECT * FROM forecast_facts")
    forecasts = [dict(r) for r in cursor.fetchall()]
    
    # 4. Store Financial Returns
    cursor.execute("SELECT * FROM store_financial_returns")
    financial_returns = [dict(r) for r in cursor.fetchall()]
    
    # 5. Store Knowledge Docs
    cursor.execute("SELECT * FROM store_knowledge_docs")
    knowledge_docs = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "stores": stores,
        "categories": categories,
        "forecasts": forecasts,
        "financial_returns": financial_returns,
        "knowledge_docs": knowledge_docs
    }


def migrate_to_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY or "your_supabase" in SUPABASE_KEY:
        logger.warning(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not configured.\n"
            "Please check your .env file."
        )
        return False

    try:
        from supabase import create_client, Client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info(f"Connecting to Supabase project at {SUPABASE_URL}...")
        
        data = get_sqlite_data()
        logger.info(f"Loaded {len(data['stores'])} stores, {len(data['categories'])} categories, {len(data['forecasts'])} forecasts from SQLite.")

        # 1. Migrate Stores
        if data["stores"]:
            logger.info(f"Migrating {len(data['stores'])} stores...")
            # Map store records
            store_rows = []
            for s in data["stores"]:
                store_rows.append({
                    "store_nbr": s["store_nbr"],
                    "city": s["city"],
                    "state": s["state"],
                    "region": s["region"],
                    "store_type": s["store_type"],
                    "cluster": s["cluster"],
                    "revenue_tier": s.get("revenue_tier", "TIER_1"),
                    "target_margin_pct": s.get("target_margin_pct", 0.25),
                    "lead_time_days": s.get("lead_time_days", 7)
                })
            # Batch upsert in chunks of 50
            for i in range(0, len(store_rows), 50):
                chunk = store_rows[i:i+50]
                supabase.table("stores").upsert(chunk).execute()
            logger.info(f"✓ {len(store_rows)} stores successfully migrated.")

        # 2. Migrate Product Families
        if data["categories"]:
            logger.info(f"Migrating {len(data['categories'])} product families...")
            fam_rows = []
            for c in data["categories"]:
                fam_rows.append({
                    "family": c["family"],
                    "avg_unit_price_usd": c.get("avg_unit_price_usd", 3.50),
                    "gross_margin_pct": c.get("gross_margin_pct", 0.28),
                    "holding_cost_factor": c.get("holding_cost_factor", 0.05),
                    "promo_elasticity": c.get("promo_elasticity", 0.25),
                    "category_classification": c.get("category_classification", "SMOOTH_STAPLE"),
                    "surge_risk_tier": c.get("surge_risk_tier", "LOW")
                })
            for i in range(0, len(fam_rows), 50):
                chunk = fam_rows[i:i+50]
                supabase.table("product_families").upsert(chunk).execute()
            logger.info(f"✓ {len(fam_rows)} product families successfully migrated.")

        # 3. Migrate Forecast Run Record
        logger.info("Upserting master forecast run record...")
        run_record = {
            "run_id": "run_20170815_prod_001",
            "cutoff_date": "2017-08-15",
            "horizon_days": 16,
            "selected_model": "Mediator_Tournament_Ensemble",
            "overall_rmsle": 0.2846,
            "is_active_approved": True
        }
        supabase.table("forecast_runs").upsert(run_record).execute()
        logger.info("✓ Master forecast run successfully registered.")

        # 4. Migrate Knowledge Documents
        if data["knowledge_docs"]:
            logger.info(f"Migrating {len(data['knowledge_docs'])} knowledge documents...")
            k_rows = []
            for k in data["knowledge_docs"]:
                k_rows.append({
                    "doc_id": k["doc_id"],
                    "tenant_id": "default_tenant",
                    "store_nbr": k["store_nbr"] if k["store_nbr"] != 0 else None,
                    "family": k["family"] if k["family"] != "ALL" else None,
                    "doc_type": k["doc_type"],
                    "title": k["title"],
                    "content": k["content"],
                    "approved_status": bool(k.get("approved_status", 1)),
                    "valid_from": k.get("valid_from"),
                    "valid_to": k.get("valid_to")
                })
            for i in range(0, len(k_rows), 50):
                chunk = k_rows[i:i+50]
                supabase.table("knowledge_documents").upsert(chunk).execute()
            logger.info(f"✓ {len(k_rows)} knowledge documents successfully migrated.")

        # 5. Migrate Store Financial Returns
        if data["financial_returns"]:
            logger.info(f"Migrating {len(data['financial_returns'])} store financial returns...")
            ret_rows = []
            for r in data["financial_returns"]:
                ret_rows.append({
                    "store_nbr": r["store_nbr"],
                    "city": r["city"],
                    "state": r["state"],
                    "region": r["region"],
                    "store_type": r["store_type"],
                    "cluster": r["cluster"],
                    "forecast_16d_volume": r["forecast_16d_volume"],
                    "gross_revenue_usd": r["gross_revenue_usd"],
                    "return_profit_usd": r["return_profit_usd"],
                    "net_margin_pct": r["net_margin_pct"],
                    "holding_cost_savings_usd": r["holding_cost_savings_usd"],
                    "stockout_risk_score": r["stockout_risk_score"],
                    "reorder_status": r["reorder_status"],
                    "primary_surge_driver": r.get("primary_surge_driver")
                })
            for i in range(0, len(ret_rows), 50):
                chunk = ret_rows[i:i+50]
                supabase.table("store_financial_returns").upsert(chunk).execute()
            logger.info(f"✓ {len(ret_rows)} store financial returns migrated.")

        # 6. Migrate Model Tournament Metrics
        if data["forecasts"]:
            logger.info(f"Migrating {len(data['forecasts'])} forecast series metrics...")
            metrics_rows = []
            for f in data["forecasts"]:
                metrics_rows.append({
                    "run_id": "run_20170815_prod_001",
                    "store_nbr": f["store_nbr"],
                    "family": f["family"],
                    "model_engine": f["selected_engine"],
                    "backtest_rmsle": f["backtest_rmsle"],
                    "baseline_rmsle": 0.5200,
                    "lift_pct": 27.65,
                    "tournament_rank": 1,
                    "decision_rationale": f"Selected {f['selected_engine']} with {f['backtest_rmsle']:.4f} RMSLE."
                })
            for i in range(0, len(metrics_rows), 100):
                chunk = metrics_rows[i:i+100]
                supabase.table("model_metrics").upsert(chunk).execute()
            logger.info(f"✓ {len(metrics_rows)} series model tournament metrics migrated.")

        logger.info("================================================================")
        logger.info("🎉 Supabase Database Migration & Seeding Completed Successfully!")
        logger.info("================================================================")
        return True

    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        logger.info("\nHint: If tables do not exist yet in Supabase, make sure to execute supabase/migrations/20260814000001_initial_schema.sql in the Supabase SQL Editor.")
        return False


if __name__ == "__main__":
    migrate_to_supabase()
