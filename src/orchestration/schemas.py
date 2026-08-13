"""
Pydantic schemas for DemandPilot Orchestration & AI Agent Layer (Layer 2).
Enforces exact REST/JSON contract compliance with Layer 1 Frontend specifications.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ForecastItem(BaseModel):
    store_nbr: int = Field(..., description="Store identification number (1-54)", example=14)
    family: str = Field(..., description="Product family category", example="SCHOOL AND OFFICE SUPPLIES")
    selected_engine: str = Field(..., description="Selected model engine", example="LightGBM_GBDT")
    backtest_rmsle: float = Field(..., description="16-day rolling backtest RMSLE score", example=0.3812)
    daily_forecasts: List[float] = Field(
        ...,
        description="16-day daily projected unit sales (Aug 16 - Aug 31)",
        min_items=16,
        max_items=16
    )
    reorder_point: float = Field(..., description="Calculated Reorder Point (ROP)", example=2480.0)
    safety_stock: float = Field(..., description="Calculated Safety Stock (SS)", example=420.0)


class ForecastGridResponse(BaseModel):
    status: str = Field("success", example="success")
    horizon_days: int = Field(16, example=16)
    start_date: str = Field("2017-08-16", example="2017-08-16")
    end_date: str = Field("2017-08-31", example="2017-08-31")
    data: List[ForecastItem]


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
    avg_net_margin_pct: float
    holding_cost_savings_usd: float
    stores_count: int
    stores: List[StoreMacroKPI]
    regional_summary: Optional[Dict[str, RegionalSummary]] = None


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

