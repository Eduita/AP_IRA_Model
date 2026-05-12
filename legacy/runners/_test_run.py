"""Quick smoke test: 2 simulations, NPV only, monthly matching."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Import only the pieces needed — do NOT import probabilistic_model_runner
# directly because it has top-level run_simulation() calls that trigger 4000 sims.
import importlib
import types

# Load the module source without executing module-level simulation calls
src_path = os.path.join(os.path.dirname(__file__), "probabilistic_model_runner.py")
with open(src_path) as f:
    source = f.read()

# Strip the module-level execution block (everything after the function definition)
# The run_simulation function ends; the rest are bare calls we don't want.
cutoff = source.find("\nCBAM = False")
assert cutoff != -1, "Could not find module-level block to strip"
safe_source = source[:cutoff]

mod = types.ModuleType("probabilistic_model_runner")
mod.__file__ = src_path
exec(compile(safe_source, src_path, "exec"), mod.__dict__)

run_simulation = mod.run_simulation

# --- Run ---
print("Starting 2-simulation NPV test (monthly matching)...")
result = run_simulation(2, NPV=True, isCBAM=False, matching="monthly")
print("\nResult shape:", result.shape)
print(result.to_string())
