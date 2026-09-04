"""Build a readable Markdown transcript from Claude Code session logs.

Adapted from `claude session/Kobe/jsonl_to_md.py`, which does the same job.
Three things differ, all forced by this machine's logs rather than by taste:

1.  **Prompt detection.** Kobe's version reads a typed prompt as a user event
    whose `content` is a plain string tagged `origin.kind == "human"`. These
    logs record prompts as *block lists* with no `origin` key at all, so that
    test dropped every prompt and produced a transcript of the agent talking to
    nobody. Here a user event is a prompt when it carries a text block that is
    neither a tool result nor an injected `<system-reminder>`.

2.  **Several logs, one transcript.** The group-project work spans three
    sessions; they are concatenated in the order given, with prompt numbering
    running continuously.

3.  **Redaction.** These sessions ran with the working directory set to the home
    folder rather than the repo, so some commands listed directories and
    processes outside the project. That output named unrelated coursework, a
    personal file or two, and an email address. `REDACTIONS` removes them. It is
    a deliberate edit, not a filter: nothing about the project's own work is
    touched.

    python jsonl_to_md.py OUT.md LOG.jsonl [LOG.jsonl ...] [--stop-at TEXT]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys

SPEAKER = "Jae"

SKIP_TYPES = {
    "mode", "permission-mode", "atis-latch", "bridge-session", "ai-title",
    "last-prompt", "frame-link", "pr-link", "file-history-snapshot",
    "file-history-delta", "queue-operation", "artifact-comment-monitor",
    "artifact-autoreact-ledger", "attachment", "system",
}

TOOL_INPUT_LIMIT = 2500
TOOL_RESULT_LIMIT = 2500

REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
B64_RE = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")

# Applied to every rendered line. Order matters: paths before names.
REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+billy", re.I), "~"),
    (re.compile(r"/c/Users/billy", re.I), "~"),
    (re.compile(r"C--Users-billy[\w-]*"), "~"),
    (re.compile(r"[\w.+-]+@gmail\.com", re.I), "<email redacted>"),
    (re.compile(r"Resume_Jaewon[^\"'\s]*", re.I), "[unrelated file]"),
    (re.compile(r"MANAGERIAL_STATS_WORKBOOK\.xlsx", re.I), "[unrelated file]"),
    (re.compile(r"회사비용처리"), "[unrelated folder]"),
    (re.compile(r"Wordcraft", re.I), "[unrelated project]"),
    (re.compile(r"Python_Bootcamp", re.I), "[unrelated folder]"),
    (re.compile(r"\b26_FA\b"), "[unrelated folder]"),
]


def redact(text: str) -> str:
    for pattern, repl in REDACTIONS:
        text = pattern.sub(repl, text)
    return text


def clean(text: str) -> str:
    text = REMINDER_RE.sub("", text)
    text = B64_RE.sub("[binary data omitted]", text)
    return redact(text).strip()


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n… [%d more characters omitted]" % (len(text) - limit)


def stamp(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%d %b %H:%M")
    except ValueError:
        return ts[:16]


def summarise(text: str, width: int = 72) -> str:
    one = " ".join(text.split())
    return one if len(one) <= width else one[: width - 1] + "…"


def prompt_text(content) -> str | None:
    """The typed text of a user event, or None if it is not a typed prompt."""
    if isinstance(content, str):
        return clean(content) or None
    if not isinstance(content, list):
        return None
    if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return None
    parts = [
        clean(b.get("text", ""))
        for b in content
        if isinstance(b, dict) and b.get("type") == "text"
    ]
    body = "\n\n".join(p for p in parts if p)
    return body or None


def load(path: str) -> list[dict]:
    events = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dest")
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--stop-at", default=None,
                    help="Truncate at the first prompt containing this text.")
    a = ap.parse_args()

    out: list[str] = []
    index: list[str] = []
    counts = {"prompts": 0, "replies": 0, "tools": 0}
    first_ts = last_ts = None
    stopped = None

    for source in a.sources:
        events = load(source)

        # Tool results ride on the following user event; index them so each can
        # be folded under the call that produced it.
        results: dict[str, str] = {}
        for e in events:
            content = (e.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    raw = b.get("content")
                    if isinstance(raw, list):
                        raw = "\n".join(x.get("text", "") for x in raw if isinstance(x, dict))
                    results[b.get("tool_use_id", "")] = clean(str(raw or ""))

        for e in events:
            if e.get("type") in SKIP_TYPES:
                continue
            message = e.get("message") or {}
            role = message.get("role")
            ts = e.get("timestamp")
            content = message.get("content")

            if role == "user":
                if (e.get("origin") or {}).get("kind") == "task-notification":
                    continue
                body = prompt_text(content)
                if not body:
                    continue
                if a.stop_at and a.stop_at.lower() in body.lower():
                    stopped = counts["prompts"] + 1
                    break
                if ts:
                    first_ts = first_ts or ts
                    last_ts = ts
                counts["prompts"] += 1
                n = counts["prompts"]
                index.append("%d. [%s](#p%d)" % (n, summarise(body), n))
                out.append("\n---\n")
                out.append('<a id="p%d"></a>\n' % n)
                out.append("## %d. %s — %s\n" % (n, SPEAKER, stamp(ts)))
                out.append(body + "\n")

            elif role == "assistant":
                if not isinstance(content, list):
                    continue
                if ts:
                    last_ts = ts
                said = False
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text":
                        body = clean(b.get("text", ""))
                        if body:
                            if not said:
                                counts["replies"] += 1
                                said = True
                            out.append("\n**Claude —** " + body + "\n")
                    elif b.get("type") == "tool_use":
                        counts["tools"] += 1
                        args = json.dumps(b.get("input", {}), indent=2, ensure_ascii=False)
                        out.append("\n> **%s**\n\n```json\n%s\n```\n" % (
                            b.get("name", "?"), clip(redact(args), TOOL_INPUT_LIMIT)))
                        res = results.get(b.get("id", ""))
                        if res:
                            out.append(
                                "<details><summary>result</summary>\n\n```\n%s\n```\n"
                                "</details>\n" % clip(res, TOOL_RESULT_LIMIT))
        if stopped:
            break

    head = [
        "# Claude Code session — %s" % SPEAKER,
        "",
        "Columbia Market. Built from the session logs with",
        "`scripts/jsonl_to_md.py`; the raw `.jsonl` files are not committed.",
        "",
        "| | |",
        "|---|---|",
        "| Span | %s → %s |" % (stamp(first_ts), stamp(last_ts)),
        "| Prompts from me | %d |" % counts["prompts"],
        "| Claude replies | %d |" % counts["replies"],
        "| Tool calls | %d |" % counts["tools"],
        "",
        "Local paths, an email address and directory listings that reached",
        "outside this project have been redacted; see `REDACTIONS` in the script.",
        "The transcript ends where the project work ended — the coursework",
        "write-ups that followed are not part of it.",
        "",
        "## What I asked, in order",
        "",
    ] + index + [""]

    with open(a.dest, "w", encoding="utf-8") as fh:
        fh.write("\n".join(head))
        fh.write("".join(out))

    print(counts, "stopped at prompt %s" % stopped, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
