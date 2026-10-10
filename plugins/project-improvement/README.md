# Project Improvement

## Purpose

Improve software, documents and working processes. Project Improvement currently
includes one skill, **Review and Improve**, for an autonomous cycle of evidence,
implementation and verification.

## Rationale

Worthwhile improvements need evidence and a clear way to verify their benefit.
This routine carries each authorized change through the project's established
workflow, then reassesses before choosing the next improvement.

## Quick start

### Requirements

- Codex with plugin and skill support. Desktop and CLI behavior must be checked
  for the version you use.
- A current project with instructions, an established workflow and authority to
  make the requested changes.
- Additional accounts, connectors and runtime dependencies: None added by this
  plugin. The project itself may require tools or access.

### Install

```sh
codex plugin marketplace add https://github.com/shpoont/codex-marketplace.git
codex plugin add project-improvement@b2a48b
```

Skip marketplace setup when it is already configured. Start a fresh chat in the
project after installation and confirm Review and Improve is available.

### Try it

```text
$review-and-improve Find one worthwhile improvement, implement it, and verify the result.
```

Expected result: a completed and recorded improvement with validation and
material limitations, or an evidence-based explanation that no worthwhile
change can be completed within the supplied limits.

## Capabilities

| Capability | Result and material effect |
| --- | --- |
| Find worthwhile improvements | Gathers relevant evidence and prioritizes by impact, effort and risk. |
| Improve software reliability | Implements and verifies changes supported by the current project. |

## Use the plugin

Invoke `$review-and-improve` explicitly in the project you want to improve.
State any additional scope, authority, time or change limits in that request.
The skill loads the [readable routine](skills/review-and-improve/references/routine.md)
and executes its cycle autonomously. It reuses sufficient evidence; any necessary
reproduction uses isolated tests or evaluations. It reassesses after each
recorded change and stops at supplied limits or when no worthwhile improvement
can be completed and verified.

Starter request:

- `$review-and-improve Find one worthwhile improvement, implement it, and verify the result.`

Project instructions and the authority you supply govern changes. Consequential
ambiguities may require a decision while independent authorized work continues.

## Data and effects

The routine can read project materials, records and available evidence and can
change project systems, processes and work products using Codex's available
tools. It records changes through the project's established workflow, which may
include commits or other authorized external actions.

Plugin-owned accounts, external services, storage, retention and telemetry:
None. The plugin contains instructions and presentation assets only; Codex and
the project's chosen tools govern their own data handling. Removal does not
undo changes or erase records produced during a run.

## Limitations

- Intended invocation is explicit. Do not rely on presentation metadata alone
  as proof of how a particular client selects the skill.
- Benefits depend on the available evidence, tools, project instructions and
  supplied authority. The routine cannot guarantee a useful change.
- Missing tools, resources, access or consequential decisions can leave affected
  work unfinished. Resolve the reported dependency before continuing it.
- Supplied limits and project boundaries still apply during autonomous work.

## Update, removal and recovery

```sh
codex plugin marketplace upgrade b2a48b
codex plugin add project-improvement@b2a48b
codex plugin remove project-improvement@b2a48b
```

Start a fresh chat after an update or removal. Ensure the intended copy is
selected if more than one copy is installed. Removal leaves recorded project
changes in place; review or revert them using the project's normal workflow.

For a bad update, stop new runs, remove the plugin and report the problem.
Reinstall after a corrected version is available. Review unfinished project
work before restarting the routine.

## Support

Report problems in [marketplace Issues](https://github.com/shpoont/codex-marketplace/issues).
Include plugin version, client/platform, expected and actual result, and a
minimal sanitized example. Do not attach credentials, private instructions,
personal data or raw traces.

## Version and license

Version: `0.1.5`. See the [changelog](CHANGELOG.md) for user-visible changes.
The package is provided under the [MIT License](LICENSE).
No third-party runtime libraries are bundled.

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
