---
name: ship
description: Manual-only, invoked with /ship. Commits current changes, does a fast review, pushes, then deploys if the repo has a deploy step.
argument-hint: "[optional commit message hint]"
disable-model-invocation: true
---

Commit, fast-review, push, and deploy the current repo. Invoking this command is my approval to commit and push to the current branch, including main/master, and to run the repo's production deploy.

1. Run `git status -sb`.
   - If HEAD is detached or the repo has no remote at all, stop and tell me.
   - If the tree is clean and not ahead of upstream, skip to step 5 (deploy only, if applicable).
   - If the tree is clean but ahead of upstream, skip to step 4.
2. Stage all changes (`git add -A`), then fast-review `git diff --cached` (a quick read, no subagents). Look only for obvious bugs, leftover debug code, secrets/credentials, or files that clearly shouldn't ship (build output, .env, large binaries).
   - Secret or clear bug: stop and tell me before committing.
   - Files that shouldn't ship: unstage them and list what was left out.
   - Minor nits: one line, don't block.
3. Commit with a concise message matching the repo's existing commit style. Message hint (may be empty): $ARGUMENTS
   - If a pre-commit hook fails, report it and stop. Never use `--no-verify`.
4. Push with `git push` (use `git push -u <remote> <branch>` if the branch has no upstream yet). Never force-push.
   - If it's rejected because the remote has new commits: `git fetch`, list them (`git log --oneline HEAD..@{u}`), then `git pull --rebase`. On a conflict, run `git rebase --abort` and stop, naming the conflicting files. If the rebase is clean, rerun the repo's typecheck/tests (if any) and stop if they fail; otherwise push again and mention which remote commits you rebased onto.
   - Any other push failure: stop, don't deploy.
5. Deploy, if the repo has a deploy step:
   - Detect it in this order: a deploy command named in the repo's CLAUDE.md; a `deploy` script in `package.json` (`npm run deploy`, or the repo's package manager); a `wrangler.jsonc`/`wrangler.json`/`wrangler.toml` with no deploy script (`npx wrangler deploy`). Anything else (no deploy step, or deploys that happen on push via CI): skip and say so.
   - If CLAUDE.md lists tests/checks to run before deploying, run them first; any failure stops the deploy.
   - Only deploy from the default branch (main/master). On another branch, skip and say so.
   - If the deploy fails or is blocked, report the error and stop; don't retry with different flags.
   - Afterwards, check it's live if there's a cheap way (e.g. fetch the site and confirm the new build is served).
6. Reply in 2-4 lines: commit hash + message, review result, push result, deploy result (or why it was skipped).
