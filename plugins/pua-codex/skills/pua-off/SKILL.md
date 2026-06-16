---
name: pua-off
description: "Use when you want to disable PUA always-on mode；sets `always_on=false` and `feedback_frequency=0` while preserving config fields. Invoke with `$pua-off`."
license: MIT
---

# pua-off

This is a Codex alias for the `$pua-off` skill.

Disable PUA always-on mode by setting ~/.pua/config.json always_on=false and feedback_frequency=0. Then report [PUA OFF].

When this alias changes `~/.pua/config.json`, preserve unknown fields and create `~/.pua/` if missing. Do not claim completion without command/output evidence.
