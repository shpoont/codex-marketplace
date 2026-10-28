# Harbor

Design trustworthy agent evaluations with Harbor. Turn a project question into
representative cases, check that the verifier measures the intended behavior,
and interpret results with clear evidence limits.

This independent package combines our `harbor-agent-tests` methodology with
six officially sourced Harbor workflows. It uses Harbor's official logo;
Harbor Framework does not publish or endorse this plugin. “Official” identifies
the origin of the bundled guides, whose exact revision and hashes appear in
[the provenance manifest](licenses/harbor-provenance.json).

| Skill | Use it for |
| --- | --- |
| `harbor-agent-tests` | Evaluation design, calibration and evidence review |
| `official-create-task` | Authoring a Harbor task |
| `official-rewardkit` | Building a task verifier with Reward Kit |
| `official-harbor-exec` | Planning Exec map and reduce jobs and artifacts |
| `official-create-adapter` | Creating a benchmark adapter in a compatible checkout |
| `official-publish` | Publishing tasks or datasets to Harbor Hub |
| `official-upload-parity-experiments` | Preparing parity-results uploads to Hugging Face |

Each official entrypoint loads [package safeguards](references/official-skill-policy.md)
before its unmodified upstream guide. The installed command/API contract and
our evaluation safeguards remain authoritative over upstream examples.

## Requirements

- Codex with support for GitHub plugin marketplaces and skills.
- Access to the project, cases or recorded results you want to review.
- For execution: a compatible [Harbor installation](https://docs.harborframework.com/),
  a supported isolated backend, and the accounts or model access you choose.
  Docker is preferred for local evaluations.

Installation does not install Harbor, Docker, models or other tools. The package
includes instructions and one optional Python helper described below. Design
and review work need no separate plugin account.
Evaluation runs can consume model usage and create containers, files and logs.
Agree on models, reasoning settings and usage limits before starting them.

## Install

Add the marketplace and install Harbor with the Codex CLI:

```sh
codex plugin marketplace add shpoont/codex-marketplace
codex plugin add harbor@b2a48b
```

Open a fresh Codex conversation after installation. Select Harbor and verify
that all seven skills above are available. If a standalone copy of the
same skill is installed, select the intended copy explicitly and preserve a
recovery copy before changing its installation.

## Use

Start with a concrete question:

```text
Use Harbor to design a focused evaluation for this project's agent behavior.
```

Or review existing evidence:

```text
Use Harbor to review these evaluation cases, verifiers and recorded results.
Explain what they establish and what remains uncertain.
```

Expect a clear claim, representative cases, a calibration plan, execution
bounds and a stopping condition. The skill checks the installed Harbor contract
before relying on version-sensitive commands or defaults. It distinguishes
valid acceptance and rejection from infrastructure errors and incomplete runs.

For an official workflow, select its prefixed name, for example:

```text
Use $official-create-task to scaffold a task and plan verifier calibration.
Do not launch an evaluation yet.
```

Harbor Hub and Hugging Face publication are separate from publishing this
plugin to a Codex marketplace. A task-design or review request does not authorize
either external write. Some upstream examples require a compatible Harbor
checkout or newer CLI/API; identify missing prerequisites before continuing.

## Boundaries and data

The plugin supplies guidance; it does not certify an agent's reliability.
One successful run, a high average score or a passing process exit is not
sufficient evidence by itself. Ordinary product unit tests are outside its scope.

Installing this package starts no server or background task and uploads no
project data. When you authorize evaluations, the selected Harbor backend and
model providers handle the inputs, credentials, trajectories and artifacts
required by that run. Review their access and retention policies. Keep secrets
out of prompts, fixtures and collected artifacts, and export only intended files.
Recorded jobs and model-generated analysis remain subject to their evidence limits.
Hub publication and parity uploads send only separately reviewed content to
the selected destination, using the intended existing account and visibility.
Do not infer permission to upload from an evaluation request.

## Optional parity helper

The official parity-upload workflow includes an upstream Python helper that
creates a Hugging Face dataset PR. It does nothing during plugin installation.
Use it only after the exact destination, description, files and visibility
have been reviewed and authorized. Reuse an existing PR when available.

The helper requires Python 3.10+ and `huggingface-hub==2.3.0`. From your chosen
working project, outside the installed plugin, explicitly create its environment:

```sh
python -m venv .harbor-parity-venv
.harbor-parity-venv/bin/python -m pip install 'huggingface-hub==2.3.0'
```

Dependency installation contacts the Python package index. It does not sign in
or create a PR. Keep the environment, credentials, staging, logs and bytecode
outside the installed package. Missing dependencies fail explicitly; ordinary
skill use never installs them automatically. Repair or replace this external
environment explicitly if setup is interrupted. Leave the installed files intact.
Run one setup process per environment; concurrent projects use separate
environment directories. The helper is optional; unsupported or missing Python
and dependency versions stop that action without changing the installed plugin.

Resolve the installed `official-upload-parity-experiments` skill directory,
then check its unchanged helper without creating anything:

```sh
.harbor-parity-venv/bin/python -B "<installed-skill>/upstream/scripts/create_pr.py" --help
```

Run a separately authorized `create-pr` invocation through a subprocess with
a 60-second deadline. It uses the existing configured Hugging Face session;
verify the intended account and dataset permission without exposing credentials.
The default destination is `harborframework/parity-experiments`. A timeout or
network failure can have an ambiguous remote result: inspect the destination
and reconcile before retrying. The helper has no internal authorization,
timeout or reconciliation guard. The package policy supplies those boundaries.

## Update, remove and recover

Refresh the marketplace and add the plugin again to obtain its current version:

```sh
codex plugin marketplace upgrade b2a48b
codex plugin add harbor@b2a48b
```

To uninstall:

```sh
codex plugin remove harbor@b2a48b
```

These commands use the Codex CLI's `add` and `remove` interface. Check
`codex plugin --help` if your installed client exposes different commands.
Use a fresh conversation to confirm the selected version after an update.
Uninstalling does not remove Harbor itself or delete your evaluation jobs.
To recover after a failed installation, refresh the marketplace and reinstall;
do not edit cached plugin files. A missing runtime, unsupported capability or
authentication failure should be reported before attempting another route.

## Support and license

Report issues in the [public issue tracker](https://github.com/shpoont/codex-marketplace/issues).
Include the plugin/client versions and a minimal sanitized description.
Do not attach credentials, personal paths or private evaluation records.

See [CHANGELOG.md](CHANGELOG.md), [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Original packaging and methodology use the Installation and Use License,
which permits normal personal use and backups; modification or redistribution
of that original material needs separate permission. Bundled upstream artwork,
guides and helper retain their [Apache-2.0 license](licenses/harbor-Apache-2.0.txt)
and its rights without those restrictions.

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
