# `mmm_0_4`: government price offers, private markup, and a universal Job Guarantee

**Status:** First specification and static-generation prototype (7 October 2026). The
Julia code generator has been executed successfully. The numerical system has
been independently integrated in Python using `scipy.solve_ivp`, but the
Julia/IDA solver and GUI **have not been run here**. This is a modelling
proposal, not a calibrated or empirically validated theory of inflation.

## 1. Economic purpose and interpretation

The currency issuer announces *nominal prices*, rather than specifying a
preferred proportion of public employment. Three kinds of labour are distinguished:
commercial firms (`F`), ordinary government services (`G`), and the job
buffer (`JG`). The JG offers a job to everyone not already employed by firms
or in ordinary public services, if and only if the wage `w_JG` is positive.

The government's nominal anchor does **not** depend on a positive JG wage:
`w_base > 0` defines the public unit of account through government wage
bids and goods procurement bids. When `w_JG=0`, the JG is off but government
continues to set the prices it offers. The JG and non-JG runs thus share the
same basic architecture; unlike an endogenous market-clearing model, the
nominal wage is not determined solely by firm price dynamics.

The government is the *currency issuer* in the MMT institutional narrative,
but the simple model does not derive price-level determination as a theorem;
it **assumes** persistent transmission of its nominal wage/procurement prices
to firm wage bargains. Commercial firms set their own goods price, with
markups and demand pressure. This is a modelling hypothesis to test, and
is distinguishable from the stronger claim that government controls each
private price or the CPI exactly.

## 2. Variables, exogenous price offers and sector employment

The dynamical state is

\[
  x(t) = (P, \lambda_F, F_D, W_D, G_N).
\]

`P` is the firm's nominal goods price (currency per unit of goods).
`lambda_F` is the share of workers **available outside ordinary government
jobs** employed by firms. `F_D` and `W_D` are respectively firm and household
bank deposits. `G_N` is the consolidated government's *signed net financial
position*, not a Treasury deposit. Negative `G_N` is the mirror of government
net liabilities outside government. We abstract from commercial banks'
reserve positions and bank equity; this is only a consolidated first-pass
accounting closure.

Productivity levels and labour force evolve exogenously:

\[
N=N_0e^{\beta t},\qquad A_j=A_{j0}e^{\alpha_jt},\quad
j\in\{F,G,JG\}.
\]

`A_F0`, `A_G0`, `A_JG0` are **physical productivity levels**.
`alpha_F`, `alpha_G`, `alpha_JG` are **productivity growth rates**. These
should not be conflated. In particular, it is not obvious that the JG
should be *more* productive than ordinary private/public employment; the
sample chooses a lower measured `A_JG0` without discounting the social
value of care, environmental services and training.

Government policy prices and wages are

\[
  w_G=w_{JG}+\delta_G w_0,\qquad
  w_F=(1+\delta_F)w_G,\qquad
  P_G=c_G^P\frac{w_0}{A_{F0}},
\]

where `w_0 = w_base > 0`, `delta_G = premium_G > 0`, and
`delta_F = premium_F > 0`. Thus `w_G > w_JG` even at positive JG
wages, firms hire *above* the public-service wage, and the firm's
nominal labour cost is anchored to the government's wage scale. The
chosen formula for `w_F` is an **assumed wage premium**, not a model
of endogenous inter-sector recruitment. Firm/public wages are constant
nominal price offers when policy parameters are constant.

Ordinary government employment derives from a **nominal payroll budget**:

\[
  L_G=\frac{B_G}{w_G}, \qquad
  N_R=N-L_G,\qquad L_F=\lambda_F N_R.
\]

The labour residual, the buffer, and total employment are

\[
  U_3^*=N_R-L_F,\qquad
  L_{JG}=\mathbf 1_{\{w_{JG}>0\}}U_3^*,\qquad
  L_{\mathrm{total}}=L_F+L_G+L_{JG},\qquad
  U_{\mathrm{open}}=N-L_{\mathrm{total}}.
\]

`U3` in the TOML is **not** the statistical agency's published U-3:
with an active JG, JG workers would ordinarily count as employed, so
published unemployment would be zero in this frictionless idealisation.
`U3` is specifically the **non-JG employment shortfall**, a useful
measure of the buffer size. When the JG is switched off,
`U_open=U3`; otherwise `U_open=0`.

The sample policy has `public_payroll=11.0`, not a percentage labour
quota. But budget and wage are policy inputs; this construction still
embodies an exogenous *nominal spending* choice. A richer model could
instead specify a government service-demand function and public
sector hiring dynamics without targeting a share of employment.

The domain constraints are `w_base > 0`, `w_JG >= 0`,
`premium_G > 0`, `premium_F > 0`,
`0 <= public_payroll / w_G < N0` and `0 < lambda_F(0) < 1`.
Population rises with nonnegative `beta`, so admissibility persists.

## 3. Government purchases, output and firm-side goods demand

Physical output services are

\[
 Q_F=A_FL_F,\quad Q_G=A_GL_G,\quad Q_{JG}=A_{JG}L_{JG}.
\]

`Q_G` and `Q_JG` are **nonmarket outputs**; they are not
artificially added to firm receipts. Government buys firm goods at a
separate posted bid `P_G`:

\[
  G_G=w_GL_G=B_G,\qquad G_{JG}=w_{JG}L_{JG},\qquad
  G_{\mathrm{goods}}=B_{\mathrm{goods}},\qquad
  Q_{\mathrm{goods}}=\frac{B_{\mathrm{goods}}}{P_G}.
\]

This assumes firms supply the requested quantity at the procurement bid.
The model does **not** yet include rationing or bid acceptance when
`P_G` differs sharply from `P`; adding a sale-acceptance rule would be
appropriate for later experiments, especially to test the limits of
state procurement pricing power.

Household wages, taxes, consumption and firm tax are

\[
 \begin{aligned}
 W_F&=w_FL_F,\\
 W&=W_F+G_G+G_{JG},\\
 T_H&=r_HW,\\
 C&=c_w(W-T_H)+c_mW_D,\\
 T_F&=r_F(C+G_{\mathrm{goods}}).
 \end{aligned}
\]

All are *nominal rates per year*. `r_F` is deliberately a **turnover
rather than a corporation profit tax**: a genuine profit tax requires
explicit cost, investment and debt financing accounts.
The goods demand seen by firms is

\[
 Q_d=\frac{C}{P}+\frac{G_{\mathrm{goods}}}{P_G}.
\]

A limitation of this prototype is that consumption from deposits remains
linear even if deposits become negative. Positivity of deposits is not
mathematically guaranteed by the accounting identity; sufficiently
extreme parameter choices may require a bank credit/overdraft sector or
nonnegative spending rule. It is therefore a restricted-domain model.

## 4. Price level, inflation and private employment adjustment

Government wage offers provide the nominal scale; private firms
calculate a **unit labour cost** and an adjustable markup. Define

\[
 e=\frac{Q_d-Q_F}{A_F(N-L_G)},\qquad
 P_{\rm target}=(1+m)\frac{w_F}{A_F}\exp(\eta_pe).
\]

Then the private goods price evolves as

\[
 \boxed{\dot P=\tau_P(P_{\rm target}-P)},\qquad
 \pi(t)=\frac{\dot P}{P}
 =\tau_P\left(\frac{P_{\rm target}}P-1\right).
\]

There is **no independent exogenous Phillips-curve inflation equation**.
Inflation comes from private price adjustment towards an anchored
unit-cost markup subject to real demand pressure. A fixed nominal
anchor does not imply a fixed measured CPI: changes in productivity,
markups, relative prices and demand can change `P`.

Firm employment adjusts to sales pressure:

\[
 \boxed{\dot\lambda_F=\kappa_L\lambda_F(1-\lambda_F)e}.
\]

Provided initial `0<lambda_F<1` and `N>L_G`, this logistic form
preserves `0<lambda_F<1` on finite intervals and leaves a
nonnegative JG/unemployment residual, without clipping. It is a
simplified employment response rather than a full Minsky investment,
capital and credit accumulation system.

## 5. Stock-flow transactions and identities

`[godley]` lists seven directed nominal flows. The generator uses
*source* and *destination* entries as negative and positive changes
in the account stocks. `G_N` is the negative counterpart of net
nongovernment deposits, not an ordinary bank account.

| Flow | Source | Destination | Rate |
|:--|:--|:--|:--|
| Firm wages | `F_D` | `W_D` | `W_F` |
| Public wages | `G_N` | `W_D` | `G_G` |
| JG wages | `G_N` | `W_D` | `G_JG` |
| Government goods purchases | `G_N` | `F_D` | `G_goods` |
| Consumption | `W_D` | `F_D` | `C` |
| Household tax | `W_D` | `G_N` | `T_H` |
| Firm tax | `F_D` | `G_N` | `T_F` |

Equations automatically generated from the table are

\[
\begin{aligned}
\dot F_D &= -W_F+G_{\mathrm{goods}}+C-T_F,\\
\dot W_D &= +W_F+G_G+G_{JG}-C-T_H,\\
\dot G_N &= -(G_G+G_{JG}+G_{\mathrm{goods}})+(T_F+T_H).
\end{aligned}
\]

Consequently,

\[
 \boxed{\dot F_D+\dot W_D+\dot G_N=0},
 \qquad
 \frac{d(F_D+W_D)}{dt}=G_{\mathrm{total}}-T_{\mathrm{total}}.
\]

Both identities hold **independently of parameter values** and are
checkable during any simulation. With initial `F_D+W_D+G_N=0`, the
identity remains exactly true algebraically. The stocks do not
track loan origination, interbank reserves, capital assets, depreciation
or retained profits separately. Accordingly this is **transaction-flow
consistent within the specified boundary**, not yet a full
stock-flow-consistent banking system.

Note a key conceptual distinction: the government is not credited
with a conventional positive deposit when it taxes. The `G_N` signed
account records the offsetting fiscal position. Calling it a Treasury
bank account would misrepresent the consolidation used here.

## 6. Test cases, preliminary diagnostics and expected behaviours

Run from the project root:

```bash
python3 generate_julia_odesolver.py mmm_0_4
julia models/mmm_0_4_cmdl.jl
python3 plots4model.py mmm_0_4
```

The generated scripts `models/mmm_0_4_cmdl.jl` and
`models/mmm_0_4_gui.jl` are included. The existing generator
currently hardcodes the Sundials `IDA()` solver even when the TOML
states `method = "Tsit5"`. Julia execution was not possible in the
review environment. The GUI template also does not yet fully wire
shared-memory parameters into the equations; use the CLI first.

Independent Python/SciPy integration of the same five-equation
system over `0 <= t <= 50` with approximately matched initial
conditions yielded:

| `w_JG` | JG switch | Maximum `|U_open|` | Max drift in `F_D+W_D+G_N` |
|:--|:--|:--|:--|
| 0.0 | off | positive, as expected | < 5e-13 |
| 0.6 | on | < 2e-14 | < 1e-12 |
| 2.0 | on | < 2e-14 | < 2e-12 |

These demonstrate correct *numerical closure and accounting*
for three sample wage settings, not economic validity or calibrated
inflation. `w_JG=0` correctly produces nonzero open unemployment;
with positive `w_JG` the JG absorbs all remaining people in the
modelled labour force.

Suggested further diagnostic checks:

- Verify `abs(F_D+W_D+G_N)` stays near zero at every step.
- Verify `L_F + L_G + L_JG == N` with JG on.
- Verify `U_open == U3` when `w_JG=0`.
- Check `0 <= lambda_F <= 1`, `P > 0`, and `N >= L_G`.
- Compare constant versus varying JG wages, markup, price response,
  productivity and tax/consumption parameters.
- Compare the offered *government* goods price `P_G` with the private
  goods price `P` before adding procurement refusal/rationing.

## 7. Outstanding modelling decisions (for the next iteration)

1. **Government staffing policy.** This prototype treats a nominal
   public-service payroll as a fiscal policy parameter. Is that a
   reasonable minimal closure, or should staffing be determined by
   a public-service demand function and vacancies?
2. **Wage competition.** `w_F` is currently a fixed premium above
   `w_G`, giving the cleanest absolute-price anchor. Should the
   firm premium instead be endogenous to vacancies, profitability
   or bargaining power? That would add an ODE for private wages.
3. **Procurement pricing.** Government goods purchases currently
   transact at the posted `P_G` regardless of the private `P`.
   Future variants could ration purchases where the bid is rejected.
4. **Inflation.** What empirical price index should the representative
   firm price proxy: CPI, GDP deflator or a sectoral producer price?
5. **Investment/debt.** Reintroducing `D`, `K`, profits and private
   bank credit from the earlier Minsky models will change demand
   closure, and needs another set of balance-sheet accounts.
6. **JG eligibility.** Universal automatic enrolment assumes every
   residual worker is available, willing, and eligible; introduce
   participation frictions only in a later model.

## 8. Sources and scope

- Pavlina Tcherneva, *Monopoly Money: The State as a Price Setter*
  (2002), especially the concluding discussion of ELR employment
  as a government-fixed-price purchase.
- Sam Levey, *Modeling Monopoly Money: Government as the Source of
  the Price Level and Unemployment* (2021), especially the role of
  an employment buffer and the separation of price-level
  determination from inflation theory.
- Warren Mosler and Phil Armstrong, *A CB Centered Analysis of the
  Price Level, Inflation and the Neutral Rate of Interest* (draft,
  2025), on government spending prices and the fixed-wage employed
  labour buffer.

**This TOML is an original stylized synthesis of selected ideas, not
an implementation or claimed validation of these authors' full models.**
