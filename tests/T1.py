import torch
import orch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
import pandas as pd
import joblib
import os

# -----------------------------
# Define Autoencoder architecture
# -----------------------------
class Autoencoder(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, input_dim // 2),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(input_dim // 2, input_dim),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))

# -----------------------------
# Training function
# -----------------------------
def train_autoencoder(model, data_loader, optimizer, criterion, epochs=50):
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for batch in data_loader:
            inputs = batch[0]
            outputs = model(inputs)
            loss = criterion(outputs, inputs)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"Epoch [{epoch+1}/{epochs}] Loss: {total_loss/len(data_loader):.6f}")

# -----------------------------
# 1️⃣ First-time training
# -----------------------------
def initial_train(file_path, model_path="autoencoder.pt", scaler_path="scaler.pkl"):
    df = pd.read_parquet(file_path).fillna(0)
    X = df.select_dtypes(include=["float", "int"]).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    joblib.dump(scaler, scaler_path)

    X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
    dataset = TensorDataset(X_tensor)
    loader = DataLoader(dataset, batch_size=64, shuffle=True)

    model = Autoencoder(X.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()

    train_autoencoder(model, loader, optimizer, criterion, epochs=30)
    torch.save(model.state_dict(), model_path)
    print(f"✅ Model trained and saved to {model_path}")

# -----------------------------
# 2️⃣ Incremental retraining
# -----------------------------
def retrain_with_new_data(new_file_path, model_path="autoencoder.pt", scaler_path="scaler.pkl"):
    df_new = pd.read_parquet(new_file_path).fillna(0)
    X_new = df_new.select_dtypes(include=["float", "int"]).values

    # Load existing scaler
    scaler = joblib.load(scaler_path)
    X_new_scaled = scaler.transform(X_new)

    X_tensor = torch.tensor(X_new_scaled, dtype=torch.float32)
    dataset = TensorDataset(X_tensor)
    loader = DataLoader(dataset, batch_size=64, shuffle=True)

    # Load existing model
    model = Autoencoder(X_new.shape[1])
    model.load_state_dict(torch.load(model_path))
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    criterion = nn.MSELoss()

    train_autoencoder(model, loader, optimizer, criterion, epochs=10)

    # Save updated weights
    torch.save(model.state_dict(), model_path)
    print(f"✅ Model retrained and saved again to {model_path}")

# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    initial_file = "A:/TB/Tool/Data_tests/IndustrialData/files/V60N/tests/Corner-power/V24-2025__0001.parquet"
    new_file = "A:/TB/Tool/Data_tests/IndustrialData/files/V60N/tests/Corner-power/V24-2025__0002.parquet"

    # First-time training (run once)
    if not os.path.exists("autoencoder.pt"):
        initial_train(initial_file)

    # Later retraining with a new file
    retrain_with_new_data(new_file)
