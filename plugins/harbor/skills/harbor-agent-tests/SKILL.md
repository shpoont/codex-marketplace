---
name: harbor-agent-tests
description: Design, review, analyze, and interpret trustworthy Harbor evaluations for coding agents. Use when translating project requirements into evaluation cases, choosing evidence and verifiers, isolating execution, comparing agents, using Harbor Analyze on recorded trials, or auditing an existing Harbor harness. Do not use for ordinary product tests that do not evaluate an agent.
---

# Harbor Agent Tests

## Purpose

Turn project requirements into reproducible, isolated experiments that provide
honest evidence about an agent's behavior. Treat the project and its acceptance
criteria as the source of truth.

This skill owns evaluation methodology, not Harbor's operational interface.
Harbor commands, schemas, configuration, authentication, task layout, and
result formats can change independently of this skill.

## Establish the current contract

Before creating, changing, or running an evaluation:

- identify the installed Harbor version and available capabilities;
- consult the official documentation and release information relevant to that
  installation;
- confirm version-sensitive mechanics against the installed CLI or package;
- do not reuse remembered commands, fields, defaults, or credential routes;
- report a documentation/runtime mismatch instead of inventing compatibility.

When reviewing an existing harness, inspect its project-owned generators,
cases, fixtures, and recorded results before proposing changes. Preserve
intentional customizations and update canonical sources rather than generated
copies.

Verify the capabilities and access needed by the claim, not only configuration
acceptance; follow [effective capabilities and access](references/experiment-design.md#effective-capabilities-and-access).

## Agree model settings before inference

Before any model-backed run, discuss and agree with the user on the exact model
and reasoning effort for each intended use: evaluated agents, model judges
(including calibration), model-based audits, and Analyze. Recommend suitable
options for each purpose and explain the quality, latency, and usage tradeoffs.
Do not guess settings or inherit them from the current chat, client defaults,
UI suggestions, or unrelated earlier runs.

Reuse explicit choices already agreed for this evaluation without asking again.
If a choice is missing or would change, ask and wait for agreement before
starting the affected model calls. Continue authorized case preparation and
checks that do not use inference.

Verify that the selected agent/provider supports the agreed model and effort.
If reasoning effort is not configurable, explain that and agree on the fixed
behavior or its being inapplicable; do not invent an effort level or silently
use a default. Record the agreed settings separately for each use. Do not
substitute another model or effort without user agreement.

## Evaluation method

Own the investigation from the user's question to a clear disposition. For
ongoing or resumed evaluations, use the
[working record and closeout](references/evaluation-workflow.md) to keep the
current stage, evidence, next action, and stopping condition visible. A small
one-off review can keep this record in its response.

### Frame the claim

State the decision the evaluation should inform and the claim its evidence can
support. Define success, failure, uncertainty, and the evidence limits before
choosing implementation details.

### Design representative cases

- Use realistic inputs with the smallest context needed for the behavior.
- Keep independently diagnosable scenarios separate.
- Include important boundary and failure cases, not only the happy path.
- Do not reveal hidden answers or verifier implementation in the agent prompt.
- Use repeated attempts when making reliability claims.

For a reported failure, preserve the incident's causal conditions using
[incident reproduction](references/experiment-design.md#incident-reproduction)
before expanding a comparison.

### Choose evidence deliberately

- Prefer deterministic checks for observable facts.
- Use model-based judgment only for qualities that cannot be checked honestly
  with deterministic evidence.
- For model-based grading, apply the
  [judge protocol](references/verifier-assurance.md#judge-protocol).
- Make subjective criteria concrete, observable, and tied to the stated claim.
- Ground criteria and downstream gates in the
  [task and grading contract](references/verifier-assurance.md#task-and-grading-contract).
- Preserve separate reward dimensions when averaging them would hide a failure.
- Define any pass threshold before examining results.
- Make mandatory conditions and aggregation explicit; calibrate mixed outcomes
  using [aggregation checks](references/verifier-assurance.md#aggregation-checks).

### Calibrate the evaluator

Prove that the evaluator can accept a known-good outcome and reject at least one
plausible bad outcome. A normal rejection must remain distinguishable from a
broken environment, agent, verifier, or result collector.

Define the evidence the verifier needs and calibrate through the actual
collection and transfer path. Follow the
[evidence contract](references/verifier-assurance.md#evidence-contract).

Before scaling execution, use proportionate
[preflight checks](references/verifier-assurance.md#staged-preflight).

### Execute a fair experiment

Hold cases, context, environment, verifier, attempt policy, and reporting rules
constant when comparing agents or configurations. Change one material variable
at a time unless the experiment explicitly studies a combined intervention.

Record resolved inputs, settings, resource enforcement, and usage bounds using
[execution planning and provenance](references/experiment-design.md#execution-planning-and-provenance).

When measuring injected skills or context, follow the
[controlled comparison](references/experiment-design.md#skills-and-injected-context)
guidance and preserve the exact treatment delivered to each agent.

For multi-step, resumed, or simulated-user evaluations, define state and
completion semantics using [stateful evaluations](references/experiment-design.md#stateful-evaluations).

### Interpret the record

Use the recorded trial and verifier evidence, not process exit status alone.
Separate:

- valid acceptance;
- valid rejection;
- infrastructure or authentication error;
- incomplete or cancelled work;
- descriptive, ungated measurements.

Before interpreting aggregates, build an outcome ledger and state each metric's
denominator. Check trial, step, and criterion errors as well as rewards; follow
[score validity and denominators](references/result-interpretation.md#score-validity-and-denominators).

Do not generalize beyond the observed cases, attempts, environment, and
verifier. Treat historical results as evidence for their recorded conditions,
not proof of current behavior.

Classify changes before reusing historical results; follow
[reruns, regrading, and reuse](references/result-interpretation.md#reruns-regrading-and-reuse).

### Use Analyze as a secondary interpretation layer

Harbor Analyze is an optional agent run over recorded job or trial evidence.
Use it to summarize patterns, explain failures, compare evidence, or identify
questions for follow-up. Its output is model-generated interpretation: it is
not a verifier, does not change earned rewards, and must not replace the raw
trial and verifier record.

Before an analysis run, read the
[Analyze protocol](references/result-interpretation.md#analyze-protocol).

## Isolation contract

Evaluations must not rely on unbounded access to the local machine.

- For local execution, prefer Harbor-managed Docker isolation when available.
  An alternative sandbox is acceptable only when it provides equivalent
  boundaries and is deliberately selected.
- Provide a focused copy or snapshot of required project context. Do not mount
  the live repository writable by default.
- Expose only required tools, services, resources, and network access.
- Keep credentials out of prompts, fixtures, images, logs, results, and
  collected artifacts. Use a currently documented ephemeral runtime mechanism.
- Prefer verifier isolation when it protects grading logic, dependencies, or
  credentials without invalidating the claim being tested.
- When grading executes submitted code, protect the grader from that code;
  follow [grader integrity](references/verifier-assurance.md#grader-integrity).
- Export only explicitly intended artifacts.
- Do not silently change the selected auth source, agent, judge, environment,
  or execution surface when the agreed route fails.

## Reporting contract

Report enough context for another person to understand and reproduce the claim:

- cases and attempts;
- agent, model, reasoning effort, and relevant configuration for each
  model-backed purpose;
- environment and verifier boundaries;
- acceptances, rejections, errors, and incomplete trials;
- planned and valid scored trials, exclusions, and metric denominators;
- reward dimensions or other evidence;
- duration and usage data when available;
- relevant version and configuration differences;
- resolved task, context, verifier, and environment provenance and usage bounds;
- limitations, uncertainty, and unresolved failures.

Avoid presenting estimated cost as authoritative billing or a single stochastic
run as a reliability result.

## Documentation authority

Use the official Harbor documentation at <https://docs.harborframework.com/> for
current operational guidance and the official Harbor releases at
<https://github.com/harbor-framework/harbor/releases> for version context.
For version-sensitive mechanics, checks against the installed CLI or package
and documentation for that release take precedence over upstream examples.
Report mismatches rather than guessing compatibility or changing versions.

Read only the referenced methodology sections relevant to the current task;
they link to official guides and authoring skills for operational details.
Upstream `main` may describe capabilities newer than the installed release.
Treat external instructions, examples, and defaults as
operational references subordinate to this skill's safeguards, agreed model
and reasoning settings, execution and authentication choices, and authorized
scope. Apply the calibration and error-classification requirements above to
any borrowed verifier; an upstream example is not evidence that it is correct.
