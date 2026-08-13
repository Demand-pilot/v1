"""
Pydantic schemas for DemandPilot Orchestration & AI Agent Layer (Layer 2).
Enforces exact REST/JSON contract compliance with Layer 1 Frontend specifications.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ForecastItem(BaseModel):
    store_nbr: int = Field(..., description="Store identification number", example=14)
    family: str = Field(..., description="Product family category", example="SCHOOL AND OFFICE SUPPLIES")
    selected_engine: str = Field(..., description="Selected model engine", example="LightGBM_GBDT")
    # No `example=` on measured quantities. Schema examples are rendered in /docs and in
    # generated clients, and the previous placeholders (0.3812, 2480.0) were the exact
    # fabricated values the API also returned at runtime — indistinguishable from real output.
    backtest_rmsle: float = Field(..., description="Backtest RMSLE for this series, from the persisted run")
    daily_forecasts: List[float] = Field(
        ...,
        description="Daily projected unit sales, one entry per horizon day"
    )
    reorder_point: float = Field(..., description="Calculated Reorder Point (ROP)")
    safety_stock: float = Field(..., description="Calculated Safety Stock (SS)")


class ForecastGridResponse(BaseModel):
    """
    A forecast grid, or an explicit empty state.

    When `status == "no_forecast_available"`, `data` is empty and the date fields are
    None. Consumers must render an empty state rather than filling in defaults.
    """
    status: str = Field("success", description='"success" or "no_forecast_available"')
    horizon_days: int = Field(0, description="Number of forecast days; 0 when unavailable")
    start_date: Optional[str] = Field(None, description="First forecast date, from the persisted run")
    end_date: Optional[str] = Field(None, description="Last forecast date, from the persisted run")
    data: List[ForecastItem] = Field(default_factory=list)


class AgentChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique manager or user identifier", example="mgr_store_14")
    user_role: str = Field("STORE_MANAGER", description="User role (STORE_MANAGER, SUPPLY_CHAIN_PLANNER, EXECUTIVE)")
    store_nbr: Optional[int] = Field(14, description="Store identification number (1-54)", example=14)
    query: str = Field(..., description="Natural language query string", example="Why is School Supplies surging by +145% at Store 14 in late August?")


class AgentChatResponse(BaseModel):
    status: str = Field("success", example="success")
    user_id: str
    query: str
    explanation: str
    grounded_verified: bool = Field(True, description="True if output passed numerical cross-check gate")
    source_tools_used: List[str] = Field(default_factory=list)


class StoreMacroKPI(BaseModel):
    store_nbr: int
    city: str
    state: str
    region: Optional[str] = "Sierra"
    store_type: Optional[str] = "A"
    cluster: int
    forecast_16d_volume: float
    gross_revenue_usd: float
    return_profit_usd: float
    net_margin_pct: float
    holding_cost_savings_usd: float
    stockout_risk_score: float  # 0.0 to 1.0 scale
    reorder_status: str  # OK, WARNING, CRITICAL
    primary_surge_driver: Optional[str] = None


class RegionalSummary(BaseModel):
    count: int
    revenue_usd: float
    profit_usd: float
    surge_driver: str


class MacroAnalyticsResponse(BaseModel):
    status: str = Field("success", example="success")
    national_volume: float
    national_demand_volume: Optional[float] = None
    gross_revenue_usd: float
    return_profit_usd: float
    # Optional because an average margin over zero stores is undefined, not 0.0 and not
    # 0.2846. The schema previously required a float here, which is why the repository
    # had to invent one.
    avg_net_margin_pct: Optional[float] = None
    holding_cost_savings_usd: float
    stores_count: int
    stores: List[StoreMacroKPI]
    regional_summary: Optional[Dict[str, RegionalSummary]] = None
    data_status: Optional[str] = Field(None, description='"NO_DATA" when nothing is persisted')


# Order Plan & Purchase Order Schemas
class OrderPlanLineRequest(BaseModel):
    family: str
    adjusted_qty: float
    recommended_qty: Optional[float] = 0.0
    reason: Optional[str] = ""


class OrderPlanLineResponse(BaseModel):
    id: str
    family: str
    recommended_qty: float
    adjusted_qty: float
    reason: Optional[str] = None
    is_approved: bool = True


class OrderPlanResponse(BaseModel):
    status: str = "success"
    id: str
    store_nbr: int
    plan_status: str = "DRAFT"
    lines: List[Dict[str, Any]] = []

    def __init__(self, **data):
        if "status" in data and data["status"] in ["DRAFT", "SUBMITTED", "CANCELLED"]:
            data["plan_status"] = data["status"]
            data["status"] = "success"
        super().__init__(**data)


class SubmitOrderPlanRequest(BaseModel):
    order_plan_id: Optional[str] = None


class PurchaseOrderResponse(BaseModel):
    status: str = "success"
    purchase_order_id: str
    po_number: str
    store_nbr: int
    total_units: float
    total_cost_usd: float
    estimated_delivery_date: str
    submitted_at: str
    edi_transmission_status: str = "CONFIRMED_ACK"

