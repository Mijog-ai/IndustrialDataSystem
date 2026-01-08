# Jupyter Notebooks for Testing IDS Components

This directory contains Jupyter notebooks for testing and exploring various components of the Industrial Data System (IDS).

## Notebooks

1. **01_data_loading_preprocessing.ipynb** - Test data loading from ASC files and preprocessing
2. **02_fft_analysis.ipynb** - Test FFT analysis and frequency domain transformations
3. **03_anomaly_detection.ipynb** - Test anomaly detection models and algorithms
4. **04_visualization.ipynb** - Test plotting and visualization components
5. **05_integration_testing.ipynb** - End-to-end integration testing

## Setup

Ensure you have Jupyter installed:

```bash
pip install jupyter notebook ipykernel matplotlib pandas numpy
```

## Running Notebooks

From the project root:

```bash
jupyter notebook industrial_data_system/notebooks/
```

Or from this directory:

```bash
cd industrial_data_system/notebooks
jupyter notebook
```

## Data Files

Test data should be placed in `industrial_data_system/Tests/Data/` directory.
