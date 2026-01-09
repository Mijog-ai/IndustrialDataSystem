# DataFrame Column Filtering - Quick Reference

## 🎯 Goal
Keep only specific columns from your DataFrame and remove the rest.

---

## 📊 Your Data

**Original columns:**
- Messzeit[s]
- Pressure [bar]
- Flow [L/min]
- Leak [L/min]
- Speed [rpm]
- Torque [Nm]
- LS [bar]
- Housing [bar]
- TempSaug [°C]
- TempLeak [°C]

**Columns to keep:**
- Messzeit[s]
- Pressure [bar]
- Flow [L/min]
- Leak [L/min]
- Torque [Nm]

---

## 🔧 Method 1: Select Specific Columns (RECOMMENDED)

```python
# List the columns you want to keep
columns_to_keep = [
    'Messzeit[s]',
    'Pressure [bar]',
    'Flow [L/min]',
    'Leak [L/min]',
    'Torque [Nm]'
]

# Create new DataFrame with only these columns
df_filtered = df[columns_to_keep]

# Check the result
print(f"Original: {df.shape[1]} columns")
print(f"Filtered: {df_filtered.shape[1]} columns")
```

**Pros:**
- ✅ Clear and explicit
- ✅ Easy to understand
- ✅ Safe - will error if column doesn't exist

**Cons:**
- ❌ Need to type exact column names

---

## 🔧 Method 2: Drop Unwanted Columns

```python
# List the columns you want to REMOVE
columns_to_remove = [
    'Speed [rpm]',
    'LS [bar]',
    'Housing [bar]',
    'TempSaug [°C]',
    'TempLeak [°C]'
]

# Create new DataFrame without these columns
df_filtered = df.drop(columns=columns_to_remove)

# Or use errors='ignore' to skip if column doesn't exist
df_filtered = df.drop(columns=columns_to_remove, errors='ignore')
```

**Pros:**
- ✅ Good when you have many columns to keep
- ✅ Can ignore missing columns with `errors='ignore'`

**Cons:**
- ❌ Less explicit about what you're keeping

---

## 🔧 Method 3: Filter by Pattern

```python
# Keep columns containing certain keywords
keywords = ['Messzeit', 'Pressure', 'Flow', 'Leak', 'Torque']

# Find matching columns
matching_columns = [col for col in df.columns 
                   if any(keyword in col for keyword in keywords)]

# Create filtered DataFrame
df_filtered = df[matching_columns]
```

**Pros:**
- ✅ Works with partial matches
- ✅ Good for many similar columns
- ✅ Flexible

**Cons:**
- ❌ Might match unexpected columns
- ❌ Less precise

---

## 🔧 Method 4: Filter by Data Type

```python
# Keep only numeric columns
df_numeric = df.select_dtypes(include=[np.number])

# Keep only specific numeric columns
numeric_cols = df.select_dtypes(include=[np.number]).columns
columns_to_keep = ['Messzeit[s]', 'Pressure [bar]', 'Flow [L/min]', 'Leak [L/min]', 'Torque [Nm]']
df_filtered = df[[col for col in columns_to_keep if col in numeric_cols]]
```

---

## 📝 Complete Example

```python
import pandas as pd

# Load your data
df = pd.read_parquet('your_file.parquet')

print(f"Original shape: {df.shape}")
print(f"Original columns: {df.columns.tolist()}")

# Method 1: Select specific columns
columns_to_keep = [
    'Messzeit[s]',
    'Pressure [bar]',
    'Flow [L/min]',
    'Leak [L/min]',
    'Torque [Nm]'
]

df_filtered = df[columns_to_keep]

print(f"\nFiltered shape: {df_filtered.shape}")
print(f"Filtered columns: {df_filtered.columns.tolist()}")

# Preview the data
print("\nFirst 5 rows:")
print(df_filtered.head())

# Check statistics
print("\nStatistics:")
print(df_filtered.describe())
```

---

## 💾 Save Filtered Data

### Save as Parquet (Recommended)
```python
df_filtered.to_parquet('filtered_data.parquet', index=False)
```

**Pros:**
- Fast to read/write
- Smaller file size
- Preserves data types

### Save as CSV
```python
df_filtered.to_csv('filtered_data.csv', index=False)
```

**Pros:**
- Human-readable
- Compatible with Excel
- Universal format

### Save as Excel
```python
df_filtered.to_excel('filtered_data.xlsx', index=False)
```

---

## 🔍 Troubleshooting

### Problem: Column not found error
```python
KeyError: "['Column Name'] not found in axis"
```

**Solution 1:** Check exact column names
```python
print(df.columns.tolist())
```

**Solution 2:** Use error handling
```python
columns_to_keep = ['Messzeit[s]', 'Pressure [bar]', 'Flow [L/min]']
existing_columns = [col for col in columns_to_keep if col in df.columns]
df_filtered = df[existing_columns]
```

### Problem: Not sure of exact column names

**Solution:** Search for columns
```python
# Find columns containing "Pressure"
pressure_cols = [col for col in df.columns if 'Pressure' in col]
print(pressure_cols)

# Case-insensitive search
temp_cols = [col for col in df.columns if 'temp' in col.lower()]
print(temp_cols)
```

### Problem: Want to keep columns in specific order

**Solution:** Specify order in list
```python
columns_to_keep = [
    'Messzeit[s]',      # Time will be first
    'Pressure [bar]',   # Pressure second
    'Flow [L/min]',     # Flow third
    'Leak [L/min]',     # Leak fourth
    'Torque [Nm]'       # Torque last
]

df_filtered = df[columns_to_keep]
```

---

## 🎨 Advanced Filtering

### Keep columns matching multiple patterns
```python
# Keep columns with "Pressure" OR "Flow" OR "Torque"
patterns = ['Pressure', 'Flow', 'Torque']
matching = [col for col in df.columns 
           if any(pattern in col for pattern in patterns)]
df_filtered = df[matching]
```

### Keep columns NOT matching a pattern
```python
# Remove all temperature columns
df_filtered = df[[col for col in df.columns if 'Temp' not in col]]
```

### Keep columns by index position
```python
# Keep first column and columns 2-5
df_filtered = df.iloc[:, [0, 1, 2, 3, 4]]

# Or by slice
df_filtered = df.iloc[:, 0:5]  # First 5 columns
```

### Keep columns with specific units
```python
# Keep only columns with [bar] or [L/min] units
units = ['[bar]', '[L/min]']
matching = [col for col in df.columns 
           if any(unit in col for unit in units)]
df_filtered = df[matching]
```

---

## 📊 Verify Your Filtering

```python
# Before filtering
print("BEFORE FILTERING:")
print(f"Shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
print(f"Memory: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

# After filtering
print("\nAFTER FILTERING:")
print(f"Shape: {df_filtered.shape}")
print(f"Columns: {df_filtered.columns.tolist()}")
print(f"Memory: {df_filtered.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

# Show what was removed
removed_cols = set(df.columns) - set(df_filtered.columns)
print(f"\nRemoved {len(removed_cols)} columns:")
for col in removed_cols:
    print(f"  - {col}")
```

---

## 🚀 Quick Copy-Paste Solution

For your specific case, just copy and paste this:

```python
# Keep only the columns you need
df_filtered = df[[
    'Messzeit[s]',
    'Pressure [bar]',
    'Flow [L/min]',
    'Leak [L/min]',
    'Torque [Nm]'
]]

# Verify
print(f"Kept {df_filtered.shape[1]} columns: {df_filtered.columns.tolist()}")

# Preview
df_filtered.head()
```

That's it! 🎉

---

## 📚 Summary

| Method | When to Use | Code |
|--------|-------------|------|
| **Select columns** | You know exact names | `df[['col1', 'col2']]` |
| **Drop columns** | Easier to list what to remove | `df.drop(columns=['col1'])` |
| **Pattern match** | Many similar columns | `df[[col for col in df.columns if 'pattern' in col]]` |
| **By data type** | Keep all numeric/string columns | `df.select_dtypes(include=[np.number])` |

**Recommendation:** Use **Method 1 (Select columns)** for clarity and safety.
