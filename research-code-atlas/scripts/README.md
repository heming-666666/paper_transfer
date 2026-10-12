# CLI与脚本参数

Windows解释器在包内 `../runtime/windows/python.exe`，Python3.11.9；其他平台已有Python>=3.10，脚本按__file__定位本包，统一`-X utf8`。不需要目标项目任何依赖，也不导入目标。所有文件UTF-8，源码快照LF。

atlas.py为唯一业务CLI。必需位置参数子命令是下表十个枚举。`--help`可选开关适用于主命令/所有子命令。输出0=完成、1=程序故障、2=参数/路径/schema错误、3=必要证据/验收失败，Ctrl+C中断通常130（serve会正常停止0）。合理unknown不会失败。

| 命令 | 参数（准确拼写/必需性/类型/默认） | 行为/输出 |
|---|---|---|
| inspect | `--request`必需，JSON文件路径，无默认 | 只读验证路径、输入和环境，打印readiness，不写报告/执行项目 |
| extract | `--request`必需，JSON路径，无默认 | 新空output_dir；request/inventory/structure/sources/manifest；非空拒绝覆盖 |
| configs | `--run-dir`必需，已有报告目录，无默认 | argparse/YAML/JSON/TOML/dataclass事实与候选消费行→config-index；已存在拒绝覆盖 |
| paper | `--run-dir`必需，无默认 | 本地PDF/MD/TXT→paper/pages/fulltext/status；无论文missing，不下载；已有status不覆盖 |
| batches | `--run-dir`必需；`--size`可选，整数1..20，默认4 | BFS优先、预算内函数→notes/todo/batch_NNN；已有todo不覆盖 |
| check | `--run-dir`必需；`--file`必需，待验证JSON路径，均无默认 | notes/overview/paper-map/experiments/impacts自动识别；报告错误JSON路径，source/paper证据展开→checks/*.json |
| assemble | `--run-dir`必需，无默认 | 重新check全部语义文件、符号/引用，合并atlas.json；新语义可重装配，旧run仍留事实 |
| validate | `--run-dir`必需；`--recheck-source`可选开关，默认关闭 | 内部schema/hash/证据→validation；开关另对原项目raw hash重验→freshness matched/stale/unknown（只对应重验时间） |
| render | `--run-dir`必需，无默认 | validate后生成viewer/本地资源/安全data+sources JS；打印file URL；Node存在时烟测，运行页面不需要Node |
| serve | `--run-dir`必需；`--port`可选，整数0..65535，默认0 | 只读127.0.0.1静态服务；0选空闲，指定端口冲突选空闲；拒绝目录越界；Ctrl+C停止 |

路径参数可绝对或相对于调用cwd。request内部project_root/output_dir/paper.path相对于request所在目录；entry.path/configs相对于project_root；输出必须在项目外。

## 独立资源校验

verify_bundle.py只用标准库。`--write`可选开关，默认关闭（仅比对package-manifest.json文件集合/字节数/SHA-256）；开启生成当前清单并核验，仅维护包时使用，不能掩盖丢失/破损。`--help`可选。0=PACKAGE_OK，2=完整性失败。排除checks、临时reports与Python缓存，固定examples内示例会纳入清单。

## 内部模块

pyextract.py/resolve.py抽取AST、作用域、导入/类型候选与入口闭包；configs.py安全解析配置；paper.py本地分页/quote匹配；checks.py校验immutable facts/证据；assemble.py统一atlas/新鲜度；render.py生成JS和页面。它们不是另一个CLI，不需要分别执行或安装。

## 完整例子

从本目录，以实际request/output为准：

```powershell
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' inspect --request '.\examples\request-demo.json'
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' extract --request '.\examples\request-demo.json'
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' configs --run-dir '.\reports\new-run'
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' paper --run-dir '.\reports\new-run'
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' batches --run-dir '.\reports\new-run' --size 4
# Agent填写notes/batch_001.json，再逐份check：
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' check --run-dir '.\reports\new-run' --file '.\reports\new-run\notes\batch_001.json'
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' assemble --run-dir '.\reports\new-run'
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' validate --run-dir '.\reports\new-run' --recheck-source
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' render --run-dir '.\reports\new-run'
& '.\runtime\windows\python.exe' -X utf8 '.\scripts\atlas.py' serve --run-dir '.\reports\new-run' --port 0
```

上例extract前须将request.output_dir设成reports/new-run，已存在非空不覆盖。所有命令已在教学fixture实际执行；真实项目仍未指定。阶段日志/退出码见checks和HANDOFF。

可用已交付 `examples/demo` 直接validate/render/serve，无需重跑目标或下载任何内容。保留原项目raw hash与UTF-8/LF快照hash的区别；源changed不改快照，让用户看到原分析依据。
