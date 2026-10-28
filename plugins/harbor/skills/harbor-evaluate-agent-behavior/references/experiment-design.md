# Experiment design

Read the relevant section for the selected evaluation mode. Apply the
[shared package safeguards](../../../references/official-skill-policy.md).

## Claim and cases

State the decision the evaluation should inform and the claim its evidence can
support. Define success, failure, uncertainty and evidence limits before choosing
implementation details. Use realistic inputs with the smallest context needed
for the behavior. Keep independently diagnosable scenarios separate; include
important boundary and failure cases. Keep hidden answers and verifier
implementation out of the agent prompt.

For comparisons, hold cases, context, environment, verifier, attempt policy and
reporting rules constant. Change one material variable at a time unless studying
an explicitly combined intervention. Use repeated attempts for reliability
claims. Apply the incident or injected-context sections below when relevant;
record resolved inputs, settings, resource enforcement and usage bounds under
[execution planning and provenance](#execution-planning-and-provenance).

## Incident reproduction

When evaluating a fix for a reported failure, start from the retained incident.
Connect each relevant case to the user's objective, the observed behavior, the
expected outcome and its justification, and the revision under test. Preserve
the interaction and information boundaries that could explain the failure;
an easier case about the same general principle is not a reproduction.

Distinguish coordinator framing, participant-visible evidence, participant
behavior, and grading. A reviewer cannot recover an objective it never received.
Identify which layer the proposed change addresses; adding missing context and
changing the participant's instructions together does not isolate either effect.

Before expanding a fix comparison, test whether the old version reproduces the
relevant failure under the intended execution and grading path. Historical
records can establish the original incident, but distinguish them from a fresh
reproduction. If the failure is not reproduced, keep it unresolved; do not force
a failure or claim it fixed because related cases pass. Broader screening may
still be useful when its separate question and limits are explicit.

Compare the changed version on the same case and preserve the old result.
Include a legitimate alternative or unchanged compliant outcome where relevant.
When both versions already pass, assess whether the case can inform the decision
before adding models or attempts. Expand for a stated coverage or variability
question; keep newly authored and held-out cases distinct from tuning evidence.

## Skills and injected context

State the intervention and comparison: a skill versus no skill, two revisions,
or another explicit context change. Separate instructions used by the
evaluation author from the treatment intentionally supplied to the evaluated
agent. Do not leak hidden evaluation guidance or reference answers into that
agent's context.

Record the exact supplied skill contents, local changes, resolved revisions,
and content digests. Check both task-bundled and job-injected sources, their
order, same-name replacements, and any additional instructions or native
configuration. A directory path or moving branch alone does not identify the
content used in a historical run.

Verify that the selected integration can register the supplied context and
that the expected content reaches its native location or prompt. Distinguish:

- delivery of the content;
- discoverability by the agent;
- observed use, when the trajectory can establish it;
- improvement in the requested outcome.

Delivery does not prove use, and use does not prove benefit. Lack of a visible
skill-read event is not proof of non-use when the runtime injects content
directly. Grade a prescribed process only when that process is part of the
evaluation claim; otherwise evaluate outcomes and report process evidence
separately.

Hold cases, environment, tools, model settings, attempts, and grading constant.
Use repeated attempts when claiming reliability, and compare on a common case
basis with uncertainty and invalid-trial coverage visible. Keep held-out cases
separate from cases used to revise the skill or tune its verifier. A result on
the tuning cases is evidence for those cases, not independent generalization.

Consult [job skills](https://docs.harborframework.com/jobs/skills),
[task skills](https://docs.harborframework.com/tasks/skills), and
[agent capabilities](https://docs.harborframework.com/agents/pre-integrated-agents#agent-capabilities)
for delivery, precedence, and provenance mechanisms. Confirm the installed
behavior rather than assuming identical discovery across agents.

## Effective capabilities and access

Identify capabilities the claim depends on, such as skill discovery, MCP tools,
trajectory capture or loading, session resume, and network or resource
enforcement. Check the installed agent integration and provider declarations,
then verify relevant behavior with a focused smoke check. Configuration
acceptance or successful setup alone does not prove tool connectivity,
enforcement, or usable evidence. Model-backed probes still require the shared
model-setting agreement.

Check effective access across environment startup, agent setup and execution,
and verification. Sandbox egress restrictions do not necessarily constrain
provider-hosted web tools or arbitrary remote MCP services. Confirm the tool
controls and inference access needed for the agreed boundary; do not describe
a run as offline merely because a sandbox network setting was accepted.

Calibrate network probes with a reachable positive control and an actual
protocol exchange. A transparent proxy may accept a local TCP connection while
denying the remote request. Match the request's host identity, including HTTP
Host or TLS SNI, to the intended allowlist entry. For a claim of complete
network denial, check relevant non-HTTP paths such as DNS and ICMP as well;
successful HTTP blocking does not establish an offline boundary. Record any
reachable channel and stop runs that require its denial until the required
boundary can be established.

Resolve provider routing and credential selection deliberately. Check for
ambient settings or automatic mappings that change the intended provider,
endpoint, account, or credential source. Record only non-secret routing
identity and credential source names or presence, never credential values or
access-bearing URLs. Do not dump resolved configuration that might contain
secrets or inspect credential files to complete this check.

Keep sandbox-provider credentials in the Harbor process, agent credentials in
the agent phase, and judge credentials in the verifier scope where supported.
Inspect inherited sandbox variables and lifecycle-hook access when evaluating
their reach; a separate verifier does not by itself establish every credential
boundary.

If a required capability or boundary cannot be established, stop that affected
run and explain the limitation. Preserve the selected backend, authentication
source, and model choices rather than weakening enforcement or substituting
another route without agreement.

Consult [agent capabilities](https://docs.harborframework.com/agents/pre-integrated-agents#agent-capabilities),
[network policies](https://docs.harborframework.com/tasks/network-policies),
[credential routing](https://docs.harborframework.com/agents/agent-auth-resolution),
and [environment variable scopes](https://docs.harborframework.com/jobs/environment-variables).
Use the current documentation and installed implementation for their mechanics.

## Stateful evaluations

Use this section only for multi-step tasks, loaded or resumed sessions, or
simulated-user interactions. Define the unit being evaluated: an individual
milestone, an entire workflow, continuation from supplied context, or interaction
under a specified user simulation.

### Multi-step and resumed sessions

Specify which filesystem state, conversation history, tools, and services
persist between steps. Continuing in the same sandbox does not establish that
the conversation resumed; loading a trajectory does not restore sandbox files.
Check support for the selected loading or resume mechanism and document losses
from conversion between trajectory formats. Record the provenance of seeded
context and exclude hidden answers unless supplying them is the intended task.

Record ordered steps, per-step inputs and overrides, execution budgets,
continuation thresholds, and reward aggregation. Declare whether later steps
depend on the previous agent's work or supplied setup. Distinguish work done by
the agent from state introduced by setup or reference solutions.

Calibrate early stopping with a trial that finishes an intermediate milestone
but never reaches the intended end. Report attempted, completed, and skipped
steps alongside intermediate quality. An aggregate over executed steps must
not be described as full workflow success without meeting the separately
defined completion rule. Inspect step errors as well as trial errors.

### Simulated users

Treat the simulated user as an experimental component with its own agreed
model and effort, persona, task knowledge, bridge instructions, turn or resource
budget, and stopping rule. Preserve those conditions across target-agent
comparisons unless the experiment deliberately varies them. Apply the shared
model agreements before user-model calls, including calibration runs.

Control what information reaches the target through conversation; keep hidden
grading material out of the simulation. Record both roles' relevant evidence
and failures. Limit conclusions to the interaction protocol and simulated users
actually tested; they do not by themselves establish behavior with humans.

Use current [multi-step](https://docs.harborframework.com/tasks/multi-step),
[trajectory loading](https://docs.harborframework.com/jobs/loading-trajectories),
and [simulated-user](https://docs.harborframework.com/jobs/simulate-a-user)
guides, checking compatibility against the installed agent and Harbor release.

## Execution planning and provenance

Choose execution bounds proportionate to the claim and existing authorization.
Account for selected cases, agent conditions, independent attempts, retries,
judge samples, simulated users or reducers, and analysis. Distinguish these
sources of usage rather than treating every invocation as another observation
of agent reliability. Apply model-setting agreements to every model-backed role.

Define when to stop or reassess before increasing execution: exhausted usage
bounds, repeated infrastructure failures, or invalid evidence that prevents the
intended comparison. Preserve partial results and explain the blocker. Do not
silently increase retries, timeouts, judge samples, or scope in response to
unfavorable results. Obtain agreement for material changes to the experiment or
its constraints; do not introduce extra approval steps for choices already
authorized.

For setup and repair decisions, assess
[cumulative effort and blockers](evaluation-workflow.md#cumulative-effort-and-blockers)
before extending the route to the original decision.

Record effective execution conditions, including timeouts, concurrency, and
resource enforcement. A requested allocation and an enforced ceiling are
different conditions. Verify the selected provider's behavior when it matters
to the claim; equal nominal CPU or memory values alone do not establish an
equivalent environment. Keep budget exhaustion distinct from provider failure.

Retain enough non-secret provenance to reconstruct the experiment:

- exact case selection, task and dataset content, and input snapshots;
- injected skills, extra instructions, native configuration, and seeded context;
- evaluated agent and integration versions, model, effort, and provider identity;
- environment images or build inputs, relevant dependency versions, access
  boundaries, and resource policies;
- verifier and rubric revisions, aggregation and metric definitions, artifact
  records, and attempt or retry policy.

Prefer resolved immutable revisions or content digests where available. A
requested version, mutable image tag, moving branch, or local path alone may
not describe the code actually used. Verify the effective agent version when
installation or prebuilt-image behavior can change it. Preserve safe
configuration and lock records without copying secrets into the archive.

For requested input-compilation or map-reduce mechanics, use
[$official-harbor-exec](../../official-harbor-exec/SKILL.md).
Include compiled-task inputs and any reducer in the provenance and model
agreements. File-existence checks establish presence, not semantic correctness.
Use the current [job config](https://docs.harborframework.com/jobs/configs),
[resources](https://docs.harborframework.com/tasks/resources), and
[agent installation](https://docs.harborframework.com/agents/pre-integrated-agents#pre-installed-agents)
references for mechanics, checked against the installed runtime.

## Benchmark conversion

When importing an existing benchmark, use
[$official-create-adapter](../../official-create-adapter/SKILL.md)
for mechanics and its compatible-checkout prerequisites. Define the parity claim and preserve the original
benchmark's relevant conditions when comparing harnesses. Contribution,
publication, or coordination steps in an upstream guide do not expand the
user's authorized scope.
