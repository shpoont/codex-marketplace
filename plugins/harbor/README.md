# Harbor

Design trustworthy agent evaluations with Harbor. Turn a project question into
representative cases, check that the verifier measures the intended behavior,
and interpret results with clear evidence limits.

This independent package contains the `harbor-agent-tests` skill and its
methodology references. It is not an official Harbor Framework plugin.

## Requirements

- Codex with support for GitHub plugin marketplaces and skills.
- Access to the project, cases or recorded results you want to review.
- For execution: a compatible [Harbor installation](https://docs.harborframework.com/),
  a supported isolated backend, and the accounts or model access you choose.
  Docker is preferred for local evaluations.

The plugin contains instructions only. It does not install Harbor, Docker,
models or other tools. Design and review work need no separate plugin account.
Evaluation runs can consume model usage and create containers, files and logs.
Agree on models, reasoning settings and usage limits before starting them.

## Install

Add the marketplace and install Harbor with the Codex CLI:

```sh
codex plugin marketplace add shpoont/codex-marketplace
codex plugin add harbor@b2a48b
```

Open a fresh Codex conversation after installation. Select Harbor and verify
that its `harbor-agent-tests` skill is available. If a standalone copy of the
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

## Boundaries and data

The plugin supplies methodology; it does not certify an agent's reliability.
One successful run, a high average score or a passing process exit is not
sufficient evidence by itself. Ordinary product unit tests are outside its scope.

Installing this package starts no server or background task and uploads no
project data. When you authorize evaluations, the selected Harbor backend and
model providers handle the inputs, credentials, trajectories and artifacts
required by that run. Review their access and retention policies. Keep secrets
out of prompts, fixtures and collected artifacts, and export only intended files.
Recorded jobs and model-generated analysis remain subject to their evidence limits.

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
The Installation and Use License permits normal personal use and backups;
modification or redistribution needs separate permission.

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
