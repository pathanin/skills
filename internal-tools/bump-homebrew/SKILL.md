---
name: bump-homebrew
description: >
  Releases a new version of a Homebrew formula in a tap repo: tags the repo,
  builds a deterministic tarball via git archive, uploads it as a GitHub Release
  asset, updates the formula's url/sha256, and pushes. Trigger when the user asks
  to bump, release, publish, tag, or ship a version of a Homebrew formula or tap
  — including phrasings like "push a new version", "cut/make a release",
  "publish to my tap", "brew bump", or "ship v0.X.Y" — provided the request is
  about Homebrew or the working repo contains Formula/*.rb. Skip for releases of
  non-Homebrew projects (npm, crates, plain GitHub releases) and for formula
  edits that aren't version bumps (dependencies, install block, caveats).
---

# bump-homebrew

Automate releasing a new version of a Homebrew formula end-to-end. Works with any tap repo — all context is detected at runtime.

**Key design:** uses `git archive` + GitHub Release asset upload instead of GitHub's auto-generated tag tarballs. The auto-generated tarballs are produced lazily by CDN nodes that can serve different bytes for minutes after a tag is pushed, causing persistent SHA256 mismatches. A release asset is uploaded once from a single source and is byte-stable immediately.

## Workflow

### Step 1 — Determine the new version tag

If the user provided a version in their message, use it. Normalize first: if it
matches `MAJOR.MINOR.PATCH` without the `v` prefix (e.g. `0.2.0`), prepend `v`.
If no version was provided, ask exactly once: "What version tag should I use? (e.g. v0.2.0)"

Validate: after normalization the tag must match `vMAJOR.MINOR.PATCH`. If it
doesn't, tell the user what you received and ask again.

Derive the bare version (no `v` prefix): e.g. `v0.2.0` → `0.2.0`.

### Step 2 — Detect repo context

Run these commands to discover the context:

```bash
# Repo root
git rev-parse --show-toplevel

# GitHub remote (owner/repo)
git remote get-url origin

# Default branch (e.g. "origin/main" → main)
git symbolic-ref --short refs/remotes/origin/HEAD

# Formula files — list ALL matches, do not truncate
find . -maxdepth 2 -path './Formula/*.rb'

# gh CLI authenticated?
gh auth status
```

Rules:
- If no `Formula/*.rb` file is found, stop and tell the user this doesn't look
  like a Homebrew tap repo.
- If exactly one formula file is found, use it. If more than one is found, this
  is the one context question you must ask: list them and ask which formula to bump.
- If `git symbolic-ref` fails (no cached origin HEAD), run
  `git remote show origin` and read the "HEAD branch" line. Call the result
  `{default-branch}` and use it everywhere below — never assume `main`.
- Auth check, operationally: if `gh auth status` exits non-zero, stop and tell
  the user to run `gh auth login`. If it succeeds and displays token scopes
  (classic tokens), verify `repo` is present; if scopes are not displayed
  (fine-grained PATs don't show them), proceed — a missing permission will
  surface as a 403 in Step 8 and is handled there.

From the remote URL, extract the GitHub `owner/repo` slug. Handle both HTTPS
(`https://github.com/owner/repo.git`) and SSH (`git@github.com:owner/repo.git`)
formats. If the remote is not GitHub, stop and ask the user to provide the
tarball URL manually.

Derive names:
- Repo name: the `repo` part of `owner/repo` (e.g. `homebrew-dedup`)
- Formula name: the formula filename without `.rb` (e.g. `Formula/dedup.rb` → `dedup`)
- Asset filename: `{repo-name}-{bare-version}.tar.gz` (e.g. `homebrew-dedup-0.2.0.tar.gz`)
- Asset URL: `https://github.com/{owner}/{repo}/releases/download/{tag}/{asset-filename}`
- Tarball prefix: `{repo-name}-{bare-version}/` (e.g. `homebrew-dedup-0.2.0/`)

### Step 3 — Show the current formula state

Read the formula file. Identify the formula's **top-level** `url` and `sha256`
lines (the ones directly in the formula body — not lines inside `bottle do`,
`resource`, or `head` blocks). Show both lines to the user so they can confirm
they're bumping the right thing, and record their exact text — Step 9 edits
exactly these strings and nothing else.

Sanity check: extract the current version from the `url` line. If the new
version is not greater than the current one, say so explicitly and ask the user
to confirm before continuing.

### Step 4 — Pre-flight checks

```bash
git fetch origin
git status --short
git rev-parse --abbrev-ref HEAD
git rev-list --count HEAD..origin/{default-branch}
```

- If there are uncommitted changes, stop and tell the user to commit or stash them first.
- If the current branch is not `{default-branch}`, stop and tell the user to switch first.
- If `rev-list --count` is greater than 0, the local branch is behind — stop and
  tell the user to pull first.

Also check whether this is a **resume** of a prior partial attempt:

```bash
git ls-remote --tags origin refs/tags/{tag}
```

- Remote tag doesn't exist → fresh run; proceed normally.
- Remote tag exists **and points at the current HEAD commit** → resume mode:
  skip Step 6, but still run Steps 7–11 in full (the tarball is deterministic,
  so rebuilding is safe and required).
- Remote tag exists and points at a **different** commit → stop. Never delete or
  move a pushed tag; explain that retagging would change the archive bytes and
  desync them from anything already published, and let the user decide.

### Step 5 — Confirm before making changes

Say: "I'll tag **{owner/repo}** as `{tag}`, build a deterministic tarball via
`git archive`, upload it as a GitHub Release asset at `{asset-url}`, update
`{formula file}`, then push everything. OK to proceed?" (In resume mode, say the
tag already exists and will be reused.)
Wait for confirmation.

### Step 6 — Create and push the git tag

Skip this step in resume mode.

```bash
git tag {tag}
git push origin {tag}
```

If the tag already exists **locally only** (not on the remote — Step 4 checked),
it is a leftover from an unpushed attempt: verify it points at HEAD; if so push
it, otherwise stop and report the mismatch.

### Step 7 — Build the tarball and compute SHA256

Use `git archive` to produce a byte-stable tarball from the exact tagged commit.
This is deterministic: the same tag always yields the same bytes. **Always
rebuild the tarball in this step — never reuse a file left over from a previous
attempt.**

```bash
git archive --format=tar.gz --prefix={tarball-prefix} {tag} -o /tmp/{asset-filename}
shasum -a 256 /tmp/{asset-filename}
```

No CDN wait required. The SHA256 is final.

### Step 8 — Create the GitHub Release and upload the asset

```bash
gh release create {tag} /tmp/{asset-filename} \
  --title "{tag}" \
  --notes "Release {tag}"
```

This creates the release and uploads the tarball as an asset in one step.

If the release already exists (a prior partial attempt), upload just the asset:
```bash
gh release upload {tag} /tmp/{asset-filename} --clobber
```

If either command fails with 403, the token lacks write permission — stop and
tell the user to re-authenticate (classic token with `repo` scope, or
fine-grained PAT with Contents: Write on this repo).

### Step 9 — Update the formula file

Using the Edit tool (not sed), replace exactly the two lines recorded in Step 3:
- the old `url` line → `url "https://github.com/{owner}/{repo}/releases/download/{tag}/{asset-filename}"`
- the old `sha256` line → `sha256 "{hash from Step 7}"`

Match on the exact old strings from Step 3 so lines inside `bottle do`,
`resource`, or `head` blocks are never touched. Keep every other line exactly
as-is — do not reformat anything.

If the edit finds no match, stop and show what was found vs. what was expected.

### Step 10 — Commit and push the formula

```bash
git add {formula file}
git commit -m "Release {tag}"
git push origin {default-branch}
```

### Step 11 — Verify the published asset

Before reporting success, confirm the published bytes match the formula:

```bash
curl -sL {asset-url} | shasum -a 256
```

The hash must equal the value written into the formula in Step 9. If it doesn't,
stop and report the mismatch — do not report success.

### Step 12 — Report success

Report using exactly this structure:
- **Tag pushed:** `{tag}` on {owner/repo}
- **Asset URL:** {asset-url}
- **SHA256:** {hash} (verified against the published asset)
- **Install:** `brew upgrade {formula-name}` now installs `{tag}`

## Error handling

- No `Formula/*.rb` found → stop, this isn't a Homebrew tap.
- Remote URL isn't GitHub → stop, ask the user to provide the tarball URL manually.
- `gh auth status` exits non-zero → stop, tell user to run `gh auth login`
  (classic token with `repo` scope, or fine-grained PAT with Contents: Write).
- Remote tag exists on a different commit → stop; never delete or force-move a
  pushed tag. A local-only leftover tag may be deleted with `git tag -d {tag}`
  if the user wants a clean retry.
- `git archive` fails → the tag doesn't exist or the repo has no commits; stop and report.
- `gh release create` fails with 403 → token lacks write permission; stop and
  tell user to re-authenticate.
- `gh release create` fails with "already exists" → use
  `gh release upload --clobber` on the existing release instead.
- Formula edit produces no change → stop, show what was found vs. what was expected.
- Verification hash (Step 11) doesn't match → stop, report both hashes; the
  likely cause is a stale asset from a prior attempt — re-run Steps 7–8 with
  `--clobber`, then verify again.
- Push rejected → show the full git error and stop. Do not force-push.

## Why not the auto-generated tag tarball?

GitHub generates `archive/refs/tags/{tag}.tar.gz` lazily when first requested.
During the minutes after a tag push, different CDN nodes may produce and cache
different archive bytes (different metadata, timestamps, or compression). This
causes the SHA256 to differ between fetches from different geographic locations,
so `brew install` fails for users who hit a node with a different cached
version. A release asset is uploaded once from one source and served as-is by
the CDN — the bytes never change.
