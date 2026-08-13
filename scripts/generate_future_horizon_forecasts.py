"""
DemandPilot reference-metadata seeding for the SQLite database.

SCOPE: this script seeds genuine reference metadata only — store metadata, category
economics, and clearly-labelled example knowledge documents.

It does NOT produce forecasts. The previous `generate_forecast_facts_and_returns()`
function was deleted: it fabricated every `forecast_facts` row from
`base_vol * dow_factor * payday_factor * school_factor` and drew "backtest RMSLE"
from `np.random.normal`, with no model and no `train.csv` involved. Forecast facts are
now written exclusively by the real inference path (Phase 3).

Until that path runs, `forecast_facts` is legitimately empty and the API must report an
empty state rather than substitute numbers.
"""

import os
import sqlite3

DB_PATH = os.environ.get("SQLITE_DB_PATH", "demandpilot.db")

# Resolved relative to this file, not the working directory, so the script works from
# anywhere and under pytest.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(_REPO_ROOT, "src", "orchestration", "db", "schema.sql")

def initialize_database():
    """Initializes the database schema cleanly."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript("""
        DROP TABLE IF EXISTS forecast_facts;
        DROP TABLE IF EXISTS store_financial_returns;
        DROP TABLE IF EXISTS forecast_runs;
        DROP TABLE IF EXISTS category_economics;
        DROP TABLE IF EXISTS store_metadata;
        DROP TABLE IF EXISTS store_knowledge_docs;
        DROP TABLE IF EXISTS chat_turns;
        DROP TABLE IF EXISTS conversation_summaries;
        DROP TABLE IF EXISTS chat_sessions;
        DROP TABLE IF EXISTS user_preferences;
        DROP TABLE IF EXISTS promo_elasticity;
    """)
    with open(SCHEMA_PATH, "r") as f:
        cursor.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"[1/4] Initialized clean SQL database schema at {DB_PATH}")

def seed_store_metadata():
    """Seeds all 54 stores across Ecuador."""
    # 54 Ecuador Stores metadata
    stores_data = [
        (1, "Quito", "Pichincha", "Sierra", "D", 13, "TIER_1", 0.26, 6),
        (2, "Quito", "Pichincha", "Sierra", "D", 13, "TIER_2", 0.25, 6),
        (3, "El Carmen", "Manabi", "Coast", "D", 8, "TIER_3", 0.24, 10),
        (4, "Quito", "Pichincha", "Sierra", "D", 9, "TIER_2", 0.25, 6),
        (5, "Santo Domingo", "Santo Domingo", "Coast", "D", 4, "TIER_2", 0.24, 8),
        (6, "Quito", "Pichincha", "Sierra", "D", 13, "TIER_2", 0.25, 6),
        (7, "Quito", "Pichincha", "Sierra", "D", 8, "TIER_2", 0.25, 6),
        (8, "Quito", "Pichincha", "Sierra", "D", 8, "TIER_1", 0.26, 6),
        (9, "Quito", "Pichincha", "Sierra", "B", 6, "TIER_1", 0.27, 7),
        (10, "Quito", "Pichincha", "Sierra", "C", 15, "TIER_3", 0.23, 7),
        (11, "Cayambe", "Pichincha", "Sierra", "B", 6, "TIER_2", 0.25, 7),
        (12, "Latacunga", "Cotopaxi", "Sierra", "C", 15, "TIER_3", 0.24, 8),
        (13, "Latacunga", "Cotopaxi", "Sierra", "C", 15, "TIER_3", 0.24, 8),
        (14, "Quito", "Pichincha", "Sierra", "A", 1, "TIER_1", 0.28, 7),
        (15, "Ibarra", "Imbabura", "Sierra", "C", 15, "TIER_3", 0.23, 8),
        (16, "Santo Domingo", "Santo Domingo", "Coast", "C", 3, "TIER_3", 0.24, 8),
        (17, "Quito", "Pichincha", "Sierra", "C", 12, "TIER_2", 0.25, 6),
        (18, "Quito", "Pichincha", "Sierra", "B", 16, "TIER_2", 0.26, 6),
        (19, "Guaranda", "Bolivar", "Sierra", "C", 15, "TIER_3", 0.23, 9),
        (20, "Quito", "Pichincha", "Sierra", "B", 6, "TIER_2", 0.25, 6),
        (21, "Santo Domingo", "Santo Domingo", "Coast", "B", 6, "TIER_2", 0.25, 8),
        (22, "Puyo", "Pastaza", "Oriente", "C", 7, "TIER_3", 0.24, 11),
        (23, "Ambato", "Tungurahua", "Sierra", "D", 9, "TIER_2", 0.25, 7),
        (24, "Guayaquil", "Guayas", "Coast", "D", 1, "TIER_1", 0.27, 9),
        (25, "Guayaquil", "Guayas", "Coast", "D", 1, "TIER_1", 0.28, 10),
        (26, "Guayaquil", "Guayas", "Coast", "D", 10, "TIER_2", 0.25, 9),
        (27, "Daule", "Guayas", "Coast", "D", 1, "TIER_2", 0.26, 9),
        (28, "Guayaquil", "Guayas", "Coast", "E", 10, "TIER_3", 0.23, 10),
        (29, "Guayaquil", "Guayas", "Coast", "E", 10, "TIER_3", 0.23, 10),
        (30, "Guayaquil", "Guayas", "Coast", "C", 3, "TIER_3", 0.24, 9),
        (31, "Babahoyo", "Los Rios", "Coast", "B", 10, "TIER_2", 0.25, 9),
        (32, "Guayaquil", "Guayas", "Coast", "C", 3, "TIER_3", 0.24, 9),
        (33, "Quevedo", "Los Rios", "Coast", "C", 3, "TIER_3", 0.24, 9),
        (34, "Guayaquil", "Guayas", "Coast", "B", 6, "TIER_2", 0.25, 9),
        (35, "Playas", "Guayas", "Coast", "C", 3, "TIER_3", 0.23, 11),
        (36, "Libertad", "Guayas", "Coast", "E", 10, "TIER_3", 0.23, 11),
        (37, "Cuenca", "Azuay", "Sierra", "D", 2, "TIER_1", 0.27, 8),
        (38, "Loja", "Loja", "Sierra", "D", 4, "TIER_2", 0.25, 9),
        (39, "Cuenca", "Azuay", "Sierra", "B", 6, "TIER_2", 0.26, 8),
        (40, "Machala", "El Oro", "Coast", "C", 3, "TIER_3", 0.24, 10),
        (41, "Machala", "El Oro", "Coast", "D", 4, "TIER_2", 0.26, 10),
        (42, "Cuenca", "Azuay", "Sierra", "D", 2, "TIER_2", 0.26, 8),
        (43, "Esmeraldas", "Esmeraldas", "Coast", "E", 10, "TIER_3", 0.22, 12),
        (44, "Quito", "Pichincha", "Sierra", "A", 5, "TIER_1", 0.29, 7),
        (45, "Quito", "Pichincha", "Sierra", "A", 11, "TIER_1", 0.29, 7),
        (46, "Quito", "Pichincha", "Sierra", "A", 14, "TIER_1", 0.29, 7),
        (47, "Quito", "Pichincha", "Sierra", "A", 14, "TIER_1", 0.29, 7),
        (48, "Quito", "Pichincha", "Sierra", "A", 14, "TIER_1", 0.28, 7),
        (49, "Quito", "Pichincha", "Sierra", "A", 11, "TIER_1", 0.28, 7),
        (50, "Ambato", "Tungurahua", "Sierra", "A", 14, "TIER_1", 0.28, 7),
        (51, "Guayaquil", "Guayas", "Coast", "A", 17, "TIER_1", 0.29, 10),
        (52, "Manta", "Manabi", "Coast", "A", 11, "TIER_2", 0.27, 11),
        (53, "Manta", "Manabi", "Coast", "D", 13, "TIER_2", 0.26, 11),
        (54, "El Carmen", "Manabi", "Coast", "C", 3, "TIER_3", 0.24, 10)
    ]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO store_metadata (
            store_nbr, city, state, region, store_type, cluster, revenue_tier, target_margin_pct, lead_time_days
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, stores_data)
    conn.commit()
    conn.close()
    print(f"[2/4] Seeded {len(stores_data)} Ecuador stores into store_metadata")

def seed_category_economics():
    """Seeds all 33 competition product families with economic prices & margins."""
    categories = [
        ("AUTOMOTIVE", 8.50, 0.32, 0.06, 0.35, "STANDARD", "LOW"),
        ("BABY CARE", 6.20, 0.30, 0.05, 0.28, "SMOOTH_STAPLE", "LOW"),
        ("BEAUTY", 7.80, 0.38, 0.04, 0.42, "PROMO_ELASTIC", "MEDIUM"),
        ("BEVERAGES", 2.20, 0.25, 0.03, 0.37, "SMOOTH_STAPLE", "MEDIUM"),
        ("BOOKS", 12.00, 0.45, 0.08, 0.00, "PERMANENT_ZERO", "NONE"),
        ("BREAD/BAKERY", 1.80, 0.24, 0.02, 0.22, "SMOOTH_STAPLE", "LOW"),
        ("CELEBRATION", 4.50, 0.40, 0.07, 0.55, "PROMO_ELASTIC", "HIGH"),
        ("CLEANING", 3.20, 0.27, 0.04, 0.31, "SMOOTH_STAPLE", "LOW"),
        ("DAIRY", 2.40, 0.22, 0.03, 0.26, "SMOOTH_STAPLE", "LOW"),
        ("DELI", 4.80, 0.28, 0.05, 0.29, "SMOOTH_STAPLE", "LOW"),
        ("EGGS", 2.10, 0.20, 0.02, 0.18, "SMOOTH_STAPLE", "LOW"),
        ("FROZEN FOODS", 4.20, 0.30, 0.06, 0.33, "SMOOTH_STAPLE", "LOW"),
        ("GROCERY I", 3.60, 0.24, 0.03, 0.43, "SMOOTH_STAPLE", "LOW"),
        ("GROCERY II", 3.10, 0.25, 0.04, 0.38, "SMOOTH_STAPLE", "LOW"),
        ("HARDWARE", 9.40, 0.35, 0.06, 0.20, "STANDARD", "LOW"),
        ("HOME AND KITCHEN I", 8.80, 0.38, 0.07, 0.58, "PROMO_ELASTIC_SURGE", "HIGH"),
        ("HOME AND KITCHEN II", 7.50, 0.36, 0.07, 0.54, "PROMO_ELASTIC_SURGE", "HIGH"),
        ("HOME APPLIANCES", 45.00, 0.32, 0.10, 0.62, "PROMO_ELASTIC_SURGE", "HIGH"),
        ("HOME CARE", 3.80, 0.28, 0.04, 0.37, "SMOOTH_STAPLE", "LOW"),
        ("LADIESWEAR", 14.50, 0.44, 0.09, 0.68, "PROMO_ELASTIC_SURGE", "HIGH"),
        ("LAWN AND GARDEN", 6.80, 0.34, 0.06, 0.45, "PROMO_ELASTIC", "MEDIUM"),
        ("LINGERIE", 11.20, 0.42, 0.08, 0.50, "PROMO_ELASTIC", "MEDIUM"),
        ("LIQUOR,WINE,BEER", 8.90, 0.33, 0.05, 0.48, "PROMO_ELASTIC", "MEDIUM"),
        ("MAGAZINES", 4.00, 0.35, 0.05, 0.15, "STANDARD", "LOW"),
        ("MEATS", 5.80, 0.23, 0.04, 0.25, "SMOOTH_STAPLE", "LOW"),
        ("PERSONAL CARE", 3.40, 0.29, 0.04, 0.32, "SMOOTH_STAPLE", "LOW"),
        ("PET SUPPLIES", 6.50, 0.32, 0.05, 0.30, "STANDARD", "LOW"),
        ("PLAYERS AND ELECTRONICS", 28.00, 0.30, 0.08, 0.52, "PROMO_ELASTIC", "HIGH"),
        ("POULTRY", 4.90, 0.22, 0.03, 0.24, "SMOOTH_STAPLE", "LOW"),
        ("PREPARED FOODS", 3.50, 0.30, 0.03, 0.28, "SMOOTH_STAPLE", "LOW"),
        ("PRODUCE", 1.60, 0.21, 0.03, 0.28, "SMOOTH_STAPLE", "LOW"),
        ("SCHOOL AND OFFICE SUPPLIES", 4.20, 0.36, 0.05, 0.74, "PROMO_ELASTIC_SURGE", "HIGH"),
        ("SEAFOOD", 6.90, 0.26, 0.05, 0.34, "SMOOTH_STAPLE", "MEDIUM")
    ]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO category_economics (
            family, avg_unit_price_usd, gross_margin_pct, holding_cost_factor, promo_elasticity, category_classification, surge_risk_tier
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, categories)
    conn.commit()
    conn.close()
    print(f"[3/4] Seeded {len(categories)} product families into category_economics")

def seed_store_knowledge_docs():
    """
    Seeds EXAMPLE store operational notes, all tagged source='SEED_EXAMPLE'.

    These are illustrative logistics fixtures (lead times, buffer levels, staging advice),
    NOT operator-authored notes and NOT model output. Every row is tagged so the retrieval
    layer and the verification gate can refuse to cite them as measured evidence.

    Deliberately stripped from the original seed text: the "+145% demand spike",
    "promotional density increases to 44.1%", and "+8.0% shopping surge" claims. Those
    were fabricated forecast statistics with no model behind them, and the verification
    gate was cross-checking LLM answers against them — which is how a made-up number
    became a "verified" fact. Qualitative direction is kept; invented magnitudes are not.
    """
    docs = [
        ("doc_014_school", 14, "SCHOOL AND OFFICE SUPPLIES", "PROMO_PLAN",
         "Store 14 Sierra Academic Campaign Restock",
         "Store 14 (Quito, Sierra) runs an academic-season restock campaign from mid-August. "
         "Replenishment is served by the Central Sierra Logistics Hub at a 7-day lead time. "
         "Expected demand magnitude is not asserted here — see the forecast run for numbers.",
         1, "2017-08-01", "2017-09-15", "SEED_EXAMPLE"),
        ("doc_014_payday", 14, "BEVERAGES", "OPERATIONAL_NOTE",
         "Store 14 Bi-Weekly Salary Payday Staging",
         "Salary disbursements land on the 15th and 30th. High-velocity Beverage and Grocery I "
         "aisles are pre-staged with pallets the following morning to avoid stockout breaches. "
         "Surge magnitude is not asserted here — see the forecast run for numbers.",
         1, "2017-01-01", "2017-12-31", "SEED_EXAMPLE"),
        ("doc_025_payday", 25, "BEVERAGES", "OPERATIONAL_NOTE",
         "Store 25 Guayaquil Payday Surge Protocol",
         "Store 25 in Guayaquil sees elevated coastal transaction velocity around the salary "
         "cycle. Recommended reorder lead time is 10 days.",
         1, "2017-01-01", "2017-12-31", "SEED_EXAMPLE"),
        ("doc_052_seafood", 52, "SEAFOOD", "OPERATIONAL_NOTE",
         "Store 52 Manta Port Transit Buffer",
         "Store 52 in Manta operates near port facilities. Coastal transit lead time is 11 days. "
         "Safety buffer must be maintained above 180 units.",
         1, "2017-01-01", "2017-12-31", "SEED_EXAMPLE"),
        ("doc_national_oil", 0, "ALL", "MODEL_EXPLANATION",
         "National Macro Oil Price and Wage Calendar Integration",
         "Ecuador macroeconomic wage cycles on 15th/30th and WTI crude oil price fluctuations "
         "are modelled as candidate drivers of purchasing power across Sierra and Coast stores. "
         "Whether they carry signal is an empirical question answered by the evaluation run.",
         1, "2017-01-01", "2017-12-31", "SEED_EXAMPLE")
    ]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO store_knowledge_docs (
            doc_id, store_nbr, family, doc_type, title, content, approved_status,
            valid_from, valid_to, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, docs)
    conn.commit()
    conn.close()
    print(f"[4/4] Seeded {len(docs)} SEED_EXAMPLE knowledge documents into store_knowledge_docs")

if __name__ == "__main__":
    print("=== Seeding DemandPilot reference metadata (no forecasts are produced here) ===")
    initialize_database()
    seed_store_metadata()
    seed_category_economics()
    seed_store_knowledge_docs()
    print("=== Reference metadata seeding complete ===")
    print("NOTE: forecast_facts is intentionally empty. It is populated only by the")
    print("      real inference path (scripts/train_pipeline.py, Phase 3).")
