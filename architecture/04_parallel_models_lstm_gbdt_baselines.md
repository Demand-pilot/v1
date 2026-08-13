# DemandPilot Architecture — Layer 4: Parallel Model Candidate Engines

**System Layer**: Forecasting Core & Candidate Model Training  
**Technologies**: PyTorch 2.2 (LSTM), LightGBM 4.3 / XGBoost 2.0 (GBDT), Scikit-Learn (Baselines)  
**Input Tensor Shape**: Sequence Input $(B, 60, F)$ $\rightarrow$ Forecast Output $(B, 16, 1)$

---

## 1. PyTorch LSTM Deep Learning Engine

The LSTM model captures complex non-linear temporal sequences in high-volume, smooth staple categories (Grocery I, Beverages).

```
                      ┌───────────────────────────────────────────┐
                      │     60-DAY INPUT TENSOR (B, 60, F)        │
                      └─────────────────────┬─────────────────────┘
                                            │
                                            ▼
                      ┌───────────────────────────────────────────┐
                      │    2-LAYER STACKED LSTM (Hidden=128)      │
                      └─────────────────────┬─────────────────────┘
                                            │
                                            ▼
                      ┌───────────────────────────────────────────┐
                      │   FULLY CONNECTED LINEAR (128 -> 16)      │
                      └─────────────────────┬─────────────────────┘
                                            │
                                            ▼
                      ┌───────────────────────────────────────────┐
                      │     16-DAY FORECAST TENSOR (B, 16, 1)     │
                      └───────────────────────────────────────────┘
```

### A. Tensor Preparation & Windowing
* **Input Window**: 60 past consecutive days ($t-59$ to $t$).
* **Output Window**: 16 future forecast days ($t+1$ to $t+16$).
* **Min-Max Target Scaling**: Log-transforms sales $y' = \ln(y + 1)$ and scales features to $[0, 1]$ per series.

### B. PyTorch Model Architecture Code
```python
import torch
import torch.nn as nn

class DemandLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim=128, num_layers=2, forecast_horizon=16, dropout=0.2):
        super(DemandLSTM, self).__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, forecast_horizon)
        )
        
    def forward(self, x):
        # x shape: (batch_size, seq_len=60, num_features)
        lstm_out, (hn, cn) = self.lstm(x)
        # Take hidden state of last sequence step: (batch_size, hidden_dim)
        last_hidden = lstm_out[:, -1, :]
        out = self.fc(last_hidden) # Output shape: (batch_size, 16)
        return out
```

### C. Training Loop & RMSLE Loss Function
* **Loss Function**: Custom Root Mean Squared Logarithmic Error (RMSLE Loss):
$$\mathcal{L}_{\text{RMSLE}} = \sqrt{\frac{1}{16} \sum_{i=1}^{16} \left( \ln(\hat{y}_i + 1) - \ln(y_i + 1) \right)^2}$$
* **Optimizer**: AdamW ($\text{lr}=10^{-3}$, weight decay $=10^{-4}$) with CosineAnnealingLR scheduler.

---

## 2. LightGBM / XGBoost Gradient Boosted Decision Trees (GBDT)

GBDT engines excel at capturing tabular feature interactions, promotional lead indicators, and category sales spikes (e.g. Sierra School Supplies).

### A. Environment Installation & Dependencies
```bash
pip install lightgbm==4.3.0 xgboost==2.0.3 optuna==3.5.0
```

### B. LightGBM Dataset Construction & Hyperparameters
```python
import lightgbm as lgb

params = {
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',
    'n_estimators': 1500,
    'learning_rate': 0.03,
    'num_leaves': 63,
    'max_depth': 8,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.7,
    'bagging_freq': 1,
    'verbose': -1,
    'random_state': 42
}

# Construct LGBM Dataset with Categorical Store/Family Features
train_data = lgb.Dataset(
    X_train, 
    label=np.log1p(y_train), 
    categorical_feature=['store_nbr', 'family', 'store_type', 'cluster']
)
model_lgb = lgb.train(params, train_data, valid_sets=[train_data])
```

### C. Capturing Sierra School Season (+145% Surge)
* During state 7, LightGBM leverages the `onpromotion` lead features and `family` categorical interactions.
* When test promotional density rises from **20.4% to 44.1%**, LightGBM applies non-linear promotional multipliers, accurately predicting +145% sales spikes without underprediction.

---

## 3. Seasonal Baseline & Intermittent Demand Models

For series with high zero ratios or limited historical depth, complex ML models risk overfitting. DemandPilot trains two deterministic baselines:

### A. Seasonal Naive / Moving Average Baseline
* Computes 7-day, 14-day, and 28-day rolling means combined with day-of-week seasonal factors:
$$\hat{y}_{t+h} = \bar{y}_{7d} \times \text{SeasonalFactor}(\text{dayofweek}(t+h))$$

### B. Croston's Method for Intermittent Demand
* Separates intermittent series into non-zero demand size ($y_k$) and inter-arrival time between orders ($q_k$):
$$\hat{a}_{k} = \alpha y_k + (1-\alpha)\hat{a}_{k-1}, \quad \hat{p}_{k} = \alpha q_k + (1-\alpha)\hat{p}_{k-1}$$
$$\text{Demand Forecast } \hat{y} = \frac{\hat{a}_k}{\hat{p}_k}$$
* Used specifically for sparse categories (e.g. Baby Care or Lawn/Garden items with 70%+ zero sales days).
