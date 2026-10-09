# `mmm_0_4`: redesign of the MMT Job Guarantee macro model

**Warning!** 

(Apologies to PukahaPai code base readers, this doc was auto-generated 
by an LLM.  I have not thoroughly vetted it, life was too short. But it 
looks ok at first glances.)


## 1. Why the previous version drove labour into the JG

The previous `mmm_0_4` was numerically consistent but economically poorly
closed.  In particular, its growing Job Guarantee pool was not evidence 
that the JG itself was "too attractive", but it loked that way, so was a 
bad model.  The JG was already defined as the **residual** labour pool.

The main problem was the rest of the model.

The old regular public sector used

```text
L_G = public_payroll / w_G
```

with a fixed nominal payroll and a fixed government wage.  Consequently
`L_G` was approximately constant in absolute worker numbers.

At the same time the model assumed

```text
N ~ exp(beta t)
A_F ~ exp(alpha_F t)
```

with `beta = 0.01` and `alpha_F = 0.02`.  Population therefore grew by about
1 percent per year while private productivity grew by about 2 percent per
year.

The old government goods budget was also fixed in nominal terms.

This gives the model a built-in long-run tendency:

1. regular government employment becomes a smaller fraction of the growing
   labour force;
2. fixed government procurement becomes a smaller fraction of the economy;
3. private productive capacity grows faster than several important components
   of nominal demand;
4. the goods-market demand gap becomes negative;
5. `lambda_F` falls;
6. the residual labour pool is automatically assigned to `L_JG`.

Thus the JG was not "preferred".  It was receiving workers whom neither of
the two regular-employment sectors had a reason to hire.

There was no hidden *financial* restriction on firms in that version.  Firms
did not yet have a bank-debt constraint at all.  Their hiring restriction was
the effective-demand equation.

That distinction is important: adding bank loans without adding loan-financed
investment demand would not by itself solve the employment problem.


## 2. Time units: `t = 50` means 50 years

The model declares its time unit to be the **year**.

Therefore

```text
t0 = 0
t1 = 50
```

means a fifty-year simulation, not approximately six months.

This matters enormously.  Over fifty years,

```text
N / N0 = exp(0.01 * 50)  ~= 1.65
A_F / A_F0 = exp(0.02 * 50) ~= 2.72
```

so the old fixed nominal payroll and procurement budget were being compared
with an economy whose population and productivity had changed drastically.

If a future model is to use months as its time unit, all annual rates must be
rescaled consistently.  One cannot simply reinterpret `t = 50` as months
without also changing `beta`, `alpha_F`, `tau_P`, `kappa_L`, the spending
propensities, and other rate parameters.

For the present model we keep the unit as one year and retain `t1 = 50` as a
long-run stress test.


## 3. Design principle: regular employment comes first; the JG is residual

The revised labour allocation is

```text
regular public employment
        +
private firm employment
        +
JG residual
        =
available labour force.
```

The JG does not compete for workers according to an independent labour-demand
curve.  It receives only labour not currently employed in the regular
government or firm sectors.

The wage ordering in the reference calibration is

```text
w_JG = 0.60
w_F  = 0.88
w_G  = 1.10
```

so a JG position is also not the highest-paid option.

This is the intended buffer-stock interpretation: the JG provides an
unconditional employment floor, while ordinary public and private jobs remain
the normal destinations of labour.

A smooth deterministic baseline should not necessarily make the JG pool
"cycle".  Cycling requires shocks or endogenous business-cycle dynamics.
The desired baseline behaviour is instead that the JG share settles in a
small range rather than absorbing an ever-growing fraction of the labour
force.


## 4. Regular government employment is now driven by desired public services

The old model determined public employment from a fixed nominal payroll.

The redesigned model instead specifies desired **real public services per
person**:

```text
q_G_pc = q_G_pc0 * exp(gamma_G_service * t)
Q_G_des = q_G_pc * N
L_G = Q_G_des / A_G
```

This makes the causal interpretation clearer:

> government chooses the quantity of ordinary public services it wants to
> provide; the required labour follows from public-sector productivity.

For the reference calibration,

```text
gamma_G_service = alpha_G
```

so desired public services per person grow at the same rate as public-sector
productivity.  Consequently `L_G/N` remains approximately constant at about
12 percent.

This is not a JG employment target.  It is a regular public-service-output
rule.

The distinction matters because regular public employment is supposed to
exist for the public services themselves, independently of whether the JG
happens to be large or small.


## 5. Government procurement now scales with the economy

The previous

```text
goods_budget = constant
```

also became progressively smaller relative to a growing economy.

The redesign specifies a real quantity of private goods purchased per person:

```text
Q_goods = q_goods_pc * N
G_goods = P_G * Q_goods
```

Thus procurement grows with population rather than remaining a fixed nominal
number for fifty years.

This is an important automatic demand stabilizer for the private sector.


## 6. Adding `Q_G` to total output is correct, but does not by itself hire anyone

The revised model explicitly reports

```text
Q_F
Q_G
Q_JG
Q_total = Q_F + Q_G + Q_JG
```

because public services are real production and should not disappear merely
because they are nonmarket output.

However, adding `Q_G` to an accounting total **cannot by itself fix
employment**.

Employment changes only if the model contains a behavioural or policy rule
that actually demands those public services.  That is why the redesign first
defines `Q_G_des` and derives `L_G` from it.

So the sequence is

```text
desired public services
    -> required regular public labour
    -> Q_G
```

rather than

```text
compute Q_G after the fact
    -> hope employment changes.
```

---

## 7. Private investment is reintroduced as a real-demand component

The previous model contained household consumption and government procurement
but no private gross-investment demand.

That omission is important.  In a growing monetary economy, firms normally
produce both consumption goods and investment goods.

The redesign adds the deliberately simple closure

```text
I_real = iota_F * Q_F
I_nom  = P * I_real
```

with the reference value

```text
iota_F = 0.08.
```

Private effective demand is therefore

```text
Q_demand = C/P + Q_goods + I_real.
```

This is not yet a full Kalecki/Minsky investment function.  It is a compact
gross-investment demand term whose purpose is to stop the model from treating
all private production as consumption production.

A later version should replace it with an investment equation depending on
expected sales, profitability, utilization, leverage and financing
conditions.


## 8. Why bank credit is not yet added

Bank credit is relevant, but it is logically a **second** step.

The employment defect in the old model arose before firms had any financing
constraint.  The model simply generated insufficient effective demand
relative to productive capacity.

A bank loan matters for employment only insofar as it permits additional
spending -- for example, loan-financed investment.

A proper bank-credit extension should not merely insert a positive spending
term.  It should add a consistent balance sheet, for example:

```text
firm deposits
firm loan liability
bank loan asset
bank equity / retained earnings
interest payments
principal repayments
possibly bank dividends
```

Credit creation would then create a firm deposit and a matching bank asset /
firm liability.  Interest and principal flows would subsequently redistribute
financial stocks.

That is worth doing, especially for a later Minsky-style model, but it is a
large enough modelling change that it should not be mixed into the present
diagnostic repair.

`mmm_0_4` therefore contains investment **demand** but not explicit bank
finance.

---

## 9. Firms now plan a small capacity margin

The private sector should not wait until demand exactly equals maximum current
output before hiring.

The redesign introduces

```text
u_F_target = 0.95
```

and defines

```text
Q_required = Q_demand / u_F_target.
```

Thus firms normally plan to operate at about 95 percent of the output capacity
associated with their current labour force.

The normalized employment pressure is

```text
excess = (Q_required - Q_F) / (A_F * N_res).
```

Private employment then evolves according to

```text
d(lambda_F)/dt
    = kappa_L * lambda_F * (1 - lambda_F) * excess.
```

The logistic factor keeps `lambda_F` inside `(0,1)` when it starts there.

Economically:

- if demand is high relative to the firm's desired capacity margin,
  `lambda_F` rises;
- if demand is weak, `lambda_F` falls;
- the JG automatically receives the residual workers.

---

## 10. The useful unemployment diagnostics are now rates as well as head counts

With a growing population, an absolute JG head count can rise even when the
labour-market situation is improving.

The revised model therefore reports

```text
lambda_G       = L_G / N
lambda_JG      = L_JG / N
lambda_regular = (L_F + L_G) / N
u3_rate        = U3 / N
```

These are more informative over a fifty-year run than `L_JG` alone.

For example, a JG pool rising from 5 workers to 7 workers is not necessarily a
deterioration if the labour force has grown from 100 to 170.

---

## 11. Reference behaviour of the redesigned calibration

An independent numerical check of the redesigned equations gives roughly the
following long-run pattern:

| year | `lambda_F` | `L_JG/N` |
|---:|---:|---:|
| 0  | 0.950 | 0.044 |
| 5  | 0.932 | 0.060 |
| 10 | 0.934 | 0.058 |
| 20 | 0.940 | 0.053 |
| 30 | 0.943 | 0.050 |
| 40 | 0.942 | 0.051 |
| 50 | 0.939 | 0.054 |

The point of this table is not calibration accuracy.  It is a structural
sanity check.

Instead of the JG taking over the labour force, the reference model leaves it
as a buffer of roughly five to six percent while:

- regular public employment remains near 12 percent of population;
- firms employ the large majority of the remaining labour force;
- `lambda_F` remains high rather than monotonically collapsing.

A model with no stochastic or cyclical shocks should not be expected to
generate realistic business-cycle oscillations by itself.

---

## 12. Interpretation of `G_N`

`G_N` remains the **signed consolidated government net financial position**.

The Godley transactions preserve

```text
d(F_D + W_D + G_N)/dt = 0.
```

Hence, with the initial condition

```text
F_D + W_D + G_N = 0,
```

we have

```text
-G_N = F_D + W_D.
```

When the government runs cumulative net deficits and the private sector
accumulates net financial assets, `G_N` becomes more negative.

That is expected in this bookkeeping convention.

It is not a Treasury checking account and should not be interpreted as the
government "running out of money".

The sign can nevertheless move in either direction from one period to another:
tax receipts can exceed spending for a time.  What matters is the accounting
identity, not that `G_N` must mechanically become more negative every year.

---

## 13. No government bonds are modelled here

The present model is a consolidated floating-currency model with no explicit
government securities.

That is a reasonable simplification.

However, government bonds should not be identified uniquely with a
fixed-exchange-rate regime.  Floating-currency governments can and do issue
interest-bearing securities.

In an MMT interpretation, such securities need not be treated as an
operational financing requirement for a currency issuer.  They can instead be
modelled as an interest-bearing alternative form of government liability.

A later bond extension could split private government-asset holdings into
items such as

```text
B_H   household government securities
B_F   firm government securities
B_B   bank government securities
```

and add government interest payments to the holders.

The consolidated government's net position would still be the counterpart to
private net financial assets; only the composition of those assets would have
changed.

---

## 14. Why we do not simply rename `G_N` to `G_D`

`G_N` is intentionally a signed net position.

Calling it `G_D` would invite interpretation as a positive government deposit
at a bank, which is not the accounting convention being used here.

If bonds are introduced later, the clean design is to add explicit security
stocks rather than relabel the existing consolidated net position.

---

## 15. What should be added next

The next economically important extension is an explicit private
capital-and-credit block.

A natural `mmm_0_5` would add:

1. a real capital stock `K`;
2. gross investment depending on utilization and expected profitability;
3. depreciation;
4. firm bank debt;
5. bank-created deposits;
6. a loan interest rate;
7. principal repayment;
8. bank income / equity and possibly dividends;
9. an investment-finance constraint that becomes tighter as debt service rises.

That would permit a genuinely Minsky-like mechanism:

```text
strong demand
 -> investment
 -> bank credit
 -> higher capacity and employment
 -> rising leverage
 -> interest burden
 -> slower investment / deleveraging
```

The JG would then buffer labour released during private-sector contractions.

For `mmm_0_4`, however, the more important task is to establish the correct
**labour-buffer architecture** before introducing endogenous financial
instability.

---

## 16. Recommended diagnostics

For every run, plot at least:

```text
lambda_F
lambda_G
lambda_JG
u3_rate
L_F
L_G
L_JG
Q_F
Q_G
Q_JG
P
pi_rate
F_D
W_D
G_N
```

and check the following identities / inequalities:

```text
L_F + L_G + L_JG = N          (JG enabled)
U_open ~= 0                    (JG enabled)
0 <= lambda_F <= 1
F_D + W_D + G_N = constant
-G_N = F_D + W_D               (given zero initial total)
P > 0
```

The most important JG diagnostic is `lambda_JG = L_JG/N`, not the absolute
worker count alone.

---

## 17. Scope of the redesign

This remains a small pedagogical macro model.

It now contains a more defensible distinction between:

- ordinary public employment,
- private employment,
- JG buffer employment,
- household consumption,
- government procurement,
- private gross investment demand,
- and consolidated fiscal balances.

It is **not yet** a complete stock-flow-consistent banking model, a calibrated
business-cycle model, or an empirical model of any particular economy.

The purpose of `mmm_0_4` is narrower: to make the JG behave like a residual
employment buffer rather than the default destination of an economy whose
regular-demand components were accidentally designed to shrink in relative
importance.
