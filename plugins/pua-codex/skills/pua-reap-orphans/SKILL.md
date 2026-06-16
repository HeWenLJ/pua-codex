---
name: pua-reap-orphans
description: "PUA reap-orphans alias for Codex. Codex PUA alias; invoke with `$pua-reap-orphans`."
license: MIT
---

# pua-reap-orphans

This is a Codex alias for the `$pua-reap-orphans` skill.

Scan for stale PUA agent state and remove only confirmed orphan records. Report evidence.

When this alias changes `~/.pua/config.json`, preserve unknown fields and create `~/.pua/` if missing. Do not claim completion without command/output evidence.
