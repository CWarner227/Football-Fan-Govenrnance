# Codex Prompt — Phase 3.5: Modular Research Dashboard & Simulation Control Center

## Project Context

We are developing a research platform investigating blockchain-supported fan ownership, governance, and funding in professional football clubs.

The project examines whether supporter governance systems can increase democratic participation, improve financial sustainability, and resist hostile takeovers or concentrated control.

We have completed three development phases:

**Phase 1 — Simulation Foundation**
- Modular Python simulation architecture.
- Synthetic supporter generation.
- Membership eligibility.
- Voting strategies.
- Election execution.
- Experiment orchestration.

**Phase 2 — Advanced Governance Simulation**
- Detailed supporter characteristics.
- Six interchangeable voting models.
- Configurable population distributions.
- Participation and preference models.
- Controlled Monte Carlo experiments.
- Voting concentration and representation metrics.

**Phase 3 — Adversarial & Economic Simulation**
- Seven adversarial strategies.
- Governance defense mechanisms.
- Multi-period membership simulations.
- Identity verification modeling.
- Club economic models.
- Membership and investor funding.
- Economic shocks.
- Combined governance and financial experiments.
- Scenario libraries and research metrics.

We now need a frontend application that makes this simulation framework easier to operate, configure, visualize, and extend.

**Your task is to build a functional, modular research dashboard that connects directly to the existing simulation engine.**

This is an internal research application, not a public fan-facing platform.

The frontend must remain independent of blockchain implementation while supporting future blockchain integrations.

---

# 1. Primary Objectives

Build a local web application that allows researchers to:

1. View all available simulation scenarios.
2. Configure simulation parameters through an intuitive interface.
3. Select voting models, attack strategies, defensive policies, and economic conditions.
4. Run individual simulations and batch Monte Carlo experiments.
5. Monitor simulation execution and progress.
6. View detailed simulation results.
7. Compare multiple scenarios side by side.
8. Visualize governance, adversarial, and financial metrics.
9. Save, load, duplicate, and modify experiment configurations.
10. Export results and visualizations.
11. Review historical simulation runs.
12. Add future simulation modules and blockchain components without rewriting the application.

Prioritize usability, correctness, modularity, and integration with the existing backend.

Do not build a static demonstration using fabricated results.

Every displayed simulation result must originate from an actual execution of the Python simulation engine or a clearly identified previously saved result.

# 2. Repository Inspection

Before implementing anything:

- Inspect the existing repository.
- Read the README and architecture documentation.
- Identify the Python package structure.
- Inspect the CLI and experiment runner.
- Identify scenario configuration formats.
- Identify available voting strategies, attacks, defenses, and economic models.
- Inspect result schemas and export formats.
- Determine how simulation runs are currently executed.
- Determine whether the repository already contains a backend API or frontend.
- Run the existing tests and record their status.

Do not assume that the code exactly matches earlier development prompts.

Reuse existing functionality and interfaces.

Do not rewrite the simulation engine.

Prepare a short implementation plan identifying how the web application will communicate with the simulation framework.

# 3. Recommended Technology Stack

Use the following unless existing project conventions justify alternatives.

## Frontend

- React.
- TypeScript.
- Vite.
- Tailwind CSS.
- React Router.
- TanStack Query for API state.
- React Hook Form for configuration forms.
- Zod for frontend validation.
- Recharts or Plotly for interactive visualizations.
- Lucide React for icons.

## Backend API

- Python.
- FastAPI.
- Pydantic.
- Existing simulation package.
- Existing experiment runner.

## Data Storage

Initially use local filesystem storage for:

- Experiment configurations.
- Run metadata.
- Simulation results.
- Exported datasets.

Use a structured storage abstraction so PostgreSQL can be introduced later.

Do not require PostgreSQL, Redis, Docker, cloud services, or blockchain infrastructure for the initial application.

## Development

- Pytest for backend tests.
- Vitest and React Testing Library for frontend tests.
- Playwright for end-to-end testing.
- Ruff for Python linting.
- ESLint for TypeScript linting.

# 4. High-Level Architecture

Use this architecture:

```text
Research Dashboard
        |
        v
React + TypeScript Frontend
        |
        v
Typed API Client
        |
        v
FastAPI Research API
        |
        +---- Simulation Service
        |           |
        |           v
        |    Existing Python Engine
        |
        +---- Experiment Service
        |           |
        |           v
        |    Existing Monte Carlo Runner
        |
        +---- Configuration Service
        |
        +---- Results Service
        |
        +---- Run Management Service
        |
        +---- Future Blockchain Service
        |
        v
Local Storage / Future Database
```

The frontend must never directly implement voting calculations, adversarial logic, or economic simulation formulas.

All scientific calculations must remain in the Python simulation engine.

The API should expose the existing functionality through stable, typed interfaces.

# 5. Proposed Repository Structure

Adapt the existing repository rather than restructuring it unnecessarily.

Suggested additions:

```text
fan-governance-simulator/
│
├── src/
│   └── fan_governance/
│       ├── api/
│       │   ├── main.py
│       │   ├── routes/
│       │   │   ├── scenarios.py
│       │   │   ├── simulations.py
│       │   │   ├── experiments.py
│       │   │   ├── results.py
│       │   │   ├── configurations.py
│       │   │   └── capabilities.py
│       │   ├── schemas/
│       │   └── services/
│       │
│       ├── storage/
│       │   ├── interfaces.py
│       │   └── filesystem.py
│       │
│       └── integrations/
│           └── interfaces.py
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── charts/
│   │   │   ├── forms/
│   │   │   ├── simulations/
│   │   │   └── results/
│   │   ├── features/
│   │   │   ├── dashboard/
│   │   │   ├── scenarios/
│   │   │   ├── simulator/
│   │   │   ├── experiments/
│   │   │   ├── results/
│   │   │   ├── history/
│   │   │   └── integrations/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
│   └── tests/
│
├── data/
│   └── dashboard/
│       ├── configurations/
│       ├── runs/
│       └── exports/
│
└── docs/
    ├── DASHBOARD_ARCHITECTURE.md
    ├── DASHBOARD_USAGE.md
    └── INTEGRATION_GUIDE.md
```

# 6. Dashboard Layout and Navigation

Create a clean, modern research dashboard.

Use a left sidebar for navigation and a main content area.

Primary pages:

1. Overview
2. Simulation Builder
3. Scenarios
4. Experiments
5. Results Explorer
6. Run History
7. Integrations
8. Settings

Use a professional analytical interface.

Avoid unnecessary animations, decorative graphics, or excessive visual complexity.

Support desktop screens primarily, but ensure the interface remains usable on smaller screens.

Use consistent spacing, typography, colors, and chart styling.

Provide light and dark themes if practical.

# 7. Overview Dashboard

The overview page should summarize available simulation activity.

Display:

- Total completed simulations.
- Total experiments.
- Recent simulation runs.
- Available scenarios.
- Available voting models.
- Available attack strategies.
- Available defenses.
- Last simulation execution time.

When historical data exists, display useful summary charts.

Examples:

- Capture probability by voting model.
- Average turnout by scenario.
- Voting concentration across experiments.
- Financial runway under economic shocks.

Do not combine incompatible experiments into a misleading aggregate.

Only aggregate results when configurations and metrics are comparable.

Provide quick actions for:

- New Simulation.
- Run Scenario.
- Compare Results.
- View History.

# 8. Simulation Builder

This is the most important page.

Create a form-driven simulation configuration interface.

Organize parameters into expandable sections or tabs.

## A. General Settings

Allow configuration of:

- Simulation name.
- Description.
- Random seed.
- Number of trials.
- Simulation duration.
- Time step.
- Population profile.
- Population size.

## B. Supporter Population

Allow researchers to configure:

- Wealth distribution.
- Income distribution.
- Contribution distribution.
- Loyalty distribution.
- Knowledge distribution.
- Forecast accuracy distribution.
- Participation distribution.
- Membership age distribution.
- Adversarial supporter percentage.

Expose relevant distribution parameters.

Support existing correlation configuration if available.

Provide sensible defaults from the backend.

## C. Governance Settings

Allow selection of:

- Equal voting.
- Proportional stake voting.
- Capped stake voting.
- Diminishing returns voting.
- Hybrid voting.
- Expertise-weighted voting.

Show voting-model-specific settings only when applicable.

Examples:

- Maximum vote weight.
- Reference contribution.
- Expertise multiplier.
- Proposal category.
- Quorum threshold.
- Approval threshold.
- Membership waiting period.

## D. Adversarial Settings

Allow selection of the seven attack strategies:

- Wealthy takeover.
- Coordinated infiltration.
- Sybil attack.
- Low-turnout capture.
- Vote buying/coercion.
- Account compromise.
- Long-term infiltration.

Expose attack-specific parameters.

Allow multiple compatible attacks when supported by the engine.

## E. Defensive Settings

Provide toggles for:

- Identity verification.
- Membership waiting periods.
- Voting caps.
- Quorum requirements.
- Participation incentives.
- Suspicious activity detection.
- Credential recovery policies.

Display configuration fields for enabled defenses.

## F. Economic Settings

Allow configuration of:

- Membership fees.
- Renewal rates.
- Supporter income distributions.
- Investor contributions.
- Starting club cash.
- Operating revenue.
- Operating expenses.
- Wage expenses.
- Transfer spending.
- Debt obligations.
- Financial reserves.

## G. Economic Shocks

Support:

- Revenue loss.
- Poor recruitment.
- Stadium closure.
- Economic downturn.

Expose:

- Shock severity.
- Start date.
- Duration.
- Recovery assumptions.

## H. Advanced Configuration

Provide an advanced YAML or JSON editor.

Researchers should be able to:

- View the generated configuration.
- Edit supported configuration fields.
- Validate configuration.
- Import configuration files.
- Export configuration files.

Use the backend as the authoritative validator.

Do not maintain a separate hardcoded copy of all simulation rules in the frontend.

# 9. Dynamic Configuration Forms

This is a critical modularity requirement.

Do not hardcode every simulation strategy's form into one large React component.

Implement a schema-driven configuration system.

The backend should expose metadata describing available models and their configurable parameters.

Example:

```json
{
  "id": "capped_voting",
  "name": "Capped Stake Voting",
  "category": "voting",
  "parameters": {
    "max_weight": {
      "type": "number",
      "default": 5,
      "minimum": 1
    },
    "reference_contribution": {
      "type": "number",
      "default": 100,
      "minimum_exclusive": 0
    }
  }
}
```

The frontend should use this metadata to generate appropriate controls.

Supported control types should include:

- Number inputs.
- Sliders.
- Checkboxes.
- Select menus.
- Date inputs.
- Text inputs.
- Nested configuration sections.

Use specialized custom components only where generic schema-driven forms are insufficient.

When a new voting model or attack strategy is registered in the backend, the frontend should be able to display its configuration without requiring major frontend changes.

# 10. Scenario Library

Create a page showing available scenarios.

Display scenarios as searchable cards or a table.

Each scenario should show:

- Name.
- Description.
- Category.
- Default population size.
- Voting model.
- Attack strategy.
- Defensive policies.
- Simulation duration.

Actions:

- View configuration.
- Load into Simulation Builder.
- Run immediately.
- Duplicate configuration.
- Compare with another scenario.

Use existing Phase 3 YAML scenario files as the source of truth.

Do not duplicate scenario definitions in frontend source code.

# 11. Simulation Execution

Implement real execution of the existing Python simulation engine.

Required workflow:

1. User configures a simulation.
2. Frontend validates basic fields.
3. Configuration is sent to FastAPI.
4. Backend performs authoritative validation.
5. Backend creates a run identifier.
6. Simulation executes.
7. Frontend displays execution status.
8. Results are saved.
9. Results become available in Results Explorer.

Support statuses:

- Queued.
- Running.
- Completed.
- Failed.
- Cancelled.

Use a background worker or managed subprocess for long-running experiments.

Do not execute CPU-intensive Monte Carlo simulations directly inside the FastAPI request handler.

For the initial local application, a lightweight process-based job manager is acceptable.

Avoid introducing Redis or Celery unless genuinely necessary.

Ensure the implementation handles:

- Multiple submitted runs.
- Controlled concurrency.
- Failed simulations.
- Server restarts.
- Cancellation.
- Resource limits.
- Run timeouts.

Cancellation must actually terminate the relevant computation rather than merely change the displayed status.

If exact progress cannot be measured, display an indeterminate running state instead of fabricated percentages.

# 12. Simulation Progress

Create a run-monitoring interface.

Display:

- Run ID.
- Simulation name.
- Current status.
- Start time.
- Elapsed time.
- Completed trials, when available.
- Total trials.
- Progress percentage, when measurable.
- Errors and warnings.
- Cancel button.

Use polling initially.

WebSockets or server-sent events can be added later if useful.

Avoid unnecessary complexity.

# 13. Results Explorer

Build a results page capable of displaying individual runs and experiments.

Organize results into tabs:

### Summary

Display:

- Simulation configuration.
- Trial count.
- Voting model.
- Population size.
- Main outcome.
- Key governance metrics.
- Key economic metrics.

### Governance

Visualize:

- Voting power distribution.
- Gini coefficient.
- Effective number of voters.
- Turnout.
- Weighted versus unweighted outcomes.
- Wealth percentile versus voting influence.

### Adversarial

Visualize:

- Capture probability.
- Attacker voting-power share.
- Attack success rate.
- Attack costs.
- Defense effectiveness.
- False positive and false negative rates.

### Economics

Visualize:

- Club cash balance over time.
- Revenue and expenses.
- Membership revenue.
- Investor contributions.
- Financial runway.
- Economic shock effects.

### Timeline

For multi-period simulations, display:

- Membership changes.
- Elections.
- Attack events.
- Defensive interventions.
- Economic shocks.
- Financial state changes.

### Raw Data

Provide searchable, sortable tables of simulation outputs.

Support CSV and JSON exports.

Display only metrics actually produced by the backend.

Use clear empty states for unavailable metrics.

# 14. Interactive Charts

Use Plotly or Recharts for interactive charts.

Required chart types:

- Line charts.
- Bar charts.
- Histograms.
- Scatter plots.
- Box plots.
- Heatmaps, where supported.

Support:

- Hover tooltips.
- Axis labels.
- Legends.
- Filtering.
- Series selection.
- Responsive sizing.
- Downloadable chart images, where practical.

Do not generate chart data independently of simulation results.

Preserve units and distinguish percentages from proportions.

Show uncertainty intervals or quantiles where available.

# 15. Experiment Comparison

Create a dedicated comparison interface.

Researchers should be able to select two or more completed runs.

Display:

- Side-by-side configuration differences.
- Key metrics.
- Comparative charts.
- Outcome differences.
- Financial differences.
- Defensive effectiveness.

Support comparisons such as:

- Equal voting versus proportional stake voting.
- Capped voting versus diminishing returns.
- Identity verification enabled versus disabled.
- Six-month versus twelve-month waiting periods.
- Low versus high supporter turnout.
- Different investor contribution levels.
- Economic shock versus baseline.

Warn users when comparing runs with incompatible populations, trial counts, assumptions, or outcome definitions.

Do not imply causal conclusions from uncontrolled comparisons.

Where matched-trial data is available, use paired differences.

# 16. Run History and Persistence

Persist simulation runs and configurations.

Store:

- Run ID.
- Experiment name.
- Creation time.
- Completion time.
- Status.
- Configuration snapshot.
- Random seed.
- Result paths.
- Error information.
- Engine version or Git commit, when available.

Allow users to:

- View previous runs.
- Reopen results.
- Duplicate configurations.
- Rerun experiments.
- Export results.
- Delete saved runs.

Use an abstraction such as:

```python
class RunRepository(Protocol):
    def save(self, run): ...
    def get(self, run_id): ...
    def list(self, filters=None): ...
    def delete(self, run_id): ...
```

Implement filesystem persistence initially.

Keep storage interchangeable for future PostgreSQL integration.

# 17. Backend API

Implement a versioned API.

Suggested endpoints:

```text
GET    /api/v1/health

GET    /api/v1/capabilities
GET    /api/v1/models
GET    /api/v1/scenarios
GET    /api/v1/scenarios/{id}

POST   /api/v1/configurations/validate
POST   /api/v1/configurations/save
GET    /api/v1/configurations
GET    /api/v1/configurations/{id}

POST   /api/v1/runs
GET    /api/v1/runs
GET    /api/v1/runs/{id}
POST   /api/v1/runs/{id}/cancel

GET    /api/v1/runs/{id}/results
GET    /api/v1/runs/{id}/events
GET    /api/v1/runs/{id}/export

POST   /api/v1/comparisons
```

Adjust endpoints to existing conventions.

Use Pydantic response models.

Expose OpenAPI documentation.

Generate or maintain TypeScript API types from the backend schema where practical.

Use consistent error responses.

Validate all incoming configuration data.

Do not expose arbitrary filesystem paths or shell commands through the API.

# 18. Future Blockchain Integration Architecture

The dashboard must support future blockchain functionality without requiring a redesign.

Do not implement smart contracts or wallet integration now.

Instead, establish clean integration boundaries.

Future modules may include:

- Wallet connection.
- Membership credential issuance.
- Smart-contract deployment.
- On-chain proposal creation.
- Blockchain voting.
- Transaction monitoring.
- Governance treasury.
- On-chain versus off-chain comparisons.
- Smart-contract security testing.
- Blockchain transaction costs.
- Governance auditability.

Create a generic integration interface.

For example:

```typescript
interface IntegrationModule {
  id: string;
  name: string;
  enabled: boolean;
  capabilities: string[];
}
```

The backend should expose integration capabilities.

The frontend should register optional features through a modular navigation and feature system.

When blockchain functionality is eventually added, it should appear as additional pages or panels rather than requiring modifications to the simulation builder's core architecture.

Do not create fake wallet connections or nonfunctional blockchain buttons.

An Integrations page may show the blockchain integration as "Not installed" or "Planned."

# 19. User Experience Requirements

The dashboard should be straightforward for a researcher who is not familiar with the underlying Python code.

Important requirements:

- Clear parameter descriptions.
- Tooltips explaining complex variables.
- Default configurations.
- Form validation.
- Reset-to-default controls.
- Save configuration.
- Load configuration.
- Visible run status.
- Clear error messages.
- Responsive charts.
- Export functionality.
- Loading states.
- Empty states.
- Accessible form labels.

Explain research-specific concepts such as:

- Voting concentration.
- Effective number of voters.
- Capture probability.
- Quorum.
- Waiting periods.
- Sybil attacks.
- Monte Carlo trials.
- Financial runway.

Do not overwhelm the default interface with every advanced parameter.

Use expandable advanced sections.

# 20. Testing Requirements

Implement tests for:

## Backend

- API health.
- Model discovery.
- Scenario discovery.
- Configuration validation.
- Simulation execution.
- Background run management.
- Cancellation.
- Failed runs.
- Results retrieval.
- Run persistence.
- Export functionality.
- Invalid configuration handling.
- Path traversal prevention.

## Frontend

- Navigation.
- Dynamic configuration forms.
- Conditional parameter fields.
- Configuration validation.
- Scenario loading.
- Simulation submission.
- Progress display.
- Results rendering.
- Experiment comparison.
- Export controls.
- Error states.

## End-to-End

Use Playwright to test:

1. Open dashboard.
2. Select an existing scenario.
3. Modify parameters.
4. Validate configuration.
5. Run a small simulation.
6. Wait for completion.
7. Open results.
8. View charts.
9. Export results.
10. Reopen the run from history.

Use real small-scale simulations in integration tests where practical.

Mock only external boundaries or computationally expensive cases.

# 21. Local Development Workflow

Provide simple commands for starting the application.

Prefer a workflow similar to:

Backend:

```bash
uvicorn fan_governance.api.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Adjust commands to the actual package structure.

Provide a simple development script or Makefile target to start both services if practical.

Configure the Vite development proxy to communicate with FastAPI.

Avoid unnecessary CORS complexity.

# 22. Performance Requirements

The frontend must remain responsive while simulations run.

Do not transfer entire 100,000-supporter datasets to the browser by default.

Use:

- Paginated tables.
- Server-side filtering where appropriate.
- Aggregated chart data.
- Lazy-loaded result details.
- Efficient API responses.

The backend must avoid loading all historical results into memory.

Large result files should be streamed or processed incrementally where practical.

# 23. Implementation Order

Follow this order:

1. Inspect repository and run existing tests.
2. Document proposed frontend/backend architecture.
3. Create FastAPI service layer.
4. Implement configuration and capability discovery.
5. Implement scenario loading.
6. Implement simulation execution API.
7. Implement background run management.
8. Implement run persistence.
9. Implement results retrieval and export.
10. Initialize React frontend.
11. Build application shell and navigation.
12. Build Overview page.
13. Build Simulation Builder.
14. Build Scenario Library.
15. Implement run monitoring.
16. Build Results Explorer.
17. Build Experiment Comparison.
18. Build Run History.
19. Add integration extension points.
20. Implement tests.
21. Run complete end-to-end validation.
22. Update documentation.

Keep the application functional throughout development.

# 24. Definition of Done

This phase is complete when:

- The frontend starts locally.
- FastAPI connects to the existing Python simulation engine.
- Available simulation models are discovered dynamically.
- Existing scenarios can be loaded.
- Researchers can change simulation parameters.
- Configuration validation works.
- Simulations can be launched from the browser.
- Run status and progress are visible.
- Completed results can be inspected.
- Governance, adversarial, and economic charts work.
- Multiple experiments can be compared.
- Configurations and run history persist.
- Results can be exported.
- The UI remains responsive during long-running experiments.
- Automated tests pass.
- The architecture supports future blockchain modules.

# 25. Final Execution Instructions

Implement the actual application, not just an architecture proposal or static mockup.

Reuse the existing simulation engine and scenario files.

Do not rewrite voting, adversarial, or economic models in JavaScript.

Do not fabricate simulation outputs.

Do not introduce real blockchain functionality yet.

Keep the code modular and well documented.

Prioritize a functional research dashboard over excessive visual polish.

When finished, provide:

1. Summary of implemented functionality.
2. Backend endpoints.
3. Frontend pages and features.
4. Repository changes.
5. Instructions for starting the application.
6. Tests executed and results.
7. End-to-end validation results.
8. Known limitations.
9. Recommended future blockchain integration steps.

**The final application should allow a researcher to configure, execute, inspect, and compare simulations entirely through a web interface without manually editing Python scripts or YAML files.**
