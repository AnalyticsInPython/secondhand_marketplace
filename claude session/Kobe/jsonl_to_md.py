"""Convert a Claude Code session transcript (.jsonl) into a readable Markdown document.

The raw log is a line-per-event stream that mixes conversation turns with a lot of
housekeeping: mode switches, token reminders, file-history snapshots, and base64
screenshots. This keeps the conversation and drops the rest.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys

# Event kinds that carry no conversation -- session bookkeeping only.
SKIP_TYPES = {
    "mode", "permission-mode", "atis-latch", "bridge-session", "ai-title",
    "last-prompt", "frame-link", "pr-link", "file-history-snapshot",
    "file-history-delta", "queue-operation", "artifact-comment-monitor",
    "artifact-autoreact-ledger", "attachment", "system",
}

TOOL_INPUT_LIMIT = 2500
TOOL_RESULT_LIMIT = 2500
THINKING_LIMIT = 6000

# System-injected blocks that arrive inside user messages but were never typed.
REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
B64_RE = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")


def clean(text: str) -> str:
    text = REMINDER_RE.sub("", text)
    text = B64_RE.sub("[binary data omitted]", text)
    return text.strip()


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    kept = text[:limit].rstrip()
    return "%s\n… [%s more characters]" % (kept, format(len(text) - limit, ","))


def fence(text: str, lang: str = "") -> str:
    """Fence a block, widening the fence if the body contains one of its own."""
    ticks = "```"
    while ticks in text:
        ticks += "`"
    return "%s%s\n%s\n%s" % (ticks, lang, text, ticks)


def flatten(content) -> str:
    """Tool results arrive as a string, or as a list of text/image blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                parts.append(str(block))
            elif block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "image":
                parts.append("[image]")
            else:
                parts.append("[%s]" % block.get("type"))
        return "\n".join(parts)
    return "" if content is None else str(content)


def stamp(raw: str) -> str:
    try:
        when = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return when.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw


def summarise(body: str, width: int = 96) -> str:
    """First line of a prompt, squeezed onto one line for the index."""
    line = " ".join(body.split())
    line = line.replace("[", "(").replace("]", ")")
    return line if len(line) <= width else line[:width].rstrip() + "…"


def convert(path: str, out_path: str) -> dict:
    events = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            events.append(json.loads(line))

    # Tool results are attached to the *following* user event; index them by the
    # id of the call they answer so each one renders beside its own tool_use.
    results: "dict[str, dict]" = {}
    for event in events:
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                results[block.get("tool_use_id")] = block

    out = []
    index: "list[str]" = []
    counts = {"user": 0, "assistant": 0, "tools": 0, "thinking": 0}
    first_ts = last_ts = None

    for event in events:
        kind = event.get("type")
        if kind in SKIP_TYPES:
            continue
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        ts = event.get("timestamp")
        if ts:
            first_ts = first_ts or ts
            last_ts = ts

        content = message.get("content")
        sidechain = " · subagent" if event.get("isSidechain") else ""

        if kind == "user":
            if isinstance(content, str):
                if (event.get("origin") or {}).get("kind") != "human":
                    continue
                body = clean(content)
                if not body:
                    continue
                counts["user"] += 1
                index.append("%d. [%s](#p%d)" % (
                    counts["user"], summarise(body), counts["user"]))
                out.append("\n---\n")
                out.append('<a id="p%d"></a>\n' % counts["user"])
                out.append("## %d. Kobe — %s%s\n" % (counts["user"], stamp(ts), sidechain))
                out.append(body + "\n")
            else:
                # A list-form user event is the tool-result carrier (already
                # indexed and rendered under its own tool call) or an injected
                # skill body. Only an interruption is worth surfacing.
                for block in content or []:
                    if not isinstance(block, dict) or block.get("type") != "text":
                        continue
                    body = clean(block.get("text", ""))
                    if body.lower().startswith(("[request interrupted",
                                                "(request interrupted")):
                        out.append("\n_%s_\n" % body)
            continue

        if kind != "assistant" or not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")

            if btype == "text":
                body = clean(block.get("text", ""))
                if body:
                    counts["assistant"] += 1
                    out.append("\n**Claude:**\n\n" + body + "\n")

            elif btype == "tool_use":
                counts["tools"] += 1
                name = block.get("name", "?")
                args = block.get("input") or {}
                out.append("\n> **`%s`**\n" % name)

                # Bash and the file tools read far better as their own payload
                # than as a JSON blob.
                if name == "Bash" and "command" in args:
                    if args.get("description"):
                        out.append("> %s\n" % args["description"])
                    out.append(fence(clip(str(args["command"]), TOOL_INPUT_LIMIT), "bash") + "\n")
                elif name in ("Read", "Edit", "Write") and "file_path" in args:
                    out.append("> `%s`\n" % args["file_path"])
                    for key in ("old_string", "new_string", "content"):
                        if key in args:
                            out.append("> _%s_\n" % key)
                            out.append(fence(clip(str(args[key]), TOOL_INPUT_LIMIT)) + "\n")
                else:
                    dumped = json.dumps(args, indent=2, ensure_ascii=False)
                    out.append(fence(clip(clean(dumped), TOOL_INPUT_LIMIT), "json") + "\n")

                result = results.get(block.get("id"))
                if result is not None:
                    text = clip(clean(flatten(result.get("content"))), TOOL_RESULT_LIMIT)
                    label = "error" if result.get("is_error") else "result"
                    if text:
                        out.append("<details><summary>%s</summary>\n\n" % label)
                        out.append(fence(text) + "\n")
                        out.append("\n</details>\n")

    header = [
        "# Columbia Market — Claude Code session transcript\n",
        "**Kobe (kwonil0131@gmail.com)** · ENGI 4503 Analytics in Python · data component\n",
        "",
        "| | |",
        "|---|---|",
        "| Session | `%s` |" % events[0].get("sessionId", "?"),
        "| Started | %s |" % stamp(first_ts or ""),
        "| Ended | %s |" % stamp(last_ts or ""),
        "| Prompts from me | %d |" % counts["user"],
        "| Replies from Claude | %d |" % counts["assistant"],
        "| Tool calls | %d |" % counts["tools"],
        "",
        "Converted from the raw `.jsonl` session log. Session bookkeeping, token",
        "reminders and base64 screenshot payloads are dropped; long tool inputs and",
        "outputs are truncated with the omitted length noted. Claude's internal",
        "reasoning is not stored in the local log and so does not appear here.\n",
        "\n## What I asked, in order\n",
        *index,
        "",
    ]

    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(header))
        handle.write("\n".join(out))
        handle.write("\n")
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("dest")
    args = parser.parse_args()
    print(convert(args.source, args.dest), file=sys.stderr)
