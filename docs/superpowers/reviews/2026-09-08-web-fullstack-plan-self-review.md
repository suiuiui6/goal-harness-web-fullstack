# Web 全栈交付详细实施计划自检

日期：2026-09-08

检查时间：2026-09-08T03:32:08.556932+00:00

状态：保留初版自检历史；用户复核后的四项修订及当前检查见文末。修订版待再次审阅，未启动运行时实现。

## 实际检查

- 14 个 Task 连续唯一，按 A(1–4) → B(5–7) → C(8–10) → D(11–14) 嵌入同一实施链。
- WF-01–WF-17 共 17 项与 SC-01–SC-08 共 8 项均有任务映射，未删除或重编号主设计案例。
- 代码围栏配对，6 个 Python 示例可通过 AST 语法解析；仅解析，不导入候选模块、不执行测试，不证明示例的运行结果。
- 没有未填写标记；设计/约束/计划间 Markdown 文件链接均指向存在的文件。
- 原 18 个安装源摘要匹配；额外 21 个已安装输入文件已登记摘要，原 baseline JSON 未改。
- 46 个技能禁用条目仍保留；本次未写配置。没有创建 source/tests/tools/fixtures/artifacts 或 Git 仓库。
- 当前工具前提：Python 3.14.3、pytest 9.0.3、tiktoken 0.13.0、Playwright 1.59.0；Chromium 路径存在，未启动浏览器或执行夹具。

初版计划 SHA-256（修订前历史）：`efaa0d8b34dc474191a51e39e6861bf55b7dec04591c847888180e9b5783322d`

配置完整性检查 SHA-256：`abd8f903948fad326bb201359d068caee8cc1aa6f8e172f4264389f71203f7ed`（仅摘要，未记录配置内容）。

## 自检后已修正的计划问题

1. 并发完整 candidate 仅加锁仍可能覆盖旧结果：明确新 profile 使用 --expected-state-sha256，在原锁内对完整 state 原字节进行 compare-and-swap；旧运行调用保持不变。该接口待实现，不声称已保护当前运行。
2. A 检查未来 C 规范文件会提前失败：权威映射增加 required_from 与 --stage，唯一 owner 始终校验，文件存在性按依赖阶段要求，发布默认 D 不得放宽。
3. 测试原本硬编码安装路径：明确候选 Guard/skills-root 环境入口及回归命令，保留旧默认但不拿安装结果冒充候选。
4. 补齐完整 draft_delivery fixture、精确测试路径、解释生成工具职责及新 CLI 的文档接线；保留行为观察的独立等级和授权边界。

## 范围与未解决风险

- 纯函数接口/字段表/错误码/逐任务修改点是本计划拟定的实现合同，仍需用户审阅；生产实现和所有 RED/GREEN 均 not-run。
- 计划中的测试与片段不是全量生产代码，未声称能够仅复制本文就跳过实现、TDD 或逐任务审查。
- 并行任务状态和 HEAD 是本次时点观察；其 commit_state 与当前安装 writer 不同。接入和安装前必须重核，不停止或改写该任务。
- 现有 Guard 不允许 executing 状态携带 required=true 但未批准计划；本次只能登记待审阅路径/证据，不能伪造 approved，也不倒退 phase。用户批准实施计划后才可更新对应计划审批记录。
- 三等级产品评测、真实读取轨迹、上下文体量前后对比、安装及回滚都为 not-run；源码哈希与 AST 检查不是这些结果。

Decision quality:
  Trigger: both；状态写入兼容、并发与公共验收契约
  Protocol: both
  Constraints: 保留旧运行、原 owner/七层、容量上限、用户确认和 audit-only-windows；只写文档
  Assumptions: 所列安装基线仍匹配，另外的 Foundation 源码不是自动接入目标
  Falsifier: 新接口丢更新、低等级证据被升格、加载收敛漏掉安全前置条件
  Falsifiers / probes: Task 6 双候选 CAS；Task 11/12 伪成功及真实反例；Task 9/13 读取时序，均计划中且 not-run
  Decision: stay at Layer 4；交付待审阅实施计划，不启动运行时实现
  Result: stay
  Residual risk: 三项高风险执行验证尚未运行，不能通过工程层门

## 当前进度

Mode: maintenance
Start Layer: 4
Touched Layers: [4]
Layer Outcomes: Layer 4 全量门禁 not-run；文档检查通过
Evidence Pointers: 本文、../plans/2026-09-08-web-fullstack-delivery-implementation.md、../specs/2026-09-08-web-fullstack-planning-inputs.json
Rollback Decisions: none
Retrospective: 设计确认后完成逐批实施计划；未接入安装包或并行源码
Next start state: Layer 4；先审阅计划及执行方式，再从 Task 1 核对基线
scope_result: incomplete
operation_state: in_progress

## 用户复核后的四项修订（2026-09-08）

检查时间：2026-09-08T04:28:37.301917+00:00

状态：四项意见已核实并纳入计划，等待用户再次审阅；未开始运行时实现。用户在此前“批准”后明确要求暂缓原版开工，当前以这一要求为准，不能复用原批准自动执行。

初版结构/AST 自检没有识别初始化默认值与验收条件冲突，也没有补齐另三项执行约束。保留前述历史记录，但不能把那些检查解释成计划业务正确性证明。

| 复核项 | 已核实事实 | 计划修订 | 待执行验证 |
| --- | --- | --- | --- |
| P1 初始化 | 只读调用已安装 _canonical_initial_state 得到 classified / accepted / in_progress，源码 scope_result 默认确实为 accepted | Task 5 仅新 delivery 候选在首次审计/创建前置 incomplete；Task 7 区分草稿与显式接受，旧模式不变 | 草稿 initialize→audit→planned→executing→首次修改；启用验收条件后重跑同一正例；空台账显式接受负例，均 not-run |
| P2 重新通过 | 原计划只有 pass→stale 和当前摘要校验，没有失效历史参与接受的可执行约束 | 第 3.3 节、Task 3/6/7 明确只追加历史、永久撤销 evidence ID、新执行/判断及派生 invalidation_count；不增加顶层状态机 | 源码恢复+旧 E1/J1 拒绝；失效后新 E2/J2 正向；执行中再次失效、只换 judgment、删历史等反例，均 not-run |
| P3 发现入口 | capability-discovery.md 仍只指向旧 helper，并要求固定脚本名字面和回复含义；原 Task 8/10 漏列该参考 | 两个 Task 均显式修改该文件；新/旧分支、缺 feature 阻止初始化、结构化 blocker及等价成功解释；实际入口 case 而非只测 helper | 新入口缺 feature、legacy 无 feature、新入口有 feature 的实际观察，以及解释变体，均 not-run |
| P4 干净 Shell | 原计划依赖 Task 2 设置 PYTHONPATH，工作区没有现成测试初始化文件 | Task 2 计划新增根 conftest 和 delivery_fixtures；pytest 显式 rootdir；Task 14 新 NoProfile 子进程清变量/设候选路径/失败即停；不声称 unittest 会读 conftest | Task 3/B 目标套件与最终完整回归从干净 Shell 执行，均 not-run |

### 本次实际完成的检查

- 只读默认值核验：没有调用写入式 initialize-state，也没有创建测试 Goal。
- 14 个 Task、17 个 WF、8 个 SC 编号与映射保留，没有新增架构工作包。
- 7 个 Python 代码块通过 AST 解析；12 个 PowerShell 代码块通过 Parser 语法解析，均未执行这些示例/回归命令。
- 确认 Task 8 和 Task 10 都列出 capability-discovery.md，包含三种真实入口 case；删除此前 PYTHONPATH 设置和跨 test_*.py fixture 导入。
- 39 个登记安装源文件摘要仍匹配，46 个禁用条目保留，配置摘要未变；没有写 source/tests/tools/fixtures/artifacts/conftest.py 或 Git 仓库。
- 通过既有 Guard 的锁、转换校验、原子写入登记文档进度，随后 audit 返回通过。没有修改 Guard 源码、推进层级或启用 delivery。

修订版计划 SHA-256：`4b7d05695abc9aa7eb3f066d62a929a69af729b7af65367c36348f356cb6fe71`

### 保证与下一步

本次只证明问题已核实、计划修订与文档语法/来源检查成立；不证明 P1–P4 的实现或业务测试已经通过。invalidation_count 是已有历史长度的绑定值，不是诚实执行证明；真实顺序仍需事件/夹具观察。

修订版待审阅后才能开始 Task 1。Layer 4 保持进行中，plan.approved=false，scope_result=incomplete，operation_state=in_progress。产品三级评测、实际重新验证、实际入口行为与干净 Shell 回归、安装/回滚均为 not-run。
