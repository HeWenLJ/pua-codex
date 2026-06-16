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
