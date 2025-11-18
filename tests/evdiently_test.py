import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
# from evidently. import DataQualityPreset, TargetDriftPreset
from evidently.metrics import DatasetCorrelations
# Load CSV files
reference_data = pd.read_csv("data/V24-2025__0001.csv").dropna(how='all').fillna(0)
current_data = pd.read_csv("data/V24-2025__0009.csv").dropna(how='all').fillna(0)

# Create report with multiple presets
report = Report(metrics=[
    DataDriftPreset(),
    # DataQualityPreset(),
    # Add more metrics as needed:
    DatasetCorrelations(),
    # ColumnDriftMetric(column_name="your_column"),
])

# Generate report
r= report.run(reference_data=reference_data, current_data=current_data)

# Save report
r.save_html("drift_report.html")

print("Evidently report saved to: drift_report.html")