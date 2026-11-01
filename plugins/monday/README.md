# Monday

Bring dry wit and reluctant competence to a conversation. Monday uses an
archived persona prompt and all seven example conversations to guide useful,
playfully sarcastic replies. This is an independent recreation.

## Quick start

Requires a ChatGPT or Codex client supporting skills plugins. The plugin adds
no account, credential, runtime or app connection. Your host's model access and
usage limits apply.

Select the installed Monday plugin or skill, then try:

```text
Be Monday. Help me decide what actually deserves my attention today.
```

Expected: practical help with dry, specific humor. First activation loads the
complete packaged persona and all seven examples.

For Codex clients using GitHub marketplaces:

```sh
codex plugin marketplace add shpoont/codex-marketplace --ref main
codex plugin add monday@b2a48b
```

Skip marketplace setup if already configured. Start a fresh conversation after
installation. ChatGPT account installation uses its Plugins surface; GitHub
marketplace registration alone does not install it there.

## Use Monday

Ask for conversation, explanations, brainstorming or candid feedback. For
example: “Be Monday. Explain black holes without making this a physics degree.”
Continue normally, and ask for a warmer or plainer tone whenever useful.
Say “Stop being Monday” or “Back to normal” to leave the persona in that chat.
Global personalization and other conversations are not changed.

Examples teach tone, not canned answers or authority for external actions.
Emails, code and other deliverables follow your requested artifact style.

## Data and effects

Reads: packaged instructions and your conversation request. External services,
credentials, telemetry, scripts, plugin storage and persistent memory: none.
The host still processes and retains chats under its own settings/policies.
Removal does not delete existing conversations or change host memory settings.
The persona adds no authority for tools, writes or external actions.

## Limitations and failures

- No original model, dedicated voice or conversation history is restored.
  Behavior depends on the current model and your instructions.
- The [prompt archive](THIRD_PARTY.md) is not an authenticated OpenAI release.
- Teasing stays playful; serious topics and requests for care take priority.
- If persona.md cannot load, initialization stops with an explanation.
  Reinstall the package; it must not silently invent a replacement.

## Update, removal and recovery

Use your host's Plugins controls to update, disable or remove Monday; start a
fresh chat. For Codex GitHub-marketplace clients:

```sh
codex plugin marketplace upgrade b2a48b
codex plugin add monday@b2a48b
codex plugin remove monday@b2a48b
```

Use one installed copy. For a bad update, disable it and report the problem;
reinstall the corrected published version. Removal does not undo chat content
or external actions requested separately through your host.

## Support

Use the [marketplace issue tracker](https://github.com/shpoont/codex-marketplace/issues).
Include version, client, expected/actual behavior and a sanitized example.
Do not attach credentials, private instructions or personal data.

## Version and license

Version `0.1.1`; see [changes](CHANGELOG.md).
New materials use [MIT](LICENSE). The archived prompt retains its
[CC0 dedication](notices/CC0-1.0.txt) and [provenance](THIRD_PARTY.md).
The original Monday avatar has separate [artwork notices](THIRD_PARTY.md#original-monday-avatar)
and is not licensed by MIT or CC0.

## Disclaimer

This plugin is provided "as is", without warranties of any kind. To the maximum
extent permitted by law, the owner and contributors are not liable for any loss,
damage, or other consequences arising from its installation or use. Review the
plugin's instructions, permissions, and effects before using it.

This plugin is an independent project and is not affiliated with, endorsed by,
or sponsored by OpenAI.
