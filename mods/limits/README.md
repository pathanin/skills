# limits (app only)

Copy of [Ryan-LT/claude-mods `limits`](https://github.com/Ryan-LT/claude-mods/tree/main/limits) at upstream 0.2.6 (commit `cb057a7`), MIT licensed (see `LICENSE`).

It shows your 5-hour and weekly usage limits, with reset countdowns and context fill, in a band above the prompt.

## Install

```
/plugin install limits --marketplace pathanin/skills
```

## What differs from upstream

Upstream runs everywhere the plugin is installed. This copy adds one option, `show`:

- `app` (default): runs only in sessions the Claude desktop app starts (`CLAUDE_CODE_ENTRYPOINT=claude-desktop`). A terminal session draws nothing, makes no usage requests and raises no toasts.
- `everywhere`: upstream's behaviour.

It also differs in a few smaller ways:

- **Refresh every 30 seconds** instead of upstream's 2 minutes (`SLOT` in `hooks/register.tsx`), still one request per slot shared by every open session (per account, as upstream does).
- **Full labels**: `5hr`, `week`, `context` instead of upstream's `5hr`, `wk`, `ctx`.
- **No early red** (`PACE_FLOOR`): below 25% used, a run-out pace does not turn a limit red; the percent alone sets the colour.
- **Narrow bands drop meters** (`fitMeters`): when the bars would shrink below 40px (desktop) or 8 cells (terminal), the context goes first, then the weekly limit, leaving the 5-hour limit. The last bar's alt text still names every limit.

The changes are all in `hooks/register.tsx`. The upstream tests run under `everywhere`; the extra tests cover `app`, the pace floor and the narrow-band fitting.

## Updating from upstream

Merge upstream's `hooks/register.tsx` and `hooks/usage.test.tsx` three-way, with the last upstream version taken as the base (`git merge-file ours base theirs`), keep the differences above, then `claude plugin test mods/limits`. Upstream tests that read the store or `env.get` need `EVERYWHERE` and the 30-second slot.
