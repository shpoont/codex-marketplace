# Third-party notices

Harbor contains original evaluation instructions and packaging, plus the
official Harbor Framework logo, six skill guides, an Exec reference and the
parity PR helper from the revision recorded in
[the provenance manifest](licenses/harbor-provenance.json). The unmodified
upstream Apache-2.0 license is included at
[licenses/harbor-Apache-2.0.txt](licenses/harbor-Apache-2.0.txt).

Bundled upstream material retains its Apache-2.0 terms. The package's
Installation and Use License does not restrict those upstream rights.
The logo is reproduced to identify Harbor compatibility; this independent
package is not published or endorsed by Harbor Framework.

This package does not bundle the Harbor Framework executable, Reward Kit,
Docker, model clients or the Hugging Face SDK. The optional Python helper
requires a separately installed `huggingface-hub==2.3.0`, under its own license.
No dependencies are installed by plugin installation or ordinary skill loading.

The `official-` entrypoints, interface metadata and shared safeguards are
independently maintained packaging. Original upstream SKILL.md files are stored
unchanged as `upstream/guide.md`; supporting reference and helper files are
also unchanged. The provenance manifest records every original path and hash.

Harbor Framework, OpenAI, Codex, Docker and other product names describe
compatibility. Their trademarks and software remain under their owners' terms;
this package grants no rights in them and implies no endorsement.

Official documentation is linked as reference material and remains under its
publishers' terms. The installed-version checks and evaluation safeguards in
this package remain authoritative when examples differ from the selected setup.

PyYAML is a source-validation dependency only. It is not distributed in this
package and retains its own license.
