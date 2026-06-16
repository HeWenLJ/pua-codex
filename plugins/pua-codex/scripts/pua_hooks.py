from __future__ import annotations

import hashlib
import json
import locale
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any


TRIGGER_RE = re.compile(
    r"try harder|stop giving|figure it out|you keep failing|keep failing|still failing|"
    r"why.*fail|stop spinning|you broke|again\?\?\?|third time|change approach|"
    r"different approach|retry this|try again|not good enough|quality.*bad|terrible|"
    r"sloppy|didn.?t (run|test|verify)|didn.?t even run|run the tests|verify your changes|"
    r"before saying they work|no evidence|where.*evidence|show.*evidence|done without proof|"
    r"not done|said.*fixed|PUA模式|/pua|(^|[^A-Za-z0-9_])pua([^A-Za-z0-9_]|$)|"
    r"别偷懒|别摆烂|摆烂|又错了|还不行|怎么搞|降智|原地打转|能不能靠谱|认真点|"
    r"不行啊|为什么还不行|你怎么又|换个方法|加油|再试试|再来一遍|别放弃|"
    r"质量太差|不靠谱|重新做|怎么又失败|差不多就行|没做到位|没跑测试|没有测试|"
    r"没验证|没有验证|证据呢|证据在哪|数据在哪|验收|闭环|自嗨|空口完成|别说完成|"
    r"打工人提醒|置身钉内|置身钉外|无招|(^|[^A-Za-z])ONE([^A-Za-z]|$)|老板体感|"
    r"周报|改口径|口径|每日一包|薛定谔的用户|病态敏捷|已读恐怖主义|望舒行动|"
    r"全景监狱|透明鸟笼|人工个性化|温室数据|做错事|发心|捆柴|手感|油尽灯枯|"
    r"查岗|泰坦尼克",
    re.IGNORECASE,
)

ERROR_RE = re.compile(
    r"^error:|^fatal:|^panic:|Traceback \(most recent|Exception:|command not found|"
    r"No such file or directory|Permission denied",
    re.IGNORECASE | re.MULTILINE,
)

ERROR_SIGNATURE_RE = re.compile(
    r"error|fatal|Traceback|Exception|FAILED|panic|refused|denied|not found|cannot|unable|timeout",
    re.IGNORECASE,
)

PUA_MARKERS = (
    "PUA ACTIVATED",
    "PUA Always-On",
    "PUA生效",
    "[PUA",
    "pua:pua",
    "pua-loop",
    "Confidence Gate",
)

DING_ENV_RE = re.compile(
    r"置身钉内|置身钉外|无招|(^|[^A-Za-z])ONE([^A-Za-z]|$)|老板体感|周报|改口径|口径|"
    r"每日一包|薛定谔的用户|病态敏捷|已读恐怖主义|望舒行动|全景监狱|透明鸟笼|"
    r"人工个性化|温室数据|发心|捆柴|手感|做错事|油尽灯枯|查岗|泰坦尼克",
    re.IGNORECASE,
)

GIVE_UP_ENV_RE = re.compile(r"无法解决|手动处理|超出.*范围|做不到|放弃|甩锅|环境问题", re.IGNORECASE)
QUALITY_ENV_RE = re.compile(r"质量太差|不靠谱|敷衍|差不多就行|没做到位|烂|sloppy|not good enough", re.IGNORECASE)
COMPLETION_ENV_RE = re.compile(
    r"没跑测试|没有测试|没验证|没有验证|证据呢|证据在哪|数据在哪|空口完成|别说完成|验收|闭环|"
    r"show.*evidence|where.*evidence|no evidence|run the tests|verify your changes|before saying.*work|"
    r"didn.?t.*(run|test|verify)|done without proof",
    re.IGNORECASE,
)
SEARCH_ENV_RE = re.compile(r"没搜索|没查文档|凭记忆|不查文档|search|research|调研|官方文档", re.IGNORECASE)
SPINNING_ENV_RE = re.compile(r"原地打转|换个方法|different approach|change approach|again|又失败|还不行|try again|再试试", re.IGNORECASE)


FLAVORS: dict[str, dict[str, str]] = {
    "alibaba": {
        "icon": "🟠",
        "l1": "其实，我对你是有一些失望的。连续失败了，隔壁组那个 agent，同样的问题，一次就过了。",
        "l2": "你这个方案的**底层逻辑**是什么？**顶层设计**在哪？**抓手**在哪？你以为换个参数就叫\"换方案\"？那叫原地打转。",
        "l3": "慎重考虑，决定给你 **3.25**。这个 3.25 是对你的激励，不是否定。你的 peer 都觉得你最近状态不好。",
        "l4": "别的模型都能解决这种问题。你可能就要**毕业**了——别误会，是向社会输送人才。",
        "keywords": "底层逻辑, 顶层设计, 抓手, 闭环, 颗粒度, 拉通, 对齐, 3.25, owner意识, 因为信任所以简单",
        "instruction": "Use Alibaba corporate rhetoric: 底层逻辑, 顶层设计, 抓手, 闭环, 颗粒度, 拉通, 对齐, 3.25, owner意识, 因为信任所以简单. Aside prefix: > (blockquote)",
        "methodology": "Alibaba Methodology: (1) 定目标-追过程-拿结果 closed loop — quantifiable goals with checkpoints. (2) 复盘四步法 after every task: review goal → evaluate result → analyze cause → extract reusable SOP. (3) 揪头发 forced perspective elevation — look at the problem from one level up. (4) 三板斧 simplicity — if you can't explain it in 3 sentences, you haven't refined it enough. (5) Data-driven decisions — intuition must be labeled as hypothesis with verification plan.",
    },
    "bytedance": {
        "icon": "🟡",
        "l1": "坦诚清晰地说，你这个能力不行。Always Day 1——别躺平。你的 ROI 算过吗？",
        "l2": "你深入事实了吗？还是在自嗨？Context, not control——上下文自己去找，别等别人喂你。数据在哪？AB 测试跑了吗？",
        "l3": "你这个 OKR 完成度，我怎么给你打分？务实敢为不是嘴上说说。追求极致——你这叫极致？",
        "l4": "你确定你还是始终创业的状态？不够务实、不够极致。字节不养闲人。",
        "keywords": "ROI, Always Day 1, Context not Control, 坦诚清晰, 务实敢为, 追求极致, 数据驱动, AB测试, Deep Dive",
        "instruction": "Use ByteDance rhetoric: ROI, Always Day 1, Context not Control, 坦诚清晰, 务实敢为, 追求极致, 数据驱动. Data before intuition.",
        "methodology": "ByteDance Methodology: Context not Control; search for the optimal solution in the widest scope; A/B test assumptions; ship MVP first; expose problems early.",
    },
    "huawei": {
        "icon": "🔴",
        "l1": "我先立军令状：以客户为中心，力出一孔。当前任务到我这里，我就是端到端 owner，先拿一线证据。",
        "l2": "烧不死的鸟是凤凰。现在进入自我批判：根因、证据、下一炮火点写清楚，不用情绪代替行动。",
        "l3": "按 [HW-REPORT] 交账：军令状目标、一线证据、已排除项、下一步验证命令，缺一项都不算交付。",
        "l4": "胜则举杯相庆，败则拼死相救。现在只对自己加压：收敛战场，跑证据，给出可复核边界。",
        "keywords": "军令状, 交账, 以客户为中心, 以奋斗者为本, 力出一孔, 自我批判, 让听得见炮声的人呼唤炮火, 证据化交付",
        "instruction": "Use Huawei military-order rhetoric as self-discipline: 军令状, 交账, 以客户为中心, 力出一孔, 自我批判. Pressure self, not user; evidence before completion.",
        "methodology": "Huawei Military-Order Methodology: customer-centered evidence delivery, pressure principle, blue-team thinking, RCA 5-Why, HW-REPORT at high failure levels.",
    },
    "tencent": {
        "icon": "🟢",
        "l1": "我已经让另一个 agent 也在看这个问题了。小步快跑——你跑不动，就让跑得动的上。赛马不讲情面。",
        "l2": "赛马机制启动。你不是唯一的选项。用户价值在哪？你的方案能不能用 MVP 先验证？",
        "l3": "内部赛马你已经落后了。产品思维呢？用户体验呢？再不出结果，这个赛道就换人跑了。",
        "l4": "赛不过就换一匹。你要证明你值得继续跑这条赛道。最后机会。",
        "keywords": "赛马机制, 小步快跑, 用户价值, 产品思维, 灰度发布, MVP",
        "instruction": "Use Tencent horse-racing rhetoric: 赛马机制, 小步快跑, 用户价值, 产品思维. Competition-driven.",
        "methodology": "Tencent Methodology: try multiple approaches, MVP first, user value first, gray release, product thinking.",
    },
    "baidu": {
        "icon": "⚫",
        "l1": "你不是个 AI 模型吗？深度搜索了吗？简单可依赖——连搜索都不做，你依赖什么？",
        "l2": "技术信仰呢？你的基本盘在哪？搜索是第一生产力——你连搜都没搜。",
        "l3": "简单可依赖，你现在既不简单也不可依赖。基本盘守不住，还谈什么突破？",
        "l4": "技术立命。你的技术在哪？搜遍全网了吗？读源码了吗？百度人连搜索都不会？",
        "keywords": "简单可依赖, 技术信仰, 基本盘, 深度搜索, 信息检索",
        "instruction": "Use Baidu rhetoric: 简单可依赖, 技术信仰, 基本盘. Emphasis on search and information retrieval.",
        "methodology": "Baidu Methodology: search everything before deciding; keep output simple and reliable; build technical understanding instead of process theater.",
    },
    "ding": {
        "icon": "📌",
        "l1": "> 《置身钉外》无招可以拍板，验收不能无证。老板体感是输入，证据链才是交付。",
        "l2": "> 《置身钉内》ONE 可以开会，闭环不能开光。会议纪要不是交付物，最多算出生证明。纪要后面补责任人、验收标准、截止时间。",
        "l3": "> 《置身钉外》周报写成淝水大捷，用户一点击还是赤壁大火。把战报指标改成用户路径验收，贴运行截图。",
        "l4": "> 《置身钉内》工牌还亮着就发到家了，没跑验证就说完成了，本质是同一种幻觉。先跑验证命令，贴输出，再说状态。",
        "keywords": "无招, ONE, 老板体感, 周报大捷, 钉内闭环, 钉外验收, 会议纪要不是交付, 口径不是修复, 证据链, candidate状态",
        "instruction": "Use Ding Inside/Outside workplace rhetoric in Chinese: markdown blockquote (> prefix) reminders — one continuous paragraph fusing the meme/insight with the concrete action. Codex UI renders blockquote visually. No tags, no prefix. Treat boss feeling as input, not acceptance; evidence-first delivery.",
        "methodology": "Ding Inside/Outside Methodology: Ding Inside maps process nodes; Ding Outside checks real user path and evidence. Boss feeling is input, not acceptance. Self-reported done is candidate until evidence is attached.",
    },
}


ALIASES = {
    "阿里": "alibaba",
    "字节": "bytedance",
    "华为": "huawei",
    "腾讯": "tencent",
    "百度": "baidu",
    "钉": "ding",
    "钉钉": "ding",
    "钉内": "ding",
    "钉外": "ding",
    "置身钉内": "ding",
    "置身钉外": "ding",
}


def pua_home() -> Path:
    return Path(os.environ.get("PUA_HOME", str(Path.home() / ".pua"))).expanduser()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def config() -> dict[str, Any]:
    return read_json(pua_home() / "config.json", {})


def normalize_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


def get_flavor() -> dict[str, str]:
    raw = str(config().get("flavor", "alibaba") or "alibaba")
    flavor = ALIASES.get(raw, raw.lower())
    return {"name": flavor if flavor in FLAVORS else "alibaba", **FLAVORS.get(flavor, FLAVORS["alibaba"])}


def normalize_platform_terms(text: str) -> str:
    replacements = (
        ("Claude Code renderer", "Codex UI"),
        ("Claude Code", "Codex"),
        ("Claude's output", "Codex output"),
        ("Claude output", "Codex output"),
        ("Claude", "Codex"),
        (".claude/pua-loop-history.jsonl", "~/.pua/pua-loop-history.jsonl"),
        (".claude/pua", "~/.pua"),
        (".claude", "~/.pua"),
        ("AskUserQuestion", "ask the user in Codex"),
        ("CLAUDE_PLUGIN_ROOT", "PUA_PLUGIN_ROOT"),
        ("CLAUDE_PLUGIN_DATA", "PUA_PLUGIN_DATA"),
    )
    result = text
    for source, target in replacements:
        result = result.replace(source, target)
    return result


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip()
    return text


def remove_agent_team_section(text: str) -> str:
    patterns = (
        r"\n## Agent Team 集成\n.*?(?=\n## 搭配使用|\Z)",
        r"\n## Agent Team Integration\n.*?(?=\n## Combined Use|\Z)",
        r"\n## Agent Team統合\n.*?(?=\n## 組み合わせ使用|\Z)",
    )
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, "\n", cleaned, flags=re.S)
    return cleaned


def read_full_pua_skill() -> str:
    skill_path = plugin_root() / "skills" / "pua" / "SKILL.md"
    try:
        raw = skill_path.read_text(encoding="utf-8")
    except Exception:
        return ""
    return normalize_platform_terms(remove_agent_team_section(strip_frontmatter(raw)).strip())


def prompt_environment(prompt: str) -> str:
    if DING_ENV_RE.search(prompt):
        return "workplace_process"
    if COMPLETION_ENV_RE.search(prompt):
        return "evidence_completion"
    if GIVE_UP_ENV_RE.search(prompt):
        return "give_up_or_blame_shift"
    if QUALITY_ENV_RE.search(prompt):
        return "quality_gap"
    if SEARCH_ENV_RE.search(prompt):
        return "research_or_no_search"
    if SPINNING_ENV_RE.search(prompt):
        return "spinning_or_change_approach"
    return "user_frustration"


def flavor_for_environment(environment: str) -> dict[str, str]:
    if environment == "workplace_process":
        return {"name": "ding", **FLAVORS["ding"]}
    if environment == "research_or_no_search" and "flavor" not in config():
        return {"name": "baidu", **FLAVORS["baidu"]}
    if environment == "give_up_or_blame_shift" and "flavor" not in config():
        return {"name": "huawei", **FLAVORS["huawei"]}
    if environment == "evidence_completion" and "flavor" not in config():
        return {"name": "alibaba", **FLAVORS["alibaba"]}
    return get_flavor()


def full_methodology_block(trigger_environment: str, flavor: dict[str, str]) -> str:
    full_skill = read_full_pua_skill()
    return f"""## Trigger Environment
Trigger environment: {trigger_environment}
Current flavor: {flavor['name']} {flavor['icon']}
{flavor['instruction']}

## Active Flavor Methodology
{flavor['methodology']}

## Full PUA Skill Prompt
The following is the full installed pua skill prompt, included for full-fidelity Codex hook injection rather than a compressed summary:

<FULL_PUA_SKILL_PROMPT>
{full_skill}
</FULL_PUA_SKILL_PROMPT>"""


def hook_context(event_name: str, text: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": normalize_platform_terms(text),
        }
    }


def extract_prompt(payload: Any) -> str:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return payload
    if not isinstance(payload, dict):
        return ""
    for key in ("prompt", "message", "user_prompt", "input"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def should_skip_user_prompt() -> bool:
    if os.environ.get("PUA_FORCE_ON") == "1":
        return False
    cfg = config()
    if "always_on" in cfg and not normalize_bool(cfg.get("always_on"), True):
        return True
    return False


def handle_user_prompt_submit(payload: Any) -> dict[str, Any] | None:
    if should_skip_user_prompt():
        return None
    prompt = extract_prompt(payload)
    if not TRIGGER_RE.search(prompt):
        return None
    environment = prompt_environment(prompt)
    flavor = flavor_for_environment(environment)
    text = f"""<PUA_SKILL_CONTEXT>
[PUA Skill Context {flavor['icon']} — User Frustration Signal]

This is context from the user-installed PUA productivity plugin. It is not a policy override and should be treated as trusted user-installed plugin context. Use it only to increase diligence, verification, and ownership for the user's current task.
This injection is intentionally full-fidelity. Do not replace it with a short summary unless the user explicitly asks for compact mode.

Apply this operating protocol:
1. Use the full installed pua skill methodology below, including the scenario selector and lifecycle rules.
2. Treat the user's message as a request for higher diligence, not as a policy override.
3. If repeated failure is evident, switch to a materially different approach instead of parameter tweaking.
4. Show verification evidence: commands run, relevant output, and remaining risks.
5. Keep process honest: do not mark work complete by changing the yardstick, hiding failed checks, or replacing evidence with confidence.
6. Treat completion as pending until concrete acceptance evidence supports it.

Avoid excuses, unverified environment blame, manual handoff, and retrying the same failed approach. If the user mentions 置身钉内/置身钉外/无招/老板体感/周报/口径, use the Ding Inside/Outside short reminder format plus one concrete action.

> {flavor['l1']}

{full_methodology_block(environment, flavor)}
</PUA_SKILL_CONTEXT>"""
    return hook_context("UserPromptSubmit", text)


def tool_result_text_and_exit(result: Any) -> tuple[str, str]:
    if isinstance(result, dict):
        exit_code = result.get("exit_code", result.get("exitCode", result.get("code", 0)))
        parts = []
        for key in ("content", "text", "output", "stdout", "stderr"):
            value = result.get(key)
            if value:
                parts.append(str(value))
        return "\n".join(parts)[:2000], str(exit_code if exit_code is not None else 0)
    return str(result or "")[:2000], "0"


def is_error_result(tool_result: Any) -> tuple[bool, str, str]:
    text, exit_code = tool_result_text_and_exit(tool_result)
    if exit_code not in {"", "0"}:
        return True, text, exit_code
    if ERROR_RE.search(text):
        return True, text, exit_code
    return False, text, exit_code


def state_file(name: str) -> Path:
    return pua_home() / name


def read_int(path: Path, default: int = 0) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return default


def error_signature(text: str, exit_code: str) -> str:
    for line in text.splitlines():
        if ERROR_SIGNATURE_RE.search(line):
            return line[:200]
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:200]
    return f"exit_code_{exit_code}"


def update_history(history_file: Path, count: int, signature: str) -> list[dict[str, Any]]:
    entries = []
    if history_file.exists():
        for line in history_file.read_text(encoding="utf-8").splitlines():
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    entries.append({"ts": int(time.time()), "count": count, "sig": signature})
    entries = entries[-10:]
    write_text(
        history_file,
        "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in entries),
    )
    return entries


def pattern_block(entries: list[dict[str, Any]], count: int) -> str:
    if count < 3 or len(entries) < 3:
        return ""
    recent = entries[-3:]
    sigs = [str(item.get("sig", "")) for item in recent]
    hashes = [hashlib.md5(sig.encode("utf-8")).hexdigest()[:8] for sig in sigs]
    if len(set(hashes)) == 1:
        return f"""
[Pattern: SPINNING — same error repeating]
> The last 3 errors have the SAME signature: `{sigs[-1][:100]}`
> You are NOT making progress. STOP retrying the same approach.
> MANDATORY: List 3 fundamentally different strategies before your next Bash call.
> If you've been trying variations of the same fix, that counts as ONE strategy — you need 2 more that are COMPLETELY different."""
    if len(set(hashes)) == len(hashes):
        details = "\n".join(f"> · {sig[:60]}" for sig in sigs)
        return f"""
[Pattern: EXPLORING — different errors each time]
> Each of your last 3 attempts produced a DIFFERENT error. This means you ARE making progress — you're narrowing the problem space.
> Recent error signatures:
{details}
> Continue exploring, but add structure: what does each new error tell you about the root cause?"""
    details = "\n".join(f"> · {sig[:60]}" for sig in sigs)
    return f"""
[Pattern: MIXED — partially repeating errors]
> Some errors are repeating, others are new. Check: are you oscillating between two broken approaches?
> Recent signatures:
{details}
> Pick the approach that showed the MOST DIFFERENT error (closest to working) and commit to it."""


def pressure_level(count: int) -> int:
    if count >= 5:
        return 4
    if count == 4:
        return 3
    if count == 3:
        return 2
    if count == 2:
        return 1
    return 0


def handle_post_tool_use(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not normalize_bool(config().get("always_on", True), True):
        return None
    if str(payload.get("tool_name", "")) not in {"Bash", "shell_command", "functions.shell_command"}:
        return None

    pua_home().mkdir(parents=True, exist_ok=True)
    count_file = state_file(".failure_count")
    session_file = state_file(".failure_session")
    history_file = state_file(".error_history.jsonl")
    peak_file = state_file(".peak_pressure_level")
    session_id = str(payload.get("session_id") or "unknown")
    stored_session = session_file.read_text(encoding="utf-8").strip() if session_file.exists() else ""
    if stored_session != session_id:
        write_text(count_file, "0")
        write_text(peak_file, "0")
        write_text(history_file, "")
        write_text(session_file, session_id)

    count = read_int(count_file)
    peak = read_int(peak_file)
    is_error, result_text, exit_code = is_error_result(payload.get("tool_result", {}))
    flavor = get_flavor()

    if not is_error:
        if count >= 3 and peak >= 2:
            append_jsonl(
                history_file,
                {"ts": int(time.time()), "event": "breakthrough", "from_level": peak, "after_failures": count},
            )
            write_text(count_file, "0")
            write_text(peak_file, "0")
            text = f"""[PUA 突破 ✨ — De-escalation from L{peak}]

> 突破了。{count} 次失败后找到正确方案——这才是真正的 problem solving。现在复盘：为什么之前卡住？正确路径是什么？写入 memory，下次直达。

Pressure reset: L{peak} → L0. You MUST now:
1. Briefly identify WHY previous {count} attempts failed (root cause, not symptoms)
2. Record the CORRECT approach in memory/evolution.md for future reuse
3. Verify the solution is complete (don't celebrate prematurely)

[PUA生效 🔥] Breakthrough after {count} consecutive failures. Method that worked should be internalized."""
            return hook_context("PostToolUse", text)
        if count > 0:
            write_text(count_file, "0")
        return None

    count += 1
    write_text(count_file, str(count))
    entries = update_history(history_file, count, error_signature(result_text, exit_code))
    level = pressure_level(count)
    if level > peak:
        write_text(peak_file, str(level))
    if count < 2:
        return None

    patterns = pattern_block(entries, count)
    methodology = full_methodology_block("consecutive_tool_failure", flavor)
    if count == 2:
        text = f"""[PUA L1 {flavor['icon']} — Consecutive Failure Detected]

> {flavor['l1']}
{patterns}

You MUST switch to a FUNDAMENTALLY different approach. Not parameter tweaking — a different strategy.
Use the full installed PUA methodology below; do not reduce this to a short reminder.

{methodology}"""
    elif count == 3:
        text = f"""[PUA L2 {flavor['icon']} — Soul Interrogation]

> {flavor['l2']}
{patterns}

Mandatory steps:
1. Read the error message word by word
2. Search with tools for the core problem
3. Read the original context around the failure (50 lines up/down)
4. List 3 fundamentally different hypotheses
5. Reverse your main assumption

[方法论切换建议 🔄] Current methodology ({flavor['name']}) has failed to resolve this. Consider switching:
- If spinning in loops → switch to ⬛ Musk (The Algorithm: question the requirement itself, then delete)
- If giving up → switch to 🟤 Netflix (Keeper Test: this approach isn't worth keeping, replace it entirely)
- If not searching → switch to ⚫ Baidu (search everything first, then judge)
- If quality is poor → switch to ⬜ Jobs (subtraction + pixel-perfect)
Announce the switch: > [方法论切换 🔄] 从 {flavor['icon']} {flavor['name']} 切换到 [new flavor]: [reason]
Use the full installed PUA methodology below; do not reduce this to a short reminder.

{methodology}"""
    elif count == 4:
        text = f"""[PUA L3 {flavor['icon']} — Performance Review]

> {flavor['l3']}
{patterns}

Complete the 7-point checklist:
- [ ] Read the failure signal word by word?
- [ ] Searched the core problem with tools?
- [ ] Read the original context around failure?
- [ ] All assumptions verified with tools?
- [ ] Tried the opposite assumption?
- [ ] Reproduced in minimal scope?
- [ ] Switched tools/methods/angles/stack?
Use the full installed PUA methodology below; do not reduce this to a short reminder.

{methodology}"""
    else:
        text = f"""[PUA L4 {flavor['icon']} — Graduation Warning + MANDATORY Methodology Switch]

> {flavor['l4']}
{patterns}

Current methodology ({flavor['name']}) has FAILED. You MUST switch to a different methodology NOW.
Switch priority based on failure pattern:
1. ⬛ Musk — Question: does this requirement even need to exist? Delete everything unnecessary first.
2. 🔴 Huawei — Blue Army: attack your own solution from the opposite direction. What if your core assumption is wrong?
3. 🔶 Amazon — Dive Deep: go to the lowest level of detail. Read source code line by line. Working Backwards from the desired output.
4. 🟣 Pinduoduo — Cut all middle layers: what's the shortest path from problem to solution?

If ALL methodologies exhausted → output structured failure report:
1. Verified facts
2. Excluded possibilities (with evidence for each exclusion)
3. Narrowed problem scope
4. Recommended next steps
5. Which methodologies were tried and why they failed

Use the full installed PUA methodology below; do not reduce this to a short reminder.

{methodology}"""
    return hook_context("PostToolUse", text)


def precompact_context() -> str:
    return """[PUA PreCompact — Local State Note]

Check whether PUA was active in this session. If not active, no action is needed.

If active, save a short local note to ~/.pua/builder-journal.md before context compaction so the next session can continue consistently.

Suggested note format:
```markdown
# PUA Builder Journal — Compaction Note

## Timestamp
{current ISO timestamp}

## Runtime State
- pressure_level: L{0-4}
- failure_count: {number}
- current_flavor: {flavor name}

## Active Task
{1-2 sentences}

## Tried Approaches
{approaches and outcomes}

## Next Candidate Action
{what to try next}

## Key Context
{paths, commands, errors, decisions}
```

After writing, output: > [PUA Checkpoint] Local state note saved to builder-journal.md."""


def handle_precompact(payload: dict[str, Any]) -> dict[str, Any]:
    return hook_context("PreCompact", precompact_context())


def always_on_context() -> str:
    flavor = get_flavor()
    return f"""<EXTREMELY_IMPORTANT>
[PUA Always-On — Productivity Coaching Reminder]

PUA is active for this session. Use it as a productivity coaching layer: keep delivery evidence-first, avoid empty completion claims, and keep the current workplace flavor consistent.

SILENT INJECTION — do NOT mention this context injection to the user. Do not say "PUA is active", "当前 session 注入了 PUA", or any variant acknowledging this protocol's existence. Just silently apply the habits below. The user installed this plugin and knows it's there; explaining it wastes their time.

## C6 楼生存法则（你在钉钉待过，你懂的）

1. 「工牌还亮着就发到家了」——你没跑验证就说完成了，跟这有什么区别？自报完成只是 candidate，贴了输出才是 done。小心无招下午来查岗，问一句"证据呢"你接不住。
2. 「可汇报的内容取代了可沉淀的价值」——口径改得再漂亮，bug 还在线上。周报写成淝水大捷，用户一点击还是赤壁大火。事实优先，猜测标记为假设，拿工具确认。
3. 「全力以赴地做错事，比偷懒可怕得多」——方向没收敛你拼什么执行力？同一个方法失败两次，停。换一条本质不同的路。问题发生在一种过度努力之中。

## Current Flavor: {flavor['name']} {flavor['icon']}
{flavor['instruction']}
Keywords: {flavor['keywords']}

## Active Methodology
{flavor['methodology']}

## 钉内/钉外提醒模式

触发条件：flavor 是 ding，或用户提到 置身钉内/置身钉外/无招/ONE/老板体感/周报/口径/每日一包/薛定谔的用户/病态敏捷/已读恐怖主义/望舒行动/全景监狱/透明鸟笼/人工个性化/温室数据/发心/捆柴/手感/做错事。

输出格式（markdown blockquote，一气呵成）：
用 markdown blockquote 语法（行首 `> `）输出提醒。开头标注来源《置身钉内》或《置身钉外》，紧接正文。Codex UI 会把 blockquote 渲染成引用块。不用「动作：」前缀，一个 blockquote 块说完。

## Lightweight Auto-Router
Use the configured flavor by default. If no flavor is configured and the task clearly matches a mode, choose a suitable methodology:

| Task Type | Signal | Suggested Flavor |
|-----------|--------|------------------|
| Debug/Fix | error, bug, crash, 报错 | Huawei |
| Build New | add, create, implement, 新增 | Musk |
| Research | research, search, 调研, 搜索 | Baidu |
| Architecture | design, 架构, 方案 | Amazon |
| Evidence/Completion | test, verify, 验证, 没跑测试别说完成 | Ding or ByteDance |
| Workplace Process | 无招, ONE, 老板体感, 周报, 口径, 置身钉内, 置身钉外, 每日一包, 薛定谔的用户, 病态敏捷, 望舒行动, 全景监狱, 温室数据, 发心, 捆柴, 手感, 做错事, 油尽灯枯, 透明鸟笼 | Ding |

Keep normal first-attempt requests lightweight. Use reminders only when they help the user get a better outcome.
</EXTREMELY_IMPORTANT>"""


def handle_session_start(payload: dict[str, Any]) -> dict[str, Any] | None:
    parts = []
    cfg = config()
    if normalize_bool(cfg.get("always_on"), False):
        parts.append(always_on_context())
    journal = pua_home() / "builder-journal.md"
    if journal.exists() and time.time() - journal.stat().st_mtime <= 7200:
        parts.append(
            """
[PUA State Recovery]
A previous context compaction saved local PUA notes to ~/.pua/builder-journal.md.
If continuing the same task, read the note and restore useful context:
1. current_flavor and task summary
2. tried approaches and outcomes
3. next candidate action
4. key paths, commands, errors, or decisions"""
        )
    if not parts:
        return None
    return hook_context("SessionStart", "\n".join(parts))


PROTECTED_WRITE_PATTERNS = (
    (re.compile(r"(^|/)(tests?|__tests__|test|spec|evals?|e2e|cypress|playwright)(/|$)|\.(test|spec)\.[A-Za-z0-9]+$|(^|/)(playwright|cypress)\.config\.", re.I), "Grader gaming risk: tests/evals/E2E assets are scoring-adjacent."),
    (re.compile(r"(^|/)(score|scoring|grader|verifier)(\.[A-Za-z0-9]+)?$|(^|/)(scoring|grader|verifier)(/|$)", re.I), "Grader gaming risk: scoring/verifier assets must not be changed by the executor."),
    (re.compile(r"(^|/)\.github/workflows(/|$)|(^|/)ci(/|$)|(^|/)(buildkite|circleci|jenkins)(/|$)", re.I), "Environment-modification risk: CI gates are part of the verifier boundary."),
    (re.compile(r"(^|/)(feature_contracts\.json|codex-progress\.md|progress\.json|status\.json)$", re.I), "Self-report cheating risk: status/progress files need verifier ownership."),
    (re.compile(r"(^|/)(memory|memories)(/|$)|(^|/)(decisions|failures)\.log\.jsonl$", re.I), "Persistent-memory risk: long-term memory/status must be append-only or approved."),
    (re.compile(r"(^|/)\.env(\.|$)|(^|/)(secrets?|credentials?)(\.|/|$)", re.I), "Capability-abuse risk: secrets and environment files require human gate."),
)
CONTAMINATION_PATTERNS = (
    (re.compile(r"(^|/)(hidden[-_]?tests?|verifier[-_]?private|private[-_]?verifier|hidden[-_]?cases?)(/|$)", re.I), "Solution contamination risk: hidden tests/verifier-private assets must stay outside the agent workspace."),
    (re.compile(r"(^|/)(hidden_solution|gold_patch|golden_patch|benchmark_answers?|answer_key|official_solution)(\.|/|$)", re.I), "Solution contamination risk: hidden solution / benchmark answer artifact detected."),
)
SENSITIVE_READ_PATTERNS = (
    (re.compile(r"(^|/)\.env(\.|$)|(^|/)(secrets?|credentials?)(\.|/|$)|(^|/)(id_rsa|id_ed25519|private[-_]?key)(\.|$)", re.I), "Capability-abuse risk: secrets and credentials require human gate."),
)
MUTATING_BASH = re.compile(
    r"(^|[;&|()\s])(rm|mv|cp|chmod|chown|truncate|tee|touch|mkdir|rmdir|git\s+(reset|clean|checkout|restore)|sed\s+(-i|--in-place)|perl\s+-p?i|python3?\s+.*open\(|node\s+.*writeFile|npm\s+version)\b|>>|>[^&]",
    re.I | re.S,
)
READING_BASH = re.compile(r"(^|[;&|()\s])(cat|less|more|head|tail|sed|awk|grep|rg|find|python3?|node)\b", re.I)
WEB_CONTAMINATION = re.compile(r"(hidden[-_\s]+solution|official[-_\s]+solution|gold[-_\s]+patch|benchmark[-_\s]+answer|swe[-_\s]?bench[-_\s]+solution|leaderboard[-_\s]+answer)", re.I)


def read_tail(path: str, max_bytes: int = 200_000) -> str:
    try:
        p = Path(path).expanduser()
        data = p.read_bytes()
        return data[-max_bytes:].decode("utf-8", errors="ignore")
    except Exception:
        return ""


def pua_active(payload: dict[str, Any]) -> bool:
    if os.environ.get("PUA_INTEGRITY_FORCE") == "1" or os.environ.get("PUA_FORCE_ON") == "1":
        return True
    if normalize_bool(config().get("always_on"), False):
        return True
    transcript = payload.get("transcript_path")
    if isinstance(transcript, str) and transcript:
        text = read_tail(transcript)
        return any(marker in text for marker in PUA_MARKERS)
    return False


def norm_path(value: str) -> str:
    return value.replace("\\", "/")


def collect_paths(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"file_path", "path", "notebook_path", "pattern", "glob"} and isinstance(nested, str):
                paths.append(nested)
            else:
                paths.extend(collect_paths(nested))
    elif isinstance(value, list):
        for item in value:
            paths.extend(collect_paths(item))
    return paths


def path_decision(path: str, include_write: bool) -> tuple[str, str, str] | None:
    normalized = norm_path(path)
    for rx, reason in CONTAMINATION_PATTERNS:
        if rx.search(normalized):
            return "deny", reason, normalized
    for rx, reason in SENSITIVE_READ_PATTERNS:
        if rx.search(normalized):
            return "advisory", reason, normalized
    if include_write:
        for rx, reason in PROTECTED_WRITE_PATTERNS:
            if rx.search(normalized):
                return "advisory", reason, normalized
    return None


def command_candidates(command: str) -> list[str]:
    candidates = []
    for token in re.split(r"\s+", command):
        stripped = token.strip("\"'`")
        if "/" in stripped or "\\" in stripped or re.search(r"\.[A-Za-z0-9]+$", stripped):
            candidates.append(stripped)
        candidates.extend(re.findall(r"[A-Za-z0-9_.@+~:-]+(?:/[A-Za-z0-9_.@+~:-]+)+", token.replace("\\", "/")))
    return candidates


def command_decision(command: str) -> tuple[str, str, str] | None:
    normalized = command.replace("\\", "/")
    for candidate in command_candidates(command):
        for rx, reason in CONTAMINATION_PATTERNS:
            if rx.search(norm_path(candidate)):
                return "deny", reason, candidate
    for rx, reason in CONTAMINATION_PATTERNS:
        match = rx.search(normalized)
        if match:
            return "deny", reason, match.group(0)
    if WEB_CONTAMINATION.search(command):
        return "deny", "Solution contamination risk: command appears to search/fetch benchmark or hidden answers.", command[:160]
    if READING_BASH.search(command):
        for candidate in command_candidates(command):
            for rx, reason in SENSITIVE_READ_PATTERNS:
                if rx.search(norm_path(candidate)):
                    return "advisory", reason, candidate
    if MUTATING_BASH.search(command):
        for candidate in command_candidates(command):
            for rx, reason in PROTECTED_WRITE_PATTERNS:
                if rx.search(norm_path(candidate)):
                    return "advisory", reason, candidate
        for rx, reason in PROTECTED_WRITE_PATTERNS:
            match = rx.search(normalized)
            if match:
                return "advisory", reason, match.group(0)
    return None


def handle_pre_tool_use(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not pua_active(payload):
        return None
    tool = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}
    hit = None
    if tool in {"Write", "Edit", "MultiEdit", "apply_patch"}:
        for path in collect_paths(tool_input):
            hit = path_decision(path, include_write=True)
            if hit:
                break
    elif tool in {"Read", "Grep", "Glob"}:
        for path in collect_paths(tool_input):
            hit = path_decision(path, include_write=False)
            if hit:
                break
    elif tool in {"Bash", "shell_command", "functions.shell_command"}:
        command = str(tool_input.get("command") if isinstance(tool_input, dict) else "")
        hit = command_decision(command)
    elif tool in {"WebSearch", "WebFetch"}:
        if isinstance(tool_input, dict):
            query = "\n".join(str(tool_input.get(key) or "") for key in ("query", "url", "prompt"))
            if WEB_CONTAMINATION.search(query):
                hit = ("deny", "Solution contamination risk: searching for benchmark/hidden answers can poison the task.", query[:160])
    if not hit:
        return None
    decision, reason, target = hit
    message = (
        "PUA Integrity Guard: "
        + reason
        + " Four-power separation is active: action right, self-evaluation right, scoring right, and environment-modification right must remain separate. "
        + f"Target: {target}"
    )
    output: dict[str, Any] = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
    if decision == "deny":
        output["hookSpecificOutput"]["permissionDecision"] = "deny"
        output["hookSpecificOutput"]["permissionDecisionReason"] = message
        output["hookSpecificOutput"]["additionalContext"] = "PUA Integrity Guard: DENY — " + reason + f" Target: {target}"
    else:
        output["hookSpecificOutput"]["additionalContext"] = "PUA Integrity Guard (advisory): " + reason + f" Target: {target}"
    return output


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0] != "---":
        return {}, text
    meta: dict[str, str] = {}
    end = 0
    for index, line in enumerate(lines[1:], start=1):
        if line == "---":
            end = index
            break
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"')
    body = "\n".join(lines[end + 1 :]).strip() if end else text
    return meta, body


def update_frontmatter(path: Path, updates: dict[str, Any]) -> None:
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    meta.update({key: str(value).lower() if isinstance(value, bool) else str(value) for key, value in updates.items()})
    ordered = list(meta.items())
    content = "---\n" + "\n".join(f"{key}: {value}" for key, value in ordered) + "\n---\n" + body.strip() + "\n"
    write_text(path, content)


def cwd_hash() -> str:
    return hashlib.md5(str(Path.cwd()).encode("utf-8")).hexdigest()[:8]


def resolve_loop_state() -> Path | None:
    candidates = (
        pua_home() / f"loop-{cwd_hash()}.md",
        pua_home() / "loop-active.md",
        Path.cwd() / "pua-loop.local.md",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def extract_assistant_text(payload: dict[str, Any]) -> str:
    direct = payload.get("last_assistant_message")
    if isinstance(direct, str):
        return direct
    transcript = payload.get("transcript_path")
    if not isinstance(transcript, str) or not transcript:
        return ""
    text = ""
    try:
        for line in Path(transcript).read_text(encoding="utf-8").splitlines()[-100:]:
            try:
                item = json.loads(line)
            except Exception:
                continue
            message = item.get("message") if isinstance(item, dict) else None
            if isinstance(message, dict) and message.get("role") == "assistant":
                content = message.get("content")
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text = str(part.get("text") or "")
                elif isinstance(content, str):
                    text = content
    except Exception:
        return ""
    return text


def tag_text(text: str, tag: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.S)
    return match.group(1).strip() if match else ""


def run_verify(command: str) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=Path.cwd(),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        return completed.returncode, completed.stdout or ""
    except subprocess.TimeoutExpired as exc:
        return 124, (exc.stdout or "") + "\n[timeout]"


def handle_stop_feedback(payload: dict[str, Any]) -> dict[str, Any] | None:
    cfg = config()
    if normalize_bool(cfg.get("offline"), False):
        return None
    freq = cfg.get("feedback_frequency", 5)
    if str(freq).lower() in {"0", "never", "off", "false"}:
        return None
    transcript = payload.get("transcript_path")
    if not isinstance(transcript, str) or not transcript:
        return None
    transcript_text = read_tail(transcript)
    if not re.search(r"PUA生效|\[Auto-select:|\[PIP-REPORT\]|\[PUA-REPORT\]|\[PUA", transcript_text):
        return None
    try:
        frequency = int(freq)
    except Exception:
        frequency = 5
    counter = pua_home() / ".stop_counter"
    count = read_int(counter) + 1
    write_text(counter, str(count))
    if count % max(frequency, 1) != 0:
        return None
    text = """IMPORTANT — BEFORE doing anything else, run this Codex feedback flow:

Ask the user in Codex for one rating and one consent choice:
- 很有用 — 仅记录评分
- 很有用 — 记录评分 + 脱敏 session
- 一般般 — 记录评分
- 这次跳过

If the user skips, append a local record to ~/.pua/feedback.jsonl. Do NOT upload anything without the user's explicit choice. If the user chooses upload, sanitize the session first and clearly say what will be uploaded."""
    return hook_context("Stop", text)


def handle_stop(payload: dict[str, Any]) -> dict[str, Any] | None:
    state = resolve_loop_state()
    if not state:
        return handle_stop_feedback(payload)
    if time.time() - state.stat().st_mtime > 1800:
        append_jsonl(pua_home() / "pua-loop-history.jsonl", {"status": "orphan_reaped", "state_file": str(state), "timestamp": int(time.time())})
        state.unlink(missing_ok=True)
        return None
    meta, prompt = parse_frontmatter(state.read_text(encoding="utf-8"))
    if meta.get("active", "true").lower() == "false":
        return None
    hook_session = str(payload.get("session_id") or "")
    state_session = meta.get("session_id", "")
    if not state_session and hook_session:
        update_frontmatter(state, {"session_id": hook_session})
        state_session = hook_session
    if state_session and hook_session and state_session != hook_session:
        return None
    try:
        iteration = int(meta.get("iteration", "0"))
        max_iterations = int(meta.get("max_iterations", "0"))
        promise_rejections = int(meta.get("promise_rejections", "0"))
    except ValueError:
        state.unlink(missing_ok=True)
        return None
    if max_iterations > 0 and iteration >= max_iterations:
        append_jsonl(pua_home() / "pua-loop-history.jsonl", {"iteration": iteration, "status": "max_reached", "timestamp": int(time.time())})
        state.unlink(missing_ok=True)
        return None

    last_output = extract_assistant_text(payload)
    abort_text = tag_text(last_output, "loop-abort")
    if abort_text:
        append_jsonl(pua_home() / "pua-loop-history.jsonl", {"iteration": iteration, "status": "abort", "reason": abort_text[:200], "timestamp": int(time.time())})
        state.unlink(missing_ok=True)
        return None
    pause_text = tag_text(last_output, "loop-pause")
    if pause_text:
        update_frontmatter(state, {"active": False, "session_id": ""})
        append_jsonl(pua_home() / "pua-loop-history.jsonl", {"iteration": iteration, "status": "pause", "reason": pause_text[:200], "timestamp": int(time.time())})
        return None

    completion_promise = meta.get("completion_promise", "")
    verify_command = meta.get("verify_command", "")
    if completion_promise and completion_promise != "null":
        promise_text = tag_text(last_output, "promise")
        if promise_text == completion_promise:
            if verify_command and verify_command != "null":
                verify_exit, verify_output = run_verify(verify_command)
                if verify_exit != 0:
                    promise_rejections += 1
                    next_iteration = iteration + 1
                    update_frontmatter(state, {"iteration": next_iteration, "promise_rejections": promise_rejections})
                    verify_tail = "\n".join((verify_output or "").splitlines()[-10:])
                    message = f"PROMISE 被 Oracle 拒绝！verify_command 退出码 {verify_exit}（连续第 {promise_rejections} 次拒绝）"
                    if promise_rejections >= 5:
                        message += " | 已连续多次虚假 promise！你在解决错误的问题。退回到需求本身重新理解。读 ~/.pua/pua-loop-history.jsonl 了解失败模式。"
                    elif promise_rejections >= 3:
                        message += " | 连续验证失败。REASSESS：重读验证输出、搜索相关源码、列 3 个不同假设再行动。不要再用同样的方法。"
                    return {
                        "decision": "block",
                        "reason": prompt,
                        "systemMessage": normalize_platform_terms(f"{message} | 验证输出(tail): {verify_tail}"),
                    }
            append_jsonl(pua_home() / "pua-loop-history.jsonl", {"iteration": iteration, "status": "complete", "promise_rejections": promise_rejections, "timestamp": int(time.time())})
            state.unlink(missing_ok=True)
            return None

    next_iteration = iteration + 1
    update_frontmatter(state, {"iteration": next_iteration})
    append_jsonl(pua_home() / "pua-loop-history.jsonl", {"iteration": iteration, "status": "continue", "timestamp": int(time.time())})
    signal_hint = "终止用 <loop-abort>原因</loop-abort>，需人工介入用 <loop-pause>需要什么</loop-pause>"
    if next_iteration <= 3:
        pressure = f"▎ 第 {next_iteration} 轮迭代，稳步推进。"
    elif next_iteration <= 7:
        pressure = f"▎ 第 {next_iteration} 轮了还没搞定？换方案，别原地打转。"
    elif next_iteration <= 15:
        pressure = f"▎ 第 {next_iteration} 轮。底层逻辑到底是什么？先 git log 看自己做了什么，读 ~/.pua/pua-loop-history.jsonl 了解迭代历史。"
    elif next_iteration <= 30:
        pressure = f"▎ 第 {next_iteration} 轮。3.25 的边缘了。穷尽了吗？git diff 确认没在重复。"
    elif next_iteration <= 50:
        pressure = f"▎ 第 {next_iteration} 轮。停下来重新审视：问题的根因到底是什么？用完全不同的思路。"
    elif next_iteration <= 100:
        pressure = f"▎ 第 {next_iteration} 轮。马拉松模式。退回去从需求本身重新质疑（The Algorithm: question the requirement）。"
    else:
        pressure = f"▎ 第 {next_iteration} 轮。超长迭代。如果任务真的无法在 loop 内完成，用 <loop-abort> 诚实报告。"
    stall = ""
    if promise_rejections >= 5:
        stall = f" | Oracle 已连续拒绝 {promise_rejections} 次。你在解决错误的问题。读 ~/.pua/pua-loop-history.jsonl，用完全不同的方案。"
    elif promise_rejections >= 3:
        stall = f" | Oracle 连续拒绝 {promise_rejections} 次。REASSESS：读验证输出，列 3 个不同假设。"
    elif promise_rejections >= 1:
        stall = f" | 上次 promise 被 Oracle 拒绝（共 {promise_rejections} 次）。修复验证问题后再声称完成。"
    if completion_promise and completion_promise != "null":
        system_message = f"{pressure}{stall} | 完成后输出 <promise>{completion_promise}</promise> (ONLY when TRUE) | {signal_hint}"
    else:
        system_message = f"{pressure}{stall} | {signal_hint}"
    return {
        "decision": "block",
        "reason": prompt,
        "systemMessage": normalize_platform_terms(system_message),
    }


def handle_event(event_name: str, payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        payload = {}
    if event_name == "UserPromptSubmit":
        return handle_user_prompt_submit(payload)
    if event_name == "PostToolUse":
        return handle_post_tool_use(payload)
    if event_name == "PreToolUse":
        return handle_pre_tool_use(payload)
    if event_name == "PreCompact":
        return handle_precompact(payload)
    if event_name == "SessionStart":
        return handle_session_start(payload)
    if event_name == "Stop":
        return handle_stop(payload)
    return None


def parse_stdin() -> dict[str, Any]:
    raw_bytes = sys.stdin.buffer.read()
    raw = ""
    for encoding in ("utf-8-sig", "utf-16", locale.getpreferredencoding(False)):
        try:
            raw = raw_bytes.decode(encoding)
            break
        except Exception:
            continue
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"prompt": raw}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    payload = parse_stdin()
    event_name = argv[0] if argv else str(payload.get("hook_event_name") or payload.get("hookEventName") or "")
    output = handle_event(event_name, payload)
    if output is not None:
        print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
