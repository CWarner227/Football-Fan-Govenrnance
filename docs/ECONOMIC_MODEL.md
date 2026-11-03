# Synthetic economic model

Ordinary fee and contribution receipts are aggregated in each reconciled economic
row by default. Set `economics.record_individual_transactions: true` to retain
each ordinary person's receipt as an additional event. Hostile fee payments,
attack actions, identity decisions, reviews, lifecycle changes, and investor
decisions remain recorded in either mode. This changes logging only, not amounts,
random draws, eligibility, or financial outcomes.

All quantities and relationships are research assumptions for a synthetic club.
They are not calibrated forecasts or observed probabilities. Economic transitions
are independent of voting strategies; scenario policies explicitly connect the
financial state to turnout and investor voting offers.

## Accounting and units

A financial month is 30 simulated days. Calendar scheduling supplies elapsed days;
monthly flows scale by `elapsed_days / 30`, including intramonth updates. At day
zero these flows are zero. Configuration monetary values use a single synthetic
currency. `debt_principal` is opening debt, `debt_repayment` a monthly principal
payment, and `debt_interest` a monthly rate on opening debt.

```text
profit = operating revenue + membership fees
         - operating expenses - wages - administration - interest
financing cash flow = supporter contributions + investor capital - principal repaid
closing cash = opening cash + profit + financing cash flow - transfer spending
closing debt = opening debt - principal repaid
```

Supporter contributions and outside capital are financing, not operating revenue.
Transfers are investing cash outflows. Starting cash and historical population
contributions are opening stocks, never new recurring revenue. Pending accepted
attack contributions, prepaid fees, and defensive administration expenses enter
the ledger exactly once. Cash may become negative; `insolvent` then becomes true.
The simulator does not assume emergency borrowing or liquidation.

Financial runway is positive remaining cash divided by the current monthly cash
burn before supporter/investor financing. Burn includes transfers and principal
payments. Runway is null when the current period does not burn cash; null does
not mean zero months. Negative cash gives zero runway when a burn is present.

## Supporter income, wealth and affordability

Monthly income has its own configurable numeric marginal: constant, uniform,
normal, lognormal, or beta. Negative draws are clipped to zero. Wealth continues
to use the original population generator's separate distribution. Optional
`income_wealth_correlation` uses normal scores of wealth ranks and a Gaussian
latent variable to reorder sampled income while retaining the income marginal.
This is a latent copula parameter, not a guarantee of a particular Pearson
correlation between differently shaped income and wealth distributions.

Initial spendable assets are `max(wealth - historical contribution, 0)`.
Disposable income is gross monthly income times `disposable_income_fraction`
and the current downturn multiplier. It enters spendable assets each period;
the remaining income is consumed outside the simulation. Gross modeled wealth
equals remaining spendable assets plus committed contributions. Paying a fee
reduces spendable assets; making a contribution converts cash into committed
stake without creating wealth.

A fee must be affordable in full or membership expires. A willing honest person
contributes `contribution_willingness` times disposable income remaining after
the current fee, bounded by actual spendable assets. Duplicate honest membership
claims share one person's income, fee, and contribution. Hostile accounts pay
separately from their controller's finite financial budget; they never fund fees
or extra contributions by spending a copied synthetic wealth attribute.
Prepaid same-date fees are not charged again.

Renewal willingness is sampled only when a term becomes due, using
`renewal_interval_months` (default 12). Fees remain monthly. Economic stress can
reduce renewal probability; inability to pay can expire membership earlier.
Credential compromise alone does not transfer the legitimate person's finances.
Optional growth creates exogenous new honest people sampled from existing honest
profiles, with fresh identities, zero inherited contribution, and new memberships.
This is a simple recruitment assumption rather than a demographic model.

## Investors and governance

Each investor has an ID, capital, arrival month, ownership share, willingness,
optional requested voting rights, and a minimum expected voting-power share.
Ownership shares sum to at most one. An investor makes a single decision at the
first scheduled date on or after arrival. A failed willingness draw or unmet
voting expectation declines the offer rather than retrying indefinitely.

Capital does not automatically create voting rights. A voting-rights request
requires the explicit scenario `investor_voting_offer` policy; accepted rights
are recorded separately from ownership. The scenario adapter supplies offered
power and creates any actual governance membership under that policy. The
economic engine never creates a voting credential for an investor. Policy and
downturn factors can reduce investment willingness. Ownership concentration is
the largest accepted investor ownership share.

## Sporting outcomes

The sporting index combines squad quality, management quality, expected injury
loss, recruitment shock factor, and normally distributed performance noise,
bounded below by zero. Revenue responds through
`max(0, 1 + sporting_revenue_sensitivity * (sporting_index - 1))`.
Transfer expenditure produces a separate cumulative squad-value stock scaled by
recruitment effectiveness and recruitment shocks. Spending therefore can buy
less sporting value without reducing its cash cost. High sporting performance
does not guarantee an operating surplus when expenses exceed receipts.

## Shocks and recovery

Each shock specifies start month, positive duration, severity in [0,1], optional
recovery months, and an optional unique ID. Its multiplier is one minus severity
during the shock, then recovers linearly toward one. Every transition derives
effects from unshocked configuration bases. Independent overlapping shocks
multiply once per affected variable; they do not repeatedly reduce a previous
month's already-shocked base. Duplicate name/start entries require distinct IDs.

| Shock | Affected variables |
| --- | --- |
| Revenue loss | Matchday and commercial receipts |
| Poor recruitment | Recruitment value and sporting index |
| Stadium closure | Matchday receipts and renewal probability; operating expenses also fall only when `keep_operating_costs=false` |
| Economic downturn | Disposable income, renewal, commercial receipts, investor willingness |

Wages, transfer payments, debt principal and interest do not disappear during a
stadium closure. The configurable matchday fraction separates receipts so a
closure and commercial downturn do not duplicate the same revenue loss.

## Reproducibility and interpretation

Per-person, per-investor, renewal, growth and sporting draws use stable named
child streams derived from each step seed. Adding hostile accounts does not
shift unrelated honest renewal or sporting draws. Scenario comparison preserves
the original population and shared random inputs where applicable.

Exports include trial summaries, elections, the financial time series, events,
configuration snapshots, seeds and metadata. Aggregation preserves scenario,
grid point, voting model and variant. Binary trial outcomes receive Wilson 95%
intervals; continuous outcomes receive 2.5%, median and 97.5% trial quantiles.
These quantify variation in synthetic experiments, not empirical real-world
capture probabilities or confidence in causal forecasts.
