---
name: harbor-agent-testing
description: Create, run and review repeatable Harbor tests of agent behavior. Preserve project acceptance criteria, reuse validated execution recipes and report clear results.
---

# Harbor Agent Testing

Turn a project question into an evaluation that can support an honest decision.
The project and its acceptance criteria are the source of truth. This skill owns
evaluation methodology and the qualified project recipes below; the packaged
official skills supply general operational mechanics.

## Start with the current decision

1. Read and apply [Harbor package safeguards](../../references/official-skill-policy.md).
   Resolve links from this `SKILL.md`'s directory. If that read fails, correct
   the path and read the policy successfully before opening other references.
   They govern installed-version authority, model/effort/authentication choices,
   explicit user limits, execution boundaries, evidence validity and external writes.
2. Identify the user's decision, current stage, success rule, existing evidence,
   next necessary action and stopping condition. For resumed work, reconcile the
   [working record](references/evaluation-workflow.md#working-record-and-resumption)
   before repeating work. A small review can keep its record in the response.
3. Inspect the existing harness's canonical generators, cases, fixtures and
   results before proposing changes. Preserve intentional customizations; update
   canonical sources rather than generated copies.

## Load the methodology that answers the question

For repeatable project tests with Docker, Codex and the owner's ChatGPT
subscription, use [validated recipes](references/validated-recipes.md) after
the safeguards above. Reuse the closest qualified recipe and preserve the
project's canonical cases and graders. Review one project's migration before
starting the next; do not restart the full qualification campaign for each suite.

Read the relevant sections, rather than every reference on every invocation.
Complete a relevant prerequisite before relying on the evidence it qualifies.

| Question or stage | Reference |
| --- | --- |
| Claim, realistic cases, incident reproduction or a fair skill/context comparison | [Experiment design](references/experiment-design.md#claim-and-cases) |
| Required capabilities/access, state, session resume or simulated users | Relevant section of [experiment design](references/experiment-design.md#effective-capabilities-and-access) |
| Evidence choice, criteria, protected grading, collection, aggregation, judge calibration or preflight | Relevant section of [verifier assurance](references/verifier-assurance.md#evidence-choice-and-calibration) |
| Scores, errors, denominators, historical reuse, regrading or Analyze | Relevant section of [result interpretation](references/result-interpretation.md#score-validity-and-denominators) |
| Resumption, cumulative effort, next action or closeout/reporting | Relevant section of [evaluation workflow](references/evaluation-workflow.md) |

Keep Analyze as optional interpretation of recorded evidence. It does not
replace verification or change earned rewards. Read its
[protocol](references/result-interpretation.md#analyze-protocol) before using it.

## Hand operational work to the packaged official skill

Pass the claim, acceptance criteria and required evidence, relevant calibration
results, agreed execution limits and model settings, and any current blocker
to the selected skill.
Follow its policy-first entrypoint and check the selected installed runtime;
an upstream example does not establish compatibility or verifier correctness.

| Requested mechanics | Skill |
| --- | --- |
| Task scaffold, environment/configuration and task README | [$official-create-task](../official-create-task/SKILL.md) |
| Reward Kit criteria, judges and aggregation implementation | [$official-rewardkit](../official-rewardkit/SKILL.md) |
| Input compilation, map/reduce execution and artifacts | [$official-harbor-exec](../official-harbor-exec/SKILL.md) |
| Benchmark adapter scaffold in a compatible checkout | [$official-create-adapter](../official-create-adapter/SKILL.md) |
| Separately authorized Harbor Hub publication | [$official-publish](../official-publish/SKILL.md) |
| Separately authorized Hugging Face parity PR/upload | [$official-upload-parity-experiments](../official-upload-parity-experiments/SKILL.md) |

Design or review does not automatically authorize execution or publication.
Operational-only requests can start directly with the appropriate official skill.

## Return a disposition

Explain what the evidence supports, what remains uncertain, and the next action
or reason to stop. Distinguish preparation, calibration, agent behavior and
demonstrated repair. Follow [results and closeout](references/evaluation-workflow.md#results-and-closeout)
for reproducible reporting; do not extend the investigation after its decision
or stopping condition is met. Report unavailable prerequisites explicitly.
