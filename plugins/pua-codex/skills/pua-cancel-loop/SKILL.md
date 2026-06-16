---
name: pua-cancel-loop
description: "Use when an active PUA loop should be stopped；cleans loop state/worktree references and records the cancellation with evidence. Invoke with `$pua-cancel-loop`."
license: MIT
---

# pua-cancel-loop

This is a Codex alias for the `$pua-cancel-loop` skill.

Cancel the active PUA loop by cleaning loop state/worktree references and recording the event.

When this alias changes `~/.pua/config.json`, preserve unknown fields and create `~/.pua/` if missing. Do not claim completion without command/output evidence.
