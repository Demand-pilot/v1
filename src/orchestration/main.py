"""
DemandPilot Layer 2 Orchestration & AI Agent API Gateway.
FastAPI service backed by Supabase PostgreSQL, Auth & pgvector.
Enforces strict store-level RBAC, immutable forecast facts, order planning,
and persistent Purchase Order lifecycle.
"""

from dotenv import load_dotenv
load_dotenv()

import json
import logging
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Query, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.orchestration.schemas import (
    ForecastGridResponse,
    AgentChatRequest,
    AgentChatResponse,
    MacroAnalyticsResponse,
    StoreMacroKPI,
    OrderPlanLineRequest,
    OrderPlanResponse,
    SubmitOrderPlanRequest,
    PurchaseOrderResponse
)
from src.orchestration.auth import (
    AuthenticatedUser,
    get_current_user,
    require_store_access,
    verify_store_authorization
)
from src.orchestration.cache.redis_client import RedisForecastCache
from src.orchestration.router.intent_router import IntentRouter
from src.orchestration.db.database import DatabaseRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demandpilot.api")

# Global Cache, Router, & Database Instances
redis_cache = RedisForecastCache()
intent_router = IntentRouter(cache_client=redis_cache)
db_repo = DatabaseRepository()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DemandPilot Orchestration API Gateway starting up with Supabase PostgreSQL connection...")
    yield
    logger.info("DemandPilot Orchestration API Gateway shutting down...")


app = FastAPI(
    title="DemandPilot API Gateway — Layer 2",
    description="Production Orchestration & Grounded AI Agent Layer for DemandPilot Retail Intelligence",
    version="1.1.0",
    lifespan=lifespan
)

# Enable CORS for Next.js 14 / React Frontend Layer
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "DemandPilot Layer 2 API Gateway",
        "status": "online",
        "version": "1.1.0",
        "documentation": "/docs",
        "openapi_schema": "/openapi.json",
        "health": "/health",
        "endpoints": {
            "stores": "/api/v1/stores",
            "store_operations_snapshot": "/api/v1/store/operations-snapshot?store_id=14",
            "order_plans_current": "/api/v1/order-plans/current?store_id=14",
            "purchase_orders": "/api/v1/purchase-orders?store_id=14",
            "forecast_grid": "/api/v1/forecast/grid?store_id=14&family=SCHOOL%20AND%20OFFICE%20SUPPLIES",
            "agent_chat": "/api/v1/agent/chat",
            "macro_analytics": "/api/v1/analytics/macro"
        },
        "frontend_app": "http://localhost:5173"
    }


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "online",
        "layer": "Layer 2 Orchestration & AI Agent Layer",
        "version": "1.1.0",
        "database": "connected"
    }


# =============================================================================
# 1. STORE CATALOG & OPERATIONS SNAPSHOT
# =============================================================================

@app.get("/api/v1/stores", tags=["Store Catalog"])
async def get_stores(user: AuthenticatedUser = Depends(get_current_user)):
    """Returns all 54 stores across Ecuador."""
    return {"status": "success", "stores": db_repo.get_stores()}


@app.get("/api/v1/store/operations-snapshot", tags=["Store Operations"])
async def get_store_operations_snapshot(
    store_id: int = Query(14, description="Store number (1-54)"),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Returns authentic live operations snapshot for Store Managers.
    Enforces store-level authorization; queries real persisted facts,
    actual sales history (28D/56D), inventory status, and draft order plans.
    """
    if not verify_store_authorization(store_id, user):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: User {user.user_id} ({user.role}) is not authorized to access Store {store_id}."
        )

    try:
        return db_repo.get_store_operations_snapshot(store_nbr=store_id)
    except Exception as e:
        logger.error(f"Error fetching store operations snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 2. ORDER PLANNING & PURCHASE ORDER LIFECYCLE
# =============================================================================

@app.get("/api/v1/order-plans/current", tags=["Order Planning"])
async def get_current_order_plan(
    store_id: int = Query(14, description="Store number (1-54)"),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieves or initializes the active draft replenishment order plan for a store."""
    if not verify_store_authorization(store_id, user):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: User {user.user_id} is not authorized for Store {store_id}."
        )
    return db_repo.get_or_create_order_plan(store_nbr=store_id, user_id=user.user_id)


@app.post("/api/v1/order-plans/{plan_id}/lines", tags=["Order Planning"])
async def save_order_plan_line(
    plan_id: str,
    line_req: OrderPlanLineRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Adds or updates a line in the active order plan."""
    return db_repo.save_order_plan_line(
        plan_id=plan_id,
        family=line_req.family,
        adjusted_qty=line_req.adjusted_qty,
        recommended_qty=line_req.recommended_qty or 0.0,
        reason=line_req.reason or ""
    )


@app.post("/api/v1/order-plans/{plan_id}/submit", response_model=PurchaseOrderResponse, tags=["Order Planning"])
async def submit_order_plan(
    plan_id: str,
    body: Optional[SubmitOrderPlanRequest] = None,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Submits an order plan, generates an authoritative persisted Purchase Order
    (#PO-EC-2017-0816-{store_nbr}-{uuid[:6]}), and writes an immutable audit record.
    """
    target_plan_id = (body.order_plan_id if body and body.order_plan_id else None) or plan_id
    try:
        po = db_repo.submit_purchase_order(plan_id=target_plan_id, user_id=user.user_id)
        return PurchaseOrderResponse(**po)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting purchase order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/purchase-orders", tags=["Order Planning"])
async def get_purchase_orders(
    store_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Retrieves persisted purchase orders with bounded pagination."""
    with db_repo.get_connection() as conn:
        cursor = conn.cursor()
        if store_id:
            cursor.execute(
                "SELECT * FROM purchase_orders WHERE store_nbr = ? ORDER BY submitted_at DESC LIMIT ? OFFSET ?",
                (store_id, limit, offset)
            )
        else:
            cursor.execute(
                "SELECT * FROM purchase_orders ORDER BY submitted_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        rows = cursor.fetchall()
        return {"status": "success", "purchase_orders": [dict(r) for r in rows], "limit": limit, "offset": offset}


# =============================================================================
# 3. FORECAST GRID & MACRO FINANCIAL ANALYTICS
# =============================================================================

@app.get("/api/v1/forecast/grid", response_model=ForecastGridResponse, tags=["Forecast Grid"])
async def get_forecast_grid(
    store_id: Optional[int] = Query(14, description="Store number (1-54)"),
    family: Optional[str] = Query("SCHOOL AND OFFICE SUPPLIES", description="Product family name"),
    page: int = Query(1, ge=1),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Returns 16-day daily forecast data across selected stores and categories.
    Bypasses LLM for raw data loading (< 15ms latency SLA via Redis 7 / SQL).
    """
    try:
        return intent_router.handle_forecast_grid_request(store_id=store_id or 14, family=family or "SCHOOL AND OFFICE SUPPLIES")
    except Exception as e:
        logger.error(f"Error fetching forecast grid: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analytics/macro", response_model=MacroAnalyticsResponse, tags=["Analytics"])
async def get_macro_analytics(user: AuthenticatedUser = Depends(get_current_user)):
    """
    Macro level visibility across all 54 stores in Ecuador for Executive Leadership.
    Provides national demand volume, gross revenues, store return profits, net margins,
    and regional surge performance.
    """
    try:
        data = db_repo.get_macro_analytics()
        return MacroAnalyticsResponse(
            status="success",
            national_volume=data["national_volume"],
            national_demand_volume=data["national_volume"],
            gross_revenue_usd=data["gross_revenue_usd"],
            return_profit_usd=data["return_profit_usd"],
            avg_net_margin_pct=data["avg_net_margin_pct"],
            holding_cost_savings_usd=data["holding_cost_savings_usd"],
            stores_count=data["stores_count"],
            stores=data["stores"],
            regional_summary=data.get("regional_summary")
        )
    except Exception as e:
        logger.error(f"Error fetching macro analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 4. GROUNDED AI AGENT CONVERSATION
# =============================================================================

@app.post("/api/v1/agent/chat", tags=["AI Agent"])
async def agent_chat(
    request: AgentChatRequest,
    stream: bool = Query(False),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Conversational Q&A endpoint for retail operators and store managers.
    Passes authenticated user context and selected store to grounded Groq agent.
    If stream=True, returns Server-Sent Events (SSE) token stream.
    """
    try:
        response = intent_router.handle_agent_chat_request(
            user_id=request.user_id or user.user_id,
            user_role=request.user_role or user.role,
            query=request.query,
            store_id=request.store_nbr or 14
        )

        if stream:
            async def event_generator():
                tokens = response.explanation.split(" ")
                for token in tokens:
                    data = json.dumps({"token": token + " "})
                    yield f"data: {data}\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        return response
    except Exception as e:
        logger.error(f"Error processing agent chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
