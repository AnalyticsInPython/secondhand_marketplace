#!/usr/bin/env python3
"""Clean, submittable transcripts of the LionsList / marketplace sessions.

Keeps the conversation only — your prompts and the assistant's written replies.
Tool calls, command output and file contents are dropped.

    python3 build_clean.py [outdir]
"""
import json, os, re, sys, glob, datetime

OUT   = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Desktop/chat-exports")
SINCE = "2026-08-31"
KEEP  = re.compile(r"lionslist|lionlist|marketplace|secondhand_marketplace|columbia market|"
                   r"market\s?place|srs|product-spec", re.I)

NOISE_PREFIX = ("<system-reminder", "<ide_opened_file", "<local-command", "<command-name",
                "<task-notification", "<ci-monitor-event", "Base directory for this skill:",
                "<recommended_plugins", "<app-context", "<environment_context",
                "<user_instructions", "<in-app-browser-context", "<external_codex",
                "The following is the Codex agent history", "Caveat:")

def clean(t):
    """Strip machinery from a message, keep what a person wrote."""
    if not t: return ""
    t = re.sub(r"<system-reminder>.*?</system-reminder>", " ", t, flags=re.S)
    t = re.sub(r"<ide_opened_file>.*?</ide_opened_file>", " ", t, flags=re.S)
    t = re.sub(r"<local-command-[a-z]+>.*?</local-command-[a-z]+>", " ", t, flags=re.S)
    t = re.sub(r"<command-(name|message|args)>.*?</command-\1>", " ", t, flags=re.S)
    t = re.sub(r"<in-app-browser-context.*?</in-app-browser-context>", " ", t, flags=re.S)
    # Codex file-attachment preamble: keep the request, note the attachment
    m = re.search(r"##\s*My request:\s*(.*)", t, flags=re.S)
    if m:
        files = re.findall(r"##\s*([^:\n]+\.(?:pdf|docx|png|csv|txt))\s*:", t)
        t = (("*[attached: " + ", ".join(dict.fromkeys(files)) + "]*\n\n") if files else "") + m.group(1)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def claude_msgs(f):
    for line in open(f, errors="ignore"):
        try: d = json.loads(line)
        except: continue
        if d.get("type") not in ("user", "assistant"): continue
        # isMeta marks harness-injected content (skill bodies, hook output) that arrives
        # as a user turn but was never typed by anyone; isSidechain marks subagent traffic.
        if d.get("isMeta") or d.get("isSidechain"): continue
        c = (d.get("message") or {}).get("content")
        if isinstance(c, list):
            c = "\n".join(p.get("text", "") for p in c
                          if isinstance(p, dict) and p.get("type") == "text")
        if not isinstance(c, str): continue
        body = clean(c)
        if body and not body.startswith(NOISE_PREFIX):
            yield d["type"], d.get("timestamp", ""), body

def codex_msgs(f):
    for line in open(f, errors="ignore"):
        try: d = json.loads(line)
        except: continue
        p = d.get("payload") or {}
        if d.get("type") != "response_item" or p.get("type") != "message": continue
        role = p.get("role")
        if role not in ("user", "assistant"): continue
        raw = "\n".join(c.get("text", "") for c in (p.get("content") or [])
                         if isinstance(c, dict)).lstrip()
        if raw.startswith(NOISE_PREFIX): continue
        body = clean(raw)
        if body:
            yield role, d.get("timestamp", ""), body

def harvest():
    out = []
    for f in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
        msgs = list(claude_msgs(f))
        if msgs: out.append(("Claude Code", f, msgs, os.path.basename(os.path.dirname(f))))
    for f in glob.glob(os.path.expanduser("~/.codex/sessions/*/*/*/*.jsonl")):
        msgs = list(codex_msgs(f))
        cwd = "?"
        for line in open(f, errors="ignore"):
            try: d = json.loads(line)
            except: continue
            if d.get("type") == "session_meta":
                cwd = os.path.basename((d["payload"].get("cwd") or "?")); break
        # Codex approval/assessor threads replay the agent transcript as a user turn.
        # A real prompt is something a person typed; 5k characters of it is not.
        if any(r == "user" and len(b) > 5000 for r, _, b in msgs): continue
        if msgs: out.append(("Codex", f, msgs, cwd))
    return out

def main():
    sessions = []
    for tool, f, msgs, proj in harvest():
        start = next((t for _, t, _ in msgs if t), "")
        if start[:10] < SINCE: continue
        prompts = "\n".join(b for r, _, b in msgs if r == "user")
        blob = prompts + " " + " ".join(b[:2000] for r, _, b in msgs if r == "assistant")
        hits = len(KEEP.findall(blob))
        if hits < 3: continue
        sessions.append({"tool": tool, "file": f, "msgs": msgs, "project": proj,
                         "start": start, "end": max((t for _, t, _ in msgs if t), default=""),
                         "hits": hits,
                         "n_user": sum(1 for r, _, _ in msgs if r == "user"),
                         "n_asst": sum(1 for r, _, _ in msgs if r == "assistant"),
                         "opening": next((b for r, _, b in msgs if r == "user"), "")})
    sessions.sort(key=lambda s: s["start"])

    dest = os.path.join(OUT, "lionslist-sessions")
    os.makedirs(dest, exist_ok=True)
    for i, s in enumerate(sessions, 1):
        day = s["start"][:10]; hhmm = s["start"][11:16].replace(":", "")
        words = [w for w in re.findall(r"[a-z0-9]+", s["opening"].lower())
                 if len(w) > 3 and w not in ("this","that","with","from","have","into","give","make","need","want","https","github","com")][:5]
        fn = f"{i:02d}_{day}_{hhmm}_{s['tool'].split()[0].lower()}_{'-'.join(words)[:45]}.md"
        s["export"] = fn
        with open(os.path.join(dest, fn), "w") as w:
            w.write(f"# Session {i} — {s['tool']}\n\n")
            w.write(f"**Date:** {s['start'][:10]} · **Time:** {s['start'][11:16]}–{s['end'][11:16]}  \n")
            w.write(f"**Exchanges:** {s['n_user']} prompts, {s['n_asst']} replies  \n")
            w.write(f"**Working folder:** `{s['project']}`\n\n")
            w.write("> Conversation only — tool calls, command output and file contents removed.\n\n---\n\n")
            for role, ts, body in s["msgs"]:
                who = "Vinayak" if role == "user" else s["tool"]
                w.write(f"### {who} · {ts[11:16]}\n\n{body}\n\n")
    return sessions, dest

if __name__ == "__main__":
    ss, dest = main()
    for i, s in enumerate(ss, 1):
        print(f"{i:2d}. {s['start'][:16]}  {s['tool']:<11} {s['n_user']:>3}p/{s['n_asst']:>3}r  hits={s['hits']:<4} {s['export']}")
    print(f"\n{len(ss)} sessions -> {dest}")
