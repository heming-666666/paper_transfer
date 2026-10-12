# JSON契约

版本schema_version=1.0。运行时原始规范是source-spec/prompt_final.md第6–7节；实现边界由scripts/checks.py与common.py确定。

request：project_root、entries（至少一项，entry_id唯一、path、symbol可选、scenario、configs/args/overrides）、paper可选（path/url）、focus、output_dir、limits（max_depth默认8/max_symbols默认300正整数）、runtime.enabled=false。路径基准见scripts/README.md。

structure：symbols、edges、file_edges（imports）、class_edges（inherits）、control_regions、entries（root_symbol、closure、depth_of）、coverage。ID为 `sym:relative/path.py:qualified.name:kind`，kind=module/class/function/method/async_function，同作用域重定义加#2，不使用行号作ID。外部是ext:package.symbol。

edge：id/caller/callee可null/candidates/relation/resolution/callsite(file,line,end_line)/expression/conditions/note。relation=calls/constructs/module_call/definition_time；resolution=resolved_static/candidate/unresolved/external。只沿前三种关系的确定/候选边算入口闭包；导入/继承和定义时调用单列，不冒充执行顺序。

symbol：id/file/qualname/kind/definition_range（1起始，两端含）/body_start/parent/signature/decorators/docstring/params/locals/returns/yields/raises/asserts/shape_hints/step_skeleton/callers/callees/in_entries。step含id/order/kind/source_range/first_line_text/calls/children；不同分支的子步骤ID含b/o/f分支命名空间。

notes批次：`{schema_version,items:[...]}`。每条需symbol_id、prefilled（脚本字段逐项原样）、role、summary、purpose、inputs、outputs、side_effects、exceptions、steps、paper_refs、config_refs、scenario_contracts、change_notes、needs_context、analysis_status。role=entry/config/data/model/loss/train_loop/optim/eval/io/util/other，analysis_status=done/partial/pending。

IO字段：name、container_path数组、type、shape（整数/符号/null数组或null）、dimensions映射、dtype/device/units/default可null、constraints、status、evidence、reason。status为confirmed_source/inferred/unknown/conflict/not_applicable；observed_runtime在本期拒绝。unknown/inferred需reason，confirmed_source需有效源码证据。

源码证据简写`models/net.py:10-12`，check展开为ev:src ID、kind/source、file、start/end、真实快照SHA-256。文件/range必须存在。snapshot按UTF-8/LF保存，原始文件raw hash另外记录，不能混淆换行归一化和源新鲜度。

scenario_contracts：entry_id、callsite、conditions、inputs/outputs、evidence；同symbol多场景各一份。overview：entry_id、summary、stages（order/title/description/symbols）、core_symbols（id/reason）、learning_path、dataflow（order/symbol_id/line_ref/variable/container_path/shape/meaning/status/evidence/reason）。dataflow不是IO对象，别误要求其name/type字段。

paper-map：status=available/missing、paper标题/来源/页数、contributions。每项id/claim/compared_to/mechanism/paper_evidence/code_mappings/key_configs/io_change/modification_constraints/conflicts；映射status=direct/inferred/not_found/conflict、symbol_id（not_found可null）、evidence、step_alignment（真实code_step ID）、on_entry_path由assemble填每entry bool。短引文15–200字符，page从1起始且确在对应页。

experiment-settings数组：id/entry_id/setting/paper_value/repo_default/selected_value/precedence/consumed_by/status/impact。status=match/mismatch/unknown/paper_only/code_only/defined_not_consumed；unknown需reason。consumed_by含evidence简写/symbol_id/how。参数线索的确定值若用request证据，source必须精确`request.entries[0].args --lr`且值实际匹配，不接受随便写request前缀。配置消费者候选不能当运行结果。

change-impacts数组：target/goal/entry_ids/why_here/upstream/downstream/affected_contracts/config_consumers/paper_constraints/suggested_checks/limitations。target与相关符号须存在，动态调用遗漏始终说明。

atlas：schema_version/generated_at/project/request/coverage/sources/symbols（合并note）/edges/file_edges/class_edges/entries/overviews/paper/experiments/config_index/change_impacts/evidence/freshness。脚本装配后是页面唯一事实数据源；JS数据安全转义`<`和U+2028/2029，源码/论文/注释用textContent。
