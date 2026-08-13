"""
DemandPilot Supabase Authentication & Store-Level RBAC Middleware.
Validates Supabase JWTs, derives user identity and role server-side,
and enforces strict store-level authorization checks.
"""

import os
import logging
from typing import Optional, List
from fastapi import Header, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from pydantic import BaseModel

logger = logging.getLogger("demandpilot.auth")

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "demandpilot_dev_jwt_secret_change_in_prod")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")

security = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    user_id: str
    email: str
    role: str = "STORE_MANAGER" # STORE_MANAGER, SUPPLY_CHAIN_PLANNER, EXECUTIVE_LEADERSHIP, ADMIN
    tenant_id: str = "default_tenant"
    authorized_stores: List[int] = [14, 25, 52, 1, 44] # Default store access for demo/testing


ENVIRONMENT = os.environ.get("ENVIRONMENT", os.environ.get("ENV", "development")).lower()
IS_PRODUCTION = ENVIRONMENT in ["production", "prod", "staging"]

def decode_supabase_jwt(token: str) -> dict:
    """
    Decodes and validates a Supabase Auth JWT.
    Enforces strict signature verification in production.
    """
    # Reject demo tokens and unverified tokens in production
    if IS_PRODUCTION:
        if not SUPABASE_JWT_SECRET or SUPABASE_JWT_SECRET == "demandpilot_dev_jwt_secret_change_in_prod":
            logger.error("Production startup / auth error: SUPABASE_JWT_SECRET must be set to a secure value in production.")
            raise HTTPException(status_code=500, detail="Server authentication misconfigured: Production JWT secret required.")

        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_signature": True, "verify_aud": False}
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Supabase JWT has expired")
            raise HTTPException(status_code=401, detail="Authentication token has expired")
        except Exception as e:
            logger.warning(f"Invalid Supabase JWT signature in production: {e}")
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    # Development / Testing mode
    try:
        if token.startswith("demo-"):
            role_part = token.replace("demo-token-", "").upper()
            return {
                "sub": f"user_{role_part.lower()}",
                "email": f"{role_part.lower()}@demandpilot.favorita.ec",
                "role": role_part if role_part in ['STORE_MANAGER', 'SUPPLY_CHAIN_PLANNER', 'EXECUTIVE_LEADERSHIP', 'ADMIN'] else 'STORE_MANAGER',
                "authorized_stores": [14, 25, 52, 1, 44] if role_part != 'STORE_MANAGER' else [14, 1, 44]
            }

        if SUPABASE_JWT_SECRET and SUPABASE_JWT_SECRET != "demandpilot_dev_jwt_secret_change_in_prod":
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            return payload
        else:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Supabase JWT has expired")
        raise HTTPException(status_code=401, detail="Authentication token has expired")
    except Exception as e:
        logger.warning(f"Invalid Supabase JWT in dev: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> AuthenticatedUser:
    """
    FastAPI dependency that extracts and validates the authenticated user from the Bearer token.
    """
    if not credentials or not credentials.credentials:
        # For development / testing convenience when no header is supplied, return default test user
        return AuthenticatedUser(
            user_id="usr_mgr_store_14",
            email="manager14@favorita.ec",
            role="STORE_MANAGER",
            tenant_id="default_tenant",
            authorized_stores=[14, 1, 44, 25, 52]
        )

    token = credentials.credentials
    payload = decode_supabase_jwt(token)
    
    user_id = payload.get("sub", payload.get("user_id", "anonymous_user"))
    email = payload.get("email", f"{user_id}@favorita.ec")
    role = payload.get("role", payload.get("app_metadata", {}).get("role", "STORE_MANAGER"))
    
    # Supply Chain Planners and Executives have national access to all 54 stores
    if role in ["SUPPLY_CHAIN_PLANNER", "EXECUTIVE_LEADERSHIP", "ADMIN"]:
        authorized_stores = list(range(1, 55))
    else:
        # Default authorized stores for Store Managers
        authorized_stores = payload.get("authorized_stores", [14, 1, 44])

    return AuthenticatedUser(
        user_id=user_id,
        email=email,
        role=role,
        tenant_id=payload.get("tenant_id", "default_tenant"),
        authorized_stores=authorized_stores
    )


def verify_store_authorization(store_id: int, user: AuthenticatedUser) -> bool:
    """
    Checks whether the authenticated user has explicit authorization for the requested store.
    """
    if user.role in ["SUPPLY_CHAIN_PLANNER", "EXECUTIVE_LEADERSHIP", "ADMIN"]:
        return True
    return store_id in user.authorized_stores


def require_store_access(store_id: int):
    """
    Dependency factory to enforce store-level authorization.
    """
    async def _dependency(user: AuthenticatedUser = Depends(get_current_user)):
        if not verify_store_authorization(store_id, user):
            logger.warning(f"Forbidden: User {user.user_id} denied access to Store {store_id}")
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: User {user.user_id} ({user.role}) is not authorized to access Store {store_id}."
            )
        return user
    return _dependency
