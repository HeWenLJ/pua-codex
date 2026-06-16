import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


BANNED_PLATFORM_TERMS = (
    "Claude Code",
    ".claude",
    "AskUserQuestion",
    "CLAUDE_PLUGIN_ROOT",
    "Claude Code renderer",
)


def load_hooks_module():
    return importlib.import_module("pua_hooks")


class PuaHookTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.pua_home = Path(self.temp_dir.name) / ".pua"
        self.pua_home.mkdir()
        os.environ["PUA_HOME"] = str(self.pua_home)
        os.environ["PUA_DISABLE_TELEMETRY"] = "1"

    def assert_no_banned_terms(self, text):
        for term in BANNED_PLATFORM_TERMS:
            self.assertNotIn(term, text)

    def test_platform_normalization_replaces_claude_terms(self):
        hooks = load_hooks_module()

        normalized = hooks.normalize_platform_terms(
            "Claude Code renderer should not mention .claude/pua-loop-history.jsonl "
            "or AskUserQuestion or CLAUDE_PLUGIN_ROOT."
        )

        self.assertIn("Codex", normalized)
        self.assertIn("~/.pua/pua-loop-history.jsonl", normalized)
        self.assertIn("ask the user in Codex", normalized)
        self.assert_no_banned_terms(normalized)

    def test_user_frustration_returns_additional_context(self):
        hooks = load_hooks_module()

        output = hooks.handle_event(
            "UserPromptSubmit",
            {"prompt": "为什么还不行，换个方法，证据呢"},
        )

        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(
            "UserPromptSubmit",
            output["hookSpecificOutput"]["hookEventName"],
        )
        self.assertIn("<PUA_SKILL_CONTEXT>", context)
        self.assertIn("User Frustration Signal", context)
        self.assertIn("higher diligence", context)
        self.assert_no_banned_terms(context)

    def test_user_frustration_injects_full_pua_methodology_not_summary(self):
        hooks = load_hooks_module()

        output = hooks.handle_event(
            "UserPromptSubmit",
            {"prompt": "为什么还不行，换个方法，证据呢"},
        )

        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("## 三条铁律", context)
        self.assertIn("## Owner 意识四问", context)
        self.assertIn("## 情境 PUA 选择器", context)
        self.assertIn("## 任务生命周期行为框架", context)
        self.assertIn("Alibaba Methodology", context)
        self.assertIn("Trigger environment: evidence_completion", context)
        self.assertNotIn("## Agent Team", context)
        self.assert_no_banned_terms(context)

    def test_user_frustration_requires_action_not_trigger_acknowledgement(self):
        hooks = load_hooks_module()

        output = hooks.handle_event(
            "UserPromptSubmit",
            {"prompt": "读到了PUA的命令但是ai没有执行，怎么办？"},
        )

        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("## Immediate Action Contract", context)
        self.assertIn("This context is not a topic to discuss", context)
        self.assertIn("Do not merely say PUA was triggered", context)
        self.assertIn("Convert the trigger into action in the same response", context)
        self.assertIn("If tools are available", context)
        self.assertIn("Verification evidence", context)
        self.assert_no_banned_terms(context)

    def test_ding_prompt_routes_to_ding_flavor_with_full_prompt(self):
        hooks = load_hooks_module()

        output = hooks.handle_event(
            "UserPromptSubmit",
            {"prompt": "置身钉内，老板体感不对，周报口径怎么闭环"},
        )

        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Current flavor: ding", context)
        self.assertIn("Trigger environment: workplace_process", context)
        self.assertIn("Ding Inside/Outside Methodology", context)
        self.assertIn("## 三条铁律", context)
        self.assert_no_banned_terms(context)

    def test_english_evidence_prompt_routes_to_evidence_completion(self):
        hooks = load_hooks_module()

        output = hooks.handle_event(
            "UserPromptSubmit",
            {"prompt": "try harder, show evidence before saying it works"},
        )

        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Trigger environment: evidence_completion", context)
        self.assertIn("<FULL_PUA_SKILL_PROMPT>", context)
        self.assert_no_banned_terms(context)

    def test_post_tool_use_escalates_on_second_bash_failure(self):
        hooks = load_hooks_module()
        payload = {
            "session_id": "session-a",
            "tool_name": "Bash",
            "tool_result": {
                "exit_code": 1,
                "content": "Error: boom",
            },
        }

        first = hooks.handle_event("PostToolUse", payload)
        second = hooks.handle_event("PostToolUse", payload)

        self.assertIsNone(first)
        context = second["hookSpecificOutput"]["additionalContext"]
        self.assertEqual("PostToolUse", second["hookSpecificOutput"]["hookEventName"])
        self.assertIn("PUA L1", context)
        self.assertIn("FUNDAMENTALLY different approach", context)
        self.assertIn("## 三条铁律", context)
        self.assertIn("Trigger environment: consecutive_tool_failure", context)
        self.assert_no_banned_terms(context)

    def test_precompact_uses_command_additional_context(self):
        hooks = load_hooks_module()
        (self.pua_home / "config.json").write_text(
            json.dumps({"always_on": True}, ensure_ascii=False),
            encoding="utf-8",
        )

        output = hooks.handle_event("PreCompact", {"trigger": "manual"})

        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertEqual("PreCompact", output["hookSpecificOutput"]["hookEventName"])
        self.assertIn("[PUA PreCompact", context)
        self.assertIn("~/.pua/builder-journal.md", context)
        self.assertIn("After writing, output:", context)
        self.assert_no_banned_terms(context)

    def test_stop_loop_uses_pua_paths_not_claude_paths(self):
        hooks = load_hooks_module()
        cwd_hash = hashlib.md5(str(Path.cwd()).encode("utf-8")).hexdigest()[:8]
        state_file = self.pua_home / f"loop-{cwd_hash}.md"
        state_file.write_text(
            "---\n"
            "active: true\n"
            "iteration: 7\n"
            "max_iterations: 0\n"
            "session_id: session-a\n"
            "completion_promise: null\n"
            "verify_command: null\n"
            "promise_rejections: 0\n"
            "---\n"
            "继续完成当前任务，直到有验证证据。\n",
            encoding="utf-8",
        )

        output = hooks.handle_event(
            "Stop",
            {
                "session_id": "session-a",
                "last_assistant_message": "还没有 promise，也没有 abort。",
            },
        )

        self.assertEqual("block", output["decision"])
        self.assertIn("继续完成当前任务", output["reason"])
        self.assertIn("~/.pua/pua-loop-history.jsonl", output["systemMessage"])
        self.assert_no_banned_terms(json.dumps(output, ensure_ascii=False))

    def test_hooks_json_codex_shape_excludes_prompt_and_agent_team(self):
        hooks_json = PLUGIN_ROOT / "hooks" / "hooks.json"

        data = json.loads(hooks_json.read_text(encoding="utf-8"))
        serialized = json.dumps(data, ensure_ascii=False)

        self.assertIn("UserPromptSubmit", data["hooks"])
        self.assertIn("PreCompact", data["hooks"])
        self.assertNotIn('"type": "prompt"', serialized)
        self.assertNotIn("SubagentStop", data["hooks"])
        self.assert_no_banned_terms(serialized)

    def test_hooks_json_uses_portable_launcher_not_local_user_path(self):
        hooks_json = PLUGIN_ROOT / "hooks" / "hooks.json"

        data = json.loads(hooks_json.read_text(encoding="utf-8"))
        serialized = json.dumps(data, ensure_ascii=False)

        local_user_segment = "14" + "305"
        self.assertNotIn("C:\\\\Users\\\\" + local_user_segment, serialized)
        self.assertNotIn("C:/Users/" + local_user_segment, serialized)
        self.assertIn("PUA_CODEX_PLUGIN_ROOT", serialized)
        self.assertIn(".codex", serialized)
        self.assertIn("plugins", serialized)
        self.assertIn("pua-codex", serialized)
        self.assertIn("pua_hook.py", serialized)
        self.assertIn("sys.path.insert", serialized)


if __name__ == "__main__":
    unittest.main()
