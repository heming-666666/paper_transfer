# 迁移说明

本目录为唯一实现单元。SKILL、scripts、refs、模板UI/vendor许可、fixture/ground truth、已渲染教学示例、Python解释器与依赖都在目录内。不安装旁边model-inspector，不依赖Codex_transfer或全局Agent配置。其资源仅在建设时复用后实际复制，运行没有包外链接。

Windows x64：CPython3.11.9 embedded，PyYAML6.0.3（可退纯Python）、pypdf6.20.0纯Python（包含原wheel）、Playwright1.63.0+greenlet/pyee/typing_extensions和对应Chromium headless shell，均已包含；用户日常双击HTML使用任意已有浏览器，headless资源用于可复现QA。无Node构建，所有图库本地。

其他平台：已有Python>=3.10可运行标准库静态分析；TOML需3.11。本包纯Python YAML/PDF代码由scripts/common.py相对定位，Windows编译加速不可用时退纯Python。非Windows解析实际运行未验收；Windows浏览器/解释器不能在Linux/macOS使用。UI使用file://，与平台无关的设计不等于已完成异机验证。

复制后：先用包内WindowsPython运行verify_bundle.py（PACKAGE_OK），再让目标Agent读取新目录SKILL.md。打开examples/demo/viewer/index.html验证源码导航；项目不在原位置时validate --recheck-source应显示unknown，不代表快照不可读。

新分析request要使用新机器的项目/论文/输出路径；示例request-demo已用相对路径。local.example.json只是相对路径参考，不把原机Python绝对路径当迁移依赖。

自动发现：Codex/Claude按目标宿主的真实项目级Skill目录放完整包，或使用显式读入口。未授权不写全局目录，不宣称当前会话热刷新；新会话发现性必须实际验证。原机创建时所用tools/config绝对路径不写成运行依赖。

版本差异：规格默认cytoscape-dagre4.0.1；这里复用已验证的cytoscape3.34.3+cytoscape-dagre2.5.0+dagre0.8.5（包含graphlib/lodash），相同原生离线图路线，已实际浏览器验证。未使用Understand-Anything运行依赖。第三方原始许可全文均保存，见vendor/LICENSES.md及runtime的license/dist-info。

边界：扫描/加密PDF不承诺文本；不OCR、不联网找论文、不运行目标/模型，不下载数据。样例非真实论文/项目；静态候选/不确定shape保留未知。换路径验收只证明路径闭包，不能宣称所有OS/系统运行库都验证。

GitHub分发：两项大文件（Chromium headless shell、Playwright的Node解释器）通过Git LFS保存。用支持Git LFS的git clone完整物化；若此前跳过LFS，执行git lfs pull后用verify_bundle.py核验。GitHub网页“Download ZIP”可能仅包含LFS指针，不能当完整包。完整物化后复制本目录离线使用，不需单独下载运行依赖。局部.gitattributes禁止自动换行转换，保证发布字节哈希；checks/reports与缓存是本机验收产物，不上传，固定examples教学报告仍包含。
