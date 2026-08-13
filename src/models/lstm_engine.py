"""
PyTorch LSTM Deep Learning Engine for DemandPilot Layer 4.
Input Tensor: (Batch, 60_past_days, Features) -> Output Tensor: (Batch, 16_future_days)
Target: Smooth high-volume staple categories (Grocery I, Beverages).
"""

from typing import Dict, Any, List, Optional
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


class RMSLELoss(nn.Module):
    """
    Custom Root Mean Squared Logarithmic Error (RMSLE) Loss Function for PyTorch.
    Formula: sqrt( mean( (log(y_pred + 1) - log(y_true + 1))^2 ) )
    """

    def __init__(self, eps: float = 1e-6):
        super(RMSLELoss, self).__init__()
        self.eps = eps

    def forward(self, y_pred: torch.Tensor, y_true: torch.Tensor) -> torch.Tensor:
        y_pred_clamped = torch.clamp(y_pred, min=0.0)
        y_true_clamped = torch.clamp(y_true, min=0.0)
        log_pred = torch.log1p(y_pred_clamped)
        log_true = torch.log1p(y_true_clamped)
        mse_log = torch.mean((log_pred - log_true) ** 2)
        return torch.sqrt(mse_log + self.eps)


class DemandLSTM(nn.Module):
    """
    Stacked 2-Layer LSTM with Fully-Connected Dense Output Adapter for 16-Day Horizon.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 2,
        forecast_horizon: int = 16,
        dropout: float = 0.2
    ):
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

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch_size, seq_len=60, num_features)
        lstm_out, _ = self.lstm(x)
        # Extract last sequence hidden state
        last_hidden = lstm_out[:, -1, :]
        out = self.fc(last_hidden)  # Output shape: (batch_size, 16)
        return out


class WindowDataset(Dataset):
    """Sequence dataset creating (60 past days, 16 future days) window pairs."""

    def __init__(self, X: np.ndarray, y: np.ndarray, seq_len: int = 60, horizon: int = 16):
        self.seq_len = seq_len
        self.horizon = horizon
        self.samples = []
        n_steps = len(X)
        for i in range(n_steps - seq_len - horizon + 1):
            x_win = X[i : i + seq_len]
            y_win = y[i + seq_len : i + seq_len + horizon]
            self.samples.append((x_win, y_win))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        x_win, y_win = self.samples[idx]
        return torch.tensor(x_win, dtype=torch.float32), torch.tensor(y_win, dtype=torch.float32)


class DemandLSTMTrainer:
    """Trainer and Inference wrapper for PyTorch DemandLSTM."""

    def __init__(self, input_dim: int, hidden_dim: int = 128, lr: float = 1e-3):
        self.model = DemandLSTM(input_dim=input_dim, hidden_dim=hidden_dim)
        self.criterion = RMSLELoss()
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=1e-4)

    def fit(self, X_train: np.ndarray, y_train: np.ndarray, epochs: int = 3, batch_size: int = 32) -> float:
        """Fits PyTorch LSTM model on historical sequence windows."""
        dataset = WindowDataset(X_train, y_train)
        if len(dataset) == 0:
            return 0.0
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        self.model.train()
        last_loss = 0.0
        for epoch in range(epochs):
            total_loss = 0.0
            for bx, by in dataloader:
                self.optimizer.zero_grad()
                out = self.model(bx)
                loss = self.criterion(out, by)
                loss.backward()
                self.optimizer.step()
                total_loss += loss.item() * len(bx)
            last_loss = total_loss / len(dataset)
        return last_loss

    def predict_16d(self, x_input: np.ndarray) -> np.ndarray:
        """Generates 16-day forecast array for a single input sequence tensor of shape (1, 60, F) or (60, F)."""
        self.model.eval()
        with torch.no_grad():
            if x_input.ndim == 2:
                x_input = np.expand_dims(x_input, axis=0)
            tensor_x = torch.tensor(x_input, dtype=torch.float32)
            preds = self.model(tensor_x).squeeze(0).numpy()
            return np.clip(preds, 0.0, None)
