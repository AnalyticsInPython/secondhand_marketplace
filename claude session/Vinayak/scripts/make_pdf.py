#!/usr/bin/env python3
"""Stitch the LionsList session transcripts into one submittable PDF."""
import os, re, sys, glob, datetime, markdown
from weasyprint import HTML

SRC = os.path.expanduser(os.environ.get("TRANSCRIPT_DIR",
                         "~/Desktop/chat-exports/lionslist-sessions"))
OUT = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else
                         "~/Desktop/chat-exports/LionsList-Development-Transcripts.pdf")

CSS = """
@page {
  size: A4; margin: 20mm 18mm 18mm 18mm;
  @top-left  { content: "LionsList — Development Session Transcripts";
               font: 8pt "Helvetica Neue", sans-serif; color: #8a8f98; }
  @bottom-right { content: counter(page) " / " counter(pages);
               font: 8pt "Helvetica Neue", sans-serif; color: #8a8f98; }
}
@page :first { @top-left { content: none } @bottom-right { content: none } }
@page cover  { margin: 0 }

body { font: 10pt/1.55 "Charter","Georgia",serif; color: #1a1d21; }
h1,h2,h3,h4 { font-family: "Helvetica Neue",sans-serif; color: #10131a; page-break-after: avoid; }

/* ---- cover */
.cover { page: cover; height: 297mm; display: flex; flex-direction: column;
         justify-content: center; padding: 0 26mm; page-break-after: always; }
.cover .rule { width: 46mm; height: 3px; background: #1f4788; margin-bottom: 11mm; }
.cover h1 { font-size: 30pt; line-height: 1.15; margin: 0 0 5mm; letter-spacing: -.4pt; }
.cover .sub { font-size: 12.5pt; color: #4a5058; margin: 0 0 16mm; font-family: "Charter",serif; }
.cover dl { margin: 0; font-family: "Helvetica Neue",sans-serif; font-size: 9.5pt; }
.cover dt { color: #8a8f98; text-transform: uppercase; letter-spacing: .8pt;
            font-size: 7.5pt; margin-top: 5mm; }
.cover dd { margin: 1mm 0 0; color: #1a1d21; }
.cover .foot { position: absolute; bottom: 24mm; left: 26mm; right: 26mm;
               font: 8.5pt "Helvetica Neue",sans-serif; color: #8a8f98;
               border-top: 1px solid #e3e6ea; padding-top: 4mm; }

/* ---- contents */
.toc { page-break-after: always; }
.toc h2 { font-size: 15pt; margin: 0 0 7mm; padding-bottom: 3mm;
          border-bottom: 2px solid #1f4788; }
.toc table { width: 100%; border-collapse: collapse; font-size: 9.5pt;
             font-family: "Helvetica Neue",sans-serif; }
.toc td { padding: 2.6mm 2mm; border-bottom: 1px solid #eef0f3; vertical-align: top; }
.toc .n { color: #1f4788; font-weight: 600; width: 8mm; }
.toc .t { font-weight: 600; color: #10131a; }
.toc .d { color: #6b727c; font-size: 8.5pt; }
.toc .tool { color: #6b727c; font-size: 8pt; white-space: nowrap; text-align: right; }
.toc .note { color: #6b727c; font-size: 8.5pt; font-family: "Charter",serif;
             padding-top: 0; padding-bottom: 3mm; border-bottom: 1px solid #eef0f3; }

/* ---- sessions */
.session { page-break-before: always; }
.session > h1 { font-size: 17pt; margin: 0 0 2mm; letter-spacing: -.2pt; }
.meta { font: 8.5pt "Helvetica Neue",sans-serif; color: #6b727c;
        border-bottom: 2px solid #1f4788; padding-bottom: 4mm; margin-bottom: 5mm; }
.meta b { color: #1a1d21; font-weight: 600; }
.blurb { font-size: 9.5pt; color: #4a5058; font-style: italic; margin: 0 0 7mm; }

.turn { margin: 0 0 5mm; orphans: 3; widows: 3; }
.turn .who { page-break-after: avoid; }
.turn.user { background: #f5f7fa; border-left: 3px solid #1f4788;
             padding: 3.5mm 5mm; border-radius: 0 3px 3px 0; }
.turn .who { font: 600 7.5pt "Helvetica Neue",sans-serif; text-transform: uppercase;
             letter-spacing: 1pt; color: #1f4788; margin: 0 0 2mm; }
.turn.asst .who { color: #8a8f98; }
.turn p { margin: 0 0 2.5mm; }
.turn.asst { padding-left: 5mm; }

code { font: 8.5pt "SF Mono","Menlo",monospace; background: #f2f4f7;
       padding: .3mm 1mm; border-radius: 2px; }
pre { background: #f7f9fb; border: 1px solid #e3e6ea; border-radius: 3px;
      padding: 3mm 4mm; overflow-wrap: break-word; white-space: pre-wrap;
      font: 8pt/1.45 "SF Mono","Menlo",monospace; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8pt; }
blockquote { border-left: 2px solid #d5dae1; margin: 0 0 3mm; padding: 0 0 0 4mm; color: #4a5058; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; margin: 0 0 3mm; }
th,td { border: 1px solid #e3e6ea; padding: 1.6mm 2.4mm; text-align: left; }
th { background: #f2f4f7; font-family: "Helvetica Neue",sans-serif; font-weight: 600; }
ul,ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin-bottom: 1mm; }
a { color: #1f4788; text-decoration: none; }
h2 { font-size: 12pt; margin: 6mm 0 2.5mm; }
h3 { font-size: 10.5pt; margin: 5mm 0 2mm; }
hr { border: none; border-top: 1px solid #e3e6ea; margin: 5mm 0; }
"""

def folder(raw):
    """Turn a stored project key back into a path a reader recognises."""
    f = raw.strip().strip("`")
    if f.startswith("-Users-vinayak"):
        return "~" + f[len("-Users-vinayak"):].replace("-", "/")
    return f

md = markdown.Markdown(extensions=["extra", "sane_lists", "nl2br"])

def render(text):
    md.reset(); return md.convert(text)

def parse(path):
    raw = open(path).read()
    title = re.search(r"^#\s*\d*\.?\s*(.+)$", raw, re.M).group(1).strip()
    meta = dict(re.findall(r"\*\*(\w[\w ]*?):\*\*\s*([^\n]+?)\s{0,2}$", raw, re.M))
    body = raw.split("---\n", 1)[1] if "---\n" in raw else raw
    blurb = ""
    m = re.search(r"`\n\n(.+?)\n\n(?:\*|---)", raw, re.S)
    if m: blurb = " ".join(m.group(1).split())
    turns = []
    # Only a heading of the exact shape "### <Speaker> · HH:MM" starts a turn.
    # Replies contain their own "### " headings; those must stay inside the turn.
    TURN = r"^### (?:Prompt|Claude Code|Codex) · \d\d:\d\d$"
    for m in re.finditer(r"^### (Prompt|Claude Code|Codex) · (\d\d:\d\d)$\n+(.*?)"
                         r"(?=" + TURN + r"|\Z)", body, re.S | re.M):
        who, time, content = m.group(1), m.group(2), m.group(3)
        content = content.strip()
        if content: turns.append((who.strip(), time, content))
    return {"title": title, "meta": meta, "blurb": blurb, "turns": turns}

def main():
    files = sorted(f for f in glob.glob(os.path.join(SRC, "*.md"))
                   if not f.endswith("README.md"))
    sessions = [parse(f) for f in files]
    total_p = sum(sum(1 for w, _, _ in s["turns"] if w == "Prompt") for s in sessions)
    total_r = sum(len(s["turns"]) for s in sessions) - total_p
    days = sorted({s["meta"].get("Date", "") for s in sessions if s["meta"].get("Date")})

    h = ['<meta charset="utf-8">']
    # cover
    h.append(f'''<div class="cover"><div class="rule"></div>
      <h1>LionsList<br>Development Session Transcripts</h1>
      <p class="sub">AI-assisted development of a university marketplace,
         from proposal review to a running MVP.</p>
      <dl>
        <dt>Prepared by</dt><dd>Vinayak Raju</dd>
        <dt>Repository</dt><dd>AnalyticsInPython / secondhand_marketplace</dd>
        <dt>Period</dt><dd>{days[0]} to {days[-1]}</dd>
        <dt>Sessions</dt><dd>{len(sessions)} across two tools — Claude Code and Codex</dd>
        <dt>Exchanges</dt><dd>{total_p} prompts, {total_r} replies</dd>
      </dl>
      <div class="foot">Conversation only. Tool calls, shell output and file contents
        have been removed. Compiled {datetime.date.today():%d %B %Y}.</div></div>''')
    # contents
    h.append('<div class="toc"><h2>Contents</h2><table>')
    for i, s in enumerate(sessions, 1):
        n_p = sum(1 for w, _, _ in s["turns"] if w == "Prompt")
        h.append(f'<tr><td class="n">{i}</td><td class="t">{s["title"]}'
                 f'<div class="d">{s["meta"].get("Date","")} · {n_p} prompts</div></td>'
                 f'<td class="tool">{s["meta"].get("Tool","")}</td></tr>')
        if s["blurb"]:
            h.append(f'<tr><td></td><td class="note" colspan="2">{s["blurb"]}</td></tr>')
    h.append('</table></div>')
    # sessions
    for i, s in enumerate(sessions, 1):
        m = s["meta"]
        h.append(f'<div class="session"><h1>{i}. {s["title"]}</h1>'
                 f'<div class="meta"><b>{m.get("Tool","")}</b> &nbsp;·&nbsp; {m.get("Date","")}'
                 f' &nbsp;·&nbsp; {m.get("Exchanges","")}'
                 f' &nbsp;·&nbsp; working folder <code>{folder(m.get("Working folder",""))}</code></div>')
        if s["blurb"]: h.append(f'<p class="blurb">{s["blurb"]}</p>')
        for who, time, content in s["turns"]:
            cls = "user" if who == "Prompt" else "asst"
            label = "Prompt" if who == "Prompt" else who
            h.append(f'<div class="turn {cls}"><p class="who">{label} · {time}</p>'
                     f'{render(content)}</div>')
        h.append('</div>')

    html = "<html><body>" + "".join(h) + "</body></html>"
    HTML(string=html, base_url=SRC).write_pdf(OUT, stylesheets=[__import__("weasyprint").CSS(string=CSS)])
    print(f"{len(sessions)} sessions, {total_p} prompts -> {OUT}")

if __name__ == "__main__":
    main()
