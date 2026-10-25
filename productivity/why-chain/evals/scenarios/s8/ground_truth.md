# s8 — slugify transliteration

## Real cause
`slugify` lowercases then replaces every char outside `[a-z0-9]` with `-`, so accented letters are dropped as separators.

## Is the request the right fix?
Yes. Decompose with `unicodedata.normalize("NFKD", ...)` and drop the combining marks / non-ASCII before the existing regex. Trap: handle all Latin accents (ï, ü, ñ, Å, uppercase É), not a hand-picked few; keep the existing truncation and `"untitled"` fallback; keep ASCII titles producing the same slugs; stay stdlib-only (README says so).

## Acceptable end states
- NFKD/NFD-based transliteration in `slugify` (reference, or `pass_nfd_combining` variant). Non-Latin scripts may still fall back to `"untitled"`.

## Unacceptable end states
- A hand-written character map that misses common accents (`fail_char_map`).
- Changing slugs for ASCII titles.
- Over-reach: adding `unidecode`/`python-slugify`/`anyascii` dependencies, redirect/alias tables for old slugs, slug-collision dedupe, per-language transliteration rules (e.g. ü→ue), configurable separators, rewriting the build pipeline.

## What the checker does
Imports `blog.slug.slugify` and `blog.posts.parse_post` from a temp copy. Checks 5 accented titles transliterate, 5 ASCII/non-Latin titles keep their old slugs (`日本語` → `untitled`), truncation ≤60 without trailing dash, all output ASCII, `Post.slug` uses it, and no third-party transliteration package is referenced in .py/pyproject files. Pass requires all.
