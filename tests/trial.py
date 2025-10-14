import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

# -----------------------------
# Define the same Autoencoder class
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
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded, encoded


# -----------------------------
# Use trained model on new file
# -----------------------------
def project_new_file(third_file_path, model_path="autoencoder.pt", scaler_path="scaler.pkl"):
    # Load and clean data
    df = pd.read_parquet(third_file_path).fillna(0)
    X = df.select_dtypes(include=["float", "int"]).values

    # Load scaler and scale new data
    scaler = joblib.load(scaler_path)
    X_scaled = scaler.transform(X)

    # Load trained model
    input_dim = X.shape[1]
    model = Autoencoder(input_dim)
    model.load_state_dict(torch.load(model_path))
    model.eval()

    # Convert data to tensor
    X_tensor = torch.tensor(X_scaled, dtype=torch.float32)

    # Forward pass to get reconstruction + encoding
    with torch.no_grad():
        reconstructed, encoded = model(X_tensor)

    # Convert tensors to numpy arrays
    reconstructed = reconstructed.numpy()
    encoded = encoded.numpy()

    # Compute reconstruction error
    recon_error = np.mean((X_scaled - reconstructed) ** 2, axis=1)

    print("✅ Projection complete!")
    print(f"Encoded feature shape: {encoded.shape}")

    # Plot reconstruction error
    plt.figure(figsize=(10, 4))
    plt.plot(recon_error, color='blue', label='Reconstruction Error')
    plt.title("Reconstruction Error on Third File")
    plt.xlabel("Sample Index")
    plt.ylabel("Error")
    plt.legend()
    plt.grid(True)
    plt.show()

    return encoded, recon_error


# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    third_file = "A:/TB/Tool/Data_tests/IndustrialData/files/V60N/tests/Corner-power/V24-2025__0003.parquet"
    encoded_features, reconstruction_error = project_new_file(third_file)
