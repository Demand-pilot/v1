# DemandPilot Architecture — Layer 5: Model Evaluation & Mediator Layer

**System Layer**: Backtesting Harness, Mediator Agent Routing & Zero Post-Processing  
**Core Responsibility**: Evaluating candidate models on historical validation windows and dynamically selecting or ensembling forecasts  
**Primary Metric**: Root Mean Squared Logarithmic Error (RMSLE)

---

## 1. Rolling 16-Day RMSLE Backtesting Protocol

To evaluate model accuracy under real supply chain conditions, DemandPilot executes a **Rolling 16-Day Backtest Window** (State 9) immediately preceding the forecast horizon:

```
[ HISTORICAL TRAIN TIMELINE (2013 - July 2017) ] ──► [ 16-DAY BACKTEST WINDOW (July 30 - Aug 14, 2017) ]
                                                                      │
                                                                      ▼
                                                       Evaluates PyTorch LSTM RMSLE
                                                       Evaluates LightGBM GBDT RMSLE
                                                       Evaluates Seasonal Baseline RMSLE
```

### RMSLE Metric Calculation
For each of the $1,782$ series ($s = 1 \dots 1782$), backtest error is calculated as:
$$\text{RMSLE}_s = \sqrt{\frac{1}{16} \sum_{i=1}^{16} \left( \ln(\hat{y}_{s,i} + 1) - \ln(y_{s,i} + 1) \right)^2}$$

---

## 2. Mediator Agent Decision Logic & Rules

The **Mediator Agent** (State 10) receives the series profile from Layer 3 and the backtest RMSLE vector from State 9. It applies three deterministic decision rules:

```
                                  ┌─────────────────────────────────────────┐
                                  │            MEDIATOR AGENT               │
                                  └────────────────────┬────────────────────┘
                                                       │
         ┌─────────────────────────────────────────────┼─────────────────────────────────────────────┐
         ▼                                             ▼                                             ▼
┌───────────────────────────┐             ┌───────────────────────────┐             ┌───────────────────────────┐
│ RULE 1: ZERO BYPASS MASK  │             │ RULE 2: SINGLE SELECTOR   │             │ RULE 3: SOFT-MAX ENSEMBLE │
├───────────────────────────┤             ├───────────────────────────┤             ├───────────────────────────┤
│ If Zero Ratio == 1.0 (53  │             │ If RMSLE difference between│             │ If top 2 models have      │
│ series), force f(t) = 0.0 │             │ top 2 models > 0.05, pick │             │ close RMSLE (diff < 0.05),│
│ Bypass ML candidate core. │             │ single winner.            │             │ blend via soft-max.       │
└───────────────────────────┘             └───────────────────────────┘             └───────────────────────────┘
```

### Decision Algorithm Code
```python
def mediator_route_series(series_profile, model_backtest_errors, candidates):
    # Rule 1: Permanent Zero Series Bypass (53 Series)
    if series_profile['is_permanent_zero']:
        return {'strategy': 'HARDCODED_ZERO', 'weights': {'zero_mask': 1.0}, 'forecast': np.zeros(16)}
    
    # Sort models by RMSLE (ascending order, lower is better)
    sorted_models = sorted(model_backtest_errors.items(), key=lambda x: x[1])
    best_model, best_rmsle = sorted_models[0]
    second_model, second_rmsle = sorted_models[1]
    
    # Rule 2: Single Model Selector (Clear Dominance)
    if (second_rmsle - best_rmsle) > 0.05 or series_profile['promo_elasticity'] > 0.6:
        return {'strategy': 'SINGLE_SELECTOR', 'selected_model': best_model, 'rmsle': best_rmsle}
    
    # Rule 3: Inverse RMSLE Soft-Max Weighted Ensemble
    rmsle_values = np.array([err for _, err in sorted_models])
    inv_rmsle = 1.0 / (rmsle_values + 1e-6)
    ensemble_weights = np.exp(inv_rmsle) / np.sum(np.exp(inv_rmsle))
    
    blended_forecast = np.zeros(16)
    weight_dict = {}
    for i, (name, _) in enumerate(sorted_models):
        blended_forecast += ensemble_weights[i] * candidates[name]
        weight_dict[name] = float(ensemble_weights[i])
        
    return {'strategy': 'WEIGHTED_ENSEMBLE', 'weights': weight_dict, 'forecast': blended_forecast}
```

---

## 3. Post-Processing Zero Masks & Calendar Overrides

Following model routing, predictions pass through a final **Post-Processing Verification Layer**:

1. **Christmas Day Mask (Dec 25)**: Retail stores are closed. All predictions for Dec 25 are hardcoded to $0.0$.
2. **New Year Day Mask (Jan 1)**: All stores except **Store 25** are closed. Predictions for Jan 1 are set to $0.0$ for non-Store 25 series.
3. **Negative Sales Truncation**: Sales unit predictions cannot be negative: $\hat{y}_{\text{final}} = \max(0.0, \hat{y})$.
