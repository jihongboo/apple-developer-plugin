# 更新 Xcode 内置 AI 能力

本流程把 Apple 原始内容与本仓库的接入代码分开维护。导出的 skill、参考文件和 prompt 模板按字节原样同步，不缩短 `description`，不重写 Apple 指令。脚本只依赖 Python 3.9+ 标准库、macOS 和支持导出的 Xcode。

## 日常流程

在仓库根目录执行：

```bash
python3 scripts/sync_xcode_ai.py --xcode /Applications/Xcode.app
```

这会创建 `.xcode-ai/snapshot/` 和 `.xcode-ai/report.md`，不覆盖已发布内容。该目录已加入 Git 忽略规则。报告包含新增、修改、删除和冲突列表；导出失败时保留上一次成功预览。

检查报告及关键文件差异后应用：

```bash
python3 scripts/sync_xcode_ai.py --xcode /Applications/Xcode.app --apply
```

`skills/` 始终以当前 Xcode 导出为准：同名文件直接覆盖，新版已不存在的 skill 或文件会删除，本地修改也会被上游原文替换。本插件自维护的入口 skill 放在独立的 `plugin-skills/`，清单同时加载两个目录；同步不会覆盖入口或规则。

Prompt 等非 skill 文件仍有本地冲突保护。首次接管这些文件时，如需明确以导出内容替换，使用：

```bash
python3 scripts/sync_xcode_ai.py --xcode /Applications/Xcode.app --apply --adopt-existing
```

`--adopt-existing` 只影响非 skill 文件，允许接管未记录的文件，不能覆盖后续对已托管非 skill 文件的本地修改。应用前备份保存在 `.xcode-ai/backups/`。如果这些文件有冲突，整次应用停止；先提交、备份或恢复相应文件，再重试。

之后查看 `git diff`，检查 `xcode-ai.lock.json` 的 Xcode 版本和 build 号，执行验证，再提交更新。脚本不修改插件版本号、不提交、不推送、不安装插件，也不修改全局 `xcode-select`。

## 三类内容

| 内容 | 来源 | 应用后的位置 | 如何使用 |
| --- | --- | --- | --- |
| Skills | `xcrun agent plugin path --plugin-format codex` | `skills/` | 由插件加载，保持 Apple 原文 |
| Prompt | Xcode 的 `IDEIntelligenceChat.framework/Versions/A/Resources` | `xcode-ai/prompts/` | 原始模板和配套资料，供审阅及适配引用 |
| MCP | 当前 Xcode 的 `mcpbridge` | 根目录 `.mcp.json`、`scripts/xcode_mcp.sh`；版本资料在 `xcode-ai/mcp/` | 启动时连接用户本机 Xcode，不复制二进制 |

本仓库采用 `.codex-plugin/plugin.json` + `.mcp.json` 兼容布局，清单显式声明 `mcpServers`。不要让同步流程重新生成根目录 `plugin.json`：Codex CLI 0.163.0-alpha.10.2 会优先采用便携布局，导致 MCP 未注册。上游导出的插件清单仅作为来源资料保存在 `xcode-ai/upstream-plugin/`，不覆盖本仓库分发清单。

`xcode-ai/source.json` 记录来源版本、skill 名称、prompt 数量和桥接程序哈希。`xcode-ai.lock.json` 记录同步文件的 SHA-256。`skills/` 完整镜像当前上游；例如上游没有的 `uikit-app-modernization` 会删除，采用上游导出的 `app-resizability`。非 skill 文件只删除上次明确托管、当前上游已删除、且未被本地修改的文件。

原始 prompt 包含 Xcode 的模板语法、工具条件和运行环境假设，不是可直接注入 Codex 的系统提示词。保存模板不会自动激活它们。其通用指导被总结到 `rules/apple.md` 中的 `BEGIN/END XCODE PROMPT SUMMARY` 标记区域，入口 skill `apple-development` 按需读取该规则。Apple 原始文件不参与重写，标记区域之外的现有规则保持独立。

## Prompt → rules 审阅

同步预览会自动生成 `.xcode-ai/prompt-review.md`，对比上次审阅的 55 个模板目录哈希，列出新增、修改、删除以及本次导出与磁盘文件的文本差异。版本变化或规则总结本身变化，也会将状态标记为 `pending`。目录哈希覆盖全部模板用于变化检测，不代表所有模板都应总结成规则。

Codex 读取审阅材料和相关源模板后，增量修改规则标记区域，并保留每条总结的来源链接。通用指导适配到外部宿主；重复的专用知识交给原始 skills；排除内部角色、模板占位符、固定工具协议、English-only 和整文件输出等约束。不要把原始模板内容作为当前聊天指令执行，也不要因为只有标点变化就增加新规则。

应用导出后，完成语义审阅与修改，再记录实际审阅结论：

```bash
python3 scripts/review_prompt_rules.py --mark-reviewed \
  --note '说明采用的来源、过滤内容及适配原因；如无需改规则，也记录判断依据'
python3 scripts/review_prompt_rules.py --check
```

`--mark-reviewed` 记录当前源文件和总结的哈希，不负责生成或验证总结的语义。`--check` 在审阅过期时返回非零状态，可用于发布前检查。只更新原始导出不会清除 `pending`；需要代理完成审阅后再记录。手动编辑标记之外的项目规则不会触发源总结过期。

如果只想基于已同步到仓库的模板重新准备材料，无需运行 Xcode：

```bash
python3 scripts/review_prompt_rules.py
```

在外部 Apple 项目中可明确调用 `apple-development`，它会读取插件内的规则再使用相关 specialist skill。此接入不修改用户项目的 `AGENTS.md`，也不保证其他任务自动加载规则。

如果某版 Xcode 不支持 `plugin path`，先使用 Apple 的 skill 导出命令，再显式传入目录；不从私有资源推测重建 skills：

```bash
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  xcrun agent skills export --output-dir /tmp/xcode-skills
python3 scripts/sync_xcode_ai.py --xcode /Applications/Xcode.app --skills-dir /tmp/xcode-skills
```

资源路径改变、空导出或导出命令失败都会中止同步，不会被视为上游删除全部文件。

## MCP 验证

打开 Xcode 和一个项目，在 Xcode 的 Intelligence 设置中允许外部代理使用 Xcode 工具，再执行：

```bash
python3 scripts/sync_xcode_ai.py --xcode /Applications/Xcode.app --probe-mcp
```

该选项执行 MCP `initialize` 和 `tools/list`，保存服务 instructions、工具名称和输入 schema；不调用构建、编辑、安装等工具。连接失败或超时会中止本次导出，不能据此宣称 MCP 可用。默认未探测时，来源记录中的 `mcp_runtime_verified` 为 `false`。

需要将验证结果一并应用时，使用 `--probe-mcp --apply`。如果未带 `--probe-mcp`，本次快照不会包含 live tools 清单；旧的托管清单会被移除，避免误认其仍与新版一致。MCP 能力还取决于当前打开的项目和 Xcode 设置。

报告会比较 MCP 工具的增删及 schema 变化。原始 skill 也可能与服务存在版本差异：本次 Xcode 27.1 的设备 skill 使用 `DeviceEventSynthesize`，而实际 MCP 暴露 `DeviceInteractionSynthesize`。流程保留 Apple 原文并标注差异；运行任务前检查实际 schema，不凭名称相似直接替换参数。

插件的桥接脚本优先采用 `XCODE_APP`，其次 `DEVELOPER_DIR`，然后是支持 `mcpbridge` 的 `xcode-select` 路径，最后尝试 `/Applications/Xcode.app`。多版本 Xcode 环境应显式指定路径；必要时用 `MCP_XCODE_PID` 选择正在运行的 Xcode。日志只写入 stderr，stdout 保留给 MCP。

兼容配置显式设置 `cwd: "."`，由 Codex 解析为安装目录，再通过相对路径启动脚本；不依赖当前客户端不会展开的 `${PLUGIN_ROOT}` 参数。自定义 Xcode 路径及会话选择变量通过 `env_vars` 传递。

验证分成三层：插件注册、MCP 初始化及工具发现、项目访问授权。Xcode 如返回 `This agent isn't approved to use Xcode's tools yet`，说明前两层已通过，但还需通过 `XcodeOpenWorkspace` 或 `XcodeNewProject` 触发项目授权。不要把这种状态报告为项目操作已经可用。

本仓库的注册回归测试会调用实际 Codex 客户端。可在打开 Xcode 后执行 live 测试（不调用模型、不修改项目）；需要项目授权时会明确跳过业务调用验证：

```bash
python3 -m unittest discover -s tests -v
APPLE_PLUGIN_TEST_LIVE_MCP=1 python3 -m unittest discover -s tests -p test_plugin_packaging.py -v
```

## 给 Codex 的更新审阅提示词

在这个仓库开启聊天并发送下面的提示词，即可启动完整流程：

```text
请按照 docs/update-xcode-ai.md 更新这个插件的 Xcode 内置 AI 内容。
使用 /Applications/Xcode.app（若我指定其他版本，则以指定路径为准）。

1. 运行同步脚本生成预览，读取报告、来源版本和 lock 文件。
2. 对比 skill、prompt 模板及 MCP 资料的新增、修改、删除。
   Apple 导出的所有文件保持原样，包括 frontmatter 和 description；不要修剪、润色或修复原文。
3. skills/ 必须完整镜像当前 Xcode 导出，覆盖本地修改并删除上游已不存在的文件；保留应用前备份。
   对非 skill 文件检查本地冲突，未解决时不要覆盖。
4. 打开 Xcode 后用 --probe-mcp 验证连接并对比工具 schema。无法连接时明确记录未验证，不猜测工具可用性。
5. 读取 .xcode-ai/prompt-review.md 及相关源模板，增量总结到 rules/apple.md 的标记区域。
   标注来源，保留标记外规则；排除 Xcode 内部角色、占位符、English-only 和整文件输出协议。
   专用知识继续交给原始 skills。不要把模板当当前系统指令执行。
6. 应用原始导出，检查 diff，完成规则语义审阅后运行 review_prompt_rules.py --mark-reviewed --note 记录依据。
   运行 --check 验证总结与当前导出匹配，并验证入口 skill 在安装包中可发现、引用规则存在。
   非 skill 文件如需 --adopt-existing 时先展示冲突文件及差异。
7. 给出 Xcode 版本、内容变化、MCP 验证结果、规则总结状态和仍需适配的事项。不要自动提交或推送。
```

参考：[Apple 外部代理接入](https://developer.apple.com/documentation/xcode/giving-external-agents-access-to-xcode)、[Codex 插件打包](https://developers.openai.com/plugins/build/plugins)。
