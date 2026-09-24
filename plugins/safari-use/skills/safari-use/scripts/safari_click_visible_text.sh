#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  safari_click_visible_text.sh --window-id <id> --text <visible text> [--exact]

Click the best visible element matching text in the current tab of a Safari window.

Options:
  --window-id <id>   Target Safari window id (required)
  --text <text>      Visible text to match (required)
  --exact            Require exact text match (default: contains/starts-with allowed)
  -h, --help         Show this help
USAGE
}

window_id=""
target_text=""
exact_match="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --window-id)
      window_id="${2:-}"
      shift 2
      ;;
    --text)
      target_text="${2:-}"
      shift 2
      ;;
    --exact)
      exact_match="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$window_id" || -z "$target_text" ]]; then
  echo "Missing required --window-id or --text" >&2
  usage >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
eval_helper="$script_dir/safari_eval_js_window.sh"
if [[ ! -x "$eval_helper" ]]; then
  echo "Required helper not executable: $eval_helper" >&2
  exit 1
fi

tmp_js="$(mktemp /tmp/safari_click_visible_text.XXXXXX.js)"
cleanup() {
  rm -f "$tmp_js"
}
trap cleanup EXIT

target_text_b64="$(printf '%s' "$target_text" | base64 | tr -d '\n')"
exact_js="false"
if [[ "$exact_match" == "true" ]]; then
  exact_js="true"
fi

cat >"$tmp_js" <<EOF
(() => {
  try {
    const normalize = (value) => String(value ?? '').replace(/\\s+/g, ' ').trim();
    const targetText = normalize(atob('${target_text_b64}'));
    const exactMatch = ${exact_js};
    const needle = targetText.toLowerCase();

    if (!needle) {
      return JSON.stringify({
        clicked: false,
        reason: 'empty-target-text',
        url: location.href,
        title: document.title,
      });
    }

    const isVisible = (el) => {
      if (!(el instanceof Element)) return false;
      const style = window.getComputedStyle(el);
      if (!style) return false;
      if (style.display === 'none' || style.visibility === 'hidden') return false;
      if (Number.parseFloat(style.opacity || '1') === 0) return false;
      const rect = el.getBoundingClientRect();
      if (!rect || rect.width <= 0 || rect.height <= 0) return false;
      const viewW = window.innerWidth || document.documentElement.clientWidth;
      const viewH = window.innerHeight || document.documentElement.clientHeight;
      if (rect.bottom < 0 || rect.right < 0 || rect.top > viewH || rect.left > viewW) return false;
      return true;
    };

    const selectors = [
      'a',
      'button',
      '[role="button"]',
      'input[type="button"]',
      'input[type="submit"]',
      'label',
      'summary',
      '[onclick]',
      '[tabindex]'
    ];
    const nodes = Array.from(document.querySelectorAll(selectors.join(',')));

    const candidates = [];
    for (const el of nodes) {
      if (!isVisible(el)) continue;

      const rawLabel =
        el.innerText ||
        el.textContent ||
        el.value ||
        el.getAttribute('aria-label') ||
        el.getAttribute('title') ||
        '';
      const label = normalize(rawLabel);
      if (!label) continue;

      const hay = label.toLowerCase();
      let score = -1;
      if (exactMatch) {
        if (hay === needle) score = 300;
      } else if (hay === needle) {
        score = 300;
      } else if (hay.startsWith(needle)) {
        score = 200;
      } else if (hay.includes(needle)) {
        score = 100;
      }

      if (score < 0) continue;
      if (el.matches('a,button,input,[role="button"],summary,[onclick]')) score += 20;

      candidates.push({
        el,
        label,
        score,
        tag: el.tagName.toLowerCase(),
        id: el.id || '',
      });
    }

    if (candidates.length === 0) {
      return JSON.stringify({
        clicked: false,
        reason: 'no-visible-match',
        target_text: targetText,
        exact: exactMatch,
        scanned_nodes: nodes.length,
        url: location.href,
        title: document.title,
      });
    }

    candidates.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.label.length - b.label.length;
    });

    const chosen = candidates[0];
    chosen.el.scrollIntoView({ block: 'center', inline: 'center' });
    if (typeof chosen.el.focus === 'function') {
      chosen.el.focus({ preventScroll: true });
    }

    const rect = chosen.el.getBoundingClientRect();
    chosen.el.click();

    const descriptor = chosen.id ? \`\${chosen.tag}#\${chosen.id}\` : chosen.tag;
    return JSON.stringify({
      clicked: true,
      target_text: targetText,
      matched_text: chosen.label,
      descriptor,
      match_count: candidates.length,
      scanned_nodes: nodes.length,
      bbox: {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      },
      url: location.href,
      title: document.title,
    });
  } catch (error) {
    return JSON.stringify({
      clicked: false,
      reason: 'js-error',
      error: String(error),
      url: location.href,
      title: document.title,
    });
  }
})();
EOF

"$eval_helper" --window-id "$window_id" --js-file "$tmp_js"
