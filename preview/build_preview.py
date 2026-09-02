"""Render the real card into a preview page.

The card cannot be seen without an Alexa+ device, so this frames the actual
`ui.PRACTICE_HTML` - not a mock-up of it - in three states and drives it through
the same `renderTurn` entry point the host uses.
"""

import base64
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "server"))
import ui  # noqa: E402

STATES = [
    {
        "n": "01",
        "name": "Asking",
        "note": "Progress and the question. Nothing the voice already said is repeated on screen.",
        "height": 230,
        "turn": {
            "question_number": 1,
            "total_questions": 6,
            "question": "Which organelle releases energy from glucose?",
        },
    },
    {
        "n": "02",
        "name": "Naming what was heard",
        "note": "Not a red cross. The answer is attributed to a concept, so the screen can say which one was reached for.",
        "height": 330,
        "turn": {
            "question_number": 5,
            "total_questions": 6,
            "verdict": "incorrect",
            "heard_as": "The chloroplasts",
            "correct_answer": "The mitochondria",
            "question": "Which organelle captures light energy in a plant cell?",
        },
    },
    {
        "n": "03",
        "name": "Separating the confusion",
        "note": "The same mix-up, twice. Voice can only say the two names in sequence; the screen puts them next to each other.",
        "height": 430,
        "turn": {
            "question_number": 6,
            "total_questions": 6,
            "verdict": "incorrect",
            "heard_as": "The mitochondria",
            "question": "Which organelle captures light energy in a plant cell?",
            "contrast": ["the mitochondria", "the chloroplasts"],
            "confusion_count": 2,
        },
    },
]

# Base64 rather than escaping: the card contains </script> and template
# literals, and every textual escaping scheme for those is a trap.
CARD_B64 = base64.b64encode(ui.PRACTICE_HTML.encode("utf-8")).decode("ascii")

sections = "\n".join(
    f"""      <section class="state">
        <div class="meta">
          <p class="eyebrow">State {s['n']}</p>
          <h2>{s['name']}</h2>
          <p class="note">{s['note']}</p>
        </div>
        <div class="frame">
          <iframe title="{s['name']}" data-turn='{json.dumps(s['turn'])}'
                  style="height:{s['height']}px" loading="lazy"></iframe>
        </div>
      </section>"""
    for s in STATES
)

PAGE = f"""<title>Study Coach Card</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
  :root {{
    --ground: #eef1f5;
    --panel:  #ffffff;
    --ink:    #131820;
    --muted:  #5a6472;
    --line:   #d8dfe8;
    --accent: #2b5cd9;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --ground: #0d1117; --panel: #141b25; --ink: #e8edf4;
      --muted: #939fae; --line: #232d3b; --accent: #7ea2ff;
    }}
  }}
  :root[data-theme="dark"] {{
    --ground: #0d1117; --panel: #141b25; --ink: #e8edf4;
    --muted: #939fae; --line: #232d3b; --accent: #7ea2ff;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--ground); color: var(--ink);
    font-family: "IBM Plex Sans", system-ui, sans-serif;
    font-size: 16px; line-height: 1.6;
  }}
  .wrap {{ max-width: 1080px; margin: 0 auto; padding: 56px 28px 72px; }}
  header {{ border-bottom: 1px solid var(--line); padding-bottom: 28px; margin-bottom: 44px; }}
  .kicker {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 12px; letter-spacing: .12em; text-transform: uppercase;
    color: var(--accent); margin: 0 0 12px;
  }}
  h1 {{ font-size: 34px; line-height: 1.15; font-weight: 600; margin: 0 0 14px;
       letter-spacing: -.015em; text-wrap: balance; }}
  .lede {{ margin: 0; max-width: 62ch; color: var(--muted); font-size: 17px; }}
  .states {{ display: flex; flex-direction: column; gap: 44px; }}
  .state {{ display: grid; grid-template-columns: minmax(0, 22rem) minmax(0, 1fr);
            gap: 32px; align-items: start; }}
  .eyebrow {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 12px; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted); margin: 0 0 6px;
  }}
  .meta h2 {{ font-size: 20px; font-weight: 600; margin: 0 0 10px; letter-spacing: -.01em; }}
  .note {{ margin: 0; color: var(--muted); font-size: 15px; max-width: 40ch; }}
  .frame {{
    background: var(--panel); border: 1px solid var(--line);
    border-radius: 14px; padding: 10px; overflow: hidden;
    box-shadow: 0 1px 2px rgba(16, 24, 40, .05);
  }}
  iframe {{ width: 100%; border: 0; border-radius: 8px; display: block; background: transparent; }}
  footer {{ margin-top: 56px; padding-top: 24px; border-top: 1px solid var(--line);
            color: var(--muted); font-size: 14px; }}
  footer code {{ font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 13px;
                 color: var(--ink); }}
  @media (max-width: 800px) {{
    .state {{ grid-template-columns: 1fr; gap: 16px; }}
    .wrap {{ padding: 40px 20px 56px; }}
    h1 {{ font-size: 27px; }}
  }}
</style>

<div class="wrap">
  <header>
    <p class="kicker">Alexa+ add-on &middot; MCP Apps extension</p>
    <h1>What the student sees while the coach is talking</h1>
    <p class="lede">Three states of the card a display device renders during a revision session.
    These frames run the real <code>ui.PRACTICE_HTML</code> shipped by the server, driven through the
    same entry point the host uses &mdash; not a mock-up. The voice experience works identically
    without any of it.</p>
  </header>

  <div class="states">
{sections}
  </div>

  <footer>
    Bound to <code>ui://study-coach/practice.html</code>, served as
    <code>text/html;profile=mcp-app</code>. Only <code>start_practice</code> and
    <code>submit_answer</code> carry a UI; the other four tools are voice-only.
  </footer>
</div>

<script>
  // Base64 rather than textual escaping: the card contains </script> and
  // template literals, and every escaping scheme for those is a trap.
  const source = new TextDecoder().decode(
    Uint8Array.from(atob("{CARD_B64}"), (c) => c.charCodeAt(0))
  );
  for (const frame of document.querySelectorAll("iframe[data-turn]")) {{
    const turn = JSON.parse(frame.dataset.turn);
    frame.addEventListener("load", () => {{
      const win = frame.contentWindow;
      let tries = 0;
      const paint = () => {{
        if (win.renderTurn) {{ win.renderTurn(turn); return; }}
        if (tries++ < 40) setTimeout(paint, 25);
      }};
      paint();
    }});
    frame.srcdoc = source;
  }}
</script>
"""

out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "preview.html")
out.write_text(PAGE, encoding="utf-8")
print(f"geschreven: {out}  ({len(PAGE)} tekens)")
