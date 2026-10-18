"""Generate docs/index.html: the Assignment 4 project page (IFR curve, discount factors, price and analytic risk).

Run from the repository root with the QuantLib interpreter:  python docs/build_page.py
"""
import html, os, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests")); os.chdir(ROOT)
from test_yield_curve import build, query_dates, notebook_product_and_price, analytic_risk, curve_time, QUERY_TENORS, VALUE_DATE  # noqa: E402
from fixedincomelib import qfDiscountFactor  # noqa: E402

model, projection_bm, funding_bm = build()
proj = model.retrieve_model_component(projection_bm.target_index)
fund = model.retrieve_model_component(funding_bm.target_index)
times, ifr = proj.state_data[0], proj.state_data[1]
dates = query_dates()
product, c, df, V = notebook_product_and_price(model)
T = curve_time(product.payment_date.ISO())
proj_risk, fund_risk = analytic_risk(model, projection_bm, funding_bm, product, V)

# ---- SVG: piecewise-constant IFR (left axis) and the discount curve (right axis) over 0..15 years
W, H, L, R, TOP, BOT = 760, 300, 56, 56, 18, 40
x_max = 15.0
def x(t): return L + (W - L - R) * t / x_max
def y_left(v): return TOP + (H - TOP - BOT) * (1 - (v - 0.028) / (0.040 - 0.028))
def y_right(d): return TOP + (H - TOP - BOT) * (1 - (d - 0.55) / (1.0 - 0.55))
step = []
lower = 0.0
for t, f in zip(times, ifr):
    step.append(f"M{x(lower):.1f},{y_left(f):.1f} L{x(t):.1f},{y_left(f):.1f}")
    lower = t
step.append(f"M{x(lower):.1f},{y_left(ifr[-1]):.1f} L{x(x_max):.1f},{y_left(ifr[-1]):.1f}")
grid = np.linspace(0.0, x_max, 151)
curve = " ".join(f"{'M' if i == 0 else 'L'}{x(t):.1f},{y_right(np.exp(-proj.state_data_interpolator.integrate(0.0, t))):.1f}" for i, t in enumerate(grid))
svg = f"""<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Piecewise-constant SOFR IFR and the implied discount curve">
<rect x="{L}" y="{TOP}" width="{W-L-R}" height="{H-TOP-BOT}" fill="none" stroke="#d8d8d8"/>
{''.join(f'<line x1="{x(t):.1f}" y1="{TOP}" x2="{x(t):.1f}" y2="{H-BOT}" stroke="#eee"/><text x="{x(t):.1f}" y="{H-BOT+16}" font-size="11" text-anchor="middle" fill="#555">{t:g}Y</text>' for t in range(0, 16, 1))}
{''.join(f'<text x="{L-6}" y="{y_left(v)+4:.1f}" font-size="11" text-anchor="end" fill="#1f4e79">{v*100:.1f}%</text>' for v in (0.028, 0.031, 0.034, 0.037, 0.040))}
{''.join(f'<text x="{W-R+6}" y="{y_right(d)+4:.1f}" font-size="11" text-anchor="start" fill="#8a4b00">{d:.2f}</text>' for d in (0.55, 0.70, 0.85, 1.00))}
<path d="{' '.join(step)}" fill="none" stroke="#1f4e79" stroke-width="2"/>
<path d="{curve}" fill="none" stroke="#c77800" stroke-width="2" stroke-dasharray="5 3"/>
<text x="{L+8}" y="{TOP+14}" font-size="12" fill="#1f4e79">SOFR-1B instantaneous forward rate (left axis)</text>
<text x="{L+8}" y="{TOP+30}" font-size="12" fill="#8a4b00">discount factor exp(-integral of f) (right axis)</text>
</svg>"""

def table(headers, rows):
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

state_rows = [["SOFR-1B", f"{i+1}Y", f"{t:.6f}", f"{f:.3f}"] for i, (t, f) in enumerate(zip(times, ifr))] + [["SOFR-1B-FLAT", "1Y", f"{fund.state_data[0][0]:.6f}", f"{fund.state_data[1][0]:.3f}"]]
df_rows = [[tenor, d, f"{curve_time(d):.6f}", f"{qfDiscountFactor(model, 'SOFR-1B', d):.6f}", f"{fund.discount_factor(__import__('fixedincomelib.date', fromlist=['Date']).Date(d)):.6f}", f"{qfDiscountFactor(model, 'SOFR-1B-FLAT', d):.6f}"] for tenor, d in zip(QUERY_TENORS, dates)]
risk_rows = [["SOFR-1B", f"{i+1}Y", f"{ifr[i]:.3f}", f"{proj_risk[i]:.6f}"] for i in range(len(ifr))] + [["SOFR-1B-FLAT", "1Y", f"{fund.state_data[1][0]:.3f}", f"{fund_risk[0]:.6f}"]]

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>FRE-GY 9743 Assignment 4 · Raj Pawar</title>
<style>
body{{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:#222;max-width:900px;margin:32px auto;padding:0 16px}}
h1{{font-size:24px;margin:0 0 4px}} h2{{font-size:18px;margin:28px 0 8px;border-bottom:1px solid #ddd;padding-bottom:4px}}
.meta{{color:#555;margin-bottom:16px}} a{{color:#1f4e79}} code{{background:#f4f4f4;padding:1px 4px;border-radius:3px}}
table{{border-collapse:collapse;margin:8px 0 12px;font-size:14px}} th,td{{border:1px solid #ddd;padding:4px 10px;text-align:right}} th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}}
th{{background:#f7f7f7}} .formula{{font-family:"Times New Roman",serif;font-size:16px}}
</style></head><body>
<h1>FRE-GY 9743 · Assignment 4: yield curves from instantaneous forward rates</h1>
<div class="meta">Raj Pawar · branch <a href="https://github.com/pawarraj8888/FRE-GY-9743-Assignments-4/tree/Raj_Pawar_Branch">Raj_Pawar_Branch</a> · value date {VALUE_DATE}</div>
<p>The model holds one piecewise-constant instantaneous forward rate (IFR) curve per component. A component's own discount factor is
<span class="formula">D<sub>local</sub>(t) = exp(&minus;&int;<sub>0</sub><sup>t</sup> f(s) ds)</span>, and the model follows the registered reference chain,
so the funding curve <code>SOFR-1B-FLAT</code> returns <span class="formula">D<sub>SOFR</sub>(t) &middot; D<sub>local</sub>(t)</span>.
Curve time is ACT/ACT (ISDA) from the value date; tenors roll Following on the USGS calendar.</p>
<h2>IFR state and the implied discount curve</h2>
{svg}
{table(["Component", "Tenor", "Time (years)", "IFR"], state_rows)}
<h2>Discount factors at the query dates</h2>
{table(["Tenor", "Date", "Curve time", "SOFR-1B", "Funding component only", "SOFR-1B-FLAT"], df_rows)}
<p>With a zero funding spread the local funding factor is 1 and the two complete curves agree.</p>
<h2>Price and analytic IFR risk of a 5-year fixed-accrual cashflow</h2>
<p>Notional 100, ACT/360, payment on {product.payment_date.ISO()}: cashflow c = {c:.6f}, discount factor {df:.6f}, price V = {V:.6f}.
The risk per unit of IFR is &minus;V&middot;w<sub>i</sub>, where w<sub>i</sub> is the length of node i's bucket inside [0, T] with T = {T:.6f};
the single funding node carries &minus;T&middot;V. Nodes beyond the payment date carry no risk.</p>
{table(["Component", "Tenor", "IFR", "dV/dX_I"], risk_rows)}
<h2>What is on the branch</h2>
<ul>
<li><code>fixedincomelib/yield_curve/yield_curve_model.py</code>: the two TODO blocks (component and recursive model discount factors).</li>
<li><code>fixedincomelib/utilities/numerics.py</code>: the Assignment 1 piecewise-constant interpolator, carried over.</li>
<li><code>hw4_ifr_yield_curve.ipynb</code>: the professor's notebook with the three TODO cells completed and executed.</li>
<li><code>tests/test_yield_curve.py</code> and <code>tests/test_interpolator_pcp.py</code>: {len(proj_risk)} IFR nodes checked by hand, bump-and-reval, serialization, validation.</li>
<li><code>writeup/Assignment4_Writeup_RajPawar.pdf</code>: Part I (OTC discount factor versus futures daily settlement) and a Part II summary.</li>
</ul>
<p class="meta">Page generated by <code>docs/build_page.py</code> from the library itself; the numbers are not typed in.</p>
</body></html>
"""
(ROOT / "docs" / "index.html").write_text(page)
print("wrote docs/index.html", len(page), "bytes")
