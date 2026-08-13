# Demand Forecasting using Long Short-Term Memory (LSTM) Neural Networks

This document synthesizes the methodology, network architectures, data preprocessing rules, and experimental findings from the foundational research paper:

> **Paper Title:** Demand Forecasting using Long Short-Term Memory Neural Networks  
> **Authors:** Marta Gołąbek, Robin Senge, and Rainer Neumann (2020)[cite: 3]  
> **Domain:** E-Grocery Retail / Fast-Moving Consumer Goods (FMCG)[cite: 3]

---

## 1. Executive Summary & Business Setting

* **Core Problem:** E-grocery operates on low product profit margins combined with high online fulfillment/delivery costs[cite: 3]. Inaccurate demand estimation causes severe losses due to food spoilage (overstocking) or lost sales/customer churn (understocking)[cite: 2, 3].
* **Goal:** Evaluate univariate and multivariate LSTM models to produce multi-step (daily) demand forecasts for an entire working week across product categories[cite: 3].
* **Dataset Overview:** Daily sales data of 100 fast-moving consumer goods across 5 distribution warehouses over 2 years and 5 months[cite: 3]. (Days on which stores/warehouses were closed were excluded)[cite: 3].

---

## 2. Preprocessing & Feature Engineering Pipeline

### A. Data Splitting Strategy
* **Training Set:** First 2.0 years of continuous daily data[cite: 3].
* **Validation Set:** Next 3 months (used for hyperparameter tuning)[cite: 3].
* **Test Set:** Final 2 months (used for evaluation against baseline models)[cite: 3].

### B. Preprocessing Rules
1. **Missing Values:** Rare missing values in `price` replaced using feature mean imputation[cite: 3].
2. **Categorical Features:** One-hot encoded (e.g., day of the week)[cite: 3].
3. **Normalization:** One-shot **Min-Max Scaling** applied across all time series[cite: 3].
   > *Note:* Normalization is critical when training across multiple series to align varying demand scales[cite: 3]. Moving-window normalization is recommended if strong trends exist, but min-max suffices for weak-trend FMCG data[cite: 3].
4. **Deseasonalization:** **Omitted**[cite: 3]. Explicit deseasonalization was unnecessary because the network was provided with calendar/holiday features, 2 full years of continuous data, and trained on series with homogeneous seasonality[cite: 3].
5. **Windowing:** Moving Window (MW) approach[cite: 3].
   * **Input Window Width ($l$):** Fixed at `36 time steps` (determined experimentally)[cite: 3].
   * **Output Window Width ($h$):** Fixed at `6 lookaheads` (1 operational working week)[cite: 3].

---

## 3. Network Architecture Specifications

### A. Core Architectural Design
The paper adopts a **Traditional LSTM** architecture (without peephole connections)[cite: 3]. Peepholes were omitted because non-operating store days were removed, meaning the network should rely on explicit exogenous calendar features rather than counting sequential steps independently[cite: 3].

                [ Normalized Input Window ]
                   (Size: 36 time steps)
                             │
                             ▼
                      [ LSTM Layer ]
               (Hidden Units: 10 - 100)
                             │
                             ▼
         [ Fully Connected Nonlinear Dense Layer(s) ]
          (1 to 3 Layers, ReLU Activation, 10-100 Units)
                             │
                             ▼
                     [ Dropout Layer ]
             (Rate: 0.1 - 0.9, Training Phase Only)
                             │
                             ▼
                 [ Linear Output Layer ]
             (Size: 6 [Forecast Horizon])
                             │
                             ▼
                [ Normalized Output Window ]


* **LSTM Layer:** Extracts temporal sequence dynamics across past time steps[cite: 3].
* **Fully Connected Nonlinear Layer(s):** Follows the LSTM layer to capture remaining non-linear relationships[cite: 3]. Uses **ReLU** activation functions[cite: 3].
* **Dropout Layer:** Placed after each hidden fully connected layer during the **training phase only** to prevent overfitting[cite: 3].
* **Linear Output Layer:** Serves as an adapter mapping hidden representations directly to the target output window size ($h = 6$)[cite: 3].

---

## 4. Hyperparameter Configuration Matrix

| Hyperparameter | Scope / Level | Selection Method | Paper Configuration / Value Range |
| :--- | :--- | :--- | :--- |
| **Input Window Width** | Assortment | Literature & Experiment | **36 time steps**[cite: 3] |
| **Output Window Width** | Assortment | Business Constraint | **6 time steps** (1 working week)[cite: 3] |
| **LSTM Neurons** | Product-level | Random Search | Range: **[10, 100]**, step = 10[cite: 3] |
| **Nonlinear Dense Layers** | Product-level | Random Search | Range: **[1, 3]** layers[cite: 3] |
| **Dense Layer Neurons** | Product-level | Random Search | Range: **[10, 100]**, step = 10[cite: 3] |
| **Activation Function** | Assortment | Literature | **ReLU**[cite: 3] |
| **Dropout Layers** | Product-level | Random Search | Included after each dense layer `{0, 1}`[cite: 3] |
| **Dropout Rate** | Product-level | Random Search | Range: **[0.1, 0.9]**, step = 0.1[cite: 3] |
| **Optimizer** | Assortment | Literature | **Adam**[cite: 3] |
| **Learning Rate** | Product-level | Random Search | Range: **[1e-4, 1e-2]**, step factor = 1e-1[cite: 3] |
| **Loss Function** | Assortment | Literature | **Mean Squared Error (MSE)**[cite: 3] |
| **Batch Size** | Assortment | Literature & Experiment | **32**[cite: 3] |
| **Max Epochs** | Assortment | Literature & Experiment | **70** (with Early Stopping)[cite: 3] |
| **Early Stopping Patience** | Assortment | Literature & Experiment | **5 epochs**[cite: 3] |

---

## 5. Optimal Feature Space Definitions

### A. Optimal Feature Set (Food & Beverages)
The paper identified that the exact same feature combination yielded peak performance for both product categories[cite: 3]:

1. **Previous Demand ($d_{t-1}$):** Historical daily sales demand[cite: 3].
2. **Known Orders ($o_t$):** Advance orders already booked at the time of prediction[cite: 3].
3. **Day of Week:** One-hot encoded categorical indicator[cite: 3].
4. **"Further Future" Store Open Features:**
   * *Is store open tomorrow ($t+1$)?* `{0, 1}`[cite: 3]
   * *Is store open day after tomorrow ($t+2$)?* `{0, 1}`[cite: 3]
5. **"Further Future" Public Holiday Features:**
   * *Is tomorrow ($t+1$) a public holiday?* `{0, 1}`[cite: 3]
   * *Is day after tomorrow ($t+2$) a public holiday?* `{0, 1}`[cite: 3]

---

## 6. Key Experimental Benchmarks & Findings

### A. Benchmark Baseline Models Used
The models were evaluated against 5 existing retail forecasting baselines[cite: 3]:
1. **LR:** Lasso Regression[cite: 3]
2. **RF:** Random Forest[cite: 3]
3. **ETS:** Exponential Smoothing[cite: 3]
4. **MPQ:** Median Previous Quarter[cite: 3]
5. **MDPQ:** Median Previous Quarter by Day of Week[cite: 3]

### B. Evaluation Metrics
* **MAE (Mean Absolute Error):** Scale-dependent; places natural weight on fast-moving, high-volume items[cite: 3].
* **mMAPE (modified Mean Absolute Percentage Error):** Scale-independent metric defined as[cite: 3]:
  $$\text{mMAPE} = \frac{1}{m} \sum_{t=1}^{m} \left( \frac{|F_t - A_t|}{1 + |A_t|} \right)$$

### C. Primary Experimental Results
* **Food Products Category:**
  * **Multivariate LSTM outperformed ALL 5 benchmark models** on both overall mean mMAPE and MAE[cite: 3].
  * Achieved the top forecast for **>60% of individual food items**[cite: 3].
* **Beverages Category Exception:**
  * High price-elasticity items (beverages) were **slightly outperformed by Random Forest and Linear Regression**[cite: 3].
  * *Reason:* Historical series contained too few significant price change events for the neural network to generalize price elasticity effectively without overfitting[cite: 3].
* **Pre-Training Across Related Series:** Training across warehouse time series did **not** improve performance on this dataset due to data availability constraints[cite: 3].
* **Parallel Multi-Product Forecasting:** Jointly forecasting substitutes/complements underperformed due to signal noise and lack of price variance[cite: 3].

---

## 7. Conclusions & Strategic Directives for System Implementation

1. **Product-Level Tuning is Essential:** Optimal network depth, neuron count, and dropout rates vary significantly across product SKUs[cite: 3].
2. **Forward-Looking Features Matter:** Exogenous "further future" features (store open status, upcoming holidays) drastically improve multi-step accuracy[cite: 3].
3. **No Single Model Dominates:** Deep Neural Networks (LSTMs) dominate stable/food categories, but tree-based/linear models perform better on sparse or price-volatile goods (beverages)—justifying an **Adaptive Mediator System**[cite: 2, 3].