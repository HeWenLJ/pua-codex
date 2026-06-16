---
name: pua-offline
description: "Use when PUA should run in offline/no-feedback mode；sets `offline=true` and disables feedback frequency without deleting other config. Invoke with `$pua-offline`."
license: MIT
---

# pua-offline

This is a Codex alias for the `$pua-offline` skill.

Enable offline mode by setting ~/.pua/config.json offline=true and feedback_frequency=0 while preserving other fields. Then report [PUA OFFLINE].

When this alias changes `~/.pua/config.json`, preserve unknown fields and create `~/.pua/` if missing. Do not claim completion without command/output evidence.
