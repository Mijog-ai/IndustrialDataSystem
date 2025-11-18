import pandas as pd

# Read CSV
df = pd.read_csv("data/V24-2025__0002.csv")

# Drop empty rows
df = df.dropna(how='all')

# Fill NaN with 0
df = df.fillna(0)

# Save back to CSV
df.to_csv("output.csv", index=False)