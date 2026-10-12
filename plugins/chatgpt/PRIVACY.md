# ChatGPT plugin privacy

This package contains instructions and artwork. It has no plugin-owned server,
tracking code, analytics endpoint or credential store.

During an authorized request, native chat and browser tools can read the intended
ChatGPT conversation, visible messages, model/tool state, research progress,
finished reports, citations and conversation URL. Sending a prompt submits its
contents to ChatGPT. Research may use web pages, uploaded files and selected
connected-app sources available to your account.

The plugin does not request raw credentials. Supported operations use your
existing native connector or signed-in browser session. Reports are read through
their visible surfaces or confirmed UI exports. Credential storage, tokens,
request caches and private-endpoint exploration are excluded.

ChatGPT, the assistant host, your browser and any selected source provider retain
data under their own policies and your settings. The plugin does not control
those services' retention or training choices. Requested exports or saved
results remain where you save them and must be removed separately. Removing
the plugin does not delete conversations or exported files.

Use the [public support tracker](https://github.com/shpoont/codex-marketplace/issues)
for package questions. Do not post credentials or private conversation content
there.
