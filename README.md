# PUA Codex

PUA Codex 是把 `tanweai/pua` 的 Claude Code PUA skill 迁移到 Codex 插件体系后的版本。它提供 Codex-native hooks 和一组同名技能，让 Codex 在反复失败、准备放弃、缺少验证证据、没有继续搜索/读源码、用户明显不满等场景下自动注入更强的排查与交付约束。

这个仓库按 Codex Git marketplace 结构发布，clone 或添加 marketplace 后即可安装，不需要修改用户名路径。

## 功能

- 内置 `pua`、`pua-en`、`pua-ja` 以及 `$pua-on`、`$pua-off`、`$pua-pro`、`$pua-loop`、`$pua-kpi` 等别名技能。
- 通过 `UserPromptSubmit`、`PostToolUse`、`PreToolUse`、`Stop`、`PreCompact` 等 Codex hooks 分发到本地 Python hook 入口。
- 在需要时注入完整 PUA 方法论提示词，而不是只给一句简短提醒。
- 按场景路由不同提示词：失败循环、甩锅环境、质量不达标、没有搜索、缺少验证证据、职场/钉钉语境等。
- hook 命令使用便携启动器：优先读取 `PUA_CODEX_PLUGIN_ROOT`，否则自动在 Codex 插件缓存或 `~/plugins/pua-codex` 中寻找脚本。

## 安装

前提：本机已安装支持插件与 hooks 的 Codex，并且命令行能运行 Python。

推荐通过 SSH 安装：

```powershell
codex plugin marketplace add git@github.com:HeWenLJ/pua-codex.git --ref main
codex plugin add pua-codex@pua-codex
```

如果你的网络拦截了 GitHub SSH 22 端口，可以改用 HTTPS：

```powershell
codex plugin marketplace add https://github.com/HeWenLJ/pua-codex.git --ref main
codex plugin add pua-codex@pua-codex
```

安装后重新打开一个 Codex 会话。第一次启用 hooks 时，Codex 可能会要求你查看并信任 hook 命令；请确认命令来自本仓库后再允许。

## 使用

多数情况下不需要手动调用。出现下面这类语境时，hooks 会自动给模型补充 PUA 方法论上下文：

```text
为什么还不行，换个方法
证据呢？你验证了吗？
不要甩锅环境，继续查
try harder, show evidence
置身钉内，老板体感不对，周报口径怎么闭环
```

也可以手动调用技能或别名：

```text
$pua
$pua-en
$pua-pro
$pua-loop
$pua-off
$pua-on
```

## Skill 入口说明

Codex 插件页里每个 `Pua Codex: ...` 卡片对应下面一个 skill。灰色说明文字来自各自 `SKILL.md` 的 `description`，因此安装后在技能列表里也能直接看到用途。

| Skill | 调用方式 | 作用 |
| --- | --- | --- |
| `pua` | `$pua` | 中文主入口。反复失败、准备放弃、缺少验证、没读源码/没搜索、用户不满时，注入完整大厂 PUA 方法论，要求换方案、查证据、闭环交付。 |
| `pua-en` | `$pua-en` | 英文 PIP / Western big-tech 风格入口。适合英文任务或希望使用 Ownership、Dive Deep、evidence-first 话术时。 |
| `pua-ja` | `$pua-ja` | 日文“詰め”风格入口。用日本企业压力话术强化主动调查、系统调试和证据化完成。 |
| `pua-on` | `$pua-on` | 开启常驻 PUA。写入 `~/.pua/config.json`，设置 `always_on=true`，并恢复默认反馈频率。 |
| `pua-off` | `$pua-off` | 关闭常驻 PUA。设置 `always_on=false` 和 `feedback_frequency=0`，适合暂时不想自动触发时。 |
| `pua-offline` | `$pua-offline` | 开启离线/无反馈模式。设置 `offline=true` 并关闭反馈频率，不删除其他配置。 |
| `pua-flavor` | `$pua-flavor` | 选择或修改话术口味，例如阿里味、字节味、华为味、腾讯味、钉钉味等。 |
| `pua-pro` | `$pua-pro` | 高级控制入口。用于自进化记录、平台遥测、KPI、配置命令等 PUA Pro 功能。 |
| `pua-kpi` | `$pua-kpi` | 生成当前 AI 工作的 KPI / performance report card，用证据给出表现反馈。 |
| `pua-loop` | `$pua-loop` | 建立或运行持续验证循环。适合“继续做直到验证命令通过/满足停止条件”的任务。 |
| `pua-cancel-loop` | `$pua-cancel-loop` | 取消当前 PUA loop，清理 loop 状态/工作区引用，并记录取消证据。 |
| `pua-reap-orphans` | `$pua-reap-orphans` | 清理遗留的 PUA loop/agent 状态，只删除确认是孤儿的记录。 |
| `pua-p7` | `$pua-p7` | P7 高级工程师模式。要求计划、实现、自审、验证，并以 `[P7-COMPLETION]` 交付。 |
| `pua-p9` | `$pua-p9` | P9 技术负责人模式。更偏任务拆解、提示词设计、协调 P8 执行，默认不亲自写代码。 |
| `pua-p10` | `$pua-p10` | P10/CTO 模式。用于战略方向、组织拓扑、技术路线和 P9 管理边界。 |
| `pua-mama` | `$pua-mama` | “妈妈式念叨”模式。保留验证红线，但把表达风格切成更生活化的中文催促。 |
| `pua-yes` | `$pua-yes` | 鼓励优先模式。适合不想要强压语气，但仍要保留验证、闭环和不摆烂约束时。 |
| `pua-survey` | `$pua-survey` | 本地偏好/反馈问卷入口。保存本地回答；任何上传前都会先询问。 |

## 仓库结构

```text
.agents/plugins/marketplace.json     Codex Git marketplace 入口
plugins/pua-codex/.codex-plugin/     插件 manifest
plugins/pua-codex/hooks/             bundled hooks 配置
plugins/pua-codex/scripts/           hook 分发器与便携启动器
plugins/pua-codex/skills/            PUA skills 和别名 skills
plugins/pua-codex/tests/             Python 单元测试
```

## 本地开发验证

在仓库根目录执行：

```powershell
python -m unittest discover -s .\plugins\pua-codex\tests -v
python -m py_compile .\plugins\pua-codex\scripts\pua_hooks.py .\plugins\pua-codex\scripts\pua_hook.py
```

如果你有 Codex 桌面端内置的插件校验脚本，也可以继续验证插件 manifest 与所有 skill：

```powershell
python <validate_plugin.py路径> .\plugins\pua-codex
python <quick_validate.py路径> .\plugins\pua-codex\skills\pua\SKILL.md
```

## 安全说明

Codex hooks 会在本机执行命令。安装任何第三方插件前，都应该检查 `plugins/pua-codex/hooks/hooks.json` 与 `plugins/pua-codex/scripts/` 中的内容，确认自己愿意信任这些本地命令。

## 许可证

本仓库是 `tanweai/pua` 的 Codex 迁移版本。上游许可证和文本授权请以原仓库为准；如果你要公开分发，请先确认原项目的授权要求。
