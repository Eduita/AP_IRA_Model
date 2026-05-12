# AP IRA Model

Stochastic financial analysis of four ammonia production technologies under U.S. Inflation Reduction Act (IRA) tax credits.

**Published paper:** [Nature Communications, 2025](https://www.nature.com/articles/s41467-025-56006-6)

---

## Overview

The model runs a Monte Carlo discounted cash flow (DCF) simulation across four ammonia production technologies, four electricity supply scenarios, and two deployment time horizons (2023 / 2030). Key outputs are:

| Output | Description |
|---|---|
| **NPV** | Net Present Value (with and without IRA policy) |
| **CAC** | Carbon Abatement Cost |
| **CI** | Carbon Intensity over the plant lifetime |
| **Tax Credits** | Annual value of 45V, 45Q, 45Y, and 48E credits |

### Technologies

| ID | Description |
|---|---|
| AP SMR | Steam methane reforming (fossil baseline) |
| AP CCS | SMR with carbon capture & storage |
| AP BH2S | Biomass-powered hydrogen synthesis |
| AP AEC | Alkaline electrolysis cell (green H2) |

### Scenarios

| ID | Electricity supply |
|---|---|
| A | Grid — AEO 2022 projections |
| B | Grid — AEO 2023 projections |
| C | Dedicated renewables + storage (wind / solar / battery) |
| D | Power Purchase Agreement (PPA) |

---

## Repository structure

```
AP_IRA_Model/
├── data/               # Shared input datasets (LCOE, PPA output, parameters, AEO energy mix)
├── paper/              # Research paper: LaTeX source, compiled PDF, and figures
├── legacy/             # Original monolithic Python codebase
│   ├── *.py            # Model modules and runners
│   ├── visualization/  # Figure-generating scripts
│   ├── power_markets/  # Location and optimization data
│   └── datasets/       # Raw input spreadsheets
└── refactor/           # Modular rewrite (ap_ira_lib)
    ├── ap_ira_lib/     # Installable library
    │   ├── core/       # CAPEX, OPEX, DCF, GBM, tax credits, carbon intensity
    │   ├── inputs/     # Parameter loading
    │   ├── io/         # Excel I/O and data cleaning
    │   └── pipeline/   # Stage-based simulation pipeline
    ├── models/         # YAML model configuration (ap_ira.yaml)
    ├── scripts/        # CLI entry point (run.py)
    └── pyproject.toml  # Package metadata and dependencies
```

---

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies
cd refactor
uv sync

# Run with default config
uv run python scripts/run.py

# Run with a custom config
uv run python scripts/run.py --config models/ap_ira.yaml
```

Results are written to `results/` as a timestamped Excel file containing NPV, CAC, CI, and tax credit sheets.

---

## Configuration

The simulation is driven by [`refactor/models/ap_ira.yaml`](refactor/models/ap_ira.yaml). Key settings:

```yaml
simulation:
  n_simulations: 400   # Monte Carlo draws per (scenario × time horizon)
  matching: monthly    # temporal matching: yearly | monthly | hourly
  L: 480               # plant lifetime in months (40 years)
  cbam: false          # include EU CBAM CO2 border price
```

The pipeline is a list of ordered stages. Each stage can be swapped by pointing `module` and `class` at a custom `Stage` subclass — see the YAML for details.

---

## Development

```bash
cd refactor
uv sync --dev
uv run pytest
uv run ruff check .
```
