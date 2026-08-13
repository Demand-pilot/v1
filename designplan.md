# Demand Pilot: End-to-End System Architecture & Data Flow

Demand Pilot is an adaptive, AI-driven demand forecasting and inventory decision-support platform designed for retail and e-grocery businesses[cite: 2]. The platform ingests historical daily sales, store metadata, promotional events, and calendar signals to dynamically route store-product time series to optimal forecasting models and convert raw forecasts into actionable inventory reorder recommendations[cite: 2, 3].

---

## 1. High-Level Data Flow Architecture
[ Raw Historical Data ]
                  (Corporación Favorita Dataset / Store APIs)
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │  Preprocessing & Feature Engineering    │
                  │  - Lagged Sales & Rolling Metrics       │
                  │  - One-Hot Encoded Calendar Attributes  │
                  │  - Min-Max Feature Normalization        │
                  └─────────────────────────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │        Adaptive Mediator Layer          │
                  │    (Series Volatility & Sparsity        │
                  │          Classification)                │
                  └─────────────────────────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │ (CV < 0.75, Food)           │ (High Price Elasticity)     │ (Sparsity > 40%)
         ▼                             ▼                             ▼
┌───────────────────────────┐ ┌───────────────────────────┐ ┌───────────────────────────┐
│ Multivariate LSTM Engine  │ │  Tree-Based Engine        │ │ Statistical Baseline      │
│ (PyTorch Deep Sequence)   │ │  (LightGBM / XGBoost)     │ │ (MDPQ / Moving Average)   │
└───────────────────────────┘ └───────────────────────────┘ └───────────────────────────┘
│                             │                             │
└─────────────────────────────┼─────────────────────────────┘
│
▼
┌─────────────────────────────────────────┐
│   Store-Specific Knowledge Layer        │
│   (SQL Context: Closures, Supplier      │
│      Bottlenecks, Local Events)         │
└─────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────┐
│    Inventory Decision Engine            │
│   - Stock-Out Risk Assessment           │
│   - Overstocking Warnings               │
│   - Reorder Quantity Calculation        │
└─────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────┐
│    User Interface & Explanation         │
│   - Next.js / Three.js 3D Dashboard     │
│   - Open-Weight LLM Rationale           │
└─────────────────────────────────────────┘


---

## 2. Comprehensive Data Flow Pipeline

### Step 1: Data Ingestion & Preprocessing
* **Input Features:**
  * **Historical Demand ($d_{t-1}$):** Past daily unit sales[cite: 3].
  * **Known Orders ($o_t$):** Booked customer orders at prediction time[cite: 3].
  * **Temporal Features:** Day of the week (one-hot encoded), month, and day of year[cite: 2, 3].
  * **Exogenous "Further Future" Signals:** 
    * *Store Open Indicators:* Is the store open at $t+1$ and $t+2$?[cite: 3]
    * *Public Holiday Flags:* Is $t+1$ or $t+2$ a public holiday?[cite: 3]
  * **Promotional Data:** On-promotion status flags and discount depths[cite: 2].
* **Normalization:** All numerical time-series arrays are normalized using **Min-Max Scaling** to align ranges across high-volume and low-volume items without destroying relative scale variance[cite: 3].
* **Windowing:** Moving Window (MW) approach[cite: 3]:
  * **Input Horizon ($l$):** 36 historical time steps[cite: 3].
  * **Output Horizon ($h$):** 6 lookahead steps (1 full operational working week)[cite: 3].

---

### Step 2: The Adaptive Mediator Routing Engine
A single global machine learning model cannot perform optimally across all retail categories[cite: 2, 3]. Based on empirical benchmarks from Gołąbek et al., **Deep Neural Networks (LSTMs) dominate stable staple food categories**, whereas **Tree-Based Models excel on price-elastic goods (e.g., beverages)** and **Statistical Baselines prevent overfitting on sparse data**[cite: 2, 3].

The **Mediator Layer** inspects every `(Store, Product)` combination and routes it using the following decision logic[cite: 2]:

                   [ Input Store-Product Series ]
                                 │
                                 ▼
            Is Intermittent/Sparse? (Zero Sales > 40%)
                           /           \
                       YES              NO
                       /                  \
      [ Statistical Baseline ]        Is High-Elasticity /
       (MDPQ / Moving Avg)            Promotions Frequent?
                                          /          \
                                      YES             NO
                                      /                 \
                     [ Tree-Based Model ]        [ Multivariate LSTM ]
                     (LightGBM / XGBoost)        (Deep Sequence Model)

#### Detailed Mediator Classification Rules:

1. **Multivariate LSTM Pipeline (Deep Learning):**
   * **Target:** Fast-moving staple food items (e.g., fresh produce, bread, dairy)[cite: 3].
   * **Selection Criteria:** Low to moderate coefficient of variation ($CV < 0.75$), continuous sales history ($<15\%$ zero-sale days), and food category tag[cite: 3].
   * **Rationale:** Gołąbek et al. proved Multivariate LSTMs achieve superior mMAPE and MAE on food products by capturing continuous sequential dynamics and multi-step lookahead features[cite: 3].

2. **Tree-Based Pipeline (LightGBM / XGBoost):**
   * **Target:** High price-elasticity products, seasonal items, and promotional beverages[cite: 3].
   * **Selection Criteria:** High promotional sensitivity ($\Delta \text{Sales} / \Delta \text{Price} > \text{Threshold}$) or beverage/snack classification[cite: 3].
   * **Rationale:** As identified in paper benchmarks, LSTMs struggle on beverages when historical price-promotion shocks are sparse[cite: 3]. Gradient-boosted decision trees handle non-linear tabular feature splits (e.g., `is_promoted == 1 AND discount > 20%`) with higher stability[cite: 3].

3. **Statistical Baseline Pipeline (MDPQ / Moving Average):**
   * **Target:** Slow-moving SKUs, intermittent items, or newly listed products ($<30$ days of sales history)[cite: 3].
   * **Selection Criteria:** High sparsity ratio ($>40\%$ zero-sales days)[cite: 3].
   * **Rationale:** Prevents complex models from overfitting on insufficient historical data[cite: 3].

---

### Step 3: Network Architecture & Dropout Handling

#### Network Layer Structure (PyTorch / TensorFlow)
For series routed to the Multivariate LSTM, the network architecture is defined as[cite: 3]:

                 [ Normalized Input Window ]
                    (36 Lookback Steps)
                             │
                             ▼
                      [ LSTM Layer ]
               (Hidden Units: 10 - 100)
                             │
                             ▼
         [ Fully Connected Dense Layer (ReLU) ]
             (1 to 3 Layers, 10 - 100 Units)
                             │
                             ▼
                     [ Dropout Layer ]
              (Rate: 0.1 - 0.9, Training Only)
                             │
                             ▼
                 [ Linear Output Layer ]
               (Output Horizon = 6 Steps)

#### The Dual-Phase Dropout Mechanics
Although defined as a single network class in code, the framework operates in two distinct operational modes[cite: 3]:

1. **Training Phase (`model.fit()` / `model.train()`):**
   * **Dropout Behavior:** **ACTIVE**[cite: 3].
   * **Mechanism:** Randomly drops a fraction of hidden neuron connections (between 10% and 90%) during each backpropagation pass[cite: 3]. This breaks co-adaptation between nodes, forcing the model to learn generalizable temporal trends rather than memorizing noise[cite: 3].
2. **Inference / Prediction Phase (`model.predict()` / `model.eval()`):**
   * **Dropout Behavior:** **AUTOMATICALLY DISABLED**[cite: 3].
   * **Mechanism:** All network connections remain active[cite: 3]. Neuron weights are scaled down proportionally so the full capacity of the network is utilized to produce deterministic multi-step predictions[cite: 3].

---

### Step 4: Operational Knowledge Layer & Decision Engine

1. **SQL Knowledge Overlay:**
   * Raw numerical forecasts ($\hat{Y}$) are adjusted using qualitative operational parameters stored in PostgreSQL/MySQL[cite: 2]:
     $$\text{Final Demand} = \hat{Y} \times \text{Operational Multiplier} + \text{Event Adjustments}$$
   * *Example:* If store managers record an upcoming road closure or a supplier delay in the SQL table, the system applies an operational offset to the raw model output[cite: 2].

2. **Inventory Recommendation Transformation:**
   * **Stock-Out Risk Alert:** Triggered if Projected 6-Day Demand $>$ Current On-Hand Inventory ($S_t$)[cite: 2].
   * **Overstock Warning:** Triggered if Current Inventory ($S_t$) $>$ Projected Demand $+$ Safety Stock[cite: 2].
   * **Suggested Reorder Quantity ($Q$):**
     $$Q = \max\left(0, \sum_{k=1}^{6} \hat{Y}_{t+k} + \text{Safety Stock} - S_t\right)$$

---

### Step 5: User Interface & LLM Explanation Layer
* **Dashboard (Next.js & Three.js):** Displays inventory heatmaps, stock-out risk indicators, and reorder tables[cite: 2].
* **Open-Weight LLM Agent (Hugging Face):** Evaluates the routing metadata, quantitative forecasts, and store knowledge to output plain-English rationales for non-technical retail staff[cite: 2]:
*"Product #104 (Fresh Milk) is forecasted at 190 units over the next 6 days using the Multivariate LSTM pipeline due to regular weekend lift and upcoming open store days[cite: 2, 3]. Current stock is 50 units[cite: 2]. Recommended reorder: 150 units by 4:00 PM to eliminate a projected stock-out risk[cite: 2]."*