---
name: harbor-evaluate-agent-behavior
description: Design, review, analyze and interpret Harbor evaluations of coding-agent behavior, including resumed investigations. Use for representative cases, controlled comparisons, evidence and verifier calibration, isolation claims, recorded results, regrading and Harbor Analyze. Do not use for ordinary product tests that do not evaluate an agent.
---

# Harbor Evaluate Agent Behavior

Turn a project question into an evaluation that can support an honest decision.
The project and its acceptance criteria are the source of truth. This skill owns
evaluation methodology; the packaged official skills own operational mechanics.

## Start with the current decision

1. Read and apply [Harbor package safeguards](../../references/official-skill-policy.md).
   They govern installed-version authority, model/effort/authentication agreements
   and budgets, execution boundaries, evidence validity and external writes.
2. Identify the user's decision, current stage, success rule, existing evidence,
   next necessary action and stopping condition. For resumed work, reconcile the
   [working record](references/evaluation-workflow.md#working-record-and-resumption)
   before repeating work. A small review can keep its record in the response.
3. Inspect the existing harness's canonical generators, cases, fixtures and
   results before proposing changes. Preserve intentional customizations; update
   canonical sources rather than generated copies.

## Load the methodology that answers the question

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

Pass the claim, acceptance/evidence contract, relevant calibration results,
agreed execution/model bounds and current blocker to the selected skill.
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
