"""The screen half of the add-on.

Voice carries the session; this is what a device with a display shows while it
happens. It deliberately does not transcribe the speech - repeating spoken words
on screen adds nothing. It shows the one thing a voice cannot: when a student
keeps mixing two concepts up, the two are put side by side, which is what makes
the confusion visible instead of merely stated.

Rendered by the host in a sandboxed iframe via the MCP Apps extension. Per
SEP-2133 the tools stay fully usable without it - a speaker with no screen loses
nothing but the picture.
"""

PRACTICE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Study Coach</title>
<style>
  :root {
    --bg: #ffffff;
    --ink: #14181f;
    --muted: #5d6673;
    --line: #e3e7ed;
    --card: #f6f8fa;
    --good: #0f7b4f;
    --good-bg: #e6f4ec;
    --bad: #a3341f;
    --bad-bg: #fbeae6;
    --unsure: #6b5d1f;
    --unsure-bg: #f7f1dc;
    --accent: #2b5cd9;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #10141a; --ink: #eef2f7; --muted: #9aa5b4; --line: #263041;
      --card: #182030; --good: #5fd39b; --good-bg: #10301f; --bad: #f3907a;
      --bad-bg: #331812; --unsure: #e3cd7d; --unsure-bg: #2e2913; --accent: #7ea2ff;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 28px 30px;
    background: var(--bg); color: var(--ink);
    font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .progress { display: flex; align-items: center; gap: 12px; margin-bottom: 22px; }
  .bar { flex: 1; height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
  .bar > i { display: block; height: 100%; background: var(--accent); border-radius: 3px;
             width: 0; transition: width .35s ease; }
  .count { font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums;
           letter-spacing: .02em; white-space: nowrap; }
  h1 { font-size: 27px; line-height: 1.25; margin: 0 0 20px; font-weight: 620; letter-spacing: -.01em; }
  .verdict { display: inline-flex; align-items: baseline; gap: 9px;
             padding: 9px 15px; border-radius: 999px; font-size: 15px; font-weight: 600;
             margin-bottom: 18px; }
  .verdict.correct  { color: var(--good);   background: var(--good-bg); }
  .verdict.incorrect{ color: var(--bad);    background: var(--bad-bg); }
  .verdict.unclear  { color: var(--unsure); background: var(--unsure-bg); }
  .verdict small { font-weight: 500; opacity: .8; }
  .answer { font-size: 15px; color: var(--muted); margin: 0 0 20px; }
  .answer b { color: var(--ink); font-weight: 600; }

  /* The reason this screen exists. */
  .contrast { margin-top: 4px; }
  .contrast-label { font-size: 13px; text-transform: uppercase; letter-spacing: .07em;
                    color: var(--muted); margin-bottom: 10px; }
  .pair { display: grid; grid-template-columns: 1fr auto 1fr; gap: 14px; align-items: stretch; }
  .pair > div { background: var(--card); border: 1px solid var(--line); border-radius: 12px;
                padding: 18px 16px; font-size: 19px; font-weight: 600; text-align: center;
                display: flex; align-items: center; justify-content: center; }
  .vs { align-self: center; color: var(--muted); font-size: 13px; font-weight: 600;
        text-transform: uppercase; letter-spacing: .06em; padding: 0 2px; }
  .note { margin-top: 16px; font-size: 14px; color: var(--muted); }
  .idle { color: var(--muted); font-size: 15px; }
  @media (max-width: 520px) {
    body { padding: 20px; }
    h1 { font-size: 22px; }
    .pair { grid-template-columns: 1fr; }
    .vs { justify-self: center; }
  }
</style>
</head>
<body>
  <div id="root"><p class="idle">Ready when you are.</p></div>

<script>
// Rendering lives in a classic script, deliberately separate from the module
// below: if the SDK fails to load, the card still renders anything handed to it
// rather than staying blank. It is also what lets the design be previewed
// without a host attached.
const root = document.getElementById("root");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function render(turn) {
  if (!turn) return;
  const parts = [];

  if (turn.question_number && turn.total_questions) {
    const pct = Math.round((turn.question_number - 1) / turn.total_questions * 100);
    parts.push(`<div class="progress">
        <div class="bar"><i style="width:${pct}%"></i></div>
        <div class="count">${turn.question_number} of ${turn.total_questions}</div>
      </div>`);
  }

  if (turn.verdict) {
    const label = { correct: "Correct", incorrect: "Not quite", unclear: "Didn't catch that" }[turn.verdict];
    const heard = turn.heard_as ? `<small>you said ${esc(turn.heard_as)}</small>` : "";
    parts.push(`<div class="verdict ${turn.verdict}">${label}${heard}</div>`);
  }

  if (turn.correct_answer) {
    parts.push(`<p class="answer">Answer: <b>${esc(turn.correct_answer)}</b></p>`);
  }

  if (turn.question) {
    parts.push(`<h1>${esc(turn.question)}</h1>`);
  }

  // A repeated confusion, shown as the two things being confused.
  if (Array.isArray(turn.contrast) && turn.contrast.length === 2) {
    const times = turn.confusion_count ? `Mixed up ${turn.confusion_count} times so far.` : "";
    parts.push(`<div class="contrast">
        <div class="contrast-label">Which one is it?</div>
        <div class="pair">
          <div>${esc(turn.contrast[0])}</div>
          <div class="vs">or</div>
          <div>${esc(turn.contrast[1])}</div>
        </div>
        <div class="note">${esc(times)}</div>
      </div>`);
  }

  root.innerHTML = parts.join("") || `<p class="idle">Ready when you are.</p>`;
}

window.renderTurn = render;
</script>

<script type="module">
import { App } from "https://cdn.jsdelivr.net/npm/@modelcontextprotocol/ext-apps@1.7.5/dist/src/app-with-deps.js";

const app = new App({ name: "Study Coach", version: "0.1.0" });

// Set before connect(), or the first result is missed.
app.ontoolresult = (result) => {
  try {
    window.renderTurn(result?.structuredContent ?? null);
  } catch (err) {
    document.getElementById("root").innerHTML =
      `<p class="idle">Keep going - the audio has you covered.</p>`;
  }
};

app.connect();
</script>
</body>
</html>
"""
