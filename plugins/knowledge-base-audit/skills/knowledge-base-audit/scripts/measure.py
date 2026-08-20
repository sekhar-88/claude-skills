#!/usr/bin/env python3
"""Measure a project's agent knowledge base.

Gathers the facts an audit needs: what gets loaded every turn, how dense it is,
where the project has actually been active versus what the docs foreground,
what's duplicated, and what's broken.

Measurement only — it never writes to the files it inspects.

Usage:
    python3 measure.py [project_dir] [--json] [--commits N]
"""

import json
import os
import re
import subprocess
import sys
from collections import Counter

TOK = 4  # bytes per token, rough but consistent

RULE_RE = re.compile(r"\b(never|Never|NEVER|must|MUST|always|ALWAYS|don't|Don't|DON'T)\b")
LINK_RE = re.compile(r"\]\((?!https?:|#|mailto:)([^)]+)\)")
CODEREF_RE = re.compile(r"`([A-Za-z0-9_./-]+\.(?:js|ts|py|rb|go|java|json))`")
WIKI_RE = re.compile(r"\[\[([^\]]+)\]\]")


def sh(args, cwd):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def discover(root):
    """Locate the knowledge-base files. Absent ones are simply skipped."""
    found = {"root": root}
    for key, names in {
        "claude_md": ["CLAUDE.md"],
        "agents_md": ["AGENTS.md"],
        "readme": ["README.md"],
    }.items():
        for n in names:
            p = os.path.join(root, n)
            if os.path.isfile(p):
                found[key] = p
                break
    for d in ("documentation", "docs", "doc"):
        p = os.path.join(root, d)
        if os.path.isdir(p):
            found["docs_dir"] = p
            break
    slug = re.sub(r"[/\\:]", "-", os.path.abspath(root))
    mem = os.path.expanduser("~/.claude/projects/" + slug + "/memory")
    if os.path.isdir(mem):
        found["memory_dir"] = mem
    return found


def context_rent(f):
    """What is loaded into context every session, and what it costs."""
    rows = []
    for label, key, when in [
        ("CLAUDE.md", "claude_md", "every turn"),
        ("AGENTS.md (Codex export)", "agents_md", "every turn, in Codex"),
        ("README.md", "readme", "only when read"),
    ]:
        if key in f:
            b = os.path.getsize(f[key])
            rows.append({"file": label, "bytes": b, "approx_tokens": b // TOK, "loaded": when})
    if "memory_dir" in f:
        idx = os.path.join(f["memory_dir"], "MEMORY.md")
        if os.path.isfile(idx):
            b = os.path.getsize(idx)
            rows.append({"file": "MEMORY.md (index)", "bytes": b,
                         "approx_tokens": b // TOK, "loaded": "every session"})
    always = sum(r["approx_tokens"] for r in rows if "every" in r["loaded"] and "Codex" not in r["loaded"])
    return {"files": rows, "always_loaded_tokens": always}


def sections(path):
    """Per-section size, rule density and pointer count for a guidance file."""
    text = read(path)
    out, head, buf = [], None, []

    def flush():
        if head is None:
            return
        body = "\n".join(buf)
        out.append({
            "heading": head.lstrip("# ").strip(),
            "bytes": len(body) + len(head) + 1,
            "rules": len(RULE_RE.findall(body)),
            "pointers": len(LINK_RE.findall(body)) + len(re.findall(r"documentation/\S+\.md", body)),
        })

    for line in text.split("\n"):
        if line.startswith("## "):
            flush()
            head, buf = line, []
        else:
            buf.append(line)
    flush()
    return sorted(out, key=lambda s: -s["bytes"])


def activity(root, n):
    """Where the work actually happened, by file touches in the last N commits."""
    log = sh(["git", "log", f"-{n}", "--name-only", "--pretty=format:"], root)
    if not log:
        return None
    skip = {"CLAUDE.md", "AGENTS.md", "README.md"}
    counts = Counter(p for p in log.split("\n") if p.strip() and p not in skip)
    grouped = Counter()
    for path, c in counts.items():
        top = path.split("/")[0]
        # collapse doc/test/tool trees, keep source files individually named
        if top in ("documentation", "docs", "test", "tests", "tools", "backtest"):
            grouped[f"<{top}>"] += c
        else:
            grouped[path] += c
    return {"commits_scanned": n, "top_files": grouped.most_common(20)}


def foregrounding(f, top_files):
    """Does the guidance talk about what the project actually works on?

    A file with many recent touches that CLAUDE.md barely mentions is a sign the
    doc's framing has drifted behind the code.
    """
    if "claude_md" not in f or not top_files:
        return []
    text = read(f["claude_md"])
    rows = []
    for path, touches in top_files[:12]:
        stem = os.path.basename(path)
        # config and dotfiles aren't "surfaces" — mentioning them proves nothing
        if path.startswith("<") or stem.startswith(".") or stem in {
                "package.json", "package-lock.json", "requirements.txt", "go.mod",
                "Cargo.toml", "tsconfig.json", "pyproject.toml"}:
            continue
        rows.append({"file": path, "touches": touches, "mentions_in_claude_md": text.count(stem)})
    return rows


def duplication(f):
    """Sections that exist in more than one always-read file."""
    if "claude_md" not in f or "readme" not in f:
        return []
    def heads(p):
        return {h.strip().lower() for h in re.findall(r"^## (.+)$", read(p), re.M)}
    return sorted(heads(f["claude_md"]) & heads(f["readme"]))


_BASENAMES = {}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__",
             ".idea", ".vscode", "coverage"}


def basenames(root):
    """Every filename in the tree, so a bare code-ref resolves wherever it lives."""
    if root in _BASENAMES:
        return _BASENAMES[root]
    names = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        names.update(filenames)
    _BASENAMES[root] = names
    return names


def links(f):
    """Pointers that no longer resolve — the fastest way a doc goes stale."""
    root = f["root"]
    broken = []
    for key in ("claude_md", "readme", "agents_md"):
        if key not in f:
            continue
        name, text = os.path.basename(f[key]), read(f[key])
        for target in LINK_RE.findall(text):
            t = target.split("#")[0].strip()
            if t and not os.path.exists(os.path.join(root, t)):
                broken.append({"in": name, "kind": "link", "target": target})
        for ref in set(CODEREF_RE.findall(text)):
            if ref.startswith("/"):
                continue  # a route like `/login.js`, not a path on disk
            if any(os.path.exists(os.path.join(root, d, ref))
                   for d in ("", "public", "src", "lib", "tools", "backtest", "app")):
                continue
            if os.path.basename(ref) in basenames(root):
                continue
            broken.append({"in": name, "kind": "code-ref", "target": ref})
    return broken


def docs_health(f):
    """Link-graph health: orphans and missing Related footers."""
    if "docs_dir" not in f:
        return None
    d = f["docs_dir"]
    files = [os.path.join(dp, fn) for dp, _, fns in os.walk(d)
             for fn in fns if fn.endswith(".md")]
    index = os.path.join(d, "README.md")
    idx_text = read(index) if os.path.isfile(index) else ""
    orphans, no_related, broken = [], [], []
    for p in files:
        rel = os.path.relpath(p, d)
        if os.path.basename(p) == "README.md":
            continue
        # a doc counts as indexed if ANY README between it and the docs root lists it
        texts, cur = [idx_text], os.path.dirname(p)
        while cur.startswith(d):
            texts.append(read(os.path.join(cur, "README.md")))
            if cur == d:
                break
            cur = os.path.dirname(cur)
        listed = any(os.path.basename(p) in t or rel in t for t in texts if t)
        if idx_text and not listed:
            orphans.append(rel)
        body = read(p)
        if "## Related" not in body:
            no_related.append(rel)
        for target in LINK_RE.findall(body):
            t = target.split("#")[0].strip()
            if t and not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), t))):
                broken.append({"in": rel, "target": target})
    return {"doc_count": len(files), "total_bytes": sum(os.path.getsize(p) for p in files),
            "has_index": bool(idx_text), "orphans": orphans,
            "missing_related": no_related, "broken_links": broken}


def memory(f):
    """Vault health: size, index/notes agreement, dangling links, and the notes
    most likely to be duplicating the docs tree."""
    if "memory_dir" not in f:
        return None
    m = f["memory_dir"]
    notes = sorted(n for n in os.listdir(m) if n.endswith(".md") and n != "MEMORY.md")
    idx = read(os.path.join(m, "MEMORY.md"))
    alive = {n[:-3] for n in notes}

    doc_stems = set()
    if "docs_dir" in f:
        for dp, _, fns in os.walk(f["docs_dir"]):
            doc_stems |= {fn[:-3] for fn in fns if fn.endswith(".md")}

    rows, dangling = [], []
    for n in notes:
        body = read(os.path.join(m, n))
        t = re.search(r"^\s*type:\s*(\w+)", body, re.M)
        stem = n[:-3]
        # a note whose name matches a doc filename is a duplication candidate
        exact = stem in doc_stems
        loose = not exact and any(
            len(set(stem.split("-")) & set(ds.split("-"))) >= 2 for ds in doc_stems)
        overlap = "exact" if exact else ("partial" if loose else "")
        rows.append({"note": n, "bytes": os.path.getsize(os.path.join(m, n)),
                     "type": t.group(1) if t else "MISSING",
                     "doc_overlap": overlap,
                     "indexed": f"({n})" in idx})
        for w in WIKI_RE.findall(body):
            if w not in alive:
                dangling.append({"in": n, "target": w})

    return {
        "dir": m,
        "note_count": len(notes),
        "total_bytes": sum(r["bytes"] for r in rows),
        "index_bytes": len(idx.encode()),
        "notes": rows,
        "same_name_as_doc": [r["note"] for r in rows if r["doc_overlap"] == "exact"],
        "topic_overlaps_doc": [r["note"] for r in rows if r["doc_overlap"] == "partial"],
        "untyped": [r["note"] for r in rows if r["type"] == "MISSING"],
        "unindexed": [r["note"] for r in rows if not r["indexed"]],
        "dangling_wikilinks": dangling,
    }


def collect(root, commits):
    f = discover(root)
    act = activity(root, commits)
    return {
        "discovered": {k: v for k, v in f.items() if k != "root"},
        "context_rent": context_rent(f),
        "claude_md_sections": sections(f["claude_md"]) if "claude_md" in f else [],
        "activity": act,
        "foregrounding": foregrounding(f, act["top_files"] if act else []),
        "duplicated_sections": duplication(f),
        "broken_pointers": links(f),
        "docs": docs_health(f),
        "memory": memory(f),
    }


def render(d):
    L = []
    a = L.append
    a("KNOWLEDGE BASE — MEASURED\n" + "=" * 60)

    a("\nContext rent (what you pay every turn)")
    for r in d["context_rent"]["files"]:
        a(f"  {r['file']:<28} {r['bytes']:>8,} B  ~{r['approx_tokens']:>6,} tok   {r['loaded']}")
    a(f"  {'ALWAYS LOADED':<28} {'':>8}    ~{d['context_rent']['always_loaded_tokens']:>6,} tok")

    if d["claude_md_sections"]:
        a("\nCLAUDE.md by section (bytes / rule-words / pointers)")
        for s in d["claude_md_sections"][:12]:
            a(f"  {s['bytes']:>7,}  {s['rules']:>3}r {s['pointers']:>3}p   {s['heading'][:52]}")
        thin = [s for s in d["claude_md_sections"]
                if s["rules"] == 0 and s["pointers"] == 0 and s["bytes"] > 800]
        if thin:
            a("  -> no rules, no pointers — check whether these are description that "
              "belongs in the docs:")
            for s in thin[:5]:
                a(f"     {s['bytes']:>7,}  {s['heading'][:50]}")

    if d["activity"]:
        a(f"\nWhere the work actually is (last {d['activity']['commits_scanned']} commits)")
        for path, c in d["activity"]["top_files"][:10]:
            a(f"  {c:>5}  {path}")

    if d["foregrounding"]:
        gaps = [r for r in d["foregrounding"] if r["mentions_in_claude_md"] == 0]
        if gaps:
            a("\nActive but UNMENTIONED in CLAUDE.md (framing may have drifted)")
            for r in gaps:
                a(f"  {r['touches']:>5} touches   {r['file']}")

    if d["duplicated_sections"]:
        a("\nSections duplicated between CLAUDE.md and README.md")
        for h in d["duplicated_sections"]:
            a(f"  - {h}")

    if d["broken_pointers"]:
        a(f"\nBroken pointers ({len(d['broken_pointers'])})")
        for b in d["broken_pointers"][:12]:
            a(f"  [{b['in']}] {b['kind']}: {b['target']}")

    if d["docs"]:
        x = d["docs"]
        a(f"\nDocs tree: {x['doc_count']} files, {x['total_bytes']:,} B"
          + ("" if x["has_index"] else "  (NO index README)"))
        if x["orphans"]:
            a(f"  orphans (not in index): {len(x['orphans'])} -> " + ", ".join(x["orphans"][:5]))
        if x["missing_related"]:
            a(f"  missing ## Related: {len(x['missing_related'])}")
        if x["broken_links"]:
            a(f"  broken internal links: {len(x['broken_links'])}")

    if d["memory"]:
        m = d["memory"]
        a(f"\nMemory vault: {m['note_count']} notes, {m['total_bytes']:,} B"
          f"  (index {m['index_bytes']:,} B)")
        if m["same_name_as_doc"]:
            a(f"  SAME NAME as a doc ({len(m['same_name_as_doc'])}) — likely duplicating it:")
            for n in m["same_name_as_doc"][:12]:
                a(f"    - {n}")
        if m["topic_overlaps_doc"]:
            a(f"  topic overlaps a doc ({len(m['topic_overlaps_doc'])}) — check before assuming:")
            for n in m["topic_overlaps_doc"][:12]:
                a(f"    - {n}")
        if m["unindexed"]:
            a(f"  not in MEMORY.md: {', '.join(m['unindexed'][:6])}")
        if m["untyped"]:
            a(f"  missing type: {', '.join(m['untyped'][:6])}")
        if m["dangling_wikilinks"]:
            a(f"  dangling wikilinks: {len(m['dangling_wikilinks'])}")

    return "\n".join(L)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = os.path.abspath(args[0]) if args else os.getcwd()
    commits = 150
    if "--commits" in sys.argv:
        commits = int(sys.argv[sys.argv.index("--commits") + 1])
    data = collect(root, commits)
    if "--json" in sys.argv:
        print(json.dumps(data, indent=2))
    else:
        print(render(data))


if __name__ == "__main__":
    main()
