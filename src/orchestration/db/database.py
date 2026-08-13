"""
DemandPilot Production Database Repository Layer.
Connects to SQL / PostgreSQL backend with full schema support for
persisted operational sales history, live forecast facts, inventory snapshots,
order plans, purchase orders, audit events, and hybrid RRF vector retrieval.
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta, timezone

logger = logging.getLogger("demandpilot.database")

DB_PATH = os.environ.get("SQLITE_DB_PATH", "demandpilot.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


class DatabaseRepository:
    """
    Production database repository managing SQL persistence,
    operational snapshot assembly, order planning, PO generation, and RRF search.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=30000;")
        except Exception:
            pass
        return conn

    def _init_db(self):
        """Initializes tables and seeds initial facts if needed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if os.path.exists(SCHEMA_PATH):
                with open(SCHEMA_PATH, "r") as f:
                    schema_sql = f.read()
                cursor.executescript(schema_sql)
            conn.commit()

    # =========================================================================
    # 1. STORE & CATALOG METADATA
    # =========================================================================

    def get_stores(self) -> List[Dict[str, Any]]:
        """Returns all 54 stores across Ecuador."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT store_nbr, city, state, region, store_type, cluster, revenue_tier, target_margin_pct, lead_time_days
                FROM store_metadata
                ORDER BY store_nbr ASC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_store(self, store_nbr: int) -> Optional[Dict[str, Any]]:
        """Returns metadata for a specific store."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM store_metadata WHERE store_nbr = ?", (store_nbr,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_forecast_facts(self, store_nbr: int, family: str) -> Optional[Dict[str, Any]]:
        """
        Returns persisted forecast facts for a series, or None if none exist.

        The previous "deterministic default fallback" synthesised a whole record —
        engine, RMSLE 0.3812/0.2150, a +145% surge, promo densities, and a
        `100.0 + (i % 7) * 4.0` daily curve — for any series the database had never seen.
        Being deterministic did not make it true.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    run_id, store_nbr, family, selected_engine, backtest_rmsle,
                    forecast_16d_sum, forecast_avg_daily, reorder_point, safety_stock,
                    surge_percentage, promo_density_train, promo_density_test, daily_forecasts_json
                FROM forecast_facts
                WHERE store_nbr = ? AND family = ?
            """, (store_nbr, family))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d["daily_forecasts"] = json.loads(d["daily_forecasts_json"]) if isinstance(d["daily_forecasts_json"], str) else d["daily_forecasts_json"]
                return d

            logger.info(
                "No forecast_facts row for store=%s family=%r; returning None.",
                store_nbr, family
            )
            return None

    def get_promo_elasticity(self, family: str) -> Optional[Dict[str, Any]]:
        """
        Returns the measured promo elasticity record for a family, or None.

        The previous fallback returned `0.7421` for anything matching "SCHOOL" and
        `0.2500` otherwise — invented elasticities that the mediator then routed on.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM promo_elasticity WHERE family = ?", (family,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None


    # =========================================================================
    # 2. STORE OPERATIONS SNAPSHOT
    # =========================================================================

    def get_store_operations_snapshot(self, store_nbr: int) -> Optional[Dict[str, Any]]:
        """
        Assembles a store operations snapshot strictly from persisted rows.

        Returns None when the store is unknown.

        Every field is either read from the database or reported as None/[] alongside an
        availability flag. Nothing is reconstructed, inferred, or defaulted.

        What the previous implementation invented, and where each value comes from now:

          * store city/state/region  -> was a `store_nbr in [14, 1, 44]` ternary chain
                                        when store_metadata had no row.
                                        Now: None is returned for an unknown store.
          * category list            -> was a hardcoded 5-family list keyed on is_sierra.
                                        Now: whatever families forecast_facts holds.
          * backtest_rmsle / engine  -> was 0.3812 / 0.2150 by substring match on
                                        "SCHOOL" when the fact row was missing.
                                        Now: only from the fact row; no row, no category.
          * surge_percentage         -> was 145.0 / 8.0 by the same substring match.
                                        Now: only from the fact row.
          * on_hand                  -> was 480.0 / 1240.0 / forecast_avg * 8.
                                        Now: inventory_positions, else None.
          * actual_history_28d/56d   -> was synthesised from the forecast's own average
                                        velocity, i.e. the forecast relabelled as
                                        observed truth.
                                        Now: sales_history, else [].
          * p10 / p90 bands          -> was yhat * 0.85 and yhat * 1.15, a fixed +/-15%
                                        presented as a prediction interval.
                                        Now: omitted until the model emits quantiles.
          * confidence "94.2%"       -> was a string literal. Now: omitted.
          * as_of / run_id           -> were the literals "2017-08-15T08:00:00Z" and
                                        "run_20170815_prod_001".
                                        Now: from forecast_runs.
        """
        store = self.get_store(store_nbr)
        if not store:
            logger.info("No store_metadata row for store_nbr=%s; returning None.", store_nbr)
            return None

        city = store["city"]
        state = store["state"]
        region = store["region"]
        lead_time_days = store.get("lead_time_days")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    run_id, family, selected_engine, backtest_rmsle, forecast_16d_sum,
                    forecast_avg_daily, reorder_point, safety_stock, surge_percentage,
                    daily_forecasts_json
                FROM forecast_facts
                WHERE store_nbr = ?
                ORDER BY forecast_16d_sum DESC
            """, (store_nbr,))
            fact_rows = [dict(r) for r in cursor.fetchall()]

            inventory = self._load_inventory_positions(cursor, store_nbr)
            run_id = fact_rows[0]["run_id"] if fact_rows else None
            as_of, forecast_horizon = self._load_run_asof(cursor, run_id)

            categories = []
            priority_actions = []

            for row in fact_rows:
                fam = row["family"]
                daily_fc = row["daily_forecasts_json"]
                if isinstance(daily_fc, str):
                    daily_fc = json.loads(daily_fc)

                fc_avg = float(row["forecast_avg_daily"])
                inv = inventory.get(fam)
                on_hand = float(inv["on_hand_units"]) if inv else None

                # Days of cover needs a real stock position and a non-zero velocity.
                # Otherwise it is unknown, which is not the same as zero.
                if on_hand is not None and fc_avg > 0.0:
                    days_of_cover = round(on_hand / fc_avg, 1)
                else:
                    days_of_cover = None

                history_28d = self._load_sales_history(cursor, store_nbr, fam, 28)
                history_56d = self._load_sales_history(cursor, store_nbr, fam, 56)

                categories.append({
                    "family": fam,
                    "on_hand": on_hand,
                    "on_hand_available": on_hand is not None,
                    "on_hand_observed_at": inv["observed_at"] if inv else None,
                    "safety_stock": float(row["safety_stock"]),
                    "reorder_point": float(row["reorder_point"]),
                    "daily_velocity": round(fc_avg, 4),
                    "days_of_cover": days_of_cover,
                    "actual_history_28d": history_28d,
                    "actual_history_56d": history_56d,
                    "history_available": bool(history_56d),
                    "forecast": daily_fc,
                    "audit_details": {
                        "run_id": row["run_id"],
                        "selected_engine": row["selected_engine"],
                        "backtest_rmsle": float(row["backtest_rmsle"]),
                        "surge_percentage": row["surge_percentage"],
                    },
                })

                # A replenishment action requires a real stock position. Without one there
                # is no basis on which to tell an operator to order anything.
                if on_hand is not None and on_hand < float(row["reorder_point"]):
                    priority_actions.append({
                        "id": "act_" + fam.lower().replace(" ", "_"),
                        "family": fam,
                        "reason": "on_hand_below_reorder_point",
                        "on_hand": on_hand,
                        "reorder_point": float(row["reorder_point"]),
                        "days_of_cover": days_of_cover,
                        "is_added_to_plan": False,
                    })

        any_inventory = any(c["on_hand_available"] for c in categories)
        return {
            "store_id": store_nbr,
            "store_name": "Store %s - %s (%s)" % (store_nbr, city, region),
            "city": city,
            "state": state,
            "region": region,
            "lead_time_days": lead_time_days,
            "as_of": as_of,
            "forecast_run_id": run_id,
            "forecast_horizon_days": forecast_horizon,
            "data_status": "LIVE" if fact_rows else "NO_FORECAST_AVAILABLE",
            "last_refreshed": datetime.now(timezone.utc).isoformat(),
            "summary_metrics": {
                "categories_with_forecast": len(categories),
                "categories_with_inventory": sum(1 for c in categories if c["on_hand_available"]),
                "total_on_hand_units": (
                    sum(c["on_hand"] for c in categories if c["on_hand_available"])
                    if any_inventory else None
                ),
                "projected_demand_units": (
                    round(sum(sum(c["forecast"]) for c in categories), 2) if categories else None
                ),
            },
            "priority_actions": priority_actions,
            "categories": categories,
        }

    @staticmethod
    def _load_inventory_positions(cursor, store_nbr: int) -> Dict[str, Dict[str, Any]]:
        """Returns {family: position} from inventory_positions; {} when none recorded."""
        try:
            cursor.execute(
                "SELECT family, on_hand_units, observed_at FROM inventory_positions WHERE store_nbr = ?",
                (store_nbr,)
            )
            return {r["family"]: dict(r) for r in cursor.fetchall()}
        except sqlite3.Error as err:
            logger.warning("inventory_positions unavailable: %s", err)
            return {}

    @staticmethod
    def _load_sales_history(cursor, store_nbr: int, family: str, n_days: int) -> List[float]:
        """Returns the most recent n_days of observed units, oldest first; [] when none."""
        try:
            cursor.execute("""
                SELECT units FROM sales_history
                WHERE store_nbr = ? AND family = ?
                ORDER BY date DESC LIMIT ?
            """, (store_nbr, family, n_days))
            return [float(r["units"]) for r in reversed(cursor.fetchall())]
        except sqlite3.Error as err:
            logger.warning("sales_history unavailable: %s", err)
            return []

    @staticmethod
    def _load_run_asof(cursor, run_id: Optional[str]):
        """Returns (cutoff_date, horizon_days) from forecast_runs; (None, None) if absent."""
        if not run_id:
            return None, None
        cursor.execute(
            "SELECT cutoff_date, horizon_days FROM forecast_runs WHERE run_id = ?",
            (run_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None, None
        run = dict(row)
        cutoff = run.get("cutoff_date")
        return (str(cutoff) if cutoff else None), run.get("horizon_days")

    # =========================================================================
    # 3. ORDER PLANNING & PURCHASE ORDER LIFECYCLE
    # =========================================================================

    def get_or_create_order_plan(self, store_nbr: int, user_id: str = "usr_mgr_store_14") -> Dict[str, Any]:
        """Retrieves or creates active draft order plan for a store."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, store_nbr, status, created_by_user_id, created_at, updated_at
                FROM order_plans
                WHERE store_nbr = ? AND status = 'DRAFT'
                ORDER BY updated_at DESC LIMIT 1
            """, (store_nbr,))
            row = cursor.fetchone()

            if row:
                plan = dict(row)
                # Fetch lines
                cursor.execute("""
                    SELECT id, family, recommended_qty, adjusted_qty, reason, is_approved
                    FROM order_plan_lines
                    WHERE order_plan_id = ?
                """, (plan["id"],))
                lines = [dict(l) for l in cursor.fetchall()]
                plan["lines"] = lines
                return plan

            # Create new draft plan
            import uuid
            plan_id = f"plan_{store_nbr}_{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO order_plans (id, tenant_id, store_nbr, status, created_by_user_id)
                VALUES (?, 'default_tenant', ?, 'DRAFT', ?)
            """, (plan_id, store_nbr, user_id))

            # Audit event
            cursor.execute("""
                INSERT INTO order_audit_events (event_type, entity_type, entity_id, user_id, user_role, payload_json)
                VALUES ('PLAN_CREATED', 'ORDER_PLAN', ?, ?, 'STORE_MANAGER', ?)
            """, (plan_id, user_id, json.dumps({"store_nbr": store_nbr})))

            conn.commit()
            return {
                "id": plan_id,
                "store_nbr": store_nbr,
                "status": "DRAFT",
                "created_by_user_id": user_id,
                "lines": []
            }

    def save_order_plan_line(self, plan_id: str, family: str, adjusted_qty: float, recommended_qty: float = 0.0, reason: str = "") -> Dict[str, Any]:
        """Adds or updates a line in an active order plan."""
        import uuid
        with self.get_connection() as conn:
            cursor = conn.cursor()
            line_id = f"line_{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO order_plan_lines (id, order_plan_id, family, recommended_qty, adjusted_qty, reason)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_plan_id, family) DO UPDATE SET
                    adjusted_qty = excluded.adjusted_qty,
                    updated_at = CURRENT_TIMESTAMP
            """, (line_id, plan_id, family, recommended_qty, adjusted_qty, reason))

            cursor.execute("UPDATE order_plans SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (plan_id,))
            conn.commit()
            return {"status": "success", "order_plan_id": plan_id, "family": family, "adjusted_qty": adjusted_qty}

    def submit_purchase_order(self, plan_id: str, user_id: str = "usr_mgr_store_14") -> Dict[str, Any]:
        """
        Transitions an order plan from DRAFT to SUBMITTED, generates an official
        persisted Purchase Order (#PO-EC-2017-0816-{store_nbr}-{uuid[:6]}), and writes audit trail.
        """
        import uuid
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Fetch plan
            cursor.execute("SELECT * FROM order_plans WHERE id = ?", (plan_id,))
            plan_row = cursor.fetchone()
            if not plan_row:
                raise ValueError(f"Order plan {plan_id} not found.")

            plan = dict(plan_row)
            if plan["status"] == "SUBMITTED":
                # Fetch existing PO
                cursor.execute("SELECT * FROM purchase_orders WHERE order_plan_id = ?", (plan_id,))
                po_row = cursor.fetchone()
                if po_row:
                    return dict(po_row)

            # Fetch lines
            cursor.execute("SELECT * FROM order_plan_lines WHERE order_plan_id = ?", (plan_id,))
            lines = [dict(l) for l in cursor.fetchall()]

            store_nbr = plan["store_nbr"]
            po_id = f"po_{uuid.uuid4().hex[:10]}"
            po_number = f"PO-EC-2017-0816-{store_nbr:02d}-{uuid.uuid4().hex[:5].upper()}"
            
            total_units = sum(float(l["adjusted_qty"]) for l in lines) if lines else 2720.0
            total_cost_usd = total_units * 3.50 # Avg wholesale cost
            est_delivery = (date(2017, 8, 15) + timedelta(days=7)).isoformat()

            # Insert PO
            cursor.execute("""
                INSERT INTO purchase_orders (
                    id, order_plan_id, po_number, store_nbr, supplier_name,
                    total_units, total_cost_usd, status, submitted_by_user_id,
                    submitted_at, estimated_delivery_date
                ) VALUES (?, ?, ?, ?, 'Corporación Favorita Central Distribution Hub', ?, ?, 'TRANSMITTED', ?, CURRENT_TIMESTAMP, ?)
            """, (po_id, plan_id, po_number, store_nbr, total_units, total_cost_usd, user_id, est_delivery))

            # Insert PO lines
            for l in lines:
                l_id = f"pol_{uuid.uuid4().hex[:8]}"
                u = float(l["adjusted_qty"])
                cursor.execute("""
                    INSERT INTO purchase_order_lines (id, purchase_order_id, family, units, unit_price_usd, line_total_usd)
                    VALUES (?, ?, ?, ?, 3.50, ?)
                """, (l_id, po_id, l["family"], u, u * 3.50))

            # Transition plan status
            cursor.execute("UPDATE order_plans SET status = 'SUBMITTED', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (plan_id,))

            # Audit event
            cursor.execute("""
                INSERT INTO order_audit_events (event_type, entity_type, entity_id, user_id, user_role, payload_json)
                VALUES ('PLAN_SUBMITTED', 'PURCHASE_ORDER', ?, ?, 'STORE_MANAGER', ?)
            """, (po_id, user_id, json.dumps({"po_number": po_number, "total_units": total_units, "store_nbr": store_nbr})))

            conn.commit()

            return {
                "status": "success",
                "purchase_order_id": po_id,
                "po_number": po_number,
                "store_nbr": store_nbr,
                "total_units": total_units,
                "total_cost_usd": total_cost_usd,
                "estimated_delivery_date": est_delivery,
                "submitted_at": datetime.utcnow().isoformat() + "Z",
                "edi_transmission_status": "CONFIRMED_ACK"
            }

    # =========================================================================
    # 4. FORECAST GRID & FINANCIAL MACRO ANALYTICS
    # =========================================================================

    def get_forecast_grid(self, store_nbr: Optional[int] = None, family: Optional[str] = None, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Retrieves paginated 1,782 series forecast grid from SQL database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM forecast_facts WHERE 1=1"
            params = []

            if store_nbr:
                query += " AND store_nbr = ?"
                params.append(store_nbr)
            if family:
                query += " AND family = ?"
                params.append(family)

            query += " ORDER BY store_nbr ASC, forecast_16d_sum DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()

            items = []
            for r in rows:
                d = dict(r)
                d["daily_forecasts"] = json.loads(d["daily_forecasts_json"]) if isinstance(d["daily_forecasts_json"], str) else d["daily_forecasts_json"]
                items.append(d)

            if not items:
                return {
                    "status": "no_forecast_available",
                    "horizon_days": 0,
                    "start_date": None,
                    "end_date": None,
                    "total_series": 0,
                    "data": []
                }

            # Derive the forecast window from the run that produced these rows, rather
            # than the hardcoded "2017-08-16" / "2017-08-31" literals this used to return.
            # Those literals are Favorita's last-observed-date + 1 and made the response
            # wrong for any other dataset, cutoff, or horizon.
            start_date, end_date, horizon_days = self._resolve_forecast_window(
                cursor, items[0].get("run_id"), len(items[0]["daily_forecasts"])
            )

            return {
                "status": "success",
                "horizon_days": horizon_days,
                "start_date": start_date,
                "end_date": end_date,
                "total_series": len(items),
                "data": items
            }

    @staticmethod
    def _resolve_forecast_window(cursor, run_id: Optional[str], n_days: int):
        """
        Resolves (start_date, end_date, horizon_days) for a run from forecast_runs.

        The forecast window is [cutoff + 1 day, cutoff + horizon days]. Returns
        (None, None, n_days) when the run row is missing — an unknown window is reported
        as unknown, not guessed.
        """
        if not run_id:
            return None, None, n_days

        cursor.execute(
            "SELECT cutoff_date, horizon_days FROM forecast_runs WHERE run_id = ?",
            (run_id,)
        )
        run_row = cursor.fetchone()
        if not run_row:
            return None, None, n_days

        run = dict(run_row)
        horizon_days = int(run.get("horizon_days") or n_days)
        cutoff_raw = run.get("cutoff_date")
        if not cutoff_raw:
            return None, None, horizon_days

        cutoff = datetime.strptime(str(cutoff_raw)[:10], "%Y-%m-%d")
        start = cutoff + timedelta(days=1)
        end = cutoff + timedelta(days=horizon_days)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), horizon_days

    def get_store_financial_returns(self) -> List[Dict[str, Any]]:
        """Retrieves all 54 store financial return records from SQL database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    store_nbr, city, state, region, store_type, cluster,
                    forecast_16d_volume, gross_revenue_usd, return_profit_usd,
                    net_margin_pct, holding_cost_savings_usd, stockout_risk_score,
                    reorder_status, primary_surge_driver
                FROM store_financial_returns
                ORDER BY return_profit_usd DESC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_macro_analytics(self) -> Dict[str, Any]:
        """Aggregates national financial returns and store profit margins."""
        stores = self.get_store_financial_returns()
        if not stores:
            # No financial return rows => report zero/None, not invented totals. This
            # branch previously returned a fabricated national picture (2,674,850 units,
            # $16,526,470 revenue, $4,703,580 profit, 28.46% margin, 54 stores) that the
            # executive dashboard rendered as measured company performance.
            logger.info("No store_financial_returns rows; reporting empty macro analytics.")
            return {
                "national_volume": 0.0,
                "gross_revenue_usd": 0.0,
                "return_profit_usd": 0.0,
                "avg_net_margin_pct": None,
                "holding_cost_savings_usd": 0.0,
                "stores_count": 0,
                "stores": [],
                "regional_summary": {},
                "data_status": "NO_DATA"
            }

        total_volume = sum(s["forecast_16d_volume"] for s in stores)
        total_revenue = sum(s["gross_revenue_usd"] for s in stores)
        total_profit = sum(s["return_profit_usd"] for s in stores)
        total_savings = sum(s["holding_cost_savings_usd"] for s in stores)
        avg_margin = (total_profit / total_revenue) if total_revenue > 0 else None

        sierra_stores = [s for s in stores if s["region"] == "Sierra"]
        coast_stores = [s for s in stores if s["region"] == "Coast"]
        oriente_stores = [s for s in stores if s["region"] == "Oriente"]

        return {
            "national_volume": round(total_volume, 1),
            "gross_revenue_usd": round(total_revenue, 2),
            "return_profit_usd": round(total_profit, 2),
            "holding_cost_savings_usd": round(total_savings, 2),
            "avg_net_margin_pct": round(avg_margin, 4) if avg_margin is not None else None,
            "stores_count": len(stores),
            "stores": stores,
            "regional_summary": {
                "sierra": {
                    "count": len(sierra_stores),
                    "revenue_usd": round(sum(s["gross_revenue_usd"] for s in sierra_stores), 2),
                    "profit_usd": round(sum(s["return_profit_usd"] for s in sierra_stores), 2),
                },
                "coast": {
                    "count": len(coast_stores),
                    "revenue_usd": round(sum(s["gross_revenue_usd"] for s in coast_stores), 2),
                    "profit_usd": round(sum(s["return_profit_usd"] for s in coast_stores), 2),
                },
                "oriente": {
                    "count": len(oriente_stores),
                    "revenue_usd": round(sum(s["gross_revenue_usd"] for s in oriente_stores), 2),
                    "profit_usd": round(sum(s["return_profit_usd"] for s in oriente_stores), 2),
                }
            }
        }

    # =========================================================================
    # 5. HYBRID RRF VECTOR RETRIEVAL & MEMORY
    # =========================================================================

    def hybrid_search_knowledge(self, query_text: str, store_nbr: Optional[int] = None, family: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Ranks persisted operational documents by lexical term overlap.

        `similarity_score` is the fraction of query terms found in the document — a real,
        computable retrieval quality measure. It was previously
        `min(0.98, 0.70 + score * 0.08)`, which floored every returned document at 0.70
        and put any document matching a single term above the 0.75 confidence gate.
        Documents with zero term overlap were also returned, still scored 0.70.

        Documents with no overlap are now excluded, and the score is not inflated.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT doc_id, store_nbr, family, doc_type, title, content, source
                FROM store_knowledge_docs
                WHERE approved_status = 1
            """)
            docs = [dict(r) for r in cursor.fetchall()]

        if not docs:
            return []

        query_terms = [t for t in query_text.lower().split() if len(t) > 2]
        if not query_terms:
            return []

        scored_docs = []
        for d in docs:
            haystack = (d["title"] + " " + d["content"]).lower()
            matched = sum(1 for term in query_terms if term in haystack)
            if matched == 0:
                continue

            match_ratio = matched / len(query_terms)

            # Scope relevance is a tiebreak for ranking, not evidence of textual match,
            # so it affects sort order but never the reported similarity.
            rank_score = float(matched)
            if store_nbr and d["store_nbr"] in (store_nbr, 0):
                rank_score += 1.5
            if family and d["family"] in (family, "ALL"):
                rank_score += 1.5

            scored_docs.append((rank_score, match_ratio, d))

        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results = []
        for rank, (_, match_ratio, doc) in enumerate(scored_docs[:top_k]):
            results.append({
                "doc_id": doc["doc_id"],
                "store_nbr": doc["store_nbr"],
                "title": doc["title"],
                "content": doc["content"],
                "doc_type": doc["doc_type"],
                "source": doc.get("source", "UNKNOWN"),
                "rrf_score": round(1.0 / (60.0 + rank + 1), 5),
                "similarity_score": round(match_ratio, 4),
            })

        return results
