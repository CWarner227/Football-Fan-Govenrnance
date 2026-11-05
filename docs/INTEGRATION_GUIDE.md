# Extending the research dashboard

The extension boundary has three layers: Python scientific components, API
metadata/services, and optional browser features. Existing scenario YAML and
registered Python factories remain the source of scientific configuration.

## Register a scientific model

1. Implement the existing engine protocol in Python. Keep scientific formulas and
   model validation alongside that component.
2. Register the factory in the appropriate core or scenario registry. Core model
   categories include voting, eligibility, participation and preference; the
   scenario registry supplies attacks and defenses.
3. Declare constructor annotations and defaults. Dataclasses are supported, as
   are factories exposing a Pydantic `parameter_model`. A parameter model is
   preferable for constrained values, enums and nested structures.
4. Add focused scientific tests plus an API discovery/validation test.
5. Check `/api/v1/models` and the generated controls in the builder. Fields with
   complex unsupported presentation retain a JSON editing route.

Model discovery returns:

```json
{
  "models": [{
    "id": "model_identifier",
    "name": "Model Identifier",
    "category": "voting",
    "description": "Factory documentation",
    "schema": {"type": "object", "properties": {}},
    "defaults": {}
  }]
}
```

The example describes the metadata envelope; it is not a simulation result.
Factories are trusted installed Python code. Registering a model does not permit
browser clients to import arbitrary modules, execute commands or choose output
paths. Untyped `**kwargs` alone cannot describe a useful dynamic form: expose a
parameter model when the constructor cannot declare its accepted fields.

Hybrid voting has a metadata adapter for the existing nested routing factory.
Any new polymorphic constructor should similarly publish a declarative schema,
while delegating numerical behavior to the engine. Do not implement model rules
again in TypeScript.

The dashboard uses the built-in distribution sampler. Core configuration can
describe injected custom samplers, but the dashboard rejects an unavailable
distribution before queueing. Installing a new distribution requires an explicit
server-side sampling boundary and validation integration.

## Replace storage

Implement `storage.interfaces.Repository` with `save`, `get`, `list`, `delete`
and `directory` semantics. `get` raises `KeyError` for absent records; malformed
collections/IDs raise `ValueError`. Records are JSON dictionaries. The filesystem
implementation isolates metadata in `record.json` and exposes an ID-derived
directory for worker artifacts.

A database migration must also provide artifact storage or adapt the worker and
results service's directory dependency. Keep status updates transactional and
retain immutable submitted configuration snapshots. Multiple API processes need
shared queue leasing and cancellation ownership; replacing JSON metadata alone
does not create a distributed job manager.

## Optional external integrations

`IntegrationModule` describes an integration's `id`, `name`, `enabled` flag and
capability names. `/api/v1/capabilities` publishes these descriptors. The current
blockchain descriptor is planned, disabled, and advertises no capabilities.
There are no wallets, on-chain transactions or deployment buttons.

Future blockchain work should introduce an installed backend service and a
separate browser page/panel through navigation registration. Suggested sequence:

1. Define read-only chain/network adapters and explicit capability schemas.
2. Add membership credential and auditability mappings with clear synthetic
   versus on-chain provenance.
3. Define wallet/transaction authorization and secret handling outside scientific
   simulation configuration.
4. Add independently tested proposal, voting and treasury adapters.
5. Add transaction cost, security and on-chain/off-chain comparison views using
   explicit units, chain identifiers and finality assumptions.

An integration should report unavailable or failed capabilities accurately and
keep external side effects behind an explicit authorization boundary. Local
simulation execution must continue to work when no external module is installed.

Before public or shared deployment, add authentication, authorization, deployment
origin controls, operational monitoring and durable shared scheduling. The
current loopback-only application assumes trusted local files and installed code.
