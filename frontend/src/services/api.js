/**
 * DemandPilot Production API Client
 * Connects securely to FastAPI Layer 2 Orchestration Gateway
 * Enforces JWT session headers, data status metadata, and typed error handling.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

let authToken = localStorage.getItem('demandpilot_auth_token') || 'demo-token-store_manager';

export const setAuthToken = (token) => {
  authToken = token;
  if (token) {
    localStorage.setItem('demandpilot_auth_token', token);
  } else {
    localStorage.removeItem('demandpilot_auth_token');
  }
};

export const getAuthToken = () => authToken;

const getHeaders = () => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${authToken || 'demo-token-store_manager'}`
});

export const api = {
  /**
   * Fetches all 54 retail stores
   */
  async getStores() {
    const res = await fetch(`${API_BASE_URL}/api/v1/stores`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch stores`);
    return await res.json();
  },

  /**
   * Fetches unified live store operations snapshot
   */
  async getStoreOperationsSnapshot(storeId = 14) {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/store/operations-snapshot?store_id=${storeId}`, {
        headers: getHeaders()
      });
      
      if (res.status === 403) {
        throw new Error(`403_FORBIDDEN: User not authorized for Store ${storeId}`);
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch store snapshot`);
      
      const data = await res.json();
      return data;
    } catch (err) {
      if (err.message.includes('403_FORBIDDEN')) {
        throw err;
      }
      console.warn('FastAPI unavailable, returning error state:', err);
      throw new Error(`CONNECTION_ERROR: Unable to reach DemandPilot API Gateway at ${API_BASE_URL}`);
    }
  },

  /**
   * Fetches or initializes the active draft replenishment order plan
   */
  async getCurrentOrderPlan(storeId = 14) {
    const res = await fetch(`${API_BASE_URL}/api/v1/order-plans/current?store_id=${storeId}`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch active order plan`);
    return await res.json();
  },

  /**
   * Saves or adjusts a line in the active order plan
   */
  async saveOrderPlanLine(planId, family, adjustedQty, recommendedQty = 0, reason = '') {
    const res = await fetch(`${API_BASE_URL}/api/v1/order-plans/${planId}/lines`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        family,
        adjusted_qty: adjustedQty,
        recommended_qty: recommendedQty,
        reason
      })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to update order plan line`);
    return await res.json();
  },

  /**
   * Submits an order plan and generates an authoritative purchase order
   */
  async submitOrderPlan(planId) {
    const res = await fetch(`${API_BASE_URL}/api/v1/order-plans/${planId}/submit`, {
      method: 'POST',
      headers: getHeaders()
    });
    if (res.status === 409) {
      throw new Error('Order plan has already been submitted.');
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}: Order plan submission failed`);
    return await res.json();
  },

  /**
   * Fetches persisted purchase orders for a store
   */
  async getPurchaseOrders(storeId = null) {
    const url = storeId 
      ? `${API_BASE_URL}/api/v1/purchase-orders?store_id=${storeId}`
      : `${API_BASE_URL}/api/v1/purchase-orders`;
    const res = await fetch(url, { headers: getHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch purchase orders`);
    return await res.json();
  },

  /**
   * Fetches 16-day forecast grid across stores & families
   */
  async getForecastGrid(storeId = 14, family = 'SCHOOL AND OFFICE SUPPLIES', page = 1) {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/forecast/grid?store_id=${storeId}&family=${encodeURIComponent(family)}&page=${page}`,
      { headers: getHeaders()}
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch forecast grid`);
    return await res.json();
  },

  /**
   * Asks the grounded AI copilot agent with store and user context (standard JSON)
   */
  async sendAgentChat(query, userId = 'usr_mgr_store_14', userRole = 'STORE_MANAGER', storeNbr = 14) {
    const res = await fetch(`${API_BASE_URL}/api/v1/agent/chat`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        user_id: userId,
        user_role: userRole,
        store_nbr: storeNbr,
        query: query
      })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to communicate with AI Agent`);
    return await res.json();
  },

  /**
   * Streams grounded AI copilot tokens via Server-Sent Events (SSE)
   */
  async sendAgentChatStream(query, userId = 'usr_mgr_store_14', userRole = 'STORE_MANAGER', storeNbr = 14, onToken = () => {}, onDone = () => {}) {
    const res = await fetch(`${API_BASE_URL}/api/v1/agent/chat?stream=true`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        user_id: userId,
        user_role: userRole,
        store_nbr: storeNbr,
        query: query
      })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}: Stream connection failed`);
    
    const reader = res.body?.getReader();
    if (!reader) throw new Error('Response body is not readable');

    const decoder = new TextDecoder();
    let accumulatedText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              accumulatedText += data.token;
              onToken(data.token, accumulatedText);
            }
          } catch (e) {
            // Ignore partial SSE chunk parse error
          }
        }
      }
    }

    onDone(accumulatedText);
    return accumulatedText;
  },

  /**
   * Fetches Macro financial analytics and 54-store return profits
   */
  async getMacroAnalytics() {
    const res = await fetch(`${API_BASE_URL}/api/v1/analytics/macro`, { headers: getHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch macro analytics`);
    return await res.json();
  }
};
