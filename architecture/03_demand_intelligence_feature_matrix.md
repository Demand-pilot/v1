# DemandPilot Architecture — Layer 3: Demand Intelligence & Feature Engineering Matrix

**System Layer**: Series Profiling, Quality Routing & Feature Transformation  
**Core Responsibility**: Segmenting 1,782 time series by demand pattern and engineering empirical shock features

---

## 1. Automated Demand Intelligence Profiler

Before sending data to candidate machine learning models, the **Demand Profiler** evaluates each of the $1,782$ series ($54 \text{ Stores} \times 33 \text{ Families}$) against four statistical metrics:

```
                                  ┌─────────────────────────────────────────┐
                                  │       AUTOMATED DEMAND PROFILER         │
                                  └────────────────────┬────────────────────┘
                                                       │
         ┌─────────────────────────────────────────────┼─────────────────────────────────────────────┐
         ▼                                             ▼                                             ▼
┌───────────────────────────┐             ┌───────────────────────────┐             ┌───────────────────────────┐
│ VOLATILITY (CV)           │             │ ZERO SALES RATIO          │             │ PROMO ELASTICITY          │
├───────────────────────────┤             ├───────────────────────────┤             ├───────────────────────────┤
│ Coefficient of Variation  │             │ Ratio of 0.0 sales days   │             │ Pearson correlation of    │
│ CV = std(sales) / mean    │             │ Zero Ratio = zeros / total│             │ sales to active promos    │
└───────────────────────────┘             └───────────────────────────┘             └───────────────────────────┘
```

### Segmentation Categories
1. **Smooth High-Volume Staples**: $\text{CV} < 0.6$, Zero Ratio $< 0.05$ (e.g. Grocery I, Beverages). Assigned to **PyTorch LSTM**.
2. **Promo-Elastic Surge Items**: Promo Elasticity $> 0.5$, $\text{CV} > 1.0$ (e.g. School Supplies). Assigned to **LightGBM / XGBoost GBDT**.
3. **Intermittent / Sparse Series**: Zero Ratio $> 0.50$, non-zero items occasional. Assigned to **Croston Baseline Rules**.
4. **Permanent Zero Series**: Zero Ratio $= 1.0$ over 1,000+ days ($53$ series). Assigned to **Hardcoded Zero Mask Bypass**.

---

## 2. Quality Router & 53 Zero-Series Bypass Mask

### The 53 Zero-Series Problem
Empirical data analysis revealed **53 store-family combinations** that generate exactly \$0 sales for years (e.g., `BOOKS` in 28 stores has 1,684 consecutive zero sales days).

### Why ML Models Fail on Zero Series
Passing permanent zero series to neural networks or decision trees causes:
* Model overfitting on non-existent zero patterns.
* Wasteful training compute time.
* Potential positive non-zero prediction bleed due to global store pooling.

### The Bypass Rule
The Quality Router intercepts all 53 permanent zero series during State 4 and routes them directly to a **Post-Processing Hardcoded Zero Mask** ($f(t) = 0.0$), completely bypassing ML candidate training.

---

## 3. Feature Engineering Matrix

DemandPilot constructs a unified feature matrix containing three distinct feature groups:

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FEATURE MATRIX (1,782 SERIES)                             │
├──────────────────────────────┬──────────────────────────────┬─────────────────────────────┤
│ 1. TEMPORAL FEATURES         │ 2. PROMOTION FEATURES        │ 3. CONTEXT & SHOCK FEATURES │
├──────────────────────────────┼──────────────────────────────┼─────────────────────────────┤
│ • day_of_week (0-6)          │ • onpromotion (binary/count) │ • store_type (Types A-E)    │
│ • is_payday (15th & 30th)    │ • promo_lag_1, promo_lag_7   │ • cluster (1-17)            │
│ • is_day_after_payday (16,1) │ • promo_rolling_mean_7d      │ • Delta Oil (oil_t - oil_t1)│
│ • lag_1, lag_7, lag_14, lag_28│ • promo_density_ratio        │ • is_earthquake_30d_decay   │
│ • rolling_mean_7d, 14d, 30d  │                              │ • is_christmas_dec25        │
└──────────────────────────────┴──────────────────────────────┴─────────────────────────────┘
```

### Empirical Feature Transformation Rules

#### 1. Payday Day-After Interaction (`is_day_after_payday`)
* *Finding*: Sales surge on the **16th and 1st of every month** (+8.0% lift) following salary disbursements. Mid-week paydays boost sales (+7.5% Wed), while weekend paydays show 0% lift.
* *Transformation*:
```python
df['is_payday'] = df['day'].isin([15, 30, 31]).astype(int)
df['is_day_after_payday'] = df['day'].isin([16, 1]).astype(int)
df['payday_weekday_interaction'] = df['is_day_after_payday'] * (df['dayofweek'] < 5).astype(int)
```

#### 2. Spurious Oil First-Differencing ($\Delta \text{oil}$)
* *Finding*: Raw daily oil price correlation is negative (-0.6280) due to coincidental 5-year macro drift. Within single years, correlation is ~0.0011.
* *Transformation*:
```python
# First differencing removes macro trend while preserving short-term oil shocks
df['delta_oil'] = df['dwtruck_price'].diff().fillna(0.0)
df['delta_oil_3d_rolling'] = df['delta_oil'].rolling(3).mean().fillna(0.0)
```

#### 3. 2016 Earthquake Emergency Decay (`is_earthquake_30d_decay`)
* *Finding*: April 16, 2016 earthquake caused temporary panic buying (+20.2% sales surge for 30 days).
* *Transformation*:
```python
# Exponential decay flag over 30 days post-earthquake date (2016-04-16)
df['days_since_earthquake'] = (df['date'] - pd.Timestamp('2016-04-16')).dt.days
df['earthquake_decay'] = np.where(
    (df['days_since_earthquake'] >= 0) & (df['days_since_earthquake'] <= 30),
    np.exp(-df['days_since_earthquake'] / 10.0),
    0.0
)
```
