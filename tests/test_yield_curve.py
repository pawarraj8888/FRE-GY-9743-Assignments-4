"""Checks for the IFR yield-curve model (fixedincomelib/yield_curve/yield_curve_model.py).

    python tests/test_yield_curve.py        # plain runner
    python -m pytest tests -q               # with pytest

The reference numbers are the ones printed by hw4_ifr_yield_curve.ipynb.
"""
import os
import sys

import numpy as np
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from fixedincomelib import (  # noqa: E402
    qfAddPeriod, qfAccrued, qfCreateData1D, qfCreateDataCollection, qfCreateBuildMethod,
    qfCreateModelBuildMethodCollection, qfCreateModel, qfDiscountFactor,
    qfCreateProductFixedAccruedCashflow,
)
from fixedincomelib.date import Date  # noqa: E402
from fixedincomelib.yield_curve import YieldCurve  # noqa: E402

VALUE_DATE = "2026-10-07"
PROJECTION_IFR = [0.030, 0.031, 0.032, 0.033, 0.034, 0.035, 0.036, 0.037, 0.038, 0.039]
QUERY_TENORS = ["6M", "1Y", "2Y", "5Y", "10Y", "15Y"]


def build(funding_values=(0.0,), funding_tenors=("1Y",)):
    """The notebook's two-component model; returns the model and its two build methods."""
    projection = pd.DataFrame({"values": PROJECTION_IFR},
                              index=pd.Index([f"{y}Y" for y in range(1, 11)], name="Tenor"))
    funding = pd.DataFrame({"values": list(funding_values)}, index=pd.Index(list(funding_tenors), name="Tenor"))
    data = qfCreateDataCollection([
        qfCreateData1D("INSTANTANEOUS FORWARD RATE", "SOFR-1B-IFR", projection),
        qfCreateData1D("INSTANTANEOUS FORWARD RATE", "SOFR-1B-FUNDING-IFR", funding),
    ])
    projection_bm = qfCreateBuildMethod("YIELD_CURVE_INDEX",
                                        {"TARGET": "SOFR-1B", "INSTANTANEOUS FORWARD RATE": "SOFR-1B-IFR"})
    funding_bm = qfCreateBuildMethod("YIELD_CURVE_FUNDING",
                                     {"TARGET": "SOFR-1B-FLAT", "REFERENCE INDEX": "SOFR-1B",
                                      "INSTANTANEOUS FORWARD RATE": "SOFR-1B-FUNDING-IFR"})
    model = qfCreateModel(VALUE_DATE, "YIELD_CURVE", data,
                          qfCreateModelBuildMethodCollection([projection_bm, funding_bm]))
    return model, projection_bm, funding_bm


def curve_time(date):
    return qfAccrued(VALUE_DATE, date, "ACT/ACT (ISDA)")


def query_dates():
    return [qfAddPeriod(VALUE_DATE, tenor, "F", "USGS") for tenor in QUERY_TENORS]


def integral_by_hand(times, values, upper):
    """integral_0^upper f, with f = values[i] on (times[i-1], times[i]] and flat beyond the last node."""
    total, lower = 0.0, 0.0
    for i, t in enumerate(times):
        if upper <= lower:
            break
        total += values[i] * (min(upper, t) - lower)
        lower = t
    if upper > lower:
        total += values[-1] * (upper - lower)
    return total


# --------------------------------------------------------------------------- #
# component discount factors
# --------------------------------------------------------------------------- #
def test_component_discount_factor_is_exp_of_minus_integrated_ifr():
    model, projection_bm, _ = build()
    component = model.retrieve_model_component(projection_bm.target_index)
    times, values = component.state_data[0], component.state_data[1]
    assert np.allclose(values, PROJECTION_IFR)
    for date in query_dates():
        expected = np.exp(-integral_by_hand(times, values, curve_time(date)))
        assert abs(component.discount_factor(Date(date)) - expected) < 1e-14, date


def test_flat_extrapolation_uses_the_last_node_beyond_ten_years():
    model, projection_bm, _ = build()
    component = model.retrieve_model_component(projection_bm.target_index)
    times, values = component.state_data[0], component.state_data[1]
    date_15y = qfAddPeriod(VALUE_DATE, "15Y", "F", "USGS")
    inside = integral_by_hand(times, values, times[-1])
    expected = np.exp(-(inside + values[-1] * (curve_time(date_15y) - times[-1])))
    assert abs(component.discount_factor(Date(date_15y)) - expected) < 1e-14


def test_discount_factor_on_the_value_date_is_one():
    model, projection_bm, funding_bm = build()
    assert model.retrieve_model_component(projection_bm.target_index).discount_factor(Date(VALUE_DATE)) == 1.0
    assert qfDiscountFactor(model, "SOFR-1B", VALUE_DATE) == 1.0
    assert qfDiscountFactor(model, "SOFR-1B-FLAT", VALUE_DATE) == 1.0


def test_invalid_dates_are_rejected():
    model, projection_bm, _ = build()
    component = model.retrieve_model_component(projection_bm.target_index)
    for bad in (Date("null date"), Date("2026-10-06")):
        try:
            component.discount_factor(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad}")


# --------------------------------------------------------------------------- #
# model discount factors through references
# --------------------------------------------------------------------------- #
def test_index_without_reference_equals_its_component():
    model, projection_bm, _ = build()
    component = model.retrieve_model_component(projection_bm.target_index)
    for date in query_dates():
        assert qfDiscountFactor(model, "SOFR-1B", date) == component.discount_factor(Date(date))


def test_funding_curve_multiplies_reference_and_local_factors():
    model, _, funding_bm = build(funding_values=(0.001,))
    funding = model.retrieve_model_component(funding_bm.target_index)
    for date in query_dates():
        t = curve_time(date)
        local = funding.discount_factor(Date(date))
        assert abs(local - np.exp(-0.001 * t)) < 1e-14
        expected = qfDiscountFactor(model, "SOFR-1B", date) * local
        assert abs(qfDiscountFactor(model, "SOFR-1B-FLAT", date) - expected) < 1e-14


def test_multi_node_funding_spread_is_integrated_on_its_own_grid():
    model, _, funding_bm = build(funding_values=(0.001, 0.002), funding_tenors=("1Y", "3Y"))
    funding = model.retrieve_model_component(funding_bm.target_index)
    times, values = funding.state_data[0], funding.state_data[1]
    assert np.allclose(values, [0.001, 0.002])
    for date in query_dates():
        expected = np.exp(-integral_by_hand(times, values, curve_time(date)))
        assert abs(funding.discount_factor(Date(date)) - expected) < 1e-14
        assert abs(qfDiscountFactor(model, "SOFR-1B-FLAT", date)
                   - qfDiscountFactor(model, "SOFR-1B", date) * expected) < 1e-14


def test_zero_funding_spread_makes_both_curves_agree():
    model, _, _ = build()
    for date in query_dates():
        assert qfDiscountFactor(model, "SOFR-1B-FLAT", date) == qfDiscountFactor(model, "SOFR-1B", date)


def test_unknown_index_is_rejected():
    model, _, _ = build()
    try:
        qfDiscountFactor(model, "EONIA-1B", "2027-10-07")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for an unknown index")


def test_serialized_model_rebuilds_to_the_same_curve():
    model, _, _ = build(funding_values=(0.001,))
    rebuilt = YieldCurve.deserialize(model.serialize())
    for date in query_dates():
        for index in ("SOFR-1B", "SOFR-1B-FLAT"):
            assert qfDiscountFactor(rebuilt, index, date) == qfDiscountFactor(model, index, date)


# --------------------------------------------------------------------------- #
# the notebook's numbers and the analytic risk
# --------------------------------------------------------------------------- #
def notebook_product_and_price(model):
    termination = qfAddPeriod(VALUE_DATE, "5Y", "F", "USGS")
    product = qfCreateProductFixedAccruedCashflow(
        effective_date=VALUE_DATE, termination_date=termination, currency="USD", notional=100.0,
        accrual_basis="ACT/360", payment_date=termination)
    c = product.notional * product.accrued
    df = qfDiscountFactor(model, "SOFR-1B-FLAT", product.payment_date.ISO(), "USD")
    return product, c, df, c * df


def test_notebook_discount_factors_are_reproduced():
    model, _, _ = build()
    reference = {"6M": 0.985152, "1Y": 0.970446, "2Y": 0.940565, "5Y": 0.852156, "10Y": 0.708223, "15Y": 0.582765}
    for tenor, date in zip(QUERY_TENORS, query_dates()):
        assert abs(qfDiscountFactor(model, "SOFR-1B", date) - reference[tenor]) < 5e-7, tenor
        assert abs(qfDiscountFactor(model, "SOFR-1B-FLAT", date) - reference[tenor]) < 5e-7, tenor


def test_notebook_price_is_reproduced():
    model, _, _ = build()
    product, c, df, value = notebook_product_and_price(model)
    assert product.payment_date.ISO() == "2031-10-07"
    assert abs(c - 507.222222) < 5e-7 and abs(df - 0.852156) < 5e-7 and abs(value - 432.232456) < 5e-7


def analytic_risk(model, projection_bm, funding_bm, product, value):
    T = curve_time(product.payment_date.ISO())
    projection = model.retrieve_model_component(projection_bm.target_index)
    funding = model.retrieve_model_component(funding_bm.target_index)
    w_p = projection.state_data_interpolator.gradient_of_integrated_value_wrt_ordinate(0.0, T)
    w_f = funding.state_data_interpolator.gradient_of_integrated_value_wrt_ordinate(0.0, T)
    return -value * w_p, -value * w_f


def test_notebook_analytic_risk_is_reproduced():
    model, projection_bm, funding_bm = build()
    product, _, _, value = notebook_product_and_price(model)
    projection_risk, funding_risk = analytic_risk(model, projection_bm, funding_bm, product, value)
    reference = [-432.232456, -436.053599, -430.779710, -429.864059, -432.232456, 0, 0, 0, 0, 0]
    assert np.allclose(projection_risk, reference, atol=5e-7)
    assert abs(funding_risk[0] + 2161.162279) < 5e-7
    assert abs(funding_risk[0] + curve_time(product.payment_date.ISO()) * value) < 1e-9


def test_analytic_risk_matches_central_bump_and_reval():
    model, projection_bm, funding_bm = build()
    product, c, _, value = notebook_product_and_price(model)
    projection_risk, funding_risk = analytic_risk(model, projection_bm, funding_bm, product, value)
    h = 1e-6

    def price():
        return c * qfDiscountFactor(model, "SOFR-1B-FLAT", product.payment_date.ISO(), "USD")

    for target, risk in ((projection_bm.target_index, projection_risk), (funding_bm.target_index, funding_risk)):
        for i, analytic in enumerate(risk):
            model.perturb_model_parameter(target, i, h)
            up = price()
            model.perturb_model_parameter(target, i, -2 * h)
            down = price()
            model.perturb_model_parameter(target, i, h)          # restore
            assert abs((up - down) / (2 * h) - analytic) < 1e-4, (target.name(), i)
    assert abs(price() - value) < 1e-12                           # state restored exactly


if __name__ == "__main__":
    tests = [obj for name, obj in sorted(globals().items()) if name.startswith("test_") and callable(obj)]
    for test in tests:
        test()
        print(f"PASS  {test.__name__}")
    print(f"\n{len(tests)} tests passed")
