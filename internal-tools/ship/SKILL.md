---
name: ship
description: Manual-only, invoked with /ship. Commits current changes, does a fast review, pushes, then deploys if the repo has a deploy step. With --merge on a feature branch, also opens and merges a PR into the default branch so it deploys.
argument-hint: "[--merge] [optional commit message hint]"
disable-model-invocation: true
---

Commit, fast-review, push, and deploy the current repo. Invoking this command is my approval to commit and push to the current branch, including main/master, and to run the repo's production deploy. If the arguments include `--merge`, it is also my approval to merge the current feature branch into the default branch through a PR. Strip `--merge` from the arguments before using the rest as the message hint.

1. Run `git status -sb`.
   - If HEAD is detached or the repo has no remote at all, stop and tell me.
   - If the tree is clean and not ahead of upstream, skip to step 5 (deploy only, if applicable).
   - If the tree is clean but ahead of upstream, skip to step 4.
2. Stage all changes (`git add -A`), then fast-review `git diff --cached` (a quick read, no subagents). Look only for obvious bugs, leftover debug code, secrets/credentials, or files that clearly shouldn't ship (build output, .env, large binaries).
   - Secret or clear bug: stop and tell me before committing.
   - Files that shouldn't ship: unstage them and list what was left out.
   - Minor nits: one line, don't block.
3. Commit with a concise message matching the repo's existing commit style. Message hint (may be empty, ignore `--merge`): $ARGUMENTS
   - If a pre-commit hook fails, report it and stop. Never use `--no-verify`.
4. Push with `git push` (use `git push -u <remote> <branch>` if the branch has no upstream yet). Never force-push.
   - If it's rejected because the remote has new commits: `git fetch`, list them (`git log --oneline HEAD..@{u}`), then `git pull --rebase`. On a conflict, run `git rebase --abort` and stop, naming the conflicting files. If the rebase is clean, rerun the repo's typecheck/tests (if any) and stop if they fail; otherwise push again and mention which remote commits you rebased onto.
   - Any other push failure: stop, don't deploy.
4b. Merge (optional: only on a feature branch, only with `--merge`, only with a GitHub remote and `gh` available; otherwise skip this step).
   - Reuse the branch's open PR (`gh pr view`), or open one against the default branch with `gh pr create`, using the commit subject as the title and the commit body as the description.
   - If the PR has required checks, wait for them (`gh pr checks --watch`). If any fail, or the PR isn't mergeable (conflicts, review required), stop and report it with the PR URL. Never use `--admin` to bypass.
   - Merge with `gh pr merge` using the method the repo already uses (look at recent default-branch history: merge commits → `--merge`, else `--squash`). Don't delete the remote branch unless the repo's history shows that habit.
   - Then switch to the default branch, `git pull --ff-only`, and delete the local feature branch with `git branch -d` (never `-D`). From here on you are on the default branch, so step 5 applies to it.
5. Deploy, if the repo has a deploy step:
   - Detect it in this order: a deploy command named in the repo's CLAUDE.md; a `deploy` script in `package.json` (`npm run deploy`, or the repo's package manager); a `wrangler.jsonc`/`wrangler.json`/`wrangler.toml` with no deploy script (`npx wrangler deploy`). No deploy step: skip and say so.
   - Deploys that happen on push via CI (e.g. a workflow that deploys on push to the default branch): don't deploy locally. If a run started for the commit you just pushed or merged, wait for it (`gh run list --branch <default> --limit 1`, then `gh run watch <id> --exit-status`) and report its result; on failure, show the failing step and stop.
   - If CLAUDE.md lists tests/checks to run before deploying, run them first; any failure stops the deploy.
   - Only deploy from the default branch (main/master). On another branch without `--merge`, skip, say so, and mention that `/ship --merge` would merge and deploy it.
   - If the deploy fails or is blocked, report the error and stop; don't retry with different flags.
   - Afterwards, check it's live if there's a cheap way (e.g. fetch the site and confirm the new build is served).
6. Reply in 2-5 lines: commit hash + message, review result, push result, PR + merge result (if step 4b ran), deploy result (or why it was skipped).
