# HW4: Yield Curves from Instantaneous Forward Rates

NYU FRE-GY 9743, Fall 2026.

---

## Assignment 4 submission: Raj Pawar (`Raj_Pawar_Branch`)

| Deliverable | Location |
|---|---|
| Library TODOs: the component discount factor `exp(-integral of the IFR)` and the model's recursive discount factor through curve references | `fixedincomelib/yield_curve/yield_curve_model.py` |
| Piecewise-constant interpolator from Assignment 1, carried over into the identical skeleton | `fixedincomelib/utilities/numerics.py` |
| Professor's notebook with the three `#TODO` cells completed (product, discount factor, analytic IFR risk), executed top to bottom | `hw4_ifr_yield_curve.ipynb` |
| Tests (component and model discount factors by hand, funding spread recursion, flat extrapolation, the notebook's reference numbers, analytic risk against bump-and-reval, serialization, validation errors) plus the interpolator tests | `tests/test_yield_curve.py`, `tests/test_interpolator_pcp.py` |
| Write-up: Part I (why exchange-traded futures carry no discount factor while collateralised OTC trades do) and a summary of Part II | `writeup/Assignment4_Writeup_RajPawar.pdf` (source `.tex` alongside) |

### How to run

```bash
pip install -r requirements.txt            # Python 3.11, QuantLib 1.41
jupyter notebook hw4_ifr_yield_curve.ipynb # Run All
python tests/test_yield_curve.py           # or: python -m pytest tests -q
```

Only the `TODO` blocks were filled in; the model, builder, data, product and API layers are unchanged.
