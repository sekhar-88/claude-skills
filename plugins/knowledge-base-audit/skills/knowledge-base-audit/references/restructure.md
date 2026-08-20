# Restructuring the guidance file

Detail for phase 4. Read this when you are actually rewriting CLAUDE.md / AGENTS.md.

## What each section holds

### `## What this is now`

The honest current shape, led by whatever the activity data says the work actually
is. Roughly fifteen lines.

Two things make this section earn its place. It orients an agent that has never
seen the project, and it stops the guidance file from silently describing a
previous era. If the opening paragraph still names the original architecture while
90% of commits land somewhere else, every downstream judgement inherits that error —
the agent will weight the wrong surfaces, read the wrong specs, and propose changes
in the wrong place.

Name what is dormant as dormant. "Four engines run alongside, in maintenance" tells
an agent more than a neutral list of five equal-looking components.

Draft it, show it, let the operator correct it. You can measure where commits land;
you cannot measure which surface they consider the product.

### `## Setup & commands`

How to run it, how to test it, and the rules around deploying that would be
expensive to get wrong (never push directly, never rsync, verify an env var first).
The full runbook stays in the docs — this is the pointer plus whatever is dangerous
enough to state twice.

### `## Where things live`

A table: surface → entry point → spec of record. This is the highest-value section
per byte in the whole file, because it is what stops an agent grepping blindly
through a large codebase, and what makes "read the doc first" actionable rather
than aspirational.

Every row should answer "if I am about to change X, what do I read?" Include the
things that live *outside* the repo, if any — a companion app, an infrastructure
repo — because nothing else will tell the agent they exist.

### `## Rules that bite`

Only non-inferable invariants, grouped by area, one line each. Group by where an
agent will be working (the REST client, the WebSocket layer, money and live state,
the main product surface, charts, shared modules, the server) rather than by
severity, so the relevant group is findable when it matters.

Open the section by saying these have all already caused a regression. That framing
does real work: it tells the reader these are empirical, not stylistic, and it sets
the bar for anything added later.

### `## Symptom → action`

The operator runbook as a two-column table. It has no rules and no pointers and it
still belongs, because it converts a symptom into an action without a doc round
trip. Do not cut it for scoring zero on rule density — measure scripts cannot tell
a runbook from filler.

## Promote, don't delete

When you find material with no home in the docs tree, do not keep it inline and do
not drop it. Promote it into a proper doc, written from the source rather than by
moving the prose you were about to delete. Reading the actual implementation
usually surfaces detail the guidance file never carried, which is the difference
between a spec and a relocated summary.

Then satisfy that tree's conventions — a `## Related` footer, an entry in the docs
index, whatever link style it uses. A promoted doc that orphans the link graph
trades one problem for another. Check the docs README for a conventions section
before writing; most mature trees have one, and it usually has opinions about link
style and frontmatter.

Add backlinks from two or three sibling docs so the new page is reachable from
where someone would actually be standing when they need it.

## Verifying the rewrite

A text diff is useless here — you will have reworded nearly every surviving line,
so the diff shows churn rather than loss. Verify semantically:

```bash
# every invariant you meant to keep, by distinctive token
for t in 'attachAutoReconnect' 'market_protection' 'period || 5' ...; do
  grep -qF -- "$t" CLAUDE.md || echo "MISSING: $t"
done

# everything you dropped, must exist in the docs
grep -rl -- "<concept>" documentation/

# pointers resolve
grep -o 'documentation/[A-Za-z0-9._/-]*\.md' CLAUDE.md | sort -u \
  | while read f; do [ -f "$f" ] || echo "MISSING: $f"; done
```

Do the same for code references and any test commands you list — a guidance file
that names a test file which no longer exists teaches an agent to distrust the
whole document.

## Sizing

There is no universal right size; there is a right *composition*. Judge by whether
each line survives the admission test, then set the ceiling slightly above where
you land so the gate has meaning without being violated on day one.

State the ceiling in the file itself, along with what to do when it is breached:
move mechanism prose into the docs, never delete invariants to fit.
