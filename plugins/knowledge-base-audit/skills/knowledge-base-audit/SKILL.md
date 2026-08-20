---
name: knowledge-base-audit
description: Audit and overhaul a project's agent knowledge base — CLAUDE.md, AGENTS.md, README.md, the docs tree, and the Claude memory vault — measuring what they cost per turn, whether their framing still matches where the project actually works, what is duplicated, and what is stale, then restructuring them so the guidance file is preflight instead of documentation. Use this whenever someone says their CLAUDE.md is too long, bloated, stale, disorganized or "not coherent anymore", asks what is even in it or what it is supposed to be, wants their agent context files cleaned up, consolidated, reorganized or ported, wonders why their context window fills up so fast, wants memory notes pruned or de-duplicated, or asks for a knowledge-base report, audit, overhaul or course correction. Also use it proactively when about to make a large edit to a CLAUDE.md that has clearly outgrown its purpose.
---

# Knowledge base audit

A project's agent context has three files doing three different jobs, and they rot
in predictable ways:

- **CLAUDE.md / AGENTS.md** — preflight. What must be in the agent's head *before*
  it touches code. Loaded every turn, so every line is rent.
- **README.md** — the human front door. What is this, how do I run it, where next.
- **`documentation/`** — the source of truth for behaviour. Loaded on demand.
- **The memory vault** — what the repo *cannot* tell you: how the operator wants
  work done, machine facts not in git, research verdicts too expensive to re-derive.

The characteristic failure is that CLAUDE.md quietly becomes a summary of the
application. It grows one reasonable-looking paragraph at a time, each addition
defensible, until it is tens of KB of mechanism that the docs already own — and its
framing describes the project as it was a year ago, not as it is.

Two modes. **`report`** measures and reports, changing nothing. **Anything else**
runs the full overhaul, which begins with the same report.

## Mode: report

Triggered by `report`, "just tell me", "audit only", or any request for numbers
rather than changes. Write nothing — not even a fix for an obviously broken link.
The point is to give someone a decision, not to start work they did not approve.

```bash
python3 <skill>/scripts/measure.py [project_dir]        # human-readable
python3 <skill>/scripts/measure.py [project_dir] --json  # if you want to compute on it
```

The script measures; you interpret. It cannot tell whether a rule is worth its
line — that judgement is the whole job, and it is yours.

Read the numbers, then spend a little effort the script cannot: open the guidance
file's opening section and compare what it says the project *is* against the
activity ranking. That comparison is usually where the real finding is.

Report in this shape, short enough to read in one screen:

```
## What it costs
   Per-turn token rent, by file. One line.

## Whether the framing still holds
   The opening description vs. where commits actually land. Quantify it —
   "139 file touches on X, 11 across all of Y" lands where "seems stale" does not.
   Name anything active that the guidance never mentions.

## What's in it
   Section sizes with rule density. Which sections carry invariants and which
   are description wearing a guidance hat.

## What's duplicated
   Sections appearing in both README and CLAUDE.md; memory notes restating docs.

## What's broken
   Dead pointers, orphan docs, dangling links, notes contradicted by the code.

## Verdict
   Two or three sentences: is the size justified, what would you cut, what is
   the realistic floor. Offer the overhaul; do not start it.
```

Be honest when the size *is* justified. A system that spends real money may
legitimately carry more always-loaded invariants than a CRUD app. Report the
tradeoff rather than assuming smaller is better.

## Mode: overhaul

Run the report first, share it, then work through the phases. Each phase ends in a
verifiable state, so stopping early still leaves things better than before.

### 1. Back up

The docs and guidance files are usually in git — confirm with `git status` and note
the parent commit. **The memory vault is not in git.** Tar it before touching it:

```bash
tar czf ~/kb-audit-backup-$(date +%Y%m%d-%H%M%S).tgz -C <memory_parent> memory
```

Offer to move the backups somewhere durable when the work is done.

### 2. Establish the framing

Rewrite the opening section to describe the project as it is now, led by whatever
the activity data says the work actually is. Draft it, show it, and ask them to
correct it — you can measure where commits land, but only they know which surface
is the product and which is maintenance.

### 3. Sort every rule

This is the intellectual core, and it cannot be scripted.

**Inferable — cut it.** A competent engineer reading the code would do this anyway.
Conventions, taste, restatements of good practice. "Ensure state machine integrity",
"use the shared time helper", "write files atomically". These cost lines and buy
nothing, and they dilute the rules that matter.

**Not inferable — keep it, in one line.** A fact about this system that contradicts
what best practice would suggest. These are irreducible: no amount of care recovers
them, and several actively point the wrong way. Real examples:

- a reconnect budget of `-1` meaning *zero* retries, not infinite
- `period || 5` making a falsy `0` mean 5
- a double *exit* not closing a position but opening the opposite one
- a deferred order silently converting and firing at market next session
- a chart range API that covers only bars, so restoring by time collapses the view

The test to apply per line: **would omitting this cause a wrong, expensive change?**

Keep the *why* only when it fits in a clause. The moment a rule needs a paragraph,
the paragraph belongs in the docs and the pointer belongs in the guidance file.

### 4. Restructure

Target shape — five sections, in this order, because it matches how someone
actually approaches an unfamiliar system:

```
## What this is now      honest current framing, ~15 lines
## Setup & commands      run, test, deploy
## Where things live     surface -> entry point -> spec doc
## Rules that bite       non-inferable invariants, grouped by area, one line each
## Symptom -> action     the operator runbook table
```

Cut wholesale: file-structure listings (that is `ls`), state diagrams and API
signature blocks (derivable, and usually already in the docs), any section that
reads like a summary of the application.

`references/restructure.md` has the detail — what each section holds, and the
promote-don't-delete rule for material the docs do not yet cover.

### 5. Rewrite the README as the front door

It should orient a human and then get out of the way: what this is, how to run it,
how to test it, and a pointer to the docs index rather than a stale copy of it.
When you are done, README and the guidance file should share no sections.

### 6. Audit what you cut

Never trust a diff here — you will have reworded almost every line, so a text diff
is noise. Verify by concept instead:

1. List the invariants you intended to keep, pick a distinctive token for each
   (an identifier, a number, a flag name), and grep the new file for all of them.
   Zero misses, or you dropped something while rewriting.
2. For every rule you dropped, grep the docs tree for it. Anything not covered is
   a real loss — restore it, or promote it into a doc properly.
3. Re-check every pointer and code reference resolves (`measure.py` does this).

Report the audit honestly, including anything you had to restore. On a real run
this step is what catches the one rule that existed nowhere else.

### 7. Consolidate the memory vault

Separate pass, after the docs settle, so the two do not fight. The governing rule:
**the vault holds only what the repo cannot tell you.** See `references/memory.md`.

### 8. Add the gate

The overhaul is worthless if the file re-bloats, and "keep it lean" as a norm has a
poor track record — it is unfalsifiable, so it loses every argument against a
specific, plausible addition. Add an `### Editing this file` section with checkable
gates: docs are the default home, the admission test, one line per rule, replace
rather than append, a byte ceiling, and re-run any export.

Then propagate it. If the project has a doc-updating command or skill, put the same
gates in it — that is the most likely re-bloat vector, and it usually already says
something toothless like "keep CLAUDE.md lean". If there is a memory note about
documentation practice, update it too, and check it for pointers into sections the
restructure just deleted.

### 9. Regenerate exports and commit

If the project exports its context anywhere (an `AGENTS.md` for Codex, a generated
onboarding doc), regenerate it and confirm it is under any size cap. Commit on a
branch, and split docs changes from tooling changes so either can be reverted alone.

## Things that go wrong

**Deleting an invariant that existed nowhere else.** The most expensive failure.
Phase 6 exists for it. When the docs do not cover something, promote it into a
proper doc — with whatever footer and index entry that tree's conventions require —
rather than keeping it inline or dropping it.

**Trusting the script's judgement.** It flags candidates. A memory note sharing a
name with a doc is a *prompt to check coverage*, not a verdict.

**Optimizing for smallness.** A 40 KB guidance file that is all non-inferable
invariants is fine. A 10 KB one that is all description is not.

**Doing it silently.** Show the report before changing anything, and let them
correct the framing. They know which surface is the product; you only know where
the commits landed.
