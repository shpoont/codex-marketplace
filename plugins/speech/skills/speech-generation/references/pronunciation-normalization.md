# Pronunciation normalization

Use this reference when Kokoro renders recurring words, acronyms, brands, names,
or foreign terms poorly.

## Policy

Keep pronunciation fixes as a narrow preprocessing step for the text sent to
Kokoro. Do not rewrite the source article, transcript, or user-facing written
copy unless the user explicitly asks for that.

Use this order:

1. **Plain text normalization**: adjust spacing, punctuation, capitalization, or
   wording so Kokoro's normal G2P reads naturally.
2. **Lexicon entry**: add a targeted replacement for a repeated token or phrase
   after listening or transcription shows the default rendering is wrong.
3. **IPA hint**: use Kokoro-style `[word](/IPA/)` only when the text rewrite
   still fails or when exact pronunciation matters, and only after confirming
   the active Kokoro/G2P install supports this syntax with a smoke test.

## Lexicon design

- Match specific phrases before shorter tokens, e.g. handle `Open AI` before
  `AI`.
- Prefer case-aware whole-word or phrase matching. Avoid unconstrained substring
  replacements.
- Keep entries small and auditable. Each entry should have an observed problem,
  a replacement, and ideally a short note about the successful smoke test.
- Apply the lexicon before sentence segmentation so chunks stay consistent.
- Keep source and TTS text separate in saved artifacts when possible, for
  example `script.txt` and `script.tts.txt`.
- Treat "lexicon" as a per-task preprocessing map by default, not as a global
  persistent skill-level dictionary unless the user explicitly asks for one.

## Examples

| Problem text | Try first | Escalate only if needed |
|---|---|---|
| `AI` sounds like a word or slurs | `A.I.` | `[AI](/ˌeɪ ˈaɪ/)` |
| `Open AI` sounds spaced or awkward | `OpenAI` | `[OpenAI](/ˈoʊpən ˌeɪ ˈaɪ/)` |
| A product name is read as ordinary words | preferred brand spelling or spaced syllables | IPA hint |
| A foreign proper noun is mangled | simple phonetic respelling for narration | IPA hint |

## Validation

For a new or changed entry, generate a short sample containing only the affected
phrase plus nearby context. Validate by listening, local transcription, or a
blind comparison pack. Do not claim a lexicon entry improves quality from file
creation alone.

If a text normalization sounds more natural than IPA, keep the normalization as
the default and reserve IPA for that term only when a future sample proves it is
needed.
