# Validated Docker, Codex and ChatGPT subscription recipes

Use these recipes for the owner's repeatable project tests. First apply
[package safeguards](../../../references/official-skill-policy.md); installed
commands and APIs remain authoritative. Qualification covers Harbor **0.25.0**,
guest Codex **0.167.0**, Linux ARM64 Docker, **GPT-6.1 Sol / High** and the existing
ChatGPT sign-in. Check the selected runtime and Docker before execution. A
different version, platform or combination needs relevant compatibility checks.
Compare the changed component with the selected recipe's pins and native API;
repeat its affected model-free good/bad controls and one representative live
case before relying on that changed profile. Reuse unchanged evidence with its
original scope; leave incompatible or untested combinations unsupported. Do not
upgrade installed Harbor or silently switch authentication.

## Start or migrate a project

Keep the project's canonical cases, generator, fixtures and graders. Select the
smallest recipe that meets its acceptance criteria. Generate native Harbor tasks
in disposable staging; adapt project inputs and grading there through the
canonical generator. Never mount the live repository, home or Docker socket into
an evaluated container. Keep inference non-root, graders separate and images
pinned. Copy only necessary project inputs; keep hidden expectations out of the
agent image. Runtime setup is not evidence of behavior quality.

The [recipe archive](../assets/validated-recipes.zip) contains native templates,
the qualified thin runners and per-increment evidence records. It contains
example skills as test data, not additional plugin entrypoints. Extract it into
a **new empty directory** outside Git; do not overwrite an existing workspace:

```sh
# SKILL_DIR is this installed skill directory; WORK is new disposable staging.
# HARBOR_PYTHON is the interpreter of the selected compatible Harbor runtime.
mkdir "$WORK" &&
"$HARBOR_PYTHON" -m zipfile -e "$SKILL_DIR/assets/validated-recipes.zip" "$WORK/recipes" &&
cd "$WORK/recipes" &&
"$HARBOR_PYTHON" tooling/run_docker_case.py --help
```

Read only the chosen example's README and its relevant qualification limits.
Prepare its images once, retain immutable IDs and reuse the prepared task for
reruns. Follow its explicit commands; do not change the shared runner to add a
case.

Make a project-local generator adapter if the existing generator does not
emit this recipe's contract: user `node`/UID 1000, pinned agent and separate
verifier images, declared artifacts and a verifier `checks.json` recording the
qualified checks for absent agent credentials in the verifier. Preserve project
grading semantics. For a harness that injects a developer instruction, pass its
complete rendered file with `--developer-instructions`; the runner uses native
Codex configuration and records its hash. Do not move it into a user prompt.
The runner's ordinary
pass/fail summary expects binary `reward`; judge/regrading recipes separately
cover their recorded scoring formats. A schema mismatch is setup work, not a
participant failure. Do not call arbitrary native tasks compatible automatically.

Review one migrated case, then add another representative case and rerun without
shared-runner edits. Inspect each result before the next migration. Reuse valid
qualification evidence: the archive's negative controls are maintainer checks,
not a compulsory campaign for every project. Record unmigrated setups explicitly.

## Choose the case form

Paths below are relative to the extracted `recipes` directory. Every row has a
README with preparation and run commands. Numbered recipes map to
`docs/iNN-*.md` qualification records (for example, I06 uses
`docs/i06-atif-loading.md`); the adaptive record is
`docs/subscription-acp-qualification.md`. These dated records describe the
qualification checkpoints, including limitations and subsequent corrections.

| Need | Example under `examples/` | Tested scope or limit |
| --- | --- | --- |
| One instruction; repeatable suite | `docker-codex-i01`, `docker-codex-i02-staging` | Two realistic file-change tasks, repeated without runner changes |
| Ordered fresh sessions with persisted files | `docker-codex-i03-workflow` | Early stopping and skipped-step reporting |
| Continued conversation with corrections | `docker-codex-i04-conversation` | Native resume, prior-message dependence; cumulative usage counted once |
| Native Codex history | `docker-codex-i05-load-native` | Malformed history rejected; loading history does not restore files |
| ATIF history and later fresh/resumed steps | `docker-codex-i06-atif`, `docker-codex-i06-atif-workflow` | Task/run precedence; conversion limits retained |
| Task/job skills | `docker-codex-i07-skills` | Delivery and precedence, rather than presence alone |
| Local tools/MCP; Compose services | `docker-codex-i08-mcp`, `docker-codex-i08-compose` | Local stdio/HTTP and service fixtures; no connected-account claim |
| Restricted network and native web controls | `docker-codex-i09-network` | Allowed/blocked routes measured; DNS and ICMP remain reachable, so no complete-egress claim |
| Shared/separate artifact transfer; submitted code | `docker-codex-i10-transfer`, `docker-codex-i10-worker` | Actual transfer receipts and exclusion checks; Reward Kit's Worker runs submitted code with configured private paths protected; Worker setup/cleanup errors invalidate trial evidence |
| Subscription Codex judge; regrading | `docker-codex-i11-judge` | Explicit judge role/settings and calibrated rubric; regrade saved evidence without rerunning targets |
| Exec map; reviewed reducer | `docker-codex-i12-exec` | Sequential map and manual reducer checkpoint; no automatic fan-out claim |
| Imported task and reference solution | `docker-codex-i12-import` | One pinned upstream task; inspect imported instructions, grader and root requirements |
| Adaptive model-backed conversation | `docker-codex-acp-subscription` | Explicit opt-in project-local ACP adapter; two single-step cases; Harbor's built-in Codex-to-ACP route still rejects ChatGPT subscription auth |

Adaptive target and simulated user both use the agreed subscription profile.
They share a guest workspace and UID: role histories establish attribution,
not filesystem isolation. Broad adaptive combinations, Windows Codex,
host handoff, selected-step startup, run-level history with simulation and
multi-step simulation remain unqualified or unsupported. Do not substitute
scripted follow-ups and label them adaptive. Do not modify installed Harbor to
enable the opt-in adapter.

## Review and move on

Retain the native job/trial, summary, actual exports, image/source pins and cleanup
evidence outside Git. Check actual behavior against the project's criteria.
Report valid passes/failures separately from input, infrastructure, collection
and grading errors; unknown usage is unknown, not zero. Scores alone do not
establish correctness, isolation or phase completion. Preserve raw rewards even
when a boundary failure invalidates their interpretation.

Give the user the cases run, meaningful outcomes, material limits and the next
project action in plain language. Fix a demonstrated setup defect within the
agreed profile and rerun its affected check. Reassess repeated failures instead
of expanding infrastructure or adding approval budgets. Stop when the project's
agreed evidence is sufficient; migrations do not authorize plugin publication.
