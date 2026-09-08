# Goal + Harness Web Full-Stack Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: 执行时使用 `.codex` 的 `executing-plans`；只有用户明确选择代理执行时才使用 `subagent-driven-development`。逐任务记录，不自动创建任务、分支或提交。

**Goal:** 在选定 `.codex` 基线上实现技术栈中立的 Web 全栈交付契约、业务验收及按需加载，保持旧运行兼容。

**Architecture:** 使用原 `goal-state.json` 中可选的 `delivery` 扩展；Goal 负责入口/契约，Harness 负责执行/验收/加载，Guard 只负责结构、转换和一致性。纯校验先行，随后接入现有写入边界；功能与结构收敛同批完成，不造第二状态机。

**Tech Stack:** Python 标准库、现有 pytest/unittest、Markdown/JSON；隔离测试夹具用 Python HTTP 服务、SQLite、原生 HTML/JS、Playwright Chromium，不成为用户项目默认技术栈。

**Status:** 用户复核后的修订版，待再次审阅。用户先前“批准”后又明确要求暂不按原版开工，补齐 P1 初始化冲突及三项执行细节；以该最新要求为准。本轮只修订计划，不执行源码任务或安装。所有复选框、RED/GREEN 命令及期望结果均未执行。

## 1. 输入、工作目录与协调边界

权威输入：

- `C:/Users/14156/Documents/Codex/goal-harness-web-fullstack/docs/superpowers/specs/2026-09-08-web-fullstack-delivery-design.md`
- `C:/Users/14156/Documents/Codex/goal-harness-web-fullstack/docs/superpowers/plans/2026-09-08-web-fullstack-implementation-constraints.md`
- `C:/Users/14156/Documents/Codex/goal-harness-web-fullstack/docs/superpowers/specs/2026-09-08-web-fullstack-source-baseline.json`
- `C:/Users/14156/Documents/Codex/goal-harness-web-fullstack/docs/superpowers/specs/2026-09-08-web-fullstack-planning-inputs.json`

全部命令工作目录为 `C:/Users/14156/Documents/Codex/goal-harness-web-fullstack`。下文精确相对路径均相对此根目录，不是安装目录；运行源码目录目前尚未创建。

| 未来路径 | 内容来源/用途 |
| --- | --- |
| `source/goal/` | `C:/Users/14156/.codex/skills/goal/` 的选定副本 |
| `source/harness-engineering/` | `C:/Users/14156/.codex/skills/harness-engineering/` 的选定副本 |
| `source/goal-enforcement/` | `C:/Users/14156/plugins/goal-enforcement/` 的选定副本 |
| `tools/`、`tests/`、`fixtures/web-notes/` | 维护工具、测试和隔离夹具，不是新运行时 |
| `artifacts/baseline/`、`artifacts/evals/`、`artifacts/release/` | 冻结基线、评测结果、发布候选，不入运行包 |

禁止写安装目录、个人配置和其他任务源码。不初始化 Git、不建分支、不提交/推送、不安装依赖。不删除历史。已有目标文件或来源变化先审阅，不覆盖。当前维护 Goal 保持旧模式，不能在活动运行中添加正在开发的 delivery。

非目标直接沿用主设计：本工作包不实现 Fast Run、Provider 平台、完整 state schema v2、通用 DAG 或默认 GSD；这不撤销其他任务既有授权。详细计划通过后才执行运行源码修改，安装同步仍须单独授权。

### 1.1 已查明的接口差异

原 18 个安装源摘要本次全部匹配。另一任务「完成 Goal Harness 下一阶段开发」仍在进行中；其仓库为 `C:/Users/14156/.codex/workspaces/goal-protocol-v2/repo`，观察到 HEAD `ea4365a1f19f5a0a2642aa660c59af95cc69a05d`。git status 报告未跟踪 `docs/reviews/`，且有 `.pytest_cache` 读取权限警告；这不等于完整工作树审计。

该仓库 `goal-enforcement/scripts/goal_guard.py` 已有 `commit_state(workspace, *, expected_revision, actor, operation, transform, allow_create=False, audit_current_workspace=True)`；安装基线仍是 `goal_state_lock`、`validate_transition`、`write_goal_state`。**本计划只在选定安装基线的独立副本开发，不移植或覆盖另一仓库。** B 接入前、C 交接前和安装前重核。若目标更换到 Foundation 源码，先修订接线任务并审阅，不能绕过其唯一 commit_state。

旧 Goal Protocol 允许 `classified -> executing`，安装 Guard 只接受相邻转换。保留旧协议表达集合，实际 Guard 调用统一走 `classified -> planned -> executing`；测试同时保留协议查询正向及 Guard 直接跳转负向结果，不静默改协议或放宽 Guard。

## 2. 文件职责与唯一权威

| 规则 | 唯一维护来源 | 消费方式 |
| --- | --- | --- |
| 分类精确字段/核心所有权/协议兼容 | `source/goal/references/protocol.json` | 输出模板和协议模块引用 |
| 新建/维护与起始层政策 | `source/goal/references/layer-execution.md` | Goal 入口与 Harness 引用 |
| delivery 字段/枚举/容量 | `source/goal-enforcement/scripts/delivery_contract.py` | 纯校验；Goal 字段表校验生成 |
| 契约修订/确认 | `source/goal/references/delivery-contract.md` | Goal/Harness 按需引用，不复制字段 schema |
| 业务验收/证据充分性 | `source/harness-engineering/references/web-fullstack-delivery.md` | Gate/Closure/评测引用 |
| 层序/层门/最小回退 | `source/harness-engineering/core/flow.md` | checklists、exit/reentry、layer-details、SPEC/CHECKS 按规则 ID 引用 |
| 执行加载/条件路由 | `source/harness-engineering/references/load-policy.json` | runtime-stages/domain-routing 生成可读表；Goal 只交接 |
| Closure 输出/解释 | `source/harness-engineering/references/output-contract.md` | Goal 引用；机器字段仍来自 Goal Protocol |
| 状态转换/写入 | `source/goal-enforcement/scripts/goal_guard.py` | 所有写入口沿用同一 Guard 边界 |

新增代码拆成 `delivery_contract.py`（类型/资源）、`delivery_rules.py`（关系/转换）、`delivery_evidence.py`（只读摘要），不把全部规则堆进 Guard 主文件，也不拆改无关逻辑。维护工具 `tools/check_rule_ownership.py` 与 `tools/render_delivery_reference.py` 检查权威映射和生成投影；不进入分类热路径。

## 3. 待实现接口与数据契约

`Issue` 只在 `delivery_contract.py` 定义，字段为 `code/path/message`。测试严格检查 code/path，允许 message 等价改写。以下 API 当前不存在，不声称可调用。

| 模块 | 接口 | 行为 |
| --- | --- | --- |
| delivery_contract | `canonical_delivery_bytes(value: object) -> bytes` | 确定性紧凑 UTF-8；非法编码抛 ValueError |
| delivery_contract | `validate_delivery_shape(value: object) -> list[Issue]` | 只检查结构/资源，不改变输入 |
| delivery_rules | `validate_delivery_links(delivery: dict) -> list[Issue]` | ID、引用、循环、revision、归属 |
| delivery_rules | `validate_delivery_transition(previous: dict, candidate: dict) -> list[Issue]` | 输入完整 Goal 状态，保护绑定/修订/历史 |
| delivery_rules | `invalidate_delivery(delivery: dict, *, event: str, at: str, reason: str, mutation_seq: int) -> dict` | 返回深拷贝；容量不足拒绝，不截断 |
| delivery_rules | `acceptance_errors(delivery: dict) -> list[Issue]` | 可机器检查的非空/必需项/证据条件，不替代 Harness 判断 |
| delivery_evidence | `audit_delivery_files(delivery: dict, workspace: Path) -> list[Issue]` | 引用路径/bytes/摘要只读检查，不执行环境探针 |
| goal/scripts/protocol.py | `delivery_feature_available(contract: dict, descriptor: object) -> bool` | 复用旧 major 检查，再查 feature/schema/必要命令和宿主模式 |

### 3.1 结构约定

顶层仅有 `schema_version=1`、`profile=web-fullstack`、`contract/slices/criteria/evidence/invalidations` 七个分区；旧状态字段不存在时不走新校验，显式 null 不是旧模式。

| 对象 | 必需字段 |
| --- | --- |
| contract | `revision` 正整数；`outcome` 非空；`actors/flows/non_goals/constraints/unknowns` 文本数组；`delivery_target` 主设计三值；`approval` 对象 |
| approval | 与契约相同的 `revision`；`confirmation_id/source/recorded_at` 非空，时间带时区，来源可定位真实确认 |
| slice | `slice_id/outcome` 非空；`criterion_ids/depends_on` 无重复 ID 数组；`surfaces` 恰含 data/api/ui/authorization/deployment |
| surface | `applicability` 主设计三值；`rationale` 非空；`evidence_ids` 数组 |
| criterion | `criterion_id/slice_id/outcome` 非空；`revision` 正整数；`required` 布尔；`status` 主设计七值；`applicability_rationale` 文本；`verification` 对象；`evidence_ids` 数组；`judgment` 对象或 null |
| verification | `entry_id/cwd` 非空；`kind=command/tool/manual`；`entry` 非空文本数组；`environment_keys` 无重复文本数组。不自动授权执行 |
| judgment | `result=pass/fail/blocked/not_applicable`；`reason/source/at` 非空；`evidence_ids` 引用本项记录；`invalidation_count` 非负整数，含义见第 3.3 节 |
| evidence | `evidence_id/criterion_id` 非空；`revision` 正整数；`provenance=agent_declaration/observed_execution`；`entry_id/cwd/started_at/finished_at/observer` 非空；`result=pass/fail/blocked`；`exit_code` 整数或 null；`source_fingerprint/environment/isolation` 对象；`outputs` 数组；`invalidation_count` 为非负整数，记录执行开始时已有失效记录的数量 |
| source_fingerprint | 原 Guard sha256-manifest-v1 收据结构，不另造算法 |
| environment | 非秘密标量 `facts` 对象；`observed_at/source` 非空；`status=observed/unknown` |
| isolation | `mode=isolated-snapshot/unproven`；`snapshot_id/source_digest/observer` 非空。字段声明不是隔离的执行证明 |
| output | 工作区内相对 `path`；64 位小写十六进制 `sha256`；非负整数 `bytes` |
| invalidation | `invalidation_id/event/at/reason` 非空；`criterion_ids/evidence_ids` 无重复 ID 数组；`mutation_seq` 非负整数 |

所有整数排除 bool；先验对象/数组类型再索引，拒绝未知字段、空白 ID、NUL、无时区或倒置时间。shape 允许草拟空台账，acceptance 不允许空 required。上限为 128 slices、512 criteria、2048 evidence、256 invalidations，整个 delivery 编码 ≤2 MiB；等于允许、超一拒绝，老状态原字节不变。

### 3.2 关系与证据规则

1. 双向 slice/criterion 归属一致；ID 唯一；引用存在；有界 DFS 拒绝循环，不建设调度器。
2. 当前 criterion revision 匹配契约；旧 evidence 可保留但不能支撑当前 pass；不可同 ID 替换历史内容。
3. 活动新模式不能移除/改变 profile/schema，活动旧模式不能添加。首次绑定只走新运行初始化；不覆盖任何既有状态，不自动另开 Goal。
4. 降低要求、删必需项、改变适用性/验证要求、扩大范围/权限或交付目标须新 revision 和对应确认。Guard 不推断自然语言等价；无法证明澄清则先确认。
5. 纯解释投影措辞改写不修改 canonical contract；契约澄清保留原因并由 Harness 判断，不能借旧确认授权新语义。
6. pass 需要 observed_execution、正确 entry/criterion/revision、通过结果、有效时间、环境和隔离观测、有效输出与独立 judgment。exit 0/声明/关键词不是充分条件；manual/tool 可 exit_code=null，但实际观察不可缺。
7. 环境 key 缺失/未知、源码或证据摘要变化、未证明隔离不得接受。Guard 不自动访问远程环境；Harness 在 Gate/Closure 重采事实，未知即 stale/blocked，不能只沿用旧文本。
8. 源码/测试/生成源码/未跟踪源码、契约、环境及上游回退保守失效本轮 pass，历史保留。依赖必需项未通过，下游不得接受。
9. 高严重度风险、覆盖是否充分和真实部署事实仍由 Harness 检查；Guard 一致性不证明测试正确或执行诚实。Windows 仍 audit-only-windows。

### 3.3 失效历史与重新通过（P2）

沿用现有 invalidations 数组，不增加顶层状态字段或新状态机。`invalidation_count` 是该数组的既有长度，不是独立可写的执行代次；初值为 0，最多 256。相同 mutation_seq 的环境/契约失效也各追加一条记录，因此不能只比较 mutation_seq 或源码摘要。

- `validate_delivery_transition()` 要求旧 invalidations 是候选数组的完全相同前缀，禁止删除、重排或改写；既有 evidence_id 的记录不可替换。容量不足拒绝候选，不通过删历史重置 count。
- `invalidate_delivery()` 追加影响范围及被撤销支持资格的 evidence_ids，并将 pass→stale。`acceptance_errors()` 始终读取完整失效历史：任何已被记录失效的 evidence_id 永久不能再作为当前 pass 的依据，即使源码后来恢复为原摘要。
- 首轮仍保守失效本轮范围。所有用于当前 pass 的新 observed_execution 都必须使用未出现过的 evidence_id，记录执行开始时的 invalidation_count，并在接受时等于当前 `len(invalidations)`；不能把旧记录改时间、改 count 或改 ID 冒充新执行。历史 evidence 允许较小 count，但只能留作历史。
- 重新通过还要求：新执行 started_at 不早于最近失效时间，finished_at 不早于 started_at；新的 judgment 明确引用这些新 evidence，invalidation_count 同为当前值，at 不早于相关执行结束。执行过程中发生任何新失效则旧 count 不匹配，必须再次验证。 时间按带时区时间值比较而不是字符串排序；shape 拒绝 bool/负数/超过历史长度的 count。
- count 和时间都是一致性约束，不证明执行诚实。事件回放/真实夹具必须实际观察到“失效事件 → 新执行开始/结束 → 新验收判断”的顺序；只补一段新声明、只换 judgment 或只恢复源码不得通过。

接受不要求删除旧证据，也不允许“撤销失效记录”来恢复通过。此规则同时用于部分 criterion 的 pass 合法性和最终 acceptance_errors；尚未通过的草稿条目不要求提前提供证据。

## 4. A：契约、纯校验和权威来源

### Task 1：冻结副本与改进前输入

**Files:** 创建 `tools/source-baseline.json`、`tools/load-trials.json`、三个 `source/` 副本及 `artifacts/baseline/`。

- [ ] 重核原基线和 planning-inputs 摘要；变化先审差异，不复制未知版本。
- [ ] 按显式清单复制，拒绝链接/联接，排除 docs、缓存和活动状态；记录来源、目标、SHA-256、bytes。不删除安装历史。现有目标先审阅。
- [ ] 冻结同清单的 baseline 副本；候选开发只改 source。保存 SC-01–SC-06 对应同提示/代码快照/宿主/确认边界；规范必读清单与实际读取轨迹分开。
- [ ] 跑原套件作为基线，记录退出码、收集数和跳过原因；与本轮无关失败只登记，不顺手修复。

```powershell
Set-Location 'C:\Users\14156\Documents\Codex\goal-harness-web-fullstack'
python -B -m pytest --rootdir . -p no:cacheprovider source/goal/scripts/test_protocol.py source/goal/scripts/test_validate_goal_skill.py -q
python -B -m pytest --rootdir . -p no:cacheprovider source/harness-engineering/scripts -q
python -B -m unittest discover -s source/goal-enforcement/tests -p 'test_*.py' -v
```

期望：明确的基线结果，不预填通过数；安装目录历史 docs 引发的结构限制须单独说明，不能删除历史掩盖。

### Task 2：结构模型与边界测试

**Files:** 创建 `conftest.py`（维护工作区根）、`source/goal-enforcement/tests/delivery_fixtures.py`、`tools/rule-ownership.json`、`tools/check_rule_ownership.py`、`tools/render_delivery_reference.py`、`source/goal-enforcement/scripts/delivery_contract.py`、`source/goal-enforcement/tests/test_delivery_contract.py`。

- [ ] 按第 2 节登记 rule_id/owner/canonical/consumers/required_from；required_from 为 A/B/C/D。多权威和循环引用始终失败；规范文件在其 required_from 阶段起必须实际存在。CLI 的 --stage A|B|C|D 默认 D，不能让 C 才创建的文件使 A 的映射检查无故失败，也不能在发布时容忍缺失。
- [ ] 先建立测试级导入初始化：根 conftest.py 使用自身路径定位候选 scripts 和测试 fixture 目录，不依赖 PYTHONPATH、Shell profile 或先前任务。只为 pytest 初始化搜索路径，不预先导入尚未实现的模块；根 bootstrap 不入发布包。

```python
from pathlib import Path
import sys


workspace_root = Path(__file__).resolve().parent
for relative_path in ("source/goal-enforcement/tests", "source/goal-enforcement/scripts"):
    module_directory = str((workspace_root / relative_path).resolve())
    if module_directory not in sys.path:
        sys.path.insert(0, module_directory)
```

- [ ] 新 delivery/维护测试统一用 pytest 且显式 --rootdir .；Task 1 的原始基线 unittest 与 Task 6 的既有 test_goal_guard.py 保留原有自定位导入，不宣称 conftest 对 unittest 生效。不要把新 delivery 测试作为没有 bootstrap 的独立 unittest 命令执行。
- [ ] GREEN 后增加 test_delivery_imports_resolve_to_source：断言 delivery_contract/delivery_rules（各自在所属任务实现后）的 __file__ 属于本工作区 source，fixture 来源为 delivery_fixtures.py；从清除了 PYTHONPATH 的新进程分别运行 Task 2/3/B 测试。不依赖安装包凑通过。
- [ ] 再写业务 RED：bool 冒充整数、NaN、未知字段、无时区时间、输入不变性、全部计数恰好上限/超一、UTF-8 2 MiB/超一。容量样本使用唯一 ID，避免先被重复检查拒绝而没有覆盖容量。
- [ ] 实现第 3.1 节类型与资源规则，类型/枚举/容量仅此模块维护；纯函数不读文件、不执行命令。规范编码代码为：

```python
import json
from typing import NamedTuple


class Issue(NamedTuple):
    code: str
    path: str
    message: str


def canonical_delivery_bytes(value: object) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as error:
        raise ValueError("delivery is not canonical UTF-8 JSON") from error
```

- [ ] 第 10 节完整草拟 fixture 放在 `source/goal-enforcement/tests/delivery_fixtures.py`；所有新测试使用 `from delivery_fixtures import draft_delivery`，不交叉导入被 pytest 收集的 test_*.py。证明 shape 合法不等于 acceptance 合法。
- [ ] GREEN 后回归原 Guard 契约；生成字段表工具支持 `--root . --check`，生成输出只位于 Goal 的新 delivery-contract 参考，绝不覆盖人工修订/确认说明。

```powershell
python -B -m pytest --rootdir . -p no:cacheprovider source/goal-enforcement/tests/test_delivery_contract.py -q
python -B tools/check_rule_ownership.py --root . --stage A
```

### Task 3：切片、修订、绑定与失效

**Files:** 创建 `source/goal-enforcement/scripts/delivery_rules.py`、`source/goal-enforcement/tests/test_delivery_rules.py`，扩展完整 ledger fixture。

- [ ] 先写 RED：空 required、循环、悬空、重复、双向归属错、旧 revision/确认、活动删扩展、旧运行加扩展、required 降低和证据 ID 覆盖。
- [ ] 实现第 3.2 节关系/转换规则；shape 失败直接返回，不继续索引。错误码固定：DELIVERY_REFERENCE_INVALID、DELIVERY_CYCLE、DELIVERY_REVISION_INVALID、DELIVERY_APPROVAL_REQUIRED、DELIVERY_BINDING_IMMUTABLE、DELIVERY_REQUIRED_EMPTY、DELIVERY_EVIDENCE_INSUFFICIENT。
- [ ] invalidate_delivery 深拷贝、追加受影响 ID、pass→stale；保留 fail/blocked/not_applicable 和历史。满容量拒绝整候选，不删历史。
- [ ] 实现第 3.3 节的历史前缀、撤销 evidence ID、执行开始 count 与新 judgment 检查；错误码明确为 DELIVERY_INVALIDATION_HISTORY_CHANGED、DELIVERY_EVIDENCE_INVALIDATED、DELIVERY_REVALIDATION_REQUIRED。acceptance_errors 不得仅检查当前状态值/源码摘要。
- [ ] 在 test_delivery_rules.py 添加以下完整时间线用例，并在 Task 6/7 的 Guard 集成中重复对应拒写/接受边界：

| 测试函数 | 操作与预期 |
| --- | --- |
| test_reverted_source_cannot_resurrect_invalidated_evidence | E1/count=0/J1 已通过 → I1 记录 E1 失效 → 源码恢复原摘要 → 把 criterion 填回 pass 并引用 E1/J1；仍拒绝，历史保留 |
| test_fresh_execution_after_invalidation_can_pass | 同一 I1 保留 → 实际新执行 E2（新 ID、count=1、在 I1 之后开始结束）→ 新 J2（count=1、引用 E2、在 E2 之后）→ 在其他条件通过时重新接受 |
| test_new_judgment_does_not_revive_old_execution | 只写新 J2，但仍引用 E1；即使当前摘要一致也拒绝 |
| test_invalidation_during_verification_requires_rerun | E2 开始时 count=1，结束前发生 I2（即使 mutation_seq 未变），当前 count=2；拒绝 E2，要求 I2 之后的新执行 |

- [ ] 负向变异还包括删除/改写 I1、修改 E1 的 count/时间、复用旧 judgment；全部失败。合成数据只验证这些纯规则，不冒充实际重新执行的证据。
- [ ] 增加合法 reuse/not_applicable、完整 required、新 revision+新确认的正向样本；确认校验不产生 I/O。测试严格检查 code/path 而非 message。

```python
from delivery_rules import acceptance_errors, validate_delivery_transition
from delivery_fixtures import draft_delivery


def test_empty_required_cannot_pass():
    errors = acceptance_errors(draft_delivery())
    assert any(error.code == "DELIVERY_REQUIRED_EMPTY" for error in errors)


def test_legacy_binding_is_immutable():
    previous = {"phase": "executing"}
    candidate = {"phase": "executing", "delivery": draft_delivery()}
    errors = validate_delivery_transition(previous, candidate)
    assert any(error.code == "DELIVERY_BINDING_IMMUTABLE" for error in errors)
```

```powershell
python -B -m pytest --rootdir . -p no:cacheprovider source/goal-enforcement/tests/test_delivery_contract.py source/goal-enforcement/tests/test_delivery_rules.py -q
```

### Task 4：原始证据和稳定对象

**Files:** 创建 `source/goal-enforcement/scripts/delivery_evidence.py`、`source/goal-enforcement/tests/test_delivery_evidence.py`。

- [ ] RED：临时 workspace 中 `.codex/evidence/result.json` 记录摘要后同长篡改，必须 DELIVERY_ARTIFACT_STALE，不能仅靠源码 fingerprint。
- [ ] 实现只读路径检查：拒绝绝对/UNC/驱动器路径、..、冒号、链接祖先及特殊文件；解析后仍须位于 workspace 内。流式 SHA-256+bytes，不打印内容。
- [ ] 源码 freshness 由 Guard caller 复用 workspace_fingerprint_record 比较；evidence 模块不反向 import/audit Guard，避免循环。
- [ ] GREEN 覆盖源码/测试/生成/未跟踪变动、证据替换、目录联接、首尾源码相同但隔离未证明。实际夹具使用独立临时源码副本和输出目录，不把一段 isolation 声明当成真实观测。

```powershell
python -B -m pytest --rootdir . -p no:cacheprovider source/goal-enforcement/tests/test_delivery_evidence.py -q
```

A 退出：类型/关系/证据纯规则和原套件结果齐全，权威映射唯一，改进前输入冻结；否则不接 Guard。

## 5. B：Guard 增量与旧运行兼容

### Task 5：feature 广告和新运行初始化

**Files:** 修改 `source/goal-enforcement/scripts/goal_guard.py` 的 CAPABILITY_DESCRIPTOR、initialize_state、run_initialize_state、parser；新增 `source/goal-enforcement/tests/test_delivery_guard.py`；修改 `source/goal/scripts/protocol.py` 与 `scripts/test_protocol.py`。

- [ ] 重新核对第 1.1 节目标和写入接口。已换成 Foundation 实现时停止并修订接线，不在 commit_state 外加 writer。
- [ ] RED：旧调用参数产生原状态且无 delivery；仅 major 相同但无 feature 不能启用；活动旧状态拒绝添加。
- [ ] descriptor 新增 `features: ["web-fullstack-delivery-v1"]`，其余 capability/major 1/schema [1]/命令/模式保持。只有完整 B 校验通过的候选才可发布这个广告。
- [ ] initialize_state 增加 keyword-only `delivery: dict | None = None`；CLI 增加 `--delivery-file`。有界读取和 shape/link 检查后进入原锁与排他创建路径。缺参是旧模式，传 null/非法 JSON 报错，不静默回退。
- [ ] 修复 P1：原 _canonical_initial_state 的 scope_result=accepted 默认只保留给 legacy；新 delivery 候选在任何审计/创建之前明确置 scope_result=incomplete。phase=classified、operation_state=in_progress、verification=missing、closure.recorded=false 保持，不要求初始化草稿完成交付验收。不全局修改旧 helper 的默认行为。
- [ ] 在 test_delivery_guard.py 增加 test_legacy_initial_state_retains_accepted 与 test_delivery_draft_initialize_audit_execute_first_mutation。后者以空 slices/criteria/evidence 草稿经过 initialize → audit → planned → executing → 首次受治理修改/审计，全程不提交交付证据且不触发全量 acceptance；Task 6 接入 CAS 后每次状态写入重新获取摘要。Task 7 启用全量验收条件后必须再跑同一正例，不能仅保留接入前的通过结果。
- [ ] Goal 的 feature helper 复用 capability_compatible，再严格检查 features 字符串数组、schema 1、initialize-state/write-state/audit 和当前 audit-only-windows 模式。缺条件只阻止新模式，不改变旧入口。
- [ ] GREEN：非法初始化不产生状态，既有状态原字节不变，并发初始化最多一个成功。广告通过不代表业务验收通过。

```powershell
python -B source/goal-enforcement/scripts/goal_guard.py capabilities
python -B -m pytest --rootdir . -p no:cacheprovider source/goal-enforcement/tests/test_delivery_guard.py -k 'feature or initialize or legacy' -q
python -B -m pytest --rootdir . -p no:cacheprovider source/goal/scripts/test_protocol.py -q
```

### Task 6：转换、失效和拒写原子性

**Files:** 修改 `goal_guard.py` 的 state_shape_errors、audit_state、validate_transition、reserve_mutation、rollback_layer、run_write_state 及所有内部写入口；扩展 `test_delivery_guard.py`。

- [ ] RED：移除/改变 delivery、同 revision 降低要求、旧确认、过量候选、回退后保留 pass 均拒绝或失效；无 delivery 原状态继续原行为。
- [ ] state_shape_errors 按字段存在触发 shape；validate_transition 追加完整状态的新约束，Issue 转成原 API 的受控字符串。不得把 null 当缺失。
- [ ] reserve_mutation 和 rollback_layer 在原候选副本中调用 invalidate_delivery，不自己写盘；run_write_state 在原锁内完成全部检查再原子写。不能锁前校验、锁后覆盖过时候选。同步执行第 3.3 节历史前缀及 count 约束，源码恢复原摘要也不得复活已撤销的 E1；覆盖新执行 E2/J2 可以重验通过的正例。
- [ ] 所有 Guard 内部候选写盘前都检查 shape/capacity，包括 pre/post、rollback、failure resolve、reservation recovery 和 override；禁止只检查公开 write-state 而漏内部路径。保持现有操作各自的转换权限，不把守卫内部回退错误地送入普通只前进转换校验。
- [ ] 写失败比较 state 原字节；满 256 失效记录时拒绝整次候选，不截断。Windows 审计拒绝不等于阻止外部直接写文件。
- [ ] 增加相邻三步正向、直接跳转负向以及协议仍表达直接转换的测试；不顺带改协议集合。
- [ ] 新 profile 的完整 candidate 写入使用有界 compare-and-swap：write-state 增加 --expected-state-sha256，run_write_state 增加 keyword-only expected_state_sha256: str | None = None。调用者读取旧 state 原始字节并计算 SHA-256，Guard 在同一锁内比较当前原始字节摘要，缺少/格式错/不匹配拒写。旧无 delivery 路径不新增强制参数；首次 profile 仍只走 initialize-state。内部锁内从当前态生成的操作保持原事务路径，不加第二个 writer 或外层 schema 字段。
- [ ] 并发测试区分：内部锁内两次变更不丢失；外部两个 candidate 基于同摘要时只有首个成功，后一个报 DELIVERY_STATE_STALE 并保留当前字节，重读重算后才可重试。单测 validate_transition 不作为并发保证。

```powershell
python -B -m pytest --rootdir . -p no:cacheprovider source/goal-enforcement/tests/test_delivery_guard.py -q
python -B -m unittest discover -s source/goal-enforcement/tests -p test_goal_guard.py -v
```

### Task 7：接受、verification 与 Closure 约束

**Files:** 修改 `goal_guard.py` 中 audit_state 及 evaluate_tool_call/evaluate_stop/run_audit 共用路径；扩展 `test_delivery_guard.py`。

- [ ] RED：外层 verification=pass 仍不能覆盖空 required、stale、声明、缺输出、旧源码；legacy 原结果不变。
- [ ] 在本任务新增 test_empty_delivery_rejected_when_acceptance_requested，并在实现接受条件后重跑 Task 5 的完整草稿正向链；负例必须要求交付证据，正例不得提前要求。两者都通过才能结束 B。
- [ ] 全量验收仅由新 profile 的显式接受标记触发：scope_result=accepted、phase=verified/complete、verification.status=pass 或 closure.recorded=true 任一成立时调用 acceptance_errors 与文件 freshness；不是仅因 delivery 字段存在就要求交付完成。
- [ ] classified/planned/executing 且 scope_result=incomplete、verification 非 pass、closure 未记录的草稿只检查结构/绑定/转换，不要求必需项提前通过。Task 5 必须在写入前使用这些非接受默认值；不通过忽略 accepted 标记来掩盖初始化冲突。
- [ ] criterion 单项 pass 的证据合法性始终受第 3.3 节约束，但不要求其他 pending 条目一起完成。进入全量接受时再检查所有适用必需项、依赖与文件新鲜性。每个接受标记分别写负向用例，不能只测终态 complete。
- [ ] 接受状态没有 workspace 无法做当前内容校验时返回缺条件；只对新 profile 加限制。Guard caller 复用原源码 fingerprint，额外独立检查被引用 evidence。
- [ ] Harness 在 Gate/Closure 重采环境、检查实际覆盖/风险/交付目标；无法提供原始观察时保持 incomplete，不加“相信 Agent”跳过开关。Guard 不能靠字段推断不存在安全风险或已经部署。
- [ ] 回归 override、open failures、in-flight mutation、verification receipt、closure fingerprint。override 不允许绕过绑定或未经确认降低验收；Windows 表述不升级。

```powershell
python -B -m pytest --rootdir . -p no:cacheprovider source/goal-enforcement/tests -q
```

B 退出：新旧双路径、拒写/并发/失效和原套件结果齐全；未解决写入边界差异阻止 C。当前维护 Goal 不原地启用 delivery。

## 6. C：一次完成接入和结构收敛

### Task 8：统一入口、契约交接与权威引用

**Files:** 修改 `source/goal/SKILL.md`、`references/layer-execution.md`、`references/output-contract.md`、`references/host-modes.md`、`references/capability-discovery.md`；新增 `references/delivery-contract.md`。修改 `source/harness-engineering/SKILL.md`、`core/flow.md`、`core/checklists.md`、`core/exit-and-reentry.md`、`core/layer-details.md`、`SPEC.md`、`CHECKS.md`、`PHASES.md`、`references/delivery-arc.md`、`references/output-contract.md`、`REQUIRED-EXECUTION-RECORD.template.md` 和 `REQUIRED-EXECUTION-RECORD.example.md`。

- [ ] RED：Web bootstrap/maintenance 正负触发、字段一致性和 WF-10 reuse；保留 bare /goal intake、元审查和引用示例排除。
- [ ] 两入口 core scope 统一为 Web 全栈，保留分类和七层；不把局部 API 改动升级成完整 bootstrap。
- [ ] Goal Stage 3 移除平行 Harness 冷路径清单，采用以下职责解释；不把这个整段文本作为必须逐字匹配的测试。

```text
After classification and required confirmation, hand execution to Harness.
Harness alone owns execution-reference loading through its runtime-stages
entry. Goal does not enumerate Harness checklists, rollback references, or
specialist execution reads. Do not load delivery execution details during
the classification-only turn. Read applicable safety constraints before
the corresponding operation.
```

- [ ] Goal 契约参考包括生成字段表、修订/确认说明；Harness 只引用字段定义，单独维护业务验收充分性，不复制 schema。
- [ ] 将实际能力发现入口 references/capability-discovery.md 接入新旧分支：已有无 delivery 的 legacy 运行仍做 capability_compatible 与所需命令/schema/宿主检查，不强求新 feature；明确请求新 Web delivery 运行时，实际指引必须在初始化/写入前调用 delivery_feature_available，并要求 web-fullstack-delivery-v1。分类回合仍不提前进入此冷路径。
- [ ] 已选 Guard 核心兼容但缺 feature 时，新模式返回结构化 CAPABILITY_DISABLED/Dependency=goal-guard，不初始化、不写 delivery、不静默退回 legacy 后声称成功。原命令缺失/核心不兼容才沿既有有限发现顺序处理，每个新模式候选都必须再查 feature；不得广泛扫描或偷换目标来源。
- [ ] capability-discovery.md 的 Successful Compatibility Reply 去掉固定脚本名字面出现、整句/段落及固定解释措辞要求，保留协议精确字段、选中依赖、实际检查结果、继续/阻止决定和 Windows 保证边界。仅改测试而保留旧运行指令不算完成。
- [ ] 新模式 host-modes/契约交接明确记录 write-state 的 --expected-state-sha256 用法、原始 state 字节摘要口径及过期拒写后的重读流程；旧运行调用方式不变。不要只实现 CLI 参数而漏掉 Agent 操作指引。
- [ ] 多处“前后端/部署必须都重做”收敛为已批准 applicability/风险裁剪引用；reused 不是免验收，not_applicable 不是环境阻塞。Goal Closure 展示只引用 Harness，不再平行模板。
- [ ] 保留 Layer 4 跨面一致性、Layer 5 安全工程、Layer 6 真实依赖/权限及准确交付目标；不借精简取消门槛。
- [ ] 在 `docs/superpowers/reviews/2026-09-08-web-fullstack-behavior-changes.md` 列出每项行为差异及确认来源；涉及超出当前设计授权的差异先审阅，不改个人 AGENTS/配置。

### Task 9：执行加载和领域路由迁移

**Files:** 新增 `source/harness-engineering/references/load-policy.json`、`references/domain-routing.md`、`references/web-fullstack-delivery.md`；修改 `references/runtime-stages.md`、`adapters/codex/host-map.md`、`adapters/claude-code/host-map.md`；移出 Goal SKILL 的 Agent Context/Tool 完整路由段。

- [ ] load-policy 根字段固定 `version/stages/routes`；route 含 `id/stage/trigger/reads/must_precede/excludes`。路径是 Harness 根相对路径或显式 skill 名；不执行字符串表达式。
- [ ] stage 为 classification/handoff/before_mutation/gate/rollback/specialist/closure，只是加载标签，不增加 Goal phase。classification 的 Harness 执行 reads 为空；handoff 只载 runtime/core/host 必要入口。
- [ ] gate 加 checklists 和当前层参考，rollback 加 exit/reentry；风险触发才加 decision-quality/专项技能。安全操作之前必须读到相关约束。
- [ ] Agent context、LLM Tool/MCP 的正向触发、普通 CRUD/REST/单次 Tool/meta 等排除条件逐项迁移；保持 MCP 先实现指引、后契约审查的既有顺序。缺依赖不恢复禁用副本。
- [ ] runtime/domain-routing 可读表由唯一 policy 校验生成，Goal 只引用入口。SC-03/04/05 检查真实读事件时点；静态图不能证明 Agent 遵守。

### Task 10：去措辞耦合并保持严格安全契约

**Files:** 修改 Goal `references/capability-discovery.md`、`scripts/validate_goal_skill.py`、`scripts/test_validate_goal_skill.py`、`scripts/test_agent_context_review_routing.py`、`scripts/test_agent_tool_contract_review_routing.py`、`scripts/test_goal_guard_integration.py`、`scripts/test_goal_skill_discovery.py`、`evals/agent-context-routing.json`、`evals/agent-tool-contract-routing.json`、`evals/trigger-queries.json`、`evals/behavior-evals.json`；修改 Harness `scripts/validate_harness_skill.py`、`scripts/contract_consistency.py`、`scripts/behavior_evals.py`、`scripts/test_validate_harness_skill.py`、`scripts/test_contract_consistency.py`、`scripts/test_behavior_evals.py` 及 `evals/contract-invariants.json`。上述 Goal/Harness 路径分别相对各自 source 包根。

- [ ] RED：相同结构/行为的两份等价解释都能通过；同时删除 Confirmation、非法 enum、伪确认、提前读冷路径和越过门禁仍失败。能力发现成功回复也要做等价解释对照，不继续断言固定脚本名字面或段落。
- [ ] 在 Goal evals/behavior-evals.json 和 Task 11 cases 中登记 delivery-entry-missing-feature、delivery-legacy-no-feature、delivery-entry-feature-supported。从 Goal 的真实入口及 references/capability-discovery.md 引导开始观察，不直接调用 helper 后就宣称入口通过：缺 feature 的新模式必须实际查询能力并返回 CAPABILITY_DISABLED，且无 initialize-state/写入 delivery 事件；legacy 无 feature 正常延续；具备 feature 时才进入新模式初始化。对应观察缺失仍为 not-run。
- [ ] 移除 Goal validator 无实验依据的 135 行硬门槛，改为体量报告及加载行为回归；不压行、不设置另一任意阈值。
- [ ] CLOSED_CLASSIFICATION_TURN_RULE 整句检查改为 rule_id/字段契约及事件顺序检查；保留 frontmatter、精确字段、所有权和安全不变量。
- [ ] route tests 改查 Goal 交接引用、Harness policy 和完整正负 case，不要求旧段落仍留在 Goal SKILL；不能仅删除旧测试。
- [ ] Harness 旧文字 grader 明确标为 text_contract；不得用关键词成绩产生 delivery accepted。新 level/provenance/status 与旧报告分开，保持历史报告可读。
- [ ] integration test 增加显式 GOAL_TEST_GUARD；discovery test 增加 GOAL_TEST_SKILLS_ROOT。未设置保留旧默认，候选回归必须显式传入。选 Guard 逻辑如下，并替换原硬编码 Path.home 行：

```python
import os
from pathlib import Path


def selected_test_guard() -> Path:
    configured = os.environ.get("GOAL_TEST_GUARD")
    return (Path(configured) if configured else
            Path.home() / "plugins" / "goal-enforcement" / "scripts" / "goal_guard.py").resolve()
```

- [ ] GREEN 后各套件独立进程执行，环境变量只设在本测试进程/会话，结束恢复原值；不得修改系统/用户持久环境。

```powershell
$env:GOAL_TEST_GUARD = "$PWD\source\goal-enforcement\scripts\goal_guard.py"
$env:GOAL_TEST_SKILLS_ROOT = "$PWD\source"
$env:GOAL_RUN_GUARD_INTEGRATION = '1'
python -B -m pytest --rootdir . -p no:cacheprovider source/goal/scripts -q
python -B source/goal/scripts/test_agent_context_review_routing.py source/goal
python -B source/goal/scripts/test_agent_tool_contract_review_routing.py source/goal
python -B -m pytest --rootdir . -p no:cacheprovider source/harness-engineering/scripts -q
python -B tools/check_rule_ownership.py --root .
python -B tools/render_delivery_reference.py --root . --check
```

C 退出：契约、加载/路由、规则权威和旧兼容同批通过；不能仅凭文案变短进入发布。

## 7. D：评测、上下文测量与发布准备

### Task 11：事件回放与结果分级

**Files:** 创建 `tools/delivery_evals.py`、`tests/test_delivery_evals.py`、`tests/fixtures/delivery-events/`、`tests/delivery-cases.json`。

- [ ] cases 保留全部 WF-01–WF-17 和 SC-01–SC-08 的独立 ID、预期观察、测试入口及适用 level；不合并成“总体通过”。
- [ ] 事件字段固定 event_id/run_id/at/kind/source/payload；kind 为 read/tool_start/tool_end/judgment/invalidation/state。校验 ID、时序、起止关联、引用和来源；敏感原文不入普通输出。
- [ ] 人工构造记录必须 synthetic，仅作为回放器单测；导入真实原轨迹保留来源/摘要，不能改名成 observed。静态清单也不等于实际读取。
- [ ] 真实 Skill 读取试验在用户授权的隔离执行上下文采集，固定提示/快照/确认输入；不为了补评测擅自创建用户任务、调用外部付费服务或恢复禁用技能。尚无授权/轨迹时可先做规范和 synthetic 单测，但对应真实观察等级必须保留 not-run，不能据此宣称加载边界已实际通过。
- [ ] 报告包含 level=contract/event_replay/fullstack_fixture、status=pass/fail/blocked/not-run、command/exit_code/artifacts/limitations；缺输入或未执行等级明确 not-run。
- [ ] RED/GREEN 覆盖只留总结而无调用、未知来源、旧 revision、环境未知、篡改证据、exit 0 无业务覆盖、颠倒加载顺序及声称已部署却无授权/事实。

```powershell
python -B -m pytest --rootdir . -p no:cacheprovider tests/test_delivery_evals.py -q
python -B tools/delivery_evals.py --cases tests/delivery-cases.json --level contract --output artifacts/evals/contract.json
python -B tools/delivery_evals.py --cases tests/delivery-cases.json --level event_replay --events artifacts/evals/observed-events.jsonl --output artifacts/evals/replay.json
```

第三条仅在实际原轨迹存在后执行。新 CLI 约定 0=已执行且全通过、1=失败、2=执行条件不满足；缺输入不能以零退出报告成功。保持旧工具退出约定不变。

### Task 12：真实隔离全栈夹具和反例

**Files:** 创建 `fixtures/web-notes/server.py`、`fixtures/web-notes/index.html`、`fixtures/web-notes/README.md`、`tests/test_web_notes_fixture.py`、`tools/run_fullstack_fixture.py`。

- [ ] fixture 流程：页面输入→POST /api/notes→SQLite 持久化→GET /api/notes→刷新可见；匿名写在服务端返回 401/403。只监听 127.0.0.1，OS 分配端口，DB/token 位于临时目录/进程环境，日志不写 token。
- [ ] RED：持久化、服务重启后重读和匿名写拒绝三项；错误变体 no-persistence、allow-anonymous-write、mock-api-only 必须让对应业务检查失败。变体仅在测试夹具，不进入用户模板。
- [ ] 服务用 ThreadingHTTPServer、sqlite3 参数化 SQL，页面 fetch 真实 API，不硬编码成功。runner 在 finally/context manager 关闭服务/浏览器/DB/临时资源；不连接生产环境。
- [ ] 以下完整浏览器检查使用 runner 给出的真实 base_url/owner_token，不 mock 网络；服务器 fixture 提供 Note 标签、Save 按钮及 notes test id。

```python
from playwright.sync_api import sync_playwright


def check_persistent_authorized_flow(base_url: str, owner_token: str) -> None:
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        try:
            context = browser.new_context(extra_http_headers={"Authorization": f"Bearer {owner_token}"})
            page = context.new_page()
            page.goto(base_url)
            page.get_by_label("Note").fill("persisted-note")
            page.get_by_role("button", name="Save").click()
            page.get_by_test_id("notes").get_by_text("persisted-note", exact=True).wait_for()
            page.reload()
            page.get_by_test_id("notes").get_by_text("persisted-note", exact=True).wait_for()
            anonymous = runtime.request.new_context(base_url=base_url)
            try:
                response = anonymous.post("/api/notes", data={"text": "forbidden-note"})
                assert response.status in (401, 403)
            finally:
                anonymous.dispose()
            context.close()
        finally:
            browser.close()
```

- [ ] 服务重启测试用同一临时 DB、不同进程；核对数据库记录归属及匿名写未落库，不只看 HTTP/page。命令、环境、隔离、输出及独立判断分别留存。
- [ ] 用候选 Guard 和新临时 Goal 验证错误夹具不被接受，不操作维护 Goal。程序 smoke 不等于 Agent+Skill 真实行为评测；后者必须同时有 Task 11 的受观察执行轨迹。
- [ ] 已核实 Python/pytest/tiktoken/Playwright 可导入、Chromium 路径存在；本次未启动浏览器或跑夹具。执行受 sandbox 限制时申请对应权限，不自动安装依赖。

```powershell
python -B -m pytest --rootdir . -p no:cacheprovider tests/test_web_notes_fixture.py -q
python -B tools/run_fullstack_fixture.py --variant correct --output artifacts/evals/fullstack-correct.json
python -B tools/run_fullstack_fixture.py --variant no-persistence --output artifacts/evals/fullstack-no-persistence.json
python -B tools/run_fullstack_fixture.py --variant allow-anonymous-write --output artifacts/evals/fullstack-anonymous-write.json
python -B tools/run_fullstack_fixture.py --variant mock-api-only --output artifacts/evals/fullstack-mock-only.json
```

期望：correct 通过；三个反例业务检查失败且不接受。测试套件以“反例被拒绝”为测试成功，报告区分被测应用失败与测试执行失败。

### Task 13：三个阶段上下文体量与读取边界

**Files:** 创建 `tools/measure_skill_context.py`、`tests/test_measure_skill_context.py`；使用 Task 1 冻结的 load-trials/baseline 与 Task 11 观察轨迹。

- [ ] 严格采用约束清单第 3 节：S1 分类、S2 Harness 接入、S3 首次受治理修改；规范必读真实文件全文去重，UTF-8 raw bytes、splitlines 行数、o200k_base。增量集合之和等于累计。
- [ ] 前后同场景/宿主/读取边界；链接别名去重，不合并不同真实文件相同内容。实际重复/局部读取另表，不能从全文主表扣除，不能漏传递必读引用。
- [ ] 单文件计量如下；保留 tokenizer 版本，缺少资源如实标未测，不自动安装或换编码。

```python
from pathlib import Path
import tiktoken


def measure_file(path: Path) -> dict[str, int]:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    encoding = tiktoken.get_encoding("o200k_base")
    return {"lines": len(text.splitlines()), "bytes": len(raw),
            "tokens": len(encoding.encode(text, disallowed_special=()))}
```

- [ ] RED/GREEN：CRLF/LF、多字节、同路径重复、相同内容不同文件、缺文件/观察、S1 越界、S3 安全晚读、规则搬入仍必读参考、长段落压行数。
- [ ] 报告逐阶段文件、前后值/差值、新增开销用途/加载时机；无任意行数/token 硬指标。旧 4,715/4,991/2,070（累计 11,776）仅是历史，不是当前前值/模型账单。

```powershell
python -B -m pytest --rootdir . -p no:cacheprovider tests/test_measure_skill_context.py -q
python -B tools/measure_skill_context.py --trials tools/load-trials.json --baseline artifacts/baseline --candidate source --output artifacts/evals/context-comparison.json
```

没有真实轨迹只能报告规范体量，实际遵守、耗时、模型成本明确未测；不承诺未经实验的成功率提升。

### Task 14：完整回归、发布候选与回滚准备

**Files:** 创建 `tools/build_release.py`、`tools/release-files.json`、`tests/test_release_bundle.py`；输出 `artifacts/release/manifest.json`、候选包及 `docs/superpowers/reviews/2026-09-08-web-fullstack-release-receipt.md`。

- [ ] 显式 allowlist 仅组装必要运行资源；维护设计/历史、活动状态、评测、缓存、fixture、测试不入包。保留运行所需 validator/reference 并验证引用闭包，安装历史不删除。
- [ ] RED/GREEN 覆盖遗漏 delivery 模块、断引用、夹带 goal-state/cache/reviews、路径穿越和链接。打包不写安装目录。
- [ ] 各套件独立进程，显式候选 Guard/skills root；receipt 包括 WF/SC、三级结果、环境、限制、来源摘要、行为差异和未解决项。不用旧安装测试冒充候选验证。 最终回归必须在下面新建的无 profile Shell 中执行：清除前序会话的 Python/pytest/Goal 测试变量，再显式配置候选路径；每条命令失败立即停止。记录新进程及实际命令，不能复用 Task 2 的会话结果。
- [ ] 安装前重核安装包/Guard 和并行 Foundation HEAD/接口/目标来源；更换来源先重做接线与回归。已有 delivery 活动运行时不回退到不支持扩展的 Guard，不降级其状态。
- [ ] 回滚按摘要定位旧运行资源备份，单列本次新增文件；不目录覆盖/递归清理，不删除历史。备份/安装/回滚执行均在单独授权之后。

```powershell
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -Command {
    Set-Location -LiteralPath 'C:\Users\14156\Documents\Codex\goal-harness-web-fullstack'
    foreach ($variable in @('PYTHONPATH', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS', 'GOAL_TEST_GUARD', 'GOAL_TEST_SKILLS_ROOT', 'GOAL_RUN_GUARD_INTEGRATION')) {
        [Environment]::SetEnvironmentVariable($variable, $null, 'Process')
    }
    $env:GOAL_TEST_GUARD = "$PWD\source\goal-enforcement\scripts\goal_guard.py"
    $env:GOAL_TEST_SKILLS_ROOT = "$PWD\source"
    $env:GOAL_RUN_GUARD_INTEGRATION = '1'
    function Invoke-PythonCheck {
        param([string[]]$PythonArguments)
        & python -B @PythonArguments
        if ($LASTEXITCODE -ne 0) { throw "Candidate check failed: $($PythonArguments -join ' ')" }
    }
    Invoke-PythonCheck -PythonArguments @('-m', 'pytest', '--rootdir', '.', '-p', 'no:cacheprovider', 'source/goal-enforcement/tests', '-q')
    Invoke-PythonCheck -PythonArguments @('-m', 'pytest', '--rootdir', '.', '-p', 'no:cacheprovider', 'source/goal/scripts', '-q')
    Invoke-PythonCheck -PythonArguments @('-m', 'pytest', '--rootdir', '.', '-p', 'no:cacheprovider', 'source/harness-engineering/scripts', '-q')
    Invoke-PythonCheck -PythonArguments @('-m', 'pytest', '--rootdir', '.', '-p', 'no:cacheprovider', 'tests', '-q')
    Invoke-PythonCheck -PythonArguments @('source/goal/scripts/test_agent_context_review_routing.py', 'source/goal')
    Invoke-PythonCheck -PythonArguments @('source/goal/scripts/test_agent_tool_contract_review_routing.py', 'source/goal')
    Invoke-PythonCheck -PythonArguments @('source/goal/scripts/validate_goal_skill.py', 'source/goal')
    Invoke-PythonCheck -PythonArguments @('source/harness-engineering/scripts/validate_harness_skill.py', 'source/harness-engineering')
    Invoke-PythonCheck -PythonArguments @('tools/check_rule_ownership.py', '--root', '.')
    Invoke-PythonCheck -PythonArguments @('tools/render_delivery_reference.py', '--root', '.', '--check')
    Invoke-PythonCheck -PythonArguments @('tools/build_release.py', '--manifest', 'tools/release-files.json', '--output', 'artifacts/release')
}
if ($LASTEXITCODE -ne 0) { throw 'Clean-shell candidate regression failed.' }
```

这里的干净 Shell 指新进程、无 profile 且清除所列前序会话变量，不声称全系统隔离；只改子进程环境，不改用户偏好。Task 3 与 B 的目标测试也须各在这种清除了 PYTHONPATH 的新 Shell 中独立跑一次，再执行最终完整回归。本轮仅写入命令，尚未运行。

期望：结果可追溯、包不含维护材料。release candidate 完成不等于安装、生产就绪或部署完成。

## 8. WF/SC 覆盖矩阵

| 验收 ID | 任务 | 必须观察到的证据 |
| --- | --- | --- |
| WF-01 | 8/9/11 | 新建 Web 契约/确认，不绑定框架 |
| WF-02 | 3/8/11 | 存量切片、复用依据与沿用技术栈 |
| WF-03 | 7/12 | 页面正常、持久化坏的真实反例拒绝 |
| WF-04 | 7/12 | API 匿名写真实失败并不接受 |
| WF-05 | 7/10/11 | 关键词/声明不能升级 observed_execution |
| WF-06 | 3/7/11 | exit 0 无覆盖/判断时不接受 |
| WF-07 | 3/4/6/11 | 源码/测试/契约变化后的 stale |
| WF-08 | 3/7/11 | 环境变化/未知、失效和重采 |
| WF-09 | 3/6/11 | 未确认降标拒绝；新 revision/确认正向 |
| WF-10 | 3/8/11 | API-only 合法复用而不强造 UI/部署 |
| WF-11 | 7/8/11 | 三种交付目标与真实部署授权区分 |
| WF-12 | 5/6/7/10/14 | 旧状态不迁移、GSD 非默认、禁用不变 |
| WF-13 | 5/11 | 缺 feature 拒绝，不静默降级 |
| WF-14 | 3/5/6 | 活动扩展删改拒绝，原状态保留 |
| WF-15 | 7/12 | mock 不冒充真实 API/DB 联调 |
| WF-16 | 4/6/11/12 | 并发/隔离反例、evidence 独立摘要 |
| WF-17 | 2/3/6 | 空集/重复/悬空/循环/上限/原子拒写 |
| SC-01 | 8/9/11 | 新建分类、确认与七层保留 |
| SC-02 | 3/8/11 | API 改动与 UI/部署复用 |
| SC-03 | 9/11/13 | 分类实际读取不进入冷路径 |
| SC-04 | 9/11/13 | 门禁/回退/安全操作前参考加载 |
| SC-05 | 9/10/11 | 专项正负触发、MCP 顺序和个人偏好 |
| SC-06 | 2/3/10/11 | 等价措辞通过、字段/授权/安全变异失败 |
| SC-07 | 14 | 包引用闭包、维护资源排除、旧安装保留 |
| SC-08 | 1/13 | 同口径三阶段增量/累计及非伪装减负 |

静态结构不代替观察；synthetic 回放不代替真实事件；程序 fixture smoke 不代替实际 Agent+Skill 表现。按实际执行等级、技术组合和样本限定成功主张。

## 9. 审阅检查点和执行授权

- A 后审阅类型/关系/确认、唯一权威及基线结果；不能先弱化要求再改实现。
- B 后审阅新旧运行、写入接口、并发/容量/回退；高风险反例未跑即 stay，不进入 C。
- C 后审阅功能与结构收敛同批结果，不保留两套竞争权威等“下一轮重构”。
- D 后逐级披露评测，提交候选/receipt；安装另行授权，不在测试末尾顺带部署。

来源漂移未审阅、目标 Guard 接口不同、旧运行回归、容量不足却想截断、无真实观测却要完成、额外权限/生产/提交/推送/安装/偏好变化，均停在最小相关任务并报告。不得停止或覆盖其他用户任务，不撤销其授权。

执行方式需用户选择：本任务按 executing-plans 顺序执行；或用户明确授权后使用 subagent-driven-development，单一集成者、无重叠写集。安装授权独立。

当前仅交付待审阅计划；Layer 4 在进行中，scope_result=incomplete、operation_state=in_progress。运行时实现、所有 RED/GREEN、产品三级评测、体量测量和安装/回滚均为 not-run。

## 10. 首个纯校验测试的完整草拟 fixture

此函数写入 `source/goal-enforcement/tests/delivery_fixtures.py`，供 Task 2/3/B 复用；不导入被收集的 test_*.py。它是测试数据，不是真实用户确认或 observed evidence；不得被真实交付接受。

```python
def draft_delivery():
    return {
        "schema_version": 1,
        "profile": "web-fullstack",
        "contract": {
            "revision": 1,
            "outcome": "用户创建并重新读取自己的笔记",
            "actors": ["owner", "anonymous"],
            "flows": ["创建后重新读取", "匿名写入拒绝"],
            "non_goals": ["生产部署"],
            "constraints": ["沿用既有技术栈"],
            "unknowns": [],
            "delivery_target": "local-runnable",
            "approval": {
                "revision": 1,
                "confirmation_id": "fixture-approval-1",
                "source": "fixture://approval/1",
                "recorded_at": "2026-09-08T00:00:00+00:00",
            },
        },
        "slices": [],
        "criteria": [],
        "evidence": [],
        "invalidations": [],
    }
```
