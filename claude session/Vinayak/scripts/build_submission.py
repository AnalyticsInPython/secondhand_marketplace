#!/usr/bin/env python3
"""Submittable transcripts of the LionsList development sessions (Aug 31 2026 onward).

Conversation only: the prompts given and the assistant's written replies.
Tool calls, shell output and file contents are removed.

    python3 build_submission.py [outdir]
"""
import os, re, sys, glob, importlib.util, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bc", os.path.join(HERE, "build_clean.py"))
bc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bc)
OUT = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Desktop/chat-exports")

# The development arc, in order. Each entry: (start-timestamps, tool, title, note)
ARC = [
 (["2026-09-01T17:29"], "Claude Code", "Critical analysis, SRS and architecture",
  "The proposal reviewed as product manager and systems architect; produced srs.md and architecture.md."),
 (["2026-09-01T18:02"], "Codex", "Reading the proposal, explaining the open decisions",
  "The product spec read back in plain language, with the outstanding team decisions surfaced."),
 (["2026-09-01T18:20"], "Codex", "Revising the scope to a Python backend",
  "The spec challenged on its stack choice and rewritten around a Python API and Python analytics, producing LionsList-Product-Spec-Python-API-and-Analytics.pdf."),
 (["2026-09-01T18:10"], "Claude Code", "First MVP attempt from the updated spec",
  "The revised scope taken as the build input."),
 (["2026-09-01T19:36", "2026-09-01T21:19"], "Codex", "MVP build and sign-in debugging",
  "A Next.js/Drizzle MVP scaffolded at ~/Documents/Codex/2026-09-01/.../lionslist-mvp, then email sign-in troubleshooting."),
 (["2026-09-02T21:23"], "Claude Code", "Python backend built, tested and pushed",
  "The FastAPI backend, schema, ZIP/distance service, facet counts and Columbia-domain auth; merged to main."),
 (["2026-09-03T20:22"], "Claude Code", "Pull, run locally, audit dashboard and search",
  "Latest main pulled and reseeded, MVP verified on localhost, analytics and search reviewed."),
]

def main():
    found = {}
    for tool, f, msgs, proj in bc.harvest():
        start = next((t for _, t, _ in msgs if t), "")
        if start[:16]: found.setdefault(start[:16], []).append((tool, f, msgs, proj))

    dest = os.path.join(OUT, "lionslist-sessions"); os.makedirs(dest, exist_ok=True)
    built = []
    for i, (stamps, tool, title, note) in enumerate(ARC, 1):
        parts = []
        for st in stamps:
            for t, f, msgs, proj in found.get(st, []):
                if t == tool: parts.append((st, msgs, proj))
        if not parts: continue
        parts.sort(key=lambda p: p[0])
        msgs = [m for _, ms, _ in parts for m in ms]
        proj = parts[0][2]
        n_u = sum(1 for r, _, _ in msgs if r == "user")
        n_a = sum(1 for r, _, _ in msgs if r == "assistant")
        day = parts[0][0][:10]
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:44]
        fn = f"{i:02d}_{day}_{slug}.md"
        with open(os.path.join(dest, fn), "w") as w:
            w.write(f"# {i}. {title}\n\n")
            w.write(f"**Tool:** {tool}  \n**Date:** {day}  \n")
            w.write(f"**Exchanges:** {n_u} prompts, {n_a} replies  \n")
            w.write(f"**Working folder:** `{proj}`\n\n")
            w.write(f"{note}\n\n")
            if len(parts) > 1:
                w.write(f"*Continued across {len(parts)} threads in the same working folder; joined here in order.*\n\n")
            w.write("---\n\n")
            for role, ts, body in msgs:
                w.write(f"### {'Prompt' if role == 'user' else tool} · {ts[11:16]}\n\n{body}\n\n")
        built.append({"i": i, "file": fn, "title": title, "tool": tool, "day": day,
                      "n_u": n_u, "n_a": n_a, "note": note})

    with open(os.path.join(dest, "README.md"), "w") as w:
        w.write("# LionsList — development session transcripts\n\n")
        w.write("AI-assisted development of the LionsList / Columbia Market marketplace, "
                "from proposal review through to a running MVP.\n\n")
        w.write(f"- **Sessions:** {len(built)} across two tools (Claude Code, Codex)\n")
        w.write(f"- **Period:** {built[0]['day']} to {built[-1]['day']}\n")
        w.write(f"- **Exchanges:** {sum(b['n_u'] for b in built)} prompts, {sum(b['n_a'] for b in built)} replies\n")
        w.write(f"- **Compiled:** {datetime.date.today()}\n\n")
        w.write("Each file contains the conversation only — the prompts given and the written "
                "replies received. Tool calls, shell output and file contents are omitted.\n\n")
        w.write("| # | Date | Tool | Session | Prompts |\n|---|---|---|---|---:|\n")
        for b in built:
            w.write(f"| {b['i']} | {b['day']} | {b['tool']} | [{b['title']}]({b['file'].replace(' ','%20')}) | {b['n_u']} |\n")
        w.write("\n## What each session covers\n\n")
        for b in built:
            w.write(f"**{b['i']}. {b['title']}** — {b['note']}\n\n")
    return built, dest

if __name__ == "__main__":
    built, dest = main()
    for b in built:
        print(f"{b['i']}. {b['day']} {b['tool']:<11} {b['n_u']:>2}p/{b['n_a']:>2}r  {b['file']}")
    print(f"\n{len(built)} sessions -> {dest}")
