# Consolidating the memory vault

Detail for phase 7. The vault lives at
`~/.claude/projects/<path-with-slashes-as-dashes>/memory/`, with `MEMORY.md` as an
index loaded every session and topic notes loaded on recall.

**Back it up first.** The vault is not in git, so a wrong deletion is unrecoverable:

```bash
tar czf ~/kb-audit-backup-$(date +%Y%m%d-%H%M%S).tgz -C <parent> memory
```

## The governing rule

**The vault holds only what the repo cannot tell you.** Anything describing how the
system works belongs in the docs tree, where it can be maintained alongside the code
and read by anyone.

That leaves four things worth keeping:

- **How the operator wants work done** — corrections they have made, approaches they
  confirmed, phrasings they object to. Not derivable from anything.
- **Machine and account facts not in git** — deployment quirks, storage behaviour,
  companion repos, external service limits and pricing.
- **Research verdicts** — expensive negative results. "We tested this exhaustively
  and it does not work" is the single highest-value memory type, because without it
  the work gets redone.
- **Operator history** — trading records, prior decisions, anything reconstructible
  only through analysis nobody wants to repeat.

Everything else is a duplicate waiting to drift out of sync with the docs.

## Classify, then act

For each note ask: **could I learn this by reading the repo?**

**Yes → retire it**, once you have confirmed the coverage. Grep the docs tree for a
distinctive term from the note. If a feature doc covers it, the note is a second
copy that will age badly; the restructured guidance file already routes to that doc.
If nothing covers it, this is not a duplicate — either keep the note or promote it
into a doc.

**Contradicted by the code → delete it.** These are the dangerous ones. A note
saying "PENDING decision, do not implement until answered" for a feature that
shipped months ago will actively mislead. Check anything phrased as a decision,
a plan, or a deferral against the current code.

**No → keep it**, and sharpen it. Fix the metadata type if it is wrong (guidance
about how to work is `feedback`, not `project`). Convert relative dates to absolute.

## Repair the link graph

Retiring notes strands links in the survivors. Repoint rather than delete: a
retired note usually had a doc that replaced it, so the link should now name that
doc's path. A dangling link to a note that never existed is fine — it marks
something worth writing — but a dangling link to a note you *just deleted* is
a broken trail.

If the project exports the vault anywhere (converting wikilinks to relative links
for another agent, for example), dangling links become broken links downstream, so
this cleanup is not cosmetic.

## Rewrite the index

`MEMORY.md` is loaded every session, so it is rent like the guidance file. Group the
survivors by the four categories above, one line each: `- [Title](file.md) — hook`.

The hook should be the reason to open the note, not a description of it. Write hooks
as instructions where that fits — "read before writing to CLAUDE.md" beats "notes
about documentation practice", because the first tells a future session *when* it
matters.

Put the governing rule in the index header. It is the thing that stops the vault
re-accumulating repo knowledge, and it needs to be visible every session, not buried
in a note nobody opens.

## Verify

```bash
# every index link resolves
grep -o '](\([a-z0-9_-]*\.md\))' MEMORY.md | tr -d '](' | tr -d ')' \
  | while read f; do [ -f "$f" ] || echo "MISSING: $f"; done

# every note is indexed
for f in *.md; do [ "$f" = MEMORY.md ] && continue
  grep -q "($f)" MEMORY.md || echo "ORPHAN: $f"; done
```

Both should be silent. Then re-run `measure.py` to confirm the dangling-link count
is down to the deliberate ones.
