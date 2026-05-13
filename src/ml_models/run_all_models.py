"""
Master pipeline — runs all four models in sequence.
Execute this file to train, evaluate, and save all models.

Run: python src/ml_models/run_all_models.py
"""

import subprocess, sys, time

models = [
    ("Model 1 — Delay Classifier",   "src/ml_models/model1_delay_classifier.py"),
    ("Model 2 — Delay Severity",      "src/ml_models/model2_delay_severity.py"),
    ("Model 3 — Supplier Risk",       "src/ml_models/model3_supplier_risk.py"),
    ("Model 4 — Inventory Forecast",  "src/ml_models/model4_inventory_forecast.py"),
]

print("=" * 65)
print("  SUPPLY CHAIN ML PIPELINE — FULL TRAINING RUN")
print("=" * 65)

results = []
for name, script in models:
    print(f"\n▶ Running {name}...")
    start = time.time()
    result = subprocess.run([sys.executable, script], capture_output=False)
    elapsed = time.time() - start
    status = "✅ SUCCESS" if result.returncode == 0 else "❌ FAILED"
    results.append((name, status, f"{elapsed:.1f}s"))
    print(f"  {status} — {elapsed:.1f}s")

print("\n" + "=" * 65)
print("  PIPELINE SUMMARY")
print("=" * 65)
for name, status, time_taken in results:
    print(f"  {status}  {name:<35} {time_taken}")

print("\n  Outputs:")
print("  ├── models/                    ← Saved model files (.pkl)")
print("  ├── data/processed/            ← Risk scores, forecasts")
print("  └── reports/figures/           ← Evaluation charts")
