# Emit — the two files

The extraction produces exactly two files plus a copy of the source. You are not
building a skill, a plugin, or a check script.

```
<slug>/
  dna.json          the full measured record; never pasted whole into a prompt
  dna.md            the payload + how to use it, nuances, do/don't
  reference/        the original, kept forever
```

In a multi-sample run, `reference/` holds **every** sample, and the anchor is named
unambiguously — `reference/anchor-*`. A reader who cannot tell which file Step 5 was
diffed against cannot re-verify the rebuild.

Name the folder after `meta.slug`, created in the current working directory unless the
user named a destination. Rebuild HTML, rendered PNGs and `squint.png` are working
files — keep them out of `<slug>/`, or under `<slug>/work/` if the user wants them.

## dna.md — the layout, in this order

### 1. Title and one line

`# <meta.name> DNA`, then `soul.one_line`. Concrete nouns, no marketing words.

### 2. The payload — a bounded region, capped at 2 KB

**The payload stays anchor-shaped even in a multi-sample run.** Ranges are
corroboration for the record, not extra rules for a generating model — a range gives a
model a licence, and the payload's job is to remove licences. Per-role ranges would also
blow the 2 KB cap for zero gain in output quality. Ranges live in `dna.json`, and in
§6/§7 below.

This is the only part anyone pastes into a context window. Wrap it in markers so the
cap is measurable:

```markdown
## Payload — paste this, with the reference image

<!-- payload:start -->
…
<!-- payload:end -->
```

Measure the region, do not eyeball it:

```bash
sed -n '/payload:start/,/payload:end/p' <slug>/dna.md | wc -c   # must be <= 2048
```

Compliance drops as rules pile up, and material in the middle of a long document is
recovered far worse than material at either end. Order the payload exactly like this,
because attention is strongest at the two ends:

1. Attach the reference image and name it first
2. `soul.one_line`
3. **The weird move, alone, unmissable**
4. The 3–9 signature moves, as ratio **bands** — never as floors. A floor drifts: a
   spec that says "at least 5:1" gets built at 14:1 and self-certifies as passing.
5. The bans, as absolutes
6. Palette and type — roles and coverage only, never a full ramp
7. Archetype names, and for each one the structural facts that are not visible from
   its name: what the ground is, where the text sits, what inverts
8. The self-check, last

Close the payload with this line, verbatim:

> Before returning any output, run every test in the self-check. Name each test and
> its result. If any fails, repair the output and run them again. Never return output
> with a failing test and a note explaining it away.

### Over the cap — cut in this order

**Expect to start around 3 KB, and expect the cut to be real.** Written to the standard
above — every ban, every archetype's structural facts, signatures as bands — the payload
does not fit in 2 KB and is not meant to. The cap is not a budget you plan into; it is a
constraint you cut down to, and the list below is the order that survives it.

Two things make that survivable, and both are permissions, not failures:

- **Bans and archetypes are compressed in wording, never dropped as rules.** Nine bans
  can become one semicolon-separated sentence. That is not cutting a ban.
- **An archetype *entry* may leave the payload** when its facts are chrome-level (a nav
  bar, a promo strip) rather than identity-level. When one does, `dna.md` must name which
  archetypes were cut and say to read them back from `dna.json` for a full-page build.
  Silently dropping one is how a reader gets a structure wrong and never knows why.

The floor, below which you stop cutting and accept being over: three signatures, every
ban in some wording, every identity-carrying archetype's name plus its non-obvious facts,
the weird move, and the closing line. If you are still over at the floor, say so in
`dna.md` rather than cutting into it.

Cut top-down and stop as soon as the `sed … | wc -c` above clears 2048:

1. **Prose fat.** Every explanatory clause that does not change what the output looks
   like from three metres away. This is usually a third of the overage.
2. **Palette roles under 1% that are imagery masses**, not brand accents. Fold them
   into one line: "imagery masses read as muted mid-tones."
3. **Archetype prose down to name + the non-obvious structural facts.** Keep the
   facts; a rule you cut here is a rule both readers get wrong. If a shelf tile sits
   directly on paper with no card ground, that sentence stays.
4. **The self-check compressed to one line** of comma-separated bars.
5. **Archetype entries whose facts are chrome-level**, not identity-level. Name the cut
   ones in the "How to use it" section and point at `dna.json`.
6. **The lowest-ranked signature.** Last resort, and never below three — three is the
   doctrine floor.

Never cut: the weird move, any ban (compress the wording instead), or the closing line.

### 3. How to use it

Three or four lines. Paste the payload plus `reference/`. Never paste `dna.json` — it
is the record for tooling and for rebuilds, and it crowds out the rules that matter.
Say which archetype to reach for first.

### 4. Do

The `scope: "style"` tests from `dna.json`, written as instructions. These are the
rules that travel to new content — a reader must be able to decide each one on a
finished piece that shares nothing with the reference.

### 5. Don't

`bans[]`, written as absolutes, plus every drift you actually observed. Name the
tempting wrong move, not just the rule: "never use the eyebrow colour for a
standalone section label — it is 12px and card-scoped" beats "use the accent
sparingly."

### 6. Nuances

The judgement calls a rule cannot carry. Where the system bends, which pairs of rules
fight each other, and what to do when they do.

In a multi-sample run this is where wide ranges go. A value whose `[min, max]` spread
across samples is wide is, literally, a place the system bends — say which value it is,
what the spread was, and what the anchor did. Never state a wide range as if it were a
tight rule, and never let it silently demote a signature: the spread is reported, the
reader judges.

### 7. What this DNA does not know

Every entry from `confidence`, in plain sentences, plus, in a multi-sample run, every
value whose range was too wide to call a rule and any archetype or weird move whose
`seen_in` count was too low to trust — including a `weird_move` set to `found: false`
because it appeared in fewer than half the samples. Plus everything the source mode
could not see: motion in image mode, page rhythm below a viewport crop, typeface
names from pixels, margins on a cropped edge. Put this where the next reader hits it,
not buried in the JSON.

### 8. Reference-fidelity tests — quarantined

The `scope: "rebuild"` tests, under a heading that says plainly they measure this
source's own imagery, crop and content, and **cannot be satisfied by new content**.
They are recorded so a rebuild can be re-verified later, and for no other purpose.
Never present them as rules for the reader's own work.

### 9. Where it came from

One line: the source, the date, the mode. In a multi-sample run, list every sample with
its mode and name the anchor. If the source is someone else's, say so
plainly and note that the DNA is structural — `meta.not_copied` lists every mark,
photograph and typeface that was substituted rather than reproduced.

## Keep dna.json and the payload doing different jobs

`dna.json` exists to reconstruct the reference faithfully. The payload exists to
style **new** content in the same voice. They are not long and short versions of each
other. Detail that helps a rebuild and hurts a fresh generation goes in `dna.json`
only.

## After the files are written

Report back in three lines: the resolved absolute path, the
`reconstruction.final_metrics` verdict, and the top three entries from `confidence`. That is the whole handoff — the user should
know where the spec is weakest before they use it, not after.

**If the reconstruction ended at four passes with a bar still red**, both files are still
written and still delivered — a spec with a named, quantified gap is useful; a withheld
one is not. The verdict line then says "did not fully pass", names the metric and its
exact margin, and says whether the failure sits on a system role or an imagery role.
`dna.md` carries the same in its reconstruction section. Never soften it to "passes with
minor deviations", and never relax a threshold so the line can read green.
