# limits (app only)

Copy of [Ryan-LT/claude-mods `limits`](https://github.com/Ryan-LT/claude-mods/tree/main/limits) at upstream commit `deb6d8b`, MIT licensed (see `LICENSE`).

It shows your 5-hour and weekly usage limits, with reset countdowns and context fill, in a band above the prompt.

## Install

```
/plugin install limits --marketplace pathanin/skills
```

## What differs from upstream

Upstream runs everywhere the plugin is installed. This copy adds one option, `show`:

- `app` (default): runs only in sessions the Claude desktop app starts (`CLAUDE_CODE_ENTRYPOINT=claude-desktop`). A terminal session draws nothing, makes no usage requests and raises no toasts.
- `everywhere`: upstream's behaviour.

It also refreshes usage every 30 seconds instead of upstream's 2 minutes (`SLOT` in `hooks/register.tsx`), still one request per slot shared by every open session.

The change is in `hooks/register.tsx` (`isRunning`, and the first line of each hook). The upstream tests run under `everywhere`; two more tests cover `app`.

## Updating from upstream

Copy the new `hooks/register.tsx` and `hooks/usage.test.tsx` over, add the `isRunning` gate back, then `claude plugin test mods/limits`.
