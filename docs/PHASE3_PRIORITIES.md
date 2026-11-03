# Phase 3 priorities

Phase 2 implements synthetic supporter modeling and six voting systems. The older
Phase 1 roadmap used different phase labels; the current Phase 2 request is authoritative.
The following capabilities are recommendations, not implemented features.

1. Define adversary resources, budget constraints, control goals, and attack success.
   Separate changed decisions, minority capture, wealth concentration and financial
   harm. A high Gini coefficient alone is not proof of an exploit or failed governance.
2. Add explicit coalition/scenario state and injected coordinated turnout/preferences.
   Begin with low-turnout capture and budget-limited wealthy influence, each compared
   to a matched no-attack counterfactual using the current snapshots and random streams.
3. Separate synthetic people from accounts/claimed credentials before modeling Sybil
   fraud or long-term infiltration. Current canonical identity uniqueness is an
   assumption; the deduplication policy is not real identity verification.
4. Implement a modular financial ledger for membership revenue, investors, budgets
   and shocks. Specify the temporal meaning of available wealth and historical
   contributions before adding borrowing, returns, resilience or economic feedback.
5. Add coalition-size/budget/waiting-period/turnout sweeps with paired effect sizes,
   uncertainty intervals and sensitivity analysis. Calibrate only where appropriate
   data exist, recording provenance and keeping synthetic assumptions visible.
6. Profile the current snapshot copying/hash costs at 100k and the in-memory result
   accumulation for large sweeps before choosing streaming/vectorized optimizations.
7. Keep blockchain credentials/on-chain auditability and a web frontend behind future
   adapters. Neither should become a dependency of election rules or experimental data.
