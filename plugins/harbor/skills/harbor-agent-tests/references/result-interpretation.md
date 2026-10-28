# Result interpretation

Read the relevant section when interpreting recorded evaluations. The core
skill's safeguards, model agreements, and installed-version checks apply.

## Score validity and denominators

Build an outcome ledger before summarizing performance. Account for planned,
completed, valid scored, invalid, cancelled, and unattempted trials; distinguish
retries from independent evaluation attempts. Identify the case and attempt
behind every counted outcome, including errors recorded on individual steps.

Use the installed release's error policy to determine whether an error permits
a valid score. An agent exhausting its agreed budget can still have a valid
verifier result; a provider or verifier failure is a different outcome. A
numeric reward alone does not establish validity. Inspect criterion-level
errors too: a judge or check may encode an error as zero without raising a
trial-level exception. Keep unknown causes unresolved rather than guessing.

For each reported metric:

- state the success rule, unit of analysis, denominator, missing-value policy,
  and exclusions;
- check which outcomes the installed aggregation path actually consumes;
- retain Harbor's original metric and label any separately calculated metric
  with its definition and provenance;
- report invalid-trial coverage alongside performance. A valid subset can be
  systematically easier or harder than the missing cases;
- preserve a common case/attempt basis for comparisons, or explain the mismatch
  and limit the claim. Do not silently drop different failures for each agent.

For example, an agent timeout followed by a valid rejection may count as a
scored failure. A provider outage followed by a zero reward remains invalid
evidence under a policy that invalidates provider errors. A judge timeout
recorded as a criterion zero requires an explicit validity decision; it is not
automatically evidence of poor agent output. Preserve the raw records in each
case.

Consult the current [error classification](https://docs.harborframework.com/jobs/error-classification)
and [metrics](https://docs.harborframework.com/datasets/metrics) documentation.
Verify error validity and metric inclusion separately against the installed
package; do not assume they implement the same filter.

## Reruns, regrading, and reuse

Classify the actual change before choosing the next experiment:

| Change | Appropriate evidence |
| --- | --- |
| Agent-facing instructions, context, tools, environment, or execution settings | New agent attempts under the changed conditions. |
| Verifier, rubric, judge protocol, or scoring only | Regrade the same recorded outputs when sufficient compatible evidence exists. |
| Metadata or presentation only | Reuse after confirming agent behavior and grading inputs are unaffected. |

Content identity and behavioral scope matter more than a task name or version
label alone. Preserve task, verifier, and source-result revisions or digests.
Regrading changes how existing outputs are scored; it does not show how an
agent would behave under changed instructions or environments.

Before regrading, confirm the installed release's requirements, source
completion, readable result and collection records, and availability of every
input needed by the updated verifier. Check artifact exclusions, task matching,
and step compatibility. If required evidence is absent, explain why regrading
cannot support the claim; get agreement before substituting another experiment.

Write derived results separately and retain original scores and provenance.
Apply the intended verifier consistently across compared conditions. Compare
old and new classifications, investigate unexpected changes, and distinguish
intended grading corrections from verifier errors or instability. Report
unregradeable cases and any resulting comparison gaps.

Regrading avoids new evaluated-agent attempts but can still consume sandbox
resources and judge usage. Apply the existing model-setting agreements to any
new model-backed grading or analysis. Label regraded evidence separately from
new attempts and from model-generated interpretation.

Use the current [regrade guide](https://docs.harborframework.com/jobs/regrade)
for mechanics and validate compatibility against the installed release.

## Analyze protocol

Before running Analyze:

- state the question the analysis should answer and what decision it may inform;
- confirm the installed Harbor version and the exact Analyze capabilities it
  exposes;
- record the agreed analyzer agent, model, reasoning effort, environment, and
  authentication route separately from those used by the evaluated agent;
- treat UI model suggestions as conveniences, not proof that an agent-model
  pairing is supported; validate the intended pairing against the installed
  runtime and do not silently substitute another model;
- preserve the source evaluation record. If the installed implementation writes
  analysis artifacts into the job directory, use a copy when testing Analyze
  itself or comparing alternative analyzer configurations;
- hold the analyzer configuration constant when comparing jobs. A changed
  analyzer model, reasoning effort, prompt, or environment is a material
  experimental variable.

After Analyze finishes:

- verify that the source trials were complete enough to support interpretation;
- compare material claims with the underlying artifacts and label unsupported
  inference, contradictions, and omissions;
- classify analyzer authentication, runtime, or artifact-collection failures
  separately from the outcome of the source evaluation;
- retain the analysis artifact with enough provenance to identify the source
  job or trial, Harbor version, analyzer configuration, and run time.
