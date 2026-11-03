# Recommended Phase 2 work

Historical Phase 1 roadmap: phase labels were superseded by the November 3 Phase 2
request. See PHASE3_PRIORITIES.md for current next steps; this document is retained
as the original planning record.

1. Define attack success, costs, resources and counterfactuals before adding attack
   code. Separate proposal capture, representation loss, concentration and funding
   outcomes; concentration alone does not establish capture.
2. Introduce explicit coalition/scenario state through a separate orchestration
   layer and injected behavior models. Reuse populations and baseline preference
   streams for paired attack/control experiments.
3. Add coordinated preferences and turnout, then test low-turnout capture under
   several waiting periods and vote rules. Require a coalition's budget and available
   members to constrain each scenario.
4. Model canonical people separately from claimed identities/accounts before Sybil
   experiments. Do not weaken the current identity deduplication and call that a
   realistic fraud model; define a replaceable verification/identity-resolution policy.
5. Sweep coalition size, contribution distribution, verification assumptions and
   turnout. Report attack/control differences within trial with uncertainty intervals
   and sensitivity analysis. Retain the full configuration and stream/version record.
6. Keep economic budgets and sporting decision quality out of conclusions until their
   corresponding models are implemented and calibrated. Blockchain integration should
   consume/record governance events through an adapter, without owning core rules.
