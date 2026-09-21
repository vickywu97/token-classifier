# Token-Classifier 诚实性审计（Howey 四要素 / 多法域定性）

> 审计目标：区分「真克制」（输入信息确实缺失，工具如实报 `unknown` / `insufficient_info`）
> 与「能力缺口」（输入**已含**相关信息，但代码未读到 / 误读，伪装成克制）。
> 方法学与 privacy-policy-checker 的 `docs/HONESTY_AUDIT.md` 一致：逐字打印原始输入、
> 引用代码路径、给出判断、记录修复方案（**只记录不修**，统一决定优先级）。
>
> 纪律（用户指令）：逐条打印原始输入，不凭记忆；遇到能力缺口只记录不修；
> token-classifier 法律风险最高（涉及证券定性），审计须最严格；不 push，按模块（A–E）逐次汇报。
>
> 代码路径索引：
> - `token_classifier/extractor.py` `scan_indicators()`（行 138–170）：扫描指标，附 `negated` 标记；`in_negation_context()`（行 82–103）：命中词前 16 字窗口内是否含否定标记（中文 `不/无/未/非…`、英文 `\bno\b` 等）。
> - `token_classifier/engine.py` `judge_factor()`（行 10–75）：`pos = [m for m in matched if not m.get("negated")]`（行 26，**否定命中整条剔除**，含 absent 权重）；无 strong/weak/absent/negated 命中 → `state="unknown"`（行 64）。
> - `token_classifier/classifier.py` `classify_howey()`（行 9–41）：`if unknown >= 3: cls = "insufficient_info"`（行 16）；`sufficiency = "none" if unknown>=3`。

---

## 报告摘要

**这份报告是什么**：对 `token-classifier`（离线代币监管定性器）的一次**诚实性审计**。目标不是「证明工具没问题」，而是系统区分两件事——**真克制**（输入信息确实缺失，工具如实报 `unknown` / `insufficient_info`）与**能力缺口**（输入已含相关信息，但代码没读到 / 误读，却伪装成克制）。

**审计范围**：Howey 四要素判定引擎 + 港新（HK SFC / SG MAS）两法域事实库 + 4 个法域隔离用例 + 3 个 demo 输入。按模块分层推进：

| 模块 | 主题 | 状态 |
|------|------|------|
| A | `insufficient_info` / `unknown` 判定逐条核查（真克制 vs 能力缺口） | 完成 |
| B | `dual_context` 覆盖度 + 消费降级 + 问题 4 系统性升级 | 完成 |
| C | weak 判定边界 + 其他三要素 strong 核查（C1–C9） | 完成 |
| D | 港新判定独立性四步：数据源 / 判定结果 / 逻辑路径 / 法理依据（D.1–D.4） | 完成 |

**核心结论（先看这三条）**：
1. **数据 / 结构层真独立，结果层仅「构造性部分通过」** —— 港新在源域、概念、criteria 上真独立（零交叉引用）；但结果层证据**全部来自构造性用例**（无真实案例回归，见下节），且两法域共用 `_ci_in` 子串匹配器，子串缺陷会同时污染两法域。
2. **两处实质缺陷（均有实测佐证）** —— ① SG PSA「数字支付代币」是**连言式功能特征**定义（含「非货币锚定」这一排除性要件），工具以正向信号 OR 判定 → **美元挂钩稳定币被误判为 DPT**（实测：与真 DPT 输出逐字相同）；② SG-MAS-002 的 criteria 用词「**集合**投资计划」**触发不了自己的指标**「**集体**投资」。
3. **缺口清单已冻结 16 项**（已修复 0 / 已测试锁定 2 / 仅记录 14）并附**修复路线图** —— 见 §待处理项清单。

**怎么读这份报告**（定性先于展开）：本节（是什么）→ 下节边界（§项目级局限）→ 模块 A–D 细节 → §审计元教训（可复用的方法论文产出）。

---

## 项目级局限：当前无真实案例回归（构造性验证）

> ⚠️ **这是本项目当前最重要的局限，建议优先于任何模块级发现阅读。**

**结论：本项目的全部验证输入均为「构造性用例」，至今不存在任何真实案例回归。**

| 验证输入 | 来源 | 性质 |
|---------|------|------|
| 模块 A / B / C 的边界用例 | 审计者自造 | 构造性 |
| 模块 D.2 的 4 个港新隔离用例 | 审计者自造（为隔离两法域指标而设计） | 构造性 |
| `demo/demo_security_token.md` | **XChain Token（XCT）** —— 名称杜撰 | 构造性（虚构代币） |
| `demo/demo_utility_token.md` | **StoragePay Token（SPT）** —— 名称杜撰 | 构造性（虚构代币） |
| `demo/demo_ambiguous_token.md` | **EcoToken（ECO）** —— 名称杜撰 | 构造性（虚构代币） |
| `tests/` 全部 56 项测试 | 基于上述构造输入 | 构造性 |

**这意味着什么（对外必须说清，不得含糊）**：
- 构造性验证只能证明「**代码在特定输入下行为正确**」——即隔离性、一致性、边界处理层面的**代码正确性**；
- **不能**证明「**代码在真实世界 / 真实监管案例下正确**」——即**法理正确性**与现实覆盖率。真实白皮书的语言远比构造用例杂乱（营销话术、跨段指代、否定与承诺交织），真实监管案例还涉及条文适用与事实认定。
- 凡引用本工具输出，须同时标注「**当前为构造性验证；真实案例回归属 Phase 2**」。

**为什么仍然公开**：合规工具的可信度来自「知道自己哪里不可靠」。这条局限不主动说明，被追问时更难看；主动标注则构成作品集叙事的一部分——「尚未完美，但清楚差在哪里」。

> 该局限在模块 D.2（用例来源标注）中被首次识别，**现已提级为项目级独立章节**，不再作为模块 D 的子发现；README「已知缺口」节将其列为**第 1 项**。

---

## 模块 A：insufficient_info / unknown 判定逐条核查

### A0. 三个 demo 的整体判定（实测）

| Demo | 综合判定 | 置信 | 信息充分度 | 计数 (s/w/abs/unk) | 触发 insufficient_info？ |
|------|----------|------|-----------|--------------------|------------------------|
| security（XChain） | likely_security | high | full | 4/0/0/0 | 否 |
| utility（StoragePay） | likely_not_security | medium | partial | 0/0/3/1 | 否（但有 1 个 unknown 要素，见 A1） |
| ambiguous（EcoToken） | possibly_security | medium | full | 2/2/0/0 | 否 |

**结论**：三个 demo 均**未**触发顶层 `insufficient_info`（unknown≥3）。三个 demo 都是信息充分、可被归类的样本，这是 demo 设计的预期（它们本就是「证券型/功能型/模糊型」的范例）。`insufficient_info` 在真实稀疏输入下确实能触发（见 A2 验证）。

### A1. StoragePay 的 `common_enterprise = unknown` —— 能力缺口（非真克制）

**原始输入（demo/demo_utility_token.md，逐字）**：

```
# StoragePay Token（SPT）机制说明

## 获取方式
SPT 为平台功能型代币，用户可免费获取该代币，不要求支付任何对价。

## 使用功能
SPT 仅用于支付平台内的存储服务费，并作为访问高级功能的功能凭证。代币仅用于支付网络内服务，不赋予任何财务权利。

## 技术与治理
StoragePay 协议完全去中心化、自执行，由智能合约自动运行，无需任何团队维护。用户独立使用代币获取服务。

## 其他安排
平台对用户不做任何价格增长或利益分配预期，代币仅作为网络内功能凭证。
```

**实测要素级结果**（utility demo）：

```
[absent ] investment_of_money  (命中: ['免费'])
[unknown] common_enterprise    (命中: 无)   ← 本应是 absent
[absent ] expectation_of_profits (命中: ['仅用于支付'])
[absent ] efforts_of_others    (命中: ['完全去中心化', '自执行'])
```

**逐字定位 `common_enterprise` 的 absent 指标 `独立使用`**：
- 输入第 10 行原文：`StoragePay 协议完全去中心化、自执行，由智能合约自动运行，无需任何团队维护。用户独立使用代币获取服务。`
- `独立使用` 是 `common_enterprise` 的 **absent 权重**指标（howey_factors.jsonl 第 2 行：`{"pattern": "独立使用", "weight": "absent"}`），语义是「独立使用 → 否定共同企业」。
- 该词**确实出现在输入中**，且未被否定语境修饰（「用户独立使用」是正面的独立使用描述）。

**为什么它被判成了 unknown（根因，逐字证据）**：

```
诊断代码输出（逐字）：
  左窗(独立使用 前 16 字): '自动运行，无需任何团队维护。用户'
  in_negation_context: True
  pattern='独立使用' weight=absent negated=True
```

- `in_negation_context()`（extractor.py 行 82–103）在命中词前 **16 字窗口内**做子串搜索，且**不识别句读/分句边界**。
- 窗口内 `无需任何团队维护` 的「**无**」（NEGATION_MARKERS_CN 含 `"无"`）被命中 → 误判 `独立使用` 处于否定语境 → `negated=True`。
- 但「无需任何团队维护」说的是「不需要团队」，与「用户独立使用代币」是**两个不同的主语/命题**，否定词并不修饰 `独立使用`。
- `judge_factor()` 行 26：`pos = [m for m in matched if not m.get("negated")]` **把被否定的命中整条剔除**——此处剔除的是 **absent 权重**指标。
- `absent` 指标被剔除后：`has_strong/has_weak` 均 False；`has_absent`（只看 `pos`，已不含被剔除项）也 False；`has_negated_strong_weak` 只统计 negated 中 weight∈{strong,weak} 的项（`独立使用` 是 absent，不计）→ 全 False → 落入 `state="unknown"`（行 64）。

**判断：能力缺口（代码误读），非真克制。**
输入**含有**明确信号（独立使用），工具逻辑里也**存在**该指标（独立使用 ∈ absent 列表），但因「否定窗口忽略句读 + 否定命中整条剔除含 absent」两个叠加缺陷，信号被吞掉，最终以 `unknown`（信息不足）呈现。**这是「能力缺口伪装成克制」的典型**——和本会话 privacy 项目里发现的三重模式同构。

**更深一层（用户指正，关键）：这是架构问题，不是边界 bug。**
`scan_indicators()`（extractor.py 行 163）对**所有**指标（含 `absent`）**无差别**调用 `in_negation_context()`。但 `absent` 指标本身**表达的就是否定信号**：
- `独立使用` → 语义即「不存在共同企业」→ 这是**正确的否定信号**，本应被采纳；
- `in_negation_context()` 的设计意图是防止「我们**不**使用」里的「使用」被误判为**肯定**信号——它只应对 `strong`/`weak` 指标有意义；
- 把 `独立使用` 这类**本就否定**的指标再送去 negation 检测 → 等于**双重否定**（被否定掉的「否定信号」反而丢失）。
所以真正的修复不是「把否定窗口按句读重置」（那只是治标，且仍让 absent 走 negation 逻辑），而是**从架构上让 absent 指标跳过 negation 过滤**——negation 检测只对 strong/weak 生效，对 absent 是架构冗余且有害。窗口重置只是补丁（防「无团队维护」这类邻句噪声误吞 strong/weak），架构修复才是主因。

**佐证 —— 该缺陷是系统性的，非偶发（A1.1 量化，经澄清重修）**：

> **澄清 1（用户质疑）：原「14 条 absent 指标中 5 条（35.7%）含否定词（不/无/未/非/独立/免/去）」统计不成立，已撤回。**
> 逐字打印 `in_negation_context` 的否定词表（`extractor.py` 行 45–48）：
> ```python
> NEGATION_MARKERS_CN = ["不","无","没有","未","非","并非","不构成","不提供","不保证","不用于",
>                        "不代表","不视为","不存在","免","禁止","不会","不得","不承诺","不向"]
> ```
> 词表**含 `免`，但不含 `独立`、`去`**。逐条核对 14 条 absent 指标（实测）：
> - 字面含 CN 否定标记：**3 条** → `免费`(免)、`无收益承诺`(无)、`无需团队`(无)
> - 字面含 EN 否定标记：**1 条** → `no profit`(`\bno\b`)
> - 字面含任一否定标记：**4/14（28.6%）** → `免费`、`无收益承诺`、`无需团队`、`no profit`
> - **`独立使用`、`完全去中心化` 字面不含任何否定标记** —— 原统计把它们算入是错的。
>
> **更关键的机制纠正**：`in_negation_context()`（行 88–89）检查的是命中词**前 16 字窗口**，不是命中词本身。因此「指标字面含否定词」**并不是** `negated=True` 的触发条件——只有该否定词实际出现在命中词上游 16 字内才会误吞。`免费` 含 `免` 不会自吞（`免` 在指标首字，窗口在它之前）。
>
> **修正后的正确量化与根因**：
> - 真正的系统性暴露是**架构层**：`scan_indicators()`（行 163）对**全部 14 条 absent 指标无差别调用 `in_negation_context`**（100% 暴露），而非「5/14 含否定词」。absent 指标本是否定信号，再经 negation 检测 = 双重否定，任何上游 16 字内的否定词（哪怕主语/命题不同）都会把它吞掉。
> - StoragePay 的 `独立使用`（字面**不含**任何否定标记）被误吞，是上述架构暴露的**直接证明**：窗口 `自动运行，无需任何团队维护。用户` 里的 `无`（来自「无需任何团队维护」，不同主语）触发误吞 → `negated=True` → `common_enterprise` 塌成 `unknown`。这比「含否定词」的统计更有力，因为它说明连不含否定词的 absent 指标也逃不掉。
> - 故原 35.7% 统计**撤回**，替换为「14/14（100%）absent 指标架构暴露」这一正确表述。

- 同一致因也影响 `strong`/`weak`，但须用**真正跨句**的例子（见下）。原举例 `本项目不提供任何分红，但由核心团队持续运营` → `分红`(strong) 被「不提供」误标 `negated=True` 是**错误示范**：「不提供分红」同句内、且语义上「不提供分红」**确实否定利润预期**，故 `negated=True` 是**正确行为，不是 bug**。
- **澄清 2 修正后的强/弱指标跨句误吞例子（已实测确认）**：`项目方不保留私钥，持币者按比例获得分红。`
  ```
  逐字诊断：
    [expectation_of_profits] '分红' weight=strong NEGATED
    window(前16字) = '目方不保留私钥，持币者按比例获得'
  ```
  「不保留私钥」（非托管，属去中心化正面特征）与「分红」（利润分配，构成利润预期）是**不同主语/命题**；`不` 落在 16 字窗口内即把 `分红` 误标 `negated=True`，使 `expectation_of_profits` 塌成 `absent`。这才是 genuine 的 strong/weak 窗口缺陷。其余候选（`本代币不用于炒作，持有者分享项目净利润分红` → 利润+分红同吞；`平台不设预挖，用户质押即可获得分红` → 质押+分红同吞）同理，证明该缺陷**跨权重**存在；架构修复（absent 跳过）只解决 absent 一半，**strong/weak 仍需窗口修复**，故两步都做、主次分清。

**影响量化**：
- 本例（StoragePay）用户侧最终判定**未被改变**：`unknown` 与 `absent` 在该 demo 里都使综合判定保持 `likely_not_security`，故 verdict 不受影响。但**要素级证据错误**：报告应展示「独立使用 → 否定共同企业(absent)」，实际展示「无证据/unknown」。
- **潜在误判风险（更关键）**：否定窗口忽略句读是**通用缺陷**，任何文本只要在某一 absent 指标前 16 字内出现 `不/无/未/非…`（哪怕是关于别的事），该 absent 信号就会被吞。若同一输入在 ≥3 个要素上因此类误吞累计到 `unknown≥3`，**会错误地把本可归类的代币判成 `insufficient_info`**（假「克制」）。属潜在错分，非纯 cosmetic。

**修复方案（记录，不修）—— 主次颠倒后修正**：

> 优先级：**架构修复为主、窗口修复为辅**，两步都做，但原因不同。

1. **【架构修复 · 主】`scan_indicators()` 让 `absent` 指标跳过 `in_negation_context()` 过滤**（extractor.py 行 163 增加按 `weight=="absent"` 的分支）。
   - 理由：absent 指标本就是否定信号，再走 negation 检测 = 双重否定。无论上下文是否有否定词，`独立使用`/`无收益承诺`/`免费` 等都**应直接计入 absent 命中**。这一步单独即可修复 StoragePay 的 G-A1，并消除全部 14 条 absent 指标（14/14=100% 架构暴露）的系统性误吞。
2. **【窗口修复 · 辅】`in_negation_context()` 以句读（`。！？!?；;`）为界重置窗口**，不在跨分句的否定词上触发（或要求前缀型标记紧邻被修饰词）。
   - 理由：架构修复只解决 absent；`strong`/`weak` 指标仍受「邻句否定词误吞」影响（如「不提供分红」→ 分红被否）。窗口修复堵住 strong/weak 这一半的同源缺陷，属补丁而非主因。
3. 以上改动须配回归测试：**新增 `tests/test_module_a_gaps.py`，其中 `test_absent_independent_use_with_neg_context` 为「否定词在邻句、absent 指标在后句」的反例**。澄清 3 修正：该用例标 `@unittest.expectedFailure`（记录「修复前应 FAIL 的已知缺口」，CI 保持全绿；架构修复后删除装饰器转正常通过）。控制用例 `test_absent_independent_use_no_neg_context` 当前即通过。**全套测试已验证：49 运行、0 失败、1 expectedFailure（`Ran 49 tests ... OK (expected failures=1)`）。**

### A2. 真克制验证（机制正确方向）

**构造输入（信息真正缺失，与代币机制无关，逐字）**：

```
本项目是一个区块链技术科普博客，主要发布行业动态与研究报告，内容涵盖密码学基础、共识算法介绍，以及每周的社群问答整理。
```

**实测**：四要素全 `unknown` → `insufficient_info`，充分度 `none`。

**判断：真克制，正确。** 输入无任何 Howey 相关信号，工具如实报「信息不足」。证明 `insufficient_info` 在「确实缺失」方向机制正常，未被破坏。

### A3. 能力缺口候选：投资资金的「劳务/算力出资」词汇未覆盖 —— **（严重度升级：中 → 中高）**

> 升级理由（用户指正）：Web3 语境里算力贡献 / 流动性挖矿 / 劳务出资是**极常见**的代币获取模式，而本工具目标用户正是不发币的 Web3 团队。该缺口**直接命中核心场景**，且会在边界情形下造成实质错分，故由「中」提至「中高」，修复优先级仅次于 G-A1。

**构造输入（逐字）**：

```
用户可通过贡献闲置算力参与网络，并按贡献比例分享协议产出的奖励，项目由核心团队持续开发并发布路线图，设有生态激励池按持币份额分红。
```

**实测要素级**：

```
[unknown] investment_of_money  命中:无
[weak   ] common_enterprise    命中:['生态']
[strong ] expectation_of_profits 命中:['分红']
[strong ] efforts_of_others    命中:['路线图','核心团队']
```

**判断：能力缺口（指标词表覆盖不足），非真克制。**
输入明确描述了「以算力/贡献参与、按比例分享奖励」——这正是 Howey 判例（SEC v. Joiner、形成判例的 Tyler 案）将「出资」扩展至**劳务/其他对价**换取权益的情形（howey_factors.jsonl 投资资金 `notes` 字段已承认此扩展）。但 `investment_of_money` 的指标词表只有 `购买/认购/出资/投资/purchase/buy/invest/contribute/ico/ieo/质押/锁仓…`，**不含 `算力/劳务/贡献(算力)`**，故该要素被判 `unknown`。

**影响量化（澄清 4 重修：每个用例打印完整四要素状态 + verdict 计算）**：

判定规则（`classifier.py` `classify_howey`，行 9–25）：
`unknown≥3 → insufficient_info`；`strong≥3 → likely_security`；
`strong==2 且 weak==2 → possibly_security`；`strong+weak≤1 → likely_not_security`；其余 → `possibly_security`。

| 用例（输入） | invest | common | profits | efforts | s/w/abs/unk | verdict | 触发规则 | invest 缺口是否左右 verdict |
|------|--------|--------|---------|---------|-------------|---------|---------|--------------------------|
| case1 算力贡献+分红+团队开发（doc 原句） | unknown | weak | strong | strong | 2/1/0/1 | possibly_security | else | **否**（2s+1w 已够 possibly） |
| case2 流动性挖矿LP+路线图（重建） | absent | weak | strong | strong | 2/1/1/0 | possibly_security | else | **否**（其余 2s+1w 兜底） |
| case3 劳务参与+分红+团队运营（重建） | unknown | unknown | strong | strong | 2/0/0/2 | possibly_security | else | **否**（2s 已够 possibly；若再叠 1 个 strong → strong≥3 → likely_security，但 invest=unknown 仍不改 security 侧） |
| case2b 流动性挖矿+其余偏弱（重建·危害态） | absent | unknown | unknown | weak | 0/1/1/2 | **likely_not_security** | strong+weak≤1 | **是（关键）**：若 流动性/挖矿 被正确识别为 invest=strong，则 s/w/abs/unk=1/1/0/2 → else → **possibly_security**，verdict 直接翻转 |

逐字实测（节选，case2b 危害态）：
```
[absent ] investment_of_money   (购买 被「无需」否→absent；流动性/挖矿 不在词表→无正向命中)
[unknown] common_enterprise
[unknown] expectation_of_profits
[weak   ] efforts_of_others     (命中:['社区治理'])
counts s/w/abs/unk = 0/1/1/2
VERDICT = likely_not_security  (规则: strong+weak<=1)
```

- **澄清 4 结论**：四个用例的 `investment_of_money` 要素**全部未正确识别为 strong/weak**（应为 strong：算力/劳务/流动性 = Joiner 扩展下的「投资资金」）。`invest` 缺口是否左右 verdict **取决于其余三要素强度**：
  - case1/2/3 中其余要素有 2 个 strong，verdict 被 `expectation_of_profits`(分红) + `efforts_of_others`(团队) 兜底在 security 侧，**invest 缺口被掩盖**——这是「要素级错误但 verdict 看似合理」的隐蔽型缺陷；
  - **case2b 危害态**证明：当其余要素偏弱（仅 1 weak），`invest=absent`（缺词导致）直接把 verdict 压到 `likely_not_security`，修复投资资金词表后会翻转为 `possibly_security`——**这才是真实错分风险**。
- **实质风险（两条路径都错）**：
  - 低估：算力/流动性贡献确构成「投资资金」，漏判 → 少一个 strong → 在**其他要素偏弱**的代币上（即 case2b 类）把 verdict 压低，甚至漏触发 `possibly/likely_security`；
  - 高估：若代币通过「空投」给算力贡献者（本非投资），但因 under-read 落 `unknown`，可能被其他 strong 要素拖成 `possibly_security`，造成假阳性。
- 目标用户即 Web3 团队，算力/挖矿/劳务是日常模式，该缺口**直接命中核心场景**，须优先补词表。

**缺失的 Howey Joiner 扩展词（补充 2c：对照 `investment_of_money` 现有指标）**：

现有指标（21 条）：`购买/认购/出资/投资/purchase/buy/invest/contribute/ico/ieo`（strong×10）、`兑换/swap/质押/stake/staking/锁仓/lock`（weak×7）、`空投/airdrop/免费/free/赠予`（absent×4）。
缺失的 Joiner 扩展词（需增补为 strong/weak）：**`算力`、`劳务`、`贡献`、`工作`、`服务`、`挖矿`、`流动性`、`提供流动性`**（及英文 `staking reward`、`LP`、`contribution`）。其中 `贡献` 与现有英文 `contribute` 语义对应但中文缺失，优先补中文同义词。

属指标词表覆盖缺口，需在 `howey_factors.jsonl` 增补劳务/资源对价类同义词（记录，不修）。

### A4. 模块 A 小结（逐条判定归类）

| 项 | 输入是否真缺信息 | 代码是否读到 | 归类 |
|----|----------------|-------------|------|
| A0 security/utility/ambiguous 三 demo | 否（均充分） | 是 | 真克制边界正常（均未误报 insufficient_info） |
| A1 StoragePay `common_enterprise` | **否（含「独立使用」）** | **否（否定窗口误吞 absent）** | **能力缺口（误读）** |
| A2 科普博客（稀疏） | 是 | 是（正确报 unknown） | 真克制（机制正确） |
| A3 算力/劳务出资 | **否（含贡献算力描述）** | **否（词表未覆盖）** | **能力缺口（覆盖不足）** |

**待统一决策的能力缺口清单（模块 A）**：
- **G-A1**（高）：**架构级**——`scan_indicators()` 对 `absent` 指标无差别跑 negation 检测（双重否定）+ 否定窗口忽略句读 → absent 信号误吞、潜在错判 insufficient_info。**量化（澄清 1 重修）：14/14（100%）absent 指标被无差别传入 `in_negation_context`（架构暴露），系统性非偶发；原「5/14(35.7%) 含否定词」统计因词表误列（独立/去 不在词表）且机制错判（窗口检测而非字面自含）已撤回。** 修复优先级：架构修复（absent 跳过 negation）为主、窗口修复为辅。边界测试见 `tests/test_module_a_gaps.py`（目标用例标 `expectedFailure`，全套 49 测全绿）。
- **G-A3**（**中高**，由中升级）：`investment_of_money` 词表缺劳务/算力/流动性对价同义词（Howey Joiner 扩展未落地到指标）。目标用户（Web3 团队）核心场景，3 个构造用例均 under-read。修复见 A3。

## 模块 A 补强轮（三处补强，澄清后再强化）

> 用户对「四点澄清」补充三处补强 + 一处状态确认。全部用实际代码跑通验证，非推理。

### B1. 实际误吞数：14/14 架构暴露 + 1/14 实际误吞（7.1%）

澄清 1 用「14/14 架构暴露」替换作废的「5/14(35.7%)」。但「架构暴露」= 代码路径会调用 `in_negation_context`，**不等于「实际误吞」**。实际误吞仅发生在「命中词前 16 字窗口内恰好有否定词」的场景。

跑三个 demo + 模块 A 边界用例，实际被 `negated=True` 吞掉的 absent 命中逐条：

| 语料 | factor | 指标 | abs_idx | 窗口(前16字) |
|------|--------|------|---------|-------------|
| demo/utility (StoragePay) | common_enterprise | 独立使用 | 194 | `自动运行，无需任何团队维护。用户` |
| A1 隔离（独立使用上游无关否定词） | common_enterprise | 独立使用 | 9 | `无需团队维护，用户` |
| A1 隔离（StoragePay 原句） | common_enterprise | 独立使用 | 45 | `自动运行，无需任何团队维护。用户` |

去重后**唯一被误吞的 absent 指标 = `独立使用`（1/14 = 7.1%）**。其余 13 条 absent 在当前语料中均未触发误吞。

**报告须同时标注两个数字**：`14/14 架构暴露`（缺陷的潜在面——任何新输入只要在 absent 指标前 16 字内出现无关否定词，哪怕不同主语，就会误吞，是潜在错分面）+ `1/14 实际误吞 (7.1%)`（已观测发生面）。二者不互相替代。

### B2. 澄清 2 的「塌成 absent」逐字确认

用例逐字：`项目方不保留私钥，持币者按比例获得分红。`

`expectation_of_profits` 共 19 条指标，逐条排查命中：

| 指标 | 权重 | 命中 | 状态 |
|------|------|------|------|
| 分红 | strong | 命中 | **negated=True** |
| 收益/利润/年化/apy/股息/dividend/升值/增值/appreciation/回报/yield/回报预期 | strong | 未命中 | — |
| 潜在价值/可能上涨/potential upside | weak | 未命中 | — |
| 仅用于支付/无收益承诺/no profit | absent | 未命中 | — |

→ 唯一命中是 `分红`(strong) 且被吞；无其他正向命中 → 按 `judge_factor` 行 61（`has_negated_strong_weak → absent`）**塌成 `absent`，非 `weak`**。

**限定条件（重要）**：此结论仅在「`分红` 是文本中唯一利润类指标」时成立。若文本另有未受否定的 `收益`/`回报`/`增值` 等正向指标，则 `expectation_of_profits` 会是 `strong`/`weak` 而非 `absent`。原表述「塌成 absent」对澄清 2 用例**正确**，但须加此限定，避免被误读为「strong 被吞必然塌成 absent」。

### B3. 修复方案风险分析（在 scratch 副本实测，不动真文件）

#### B3a. 架构修复（absent 跳过 negation）—— 安全面与危险面

把 absent 指标跳过 `in_negation_context` 后实测：

- ✅ **对 6 条「属性描述型」absent 安全**（跳过否定正确）：`独立使用`/`independent use`（common_enterprise）、`完全去中心化`/`自执行`/`smart contract`/`无需团队`（efforts_of_others）。StoragePay 的 `独立使用` 修复后正确判 absent。
- ❌ **对 8 条「要素否定型」absent 危险**（跳过否定会引入假阳性）：`空投`/`airdrop`/`免费`/`free`/`赠予`（investment）、`仅用于支付`/`无收益承诺`/`no profit`（expectation）。这类指标本身编码「缺乏某要素」，文本若**自我否定**则语义反转。实测误判：
  - `我们不是免费提供服务` → investment_of_money 误判 **absent**（应为 strong/投资，因「不免费」= 需付费）
  - `本平台代币不免费，需购买` → investment_of_money 误判 **absent**（应为 strong）
  - `项目并未做出无收益承诺，反而承诺高额分红` → expectation_of_profits 误判 **absent**（应为 strong）

**补强 A：14 条 absent 指标完整分类证据表**（逐条来自 `howey_factors.jsonl`，分类经 scratch 实测确认）：

| # | 指标 | 所属要素 | 分类 | 跳 negation 是否安全 | 危险场景（自我否定时） |
|---|------|---------|------|---------------------|----------------------|
| 1 | 独立使用 | common_enterprise | property | ✅ | — |
| 2 | independent use | common_enterprise | property | ✅ | — |
| 3 | 完全去中心化 | efforts_of_others | property | ✅ | — |
| 4 | 自执行 | efforts_of_others | property | ✅ | — |
| 5 | smart contract | efforts_of_others | property | ✅ | — |
| 6 | 无需团队 | efforts_of_others | property | ✅ | — |
| 7 | 免费 | investment_of_money | element | ❌ | 「不免费」→ 应判投资资金 strong，误判 absent |
| 8 | free | investment_of_money | element | ❌ | 「not free」→ 应判投资资金 strong，误判 absent |
| 9 | 空投 | investment_of_money | element | ❌ | 「非空投」→ 属发售，应判投资资金 strong，误判 absent |
| 10 | airdrop | investment_of_money | element | ❌ | 「not airdrop」→ 应判投资资金 strong，误判 absent |
| 11 | 赠予 | investment_of_money | element | ❌ | 「非赠予」→ 属买卖，应判投资资金 strong，误判 absent |
| 12 | 仅用于支付 | expectation_of_profits | element | ❌ | 「并非仅用于支付」→ 可作投资，应判利润预期 strong，误判 absent |
| 13 | 无收益承诺 | expectation_of_profits | element | ❌ | 「做出收益承诺」→ 应判利润预期 strong，误判 absent |
| 14 | no profit | expectation_of_profits | element | ❌ | 「with profit」→ 应判利润预期 strong，误判 absent |

> 合计 **6 property（✅ 可安全跳过 negation）+ 8 element（❌ 不可盲跳）**。无此表则读者无法验证 6/8 分类，故列为核心证据而非附录。`仅用于支付` 的 element 分类经实测确认（文本「该代币并非仅用于支付，也支持投资增值。」→ `仅用于支付` 命中且 `negated=True`，盲跳后误判 absent）。

**结论**：盲跳 negation 的架构修复**不可用**。需更细处理——按指标语义二分：`属性描述型` 跳过 negation（安全）；`要素否定型` 遇否定不跳过，且**被否定的要素否定型 absent 应翻转为正向证据**（如「不免费」→ 构成投资资金 strong）。建议数据层给每条 absent 加 `negation_semantics: property | element` 字段区分。

**补强 B：「翻转为正向证据」方案的自身边界（已知缺陷，须标注）**

「要素否定型遇否定翻转为正向证据」比「盲跳」进了一步，但**并非完整解法**。反例：

```
文本：我们不是免费提供服务，但也不收取任何费用。
解析：「免费」命中，被「不是」否定 → 按翻转规则 → 判 investment_of_money = strong（需付费）
矛盾：后句「也不收取任何费用」→ 实际仍免费 → 应为 absent
```

→ 翻转规则混淆了「**局部否定指标**」（否定的是「免费」这个词）与「**整体否定状态**」（否定的是「收费」这个状态）。当文本用「不是 A，但也不是非 A」的对称否定结构时，翻转规则会给出错误结论。

**处置**：此边界**不建议在本轮实现**（需引入「整体状态」语义解析，复杂度高、易引入新回归）。但必须在报告中明确标注为**「element 型修复方案自身的已知边界」**——即：即便未来按 `negation_semantics: element` 实现「翻转」，仍需额外的「对称否定 / 整体状态」判定，否则该方案只是把 G-A1 从「误吞」换成「误翻转」，并未真正闭合。当前记录未修。

#### B3b. 窗口修复（按句读重置）—— 5 个边界用例验证安全

重置窗口到最近句读（`。！？!?；;`）后，`in_negation_context` 只在指标所在分句内查否定词。5 个边界用例：

| 用例 | 指标 | 原 negated | 修复后 negated | 判定 |
|------|------|-----------|---------------|------|
| `我们不承诺分红，但保留解释权。` | 分红 | True | True | ✅ 同句否定保留 |
| `本条款不适用。我们承诺分红。` | 分红 | True | **False** | ✅ 跨句否定释放 |
| `我们承诺分红。但本条款不保证收益。` | 收益 | True | True | ✅ 同句(指标所在句)否定保留 |
| `不提供分红，用户独立使用代币。` | 独立使用 | True | True | ⚠️ 逗号隔开的跨小句未释放（见下） |
| `不提供任何分红的代币。` | 分红 | True | True | ✅ 同句否定保留 |

→ 5 例中**无任何「正确否定被误释放」**（无假阳性），窗口修复对强/弱指标**安全**。

**限定（重要）**：句读重置只重置到句末标点（`。！？`），逗号（`，`）分隔的**同句跨小句**否定不会释放（第 4 例 `不提供分红，用户独立使用代币。` 中 `独立使用` 仍被前小句 `不` 误吞）。要覆盖此类需额外在 `，`、`、` 处重置。架构修复（absent 跳过）对 absent 指标覆盖更完整（含逗号场景），故**架构修复仍为主、窗口修复为辅**的排序不变；窗口修复主攻强/弱指标的跨句误吞且已验证安全。

## 模块 B：dual_context 覆盖度与消费降级审计

> 审计对象：`engine.py:30-50`（降级 / dual_context 逻辑）、`extractor.py:69-73`（`_ci_in` 匹配）、
> `howey_factors.jsonl` 的 `investment_of_money` 配置（`purchase_indicators` / `consumption_context` / `investment_rebuttal`）。
> 纪律：逐字打印输入；能力缺口只记录不修；判定分「真克制 / 能力缺口」；每例附代码路径引用。

### B.1 三问题框架（经用户纠正后定稿）

| 问题 | 纠正后定性 | 证据用例 | 性质 |
|------|-----------|---------|------|
| 1. `购买` 作 strong 是否过泛 | **是**：不限定对象词（代币/份额/权益），非投资购买误判 strong | B4（服务器硬件）、B6（纯购买）、B8（购买+分红） | 指标过泛 |
| 2. dual_context 是否真双语境 | **触发过窄（词表锁定）**，非过宽误标：仅 `purchase_set={购买,buy,purchase}` + 消费词 + 反证词 三条件齐备才标 | B3（认购不标 dual，字面正确非漏报）、B3b（购买标 dual） | 触发词表锁定 |
| 3. consumption 降级是否过宽 | **不过宽，但范围过窄**（对称问题2）：对「购买类」正确降级，且仅绑定 purchase_set | B2（正确降 weak）、B7（无误伤） | 范围过窄 |

**dup_context 真实定义（从 `engine.py:36-50` 逐行读出）**：
```python
if m["weight"]=="strong" and m["pattern"].lower() in purchase_set:  # purchase_set={购买,buy,purchase}
    if cons_hit and not rebut_hit:
        m["weight"]="weak"; m["downgraded"]=True          # 纯消费 → 降级
    elif cons_hit and rebut_hit:
        m["dual_context"]=True                            # 消费+投资反证 → 双语境标柱
```
即 dual_context 语义确实是「购买行为兼具消费支付与投资收益双重性质」，但**触发被词表锁定在 `purchase_set`**——`认购/投资/出资` 在完全相同的双语境里**不标柱**。

### B.2 问题 4：consumption_context 子串匹配系统性缺陷（强化1 完整枚举）

**机制确认**（`extractor.py:69-73`）：`_ci_in` 对中文做 `needle in haystack` 精确子串匹配、英文大小写不敏感 `in`——**全无词边界**。`consumption_context` 实值（7 词）：
`['支付','服务费','手续费','使用费','消费','购买服务','兑换服务']`。其中 `购买服务` 是 `购买`(purchase_set)+`服务` 的拼接词。

**7 词完整碰撞枚举（每词构造「购买 + 碰撞短语」，验证降级是否误触发）**：

| consumption 词 | 碰撞短语 | _ci_in | 含 购买→降级 | invest 状态 |
|---------------|---------|--------|------------|------------|
| 支付 | 支付宝 / 支付通道 / 支付机构 | True×3 | **True×3** | weak |
| 服务费 | 服务费率 / 服务费用 | True×2 | **True×2** | weak |
| 手续费 | 手续费用 | True | **True** | weak |
| 使用费 | 使用费用 / 使用费率 | True×2 | **True×2** | weak |
| 消费 | 消费者 / **消费者权益** / 消费品 | True×3 | **True×3** | weak |
| 购买服务 | 购买服务器 / 购买服务协议 / 购买服务费 | True×3 | **True×3** | weak |
| 兑换服务 | 兑换服务费 / 兑换服务卡 | True×2 | **True×2** | weak |

**16/16 碰撞短语在「`购买`/`buy`/`purchase` 与碰撞词共现」时全部误触发降级** → 影响面**不是「仅 购买服务 一词」，而是整个 consumption_context 词表的系统性缺陷**（子串匹配 + 无词边界）。

> **前提条件（关键限定，避免夸大）**：降级路径的**主条件**是 `购买`/`buy`/`purchase` 命中（`engine.py:37` 的 `m["pattern"].lower() in purchase_set`），`消费语境词(cons_hit)` 只是**辅助条件**（`engine.py:38`）。因此「16/16 误降级」只有在 `购买` 与碰撞词**共现**时才成立；若文本只含「消费者权益」「支付宝」「消费品」等碰撞词而**不含** `购买`，不会进入降级分支（`cons_hit` 单独不足以触发——`judge_factor` 只对已命中 `purchase_set` 的 strong 指标做消费降级）。原「16/16 全部误触发降级」须在此限定下理解：**不是「任何含消费词文本都降级」，而是「含购买 + 含消费词的文本有 16/16 概率误降级」**。电商/服务类高频误触发场景（见下）也均满足「购买 + 消费词共现」结构。

**高危特别验证（用户预警的「消费者权益」高频词）**：
```
输入（逐字）：用户购买平台代币，我们重视消费者权益，提供透明的服务。
解析：'消费' ∈ '消费者权益' → cons_hit=True；'购买'∈purchase_set 且 rebut_hit=False
     → 购买 被降级为 weak，invest 状态=weak
```
任何电商/服务类代币文本只要同时出现「购买」与「消费者权益」「支付宝」「消费品」等高频词，都会被**错误降级**。这是真实生产场景（非边角 case）。

**严重性升级**：问题 4 从「代码缺陷（单点）」升级为「**系统性缺陷**」——只要子串匹配 + 无词边界存在，新增任何消费词都可能引入同类碰撞。修复建议：`_ci_in` 对中文改词边界/语义匹配，或移除 `购买服务` 拼接词、消费词改为「消费+抵扣/消费+用途」等约束短语。

### B.2.1 问题 4 修复方向候选（记录不修）

审计报告纪律：发现问题 **+ 给出修复方向（记录不修，统一决定优先级）**。问题 4 已定性为系统性缺陷，以下 3 个候选：

- **候选 A：子串 → 词边界匹配**。对中文引入分词 / 词边界约束（如 `消费` 须为独立词而非 `消费者权益` 的子串）。
  - **为什么不可行（三条，逐条是硬约束）**：
    1. **违背零依赖原则（决定性）**：中文没有空格，词边界**无天然标记**，要判定「`消费` 是否独立成词」必须引入分词器（jieba / pkuseg 等）或大型词表。本项目定位是 **stdlib-only、离线可用**（README 明示零外部依赖），引入分词库直接破坏该定位，也破坏 CI 的可复现性（无需联网装包）。
    2. **自写边界正则不可靠**：若退而求其次用正则 / 邻接字表模拟词边界，中文复合词形态多变（`消费者` / `消费品` / `消费者权益` / `消费抵扣`），规则会迅速膨胀且必然漏判，维护成本高于收益。
    3. **即便做成，A 也不充分**：A 只解决「子串碰撞」（`消费` ⊂ `消费者权益`），**不解决「跨句共现」误降级**——`购买` 与 `消费抵扣` 分属两句时仍会误降级，那属于候选 B 的域。故单靠 A 不能闭合问题 4。
  - 结论：A 方向「正确但代价与定位冲突」，当前阶段**不推荐**；仅当未来接受引入分词依赖时再重估。
- **候选 B：消费词与 `购买` 同句 / 近邻约束**。降级仅在「`购买`(purchase_set) 与消费词位于同一句 / 邻近窗口内」时触发，复用现有句级逻辑（`in_negation_context` 的句读重置思路）。**简单、零新增依赖**，直接堵住「消费者权益 / 支付宝」这类与 `购买` 跨句的误触发。**但局限**：候选 B 只约束「何时算消费降级」，不解决 `购买服务` 这类**纯子串**碰撞（见下）。
- **候选 C：消费词列表收窄**。从 `consumption_context` 移除可碰撞词——删除拼接词 `购买服务`（它本就是 `购买`+`服务`，必然与 `购买` 同现误触），并将 `消费` 改为约束短语（如 `消费抵扣` / `消费用途`）以排除 `消费者权益` / `消费品` / `消费者`。代价是消费降级覆盖面缩窄（漏掉「纯消费无购买动词」场景），但因 `购买` 已是主条件，收窄几乎不损失正判。

**推荐：候选 B + C 组合**（既有语境约束又清理碰撞词）。**两者互补，任一单独均不充分**：

| 单独用 | 能挡住 | 挡不住（故需另一个） |
|--------|--------|---------------------|
| 仅 B（同句/近邻约束） | 跨句共现误降级（如「购买代币……我们重视消费者权益」分属两句） | **纯子串碰撞**：`购买服务` 与 `购买` 天然同句（「购买服务器」），同句约束**反而放行**它，必须靠 C 删除该拼接词 |
| 仅 C（收窄词表） | 高频碰撞词误触（`消费者权益`/`支付宝`/`购买服务`） | **跨句共现**：收窄后剩下的 `支付`/`服务费` 与跨句的 `购买` 共现仍会误降级，必须靠 B 的语境约束 |

**推荐理由**：C 是**低成本、高收益**的先手（删除 1 个拼接词 + 1 个泛词即可消除大多数高频误触，且不改任何逻辑）；B 是**兜底**（复用现有句级逻辑，堵住剩余跨句场景）。两者均**不引入新依赖**、不破坏零依赖原则——这是相对候选 A 的决定性优势。可在单 PR 内实现，并同步删除 `test_b4_substring_collision_no_false_downgrade` 与 `test_b4_consumer_rights_no_false_downgrade` 的 `expectedFailure` 装饰器（转正常通过）。
**残留风险（须标注）**：B 的「同句 / 近邻窗口」阈值需实测定标，窗口过宽会漏掉真实消费降级（回归风险），过窄则挡不住中等距离的共现——建议补一组「距离梯度」边界测试再定窗口值。

### B.3 补强 1：消费降级目标 = weak（设计决策，非能力缺口）

```
输入（逐字）：用户可购买平台代币用于支付平台内的各项服务费，代币仅作消费抵扣用途。
解析：'购买'(strong∈purchase_set) → cons_hit=True, rebut_hit=False → 降为 weak
      invest 状态=weak；其余三要素 unknown → 整体 verdict=insufficient_info
```
**降级目标是 weak 而非 absent 的设计理由**（`engine.py:17-22` docstring + factor 级 dispute_note）：代币购买**确实发生**（资金为代币易手），只是主导语义为消费，故保守保留 weak 信号（合规工具倾向 over-flag），而非归零为 absent。若改 absent 需「纯消费且零投资意图」的更严口径。
**测试锁定**：`tests/test_module_b.py::test_b2_consumption_downgrade_target_is_weak`（通过）——断言 购买 须 `downgraded` 且 `weight=='weak'`、invest 状态==weak（非 absent）。

### B.4 补强 2：G-A1 修复双维度护栏（补强2 + 模块A补强3 的完整表达）

G-A1 架构修复必须**同时**约束两个维度，否则引入回归：
- **维度 1（weight）**：只对 `absent` 指标跳过 negation，避免 B7 的 strong 否定路径被吞。
- **维度 2（semantics）**：absent 指标内部按 `property / element` 分别处理（呼应模块A补强3 的 6/8 二分）。

4 条路径锁定（`tests/test_module_b.py::TestModuleAGA1TwoDimensionFixGuard`）：

| 路径 | 条件 | 当前行为 | 修复后目标 | 测试现状 |
|------|------|---------|-----------|---------|
| A | absent+property(独立使用)+否定语境 | NEGATED → unknown（**G-A1 bug**） | 跳过 negation → absent | `@expectedFailure` |
| B | absent+element(免费)+否定语境（不免费） | 否定→丢弃，不作 absent 证据 | 不跳过，否定后**不得**产生 absent 证据 | 通过（锁约束） |
| C | strong+否定语境（无需购买，B7） | NEGATED → absent | 保持现有 negation → absent | 通过（回归护栏） |
| D | absent+property(独立使用)+无否定 | absent（正确） | 保持 absent | 通过（对照） |

**关键回归护栏**：naive「对所有 absent 跳过 negation」会让路径 B 的「我们不免费」误判 absent（免费），且若泛化到 strong 会破坏路径 C 的 B7（购买被否定→absent 的正确结果翻成 strong）。故修复必须 weight-scoped + semantics-scoped 双约束——印证模块A补强3 的「属性/要素二分」是同一设计的完整表达。

### B.5 补强 3：B5 锁仓=weak 有法律争议（已知法律不确定性，非能力缺口）

```
输入（逐字）：项目方将代币空投给早期用户，用户需锁仓一定期限后方可交易，项目方承诺按持币比例分配收益。
解析：'锁仓'(weak) / '空投'(absent) / '收益'(strong)
      四要素：invest=weak（weak 优先于 absent）, profits=strong, common/efforts unknown → 1/1/0/2 → possibly_security
```
`锁仓`/`lock` 当前判 `weak`，**但 SEC 判例对「锁仓单独构成 investment of money」认定并不统一**（多为流动性/vesting 机制，须结合其它对价才可能构成）。故该判定属**存在争议的简化**——性质是**已知法律不确定性，非能力缺口**。报告须给 `锁仓`/`lock` 补 `dispute_note` 标注；当前仅记录未改数据（与 G-A3 形成对照：G-A3 是算力/劳务/流动性对价词**缺失**的真实缺口，B5 是已收录但法律边界模糊的简化判定）。

### B.6 深层共性：purchase_set 硬编码

降级（B.3）与 dual_context（B.1 问题2）两套逻辑都**硬编码在 `purchase_set={购买,buy,purchase}`** 上：
- `认购/投资/出资` 等同权重的投资词既不享受消费降级保护（B4 中 `出资` 直接 strong），也**不获 dual_context 标柱**（B3 认购不标）。
- 这是模块 B 最该记的架构性观察：消费降级与双语境检测应基于「投资资金要素的语义」而非「购买」字面，否则以 `认购/投资/出资` 表述的双性质代币系统性漏判。

---



## 模块 C：weak 判定边界 + 其他三要素 strong 核查（C1-C4）

> 审计对象：`engine.py:52-64`（状态优先级 strong>weak>absent>unknown）、`classifier.py:9-25`（`classify_howey` 综合 rubric）。
> 纪律：逐字打印输入；能力缺口只记录不修；判定分「真克制 / 能力缺口 / 设计决策」；每 4 用例汇报一次（本批 C1-C4）。

### C.0 问题1：所有 weak 判定的来源路径枚举

跑 3 个 demo + 模块 B 的 B2/B4 + C1-C4，共 **12 个 weak 指标命中**，按来源路径分布：

| 来源路径 | 数量 | 明细 |
|---------|------|------|
| 指标本身 weight=weak | 9 | 锁仓×3（C1/C3/C4）、生态×2（DEMO-SEC/DEMO-AMB）、兑换（DEMO-AMB）、部分去中心化（DEMO-AMB）、社区治理×2（DEMO-AMB/C4） |
| strong 被消费降级（B2 路径） | 3 | 购买（B2）、购买（B4）、购买（C2） |

> 注：DEMO-SECURITY 的 `生态`(weak) 命中 common_enterprise，但该因子另有 strong 命中（最终 4/0/0/0），故 `生态` 作为 weak 指标存在但未成为因子状态——**枚举的是 weak 指标命中，非 weak 因子状态**。其余 11 个 weak 指标均成为对应因子状态（或被降级 / 优先级规则处理）。

**结论（问题1）**：weak 判定**全部合理**——9 个来自权重本就为 weak 的指标（锁仓 / 社区治理 / 生态 / 兑换 / 部分去中心化，均为「弱信号」语义），3 个来自消费降级（B2 路径，目标 = weak 是设计决策）。**未发现 weak 误判**。weak 的两种来源路径清晰、可解释。

### C.1-C.4 用例（逐字）

#### C1：纯 weak 指标命中（锁仓）— 验证 weak 不被错误升级

输入（逐字）：`项目方要求用户锁仓代币后方可交易。`

```
四要素：investment_of_money=weak（锁仓, weight=weak）
        common_enterprise=unknown / expectation_of_profits=unknown / efforts_of_others=unknown
四态计数：strong=0 weak=1 absent=0 unknown=3
Howey 综合：insufficient_info（confidence=low）
路径：unknown>=3 → insufficient_info
```

- **路径**：`judge_factor` 命中 `锁仓`(weak) → 该因子 weak；其余三因子无命中 → unknown。
- **判定**：**真克制 / 设计决策**。weak 指标正确保持 weak，未升级为 strong；verdict 因 3 unknown 落 insufficient_info，对稀疏信号保守正确。无错误升级。✅

#### C2：strong 被消费降级（B2 场景）— 验证降级路径稳定

输入（逐字）：`用户使用人民币购买平台代币，代币用于支付平台内的课程服务费。`

```
四要素：investment_of_money=weak（购买, DOWNGRADED→weak）
        common/efforts/profits=unknown
四态计数：strong=0 weak=1 absent=0 unknown=3
Howey 综合：insufficient_info
路径：unknown>=3 → insufficient_info
```

- **路径**：`购买`(strong) 命中 purchase_set，cons_hit（服务费 / 支付）→ 无 rebut → `downgraded=True`，weight→weak（`engine.py:37-39`）。
- **判定**：**设计决策**（消费降级目标 = weak，模块 B 已定稿）。降级稳定复现 B2，未误升为 strong。✅

#### C3：空投（weak 优先于 absent）— 验证优先级依据

输入（逐字）：`项目方将代币空投给早期用户，用户需锁仓一定期限后方可交易，项目方承诺按持币比例分配收益。`

```
四要素：investment_of_money=weak（锁仓 weak + 空投 absent → 优先级取 weak）
        expectation_of_profits=strong（收益）
        common/efforts=unknown
四态计数：strong=1 weak=1 absent=0 unknown=2
Howey 综合：possibly_security（confidence=low）
路径：else（strong+weak=2，非 2&2）→ possibly_security
```

- **路径**：investment_of_money 同场命中 `锁仓`(weak) 与 `空投`(absent)。`engine.py:52-64` 优先级 `has_weak → state=weak`，**absent 被 weak 压过**。docstring 明示："absent 类指标仅在该要素无任何 strong/weak 命中时生效，避免「既购买了又空投」被错误判为 absent"。
- **判定（C3 重点）：设计决策（有依据，但为 blanket 规则）**。优先级在 `engine.py` 硬编码且文档化，意图是防止「又买又空投」被误判 absent。对 C3（空投 + 锁仓）：锁仓是投资型限制（illiquidity / vesting），判 weak 比 absent 更保守（偏 security），**结果可辩护**。但需注意：该优先级是**因子级 blanket 规则**，非按案情判定——任何 weak 都会压过同因子 absent，即便 weak 是附带信号。本例结果合理，不记为缺陷，但标注为「blanket 优先级，依赖个案复核」。
- verdict possibly_security 由 `收益`(strong profits) + invest=weak 驱动，合理。

#### C4：多 weak 叠加（锁仓 + 社区治理）— 验证 2 weak 对 verdict 的推动

输入（逐字）：`用户需锁仓代币，项目完全由社区治理，无中心化团队管理。`

```
四要素：investment_of_money=weak（锁仓）
        efforts_of_others=weak（社区治理）
        common_enterprise=unknown / expectation_of_profits=unknown
四态计数：strong=0 weak=2 absent=0 unknown=2
Howey 综合：possibly_security（confidence=low）
路径：else（strong+weak=2，非 2&2）→ possibly_security
```

- **路径**：`锁仓`(invest weak) + `社区治理`(efforts weak) → 两因子 weak；common / profits unknown。
- **判定（C4 重点，两层）**：
  - **第一层（表象）**：2 weak（零 strong）≡ 2 strong → possibly_security。weak 阈值权重偏重（见下「更尖锐的观察」）。
  - **第二层（根本 · 用户深挖）**：用 **Howey Test** 重析 C4。C4 四要素：investment=weak(锁仓)、common=unknown/absent、**expectation_of_profits=absent（无收益预期）**、efforts=weak(社区治理)。Howey 判据是**四要素同时满足**，且 **"expectation of profits" 是核心要件**——没有利润预期就不构成投资合同。但 rubric 判 **possibly_security**，把「利润预期 absent」的代币判成「可能构成证券」，**与 Howey 法理相悖**。故根本问题是 **rubric 未对 Howey 核心要件（利润预期）赋特殊权重**，而非简单的 weak 权重偏重。
  - **极端验证（C9，见下）**：investment=strong, common=strong, **profits=absent**, efforts=strong → 按 rubric `strong>=3 → likely_security`；按 Howey：无利润预期 → 不构成投资合同 → 应 **likely_not_security**。**3 strong + profits absent 被判 likely_security，是 rubric 的实质性误判**，比 C4 更尖锐地证明严重性。
  - **定性变更**：C4 性质从「权重偏重（表象）」升级为「**rubric 未对利润预期赋 Howey 核心权重（根本）**」。属**设计缺陷（设计决策层面）**，非代码 bug；但影响**跨所有代币的判定**，非单案例边界。

### C5-C9 用例（逐字）

#### C5：生态 单独出现（无其他信号）— common 是否过判 strong

输入（逐字）：`该项目构建了一个庞大的生态，用户可在其中使用代币。`

```
四要素：common_enterprise=weak（生态）
        investment/common/profits/efforts=unknown
四态计数：strong=0 weak=1 absent=0 unknown=3
Howey 综合：insufficient_info（confidence=low）
路径：unknown>=3 → insufficient_info
```

- **路径**：`生态` 权重=weak（非 strong），命中 common_enterprise。
- **判定**：**真克制 / 设计决策**。`生态` 这类泛词**只到 weak，未越级为 strong**，verdict 落 insufficient_info。回答了原问题"会不会把生态这类泛词判 strong"——**不会**。无过判。✅

#### C6：增值 单独出现 — profits 是否过判 strong

输入（逐字）：`白皮书称持币者可享受生态增值。`

```
四要素：expectation_of_profits=strong（增值）
        common_enterprise=weak（生态）
        investment/efforts=unknown
四态计数：strong=1 weak=1 absent=0 unknown=2
Howey 综合：possibly_security（confidence=low）
路径：else（strong+weak=2）→ possibly_security
```

- **代码路径（逐字，补充 3）**：
  1. 指标定义：`howey_factors.jsonl` 第 3 行（expectation_of_profits）含 `{"pattern": "增值", "weight": "strong"}`。
  2. 匹配：`scan_indicators`（`extractor.py:146-150`）取 pattern=`增值` → `find_evidence(text, 增值)`（`extractor.py:106-135`）内部走 `_ci_in`（`extractor.py:69-73`）**精确子串匹配** → `增值 in 生态增值` = True → 命中。
  3. 因子状态：`judge_factor`（`engine.py:57-58`）`has_strong → state=strong`。
  4. Verdict：`classify_howey`（`classifier.py:16-25`）本例 s/w/u = 1/1/2 → `unknown>=3`? 否（u=2）→ `strong>=3`? 否 → `strong==2 and weak==2`? 否 → `strong+weak<=1`? 否（=2）→ **`else → possibly_security`**。
- **「3-unknown 保护」是否成立？修正 + 实测证据（补充 3）**：
  - **修正**：我原报告称「`增值` 为唯一强信号时因 3-unknown 规则 verdict 会落 likely_not_security」——**该表述错误，已撤回**。实测探针 P1（s/w/a/u = 1/0/0/3）→ `classify_howey` 第 16 行 `unknown>=3` **优先于**第 22 行 `strong+weak<=1` 命中 → **insufficient_info**，**不是** likely_not_security。错误原因：两个分支判据不同且 `unknown>=3` 在前，不能混为一谈。
  - **保护是偶然的，不是设计的**（两条证据）：
    1. 该保护来自 `unknown>=3 → insufficient_info`（**信息不足兜底**），与「利润预期」无关——它保护的是「任何单因子强信号」，并非专门防止 `增值` 过触发；
    2. 保护极脆弱：探针 P2（= 本 C6，仅多一个 `生态`(weak)）→ s/w/u = 1/1/2 → `unknown>=3` 失效（u=2）→ `else → possibly_security`。即**只要任一其它因子给出一个 weak，保护立即蒸发**。
  - 结论：`增值` 是泛词（`生态增值` / `资产增值` / `品牌增值`），单独即可触发 profits=strong；该 strong 与任一其它因子的弱信号叠加就能推高 verdict，而 rubric 中**不存在任何针对「利润预期由泛词触发」的抑制机制**（与 C4/C9 同源：rubric 对利润预期只做计数，不做语义/权重区分）。
- **判定（升级链）**：由「设计决策」→「设计决策 + 潜在过宽」→ **现定为「设计缺陷性质：泛词 strong 未做语境约束」**（质疑 1 后再升级）。C6 实质不是"可能过宽"（偶发），而是"**一旦非孤立出现，泛词 strong 即直接推动 verdict 升级**"——这正由我在补充 3 揭示的「3-unknown 保护是偶然而非设计、一个 weak 即蒸发」证据所推翻。→ 列入待处理项 **#8（设计复核，严重性=中高）**。

> 探针逐字记录：
> - P1 `白皮书称持币者可享受资产增值。` → profits=strong，s/w/a/u = 1/0/0/3 → **insufficient_info**（`unknown>=3` 分支）
> - P2 `白皮书称持币者可享受生态增值。`（= C6）→ common=weak + profits=strong，s/w/a/u = 1/1/0/2 → **possibly_security**（保护蒸发）

#### C7：核心团队 vs 团队 — efforts strong 边界

输入 C7a（逐字）：`项目由核心团队负责开发与运营。`

```
四要素：efforts_of_others=strong（核心团队）
        investment/common/profits=unknown
四态计数：strong=1 weak=0 absent=0 unknown=3
Howey 综合：insufficient_info（confidence=low）
路径：unknown>=3 → insufficient_info
```

输入 C7b（逐字）：`项目由一个分布式团队负责开发与运营。`

```
四要素：efforts_of_others=unknown（"团队" 未命中 核心团队/团队开发 连续短语）
        investment/common/profits=unknown
四态计数：strong=0 weak=0 absent=0 unknown=4
Howey 综合：insufficient_info（confidence=low）
路径：unknown>=3 → insufficient_info
```

- **代码路径（逐字，补充 3）**：
  1. 指标定义：`howey_factors.jsonl` 第 4 行（efforts_of_others）的 strong 指标为 `团队开发 / 创始人 / 持续运营 / 路线图 / roadmap / 基金会管理 / 核心团队 / ongoing development`——**无裸 `团队`**。
  2. 匹配（C7b 不命中的原因）：`scan_indicators`（`extractor.py:146-150`）判定的是 **indicator pattern 是否为文本子串**（`_ci_in`，`extractor.py:69-73`）：
     - `核心团队 in 项目由一个分布式团队负责开发与运营` → **False**（文本只有「分布式团队」）
     - `团队开发 in 项目由一个分布式团队负责开发与运营` → **False**（`团队` 与 `开发` 被 `负责` 隔开，非连续）
     - 两个 strong 指标经 `find_evidence` 返回 `None` → `continue`（`extractor.py:151-153`）→ 不进入 `matched`。
  3. 因子状态：`matched=[]` → `judge_factor`（`engine.py:52-64`）中 `has_strong / has_weak / has_absent / has_negated_strong_weak` 全 False → `else: state=unknown`（`engine.py:63-64`）。
- **对照（C7a 命中）**：`核心团队 in 项目由核心团队负责开发与运营` → **True** → `_ci_in` 命中 → `has_strong → state=strong`（实测 s/w/a/u = 1/0/0/3）。**差异仅在「pattern 是否连续出现」**，无语义判断。
- **覆盖度补充（P5 探针）**：`创始团队负责开发并持续运营。` → 虽无 `核心团队`/`团队开发`，但命中 `持续运营`(strong) → efforts=strong。说明 efforts 的漏检**仅在文本只提「团队」而未出现任何 strong 短语时发生**（如 C7b）。故严重性低，但属真实词表覆盖缺口。
- **判定**：**词表覆盖不全（漏检方向）**，与 G-A3 同类（缺词），但发生在 efforts 要素。单列为待处理项 **#9（处置类型 = 修复代码·补词表，严重性 = 低）**；可与 G-A3 合并为一个「补词表」PR（不同要素、同类操作），二者不互相依赖。

#### C8：同要素 strong + weak + absent 混合 — 状态优先级

输入（逐字）：`用户兑换并质押代币，同时出资认购项目份额。`

```
四要素：investment_of_money=strong（认购 strong + 出资 strong + 兑换 weak + 质押 weak → 优先级取 strong）
        common/profits/efforts=unknown
四态计数：strong=1 weak=0 absent=0 unknown=3（weak 被同因子 strong 压过，不计入状态）
Howey 综合：insufficient_info（confidence=low）
路径：unknown>=3 → insufficient_info
```

- **路径**：`engine.py:57-58` `has_strong → state=strong`，strong 压过同因子 weak/absent。
- **判定**：**设计决策（优先级链正确）**。strong > weak > absent 的优先级链在此一致生效，混合因子正确取 strong。与 C3 的 weak>absent 同一优先级体系的下端，逻辑自洽。✅

#### C9：极端验证 — investment=strong, common=strong, profits=absent, efforts=strong

输入（逐字）：`由核心团队负责持续运营并发布路线图。用户以人民币认购代币。项目方设立资金池，代币持有者权益按比例分配。项目方不承诺任何收益，也不保证利润。`

```
四要素：investment_of_money=strong（认购）
        common_enterprise=strong（资金池 + 按比例分配）
        expectation_of_profits=absent（收益 / 利润 均被"不"否定）
        efforts_of_others=strong（持续运营 + 路线图 + 核心团队）
四态计数：strong=3 weak=0 absent=1 unknown=0
Howey 综合：likely_security（confidence=high）
路径：strong>=3 → likely_security
```

- **路径**：三因子 strong + profits 经 `不承诺收益 / 不保证利润` 否定 → absent。
- **判定（C4 深挖根本层 · 关键证据）**：**rubric 实质性误判**。
  - 按 **Howey Test**：投资合同须四要素同时满足，且 **"expectation of profits" 是核心要件**——无利润预期即不构成投资合同。本例明确"不承诺收益、不保证利润"，**应判 likely_not_security（或至少非 security）**。
  - 按 **当前 rubric**：`strong>=3 → likely_security`，**完全无视 profits=absent**。
  - 这是 **3 strong + profits absent 被判 likely_security**，比 C4 更尖锐地证明 rubric 缺陷的严重性：**它不对 Howey 核心要件（利润预期）赋任何特殊权重**。

### C3/C4 联动（同一 rubric 的两个侧面）

C3 的"weak 优先于 absent"规则与 C4 的"2 weak → possibly_security"**不是独立问题，是同一 rubric 设计的两个侧面**，且 C3 直接推动 C4 的 verdict 升级：

| 用例 | 输入要点 | investment 状态 | efforts 状态 | verdict |
|------|---------|----------------|------------|---------|
| XY-X（无 锁仓） | 空投(absent) + 社区治理(weak) | **absent**（空投） | weak | **likely_not_security**（strong+weak=1） |
| XY-Y（+锁仓，触发 weak>absent） | 空投 + 锁仓(weak) + 社区治理(weak) | **weak**（锁仓压过空投） | weak | **possibly_security**（2 weak） |

- 两例仅差一个 `锁仓`(weak)。XY-X 中 investment=absent（空投），verdict=likely_not_security；XY-Y 因 C3 的 **weak>absent 规则把 investment 从 absent 抬到 weak**，叠上 efforts=weak 形成 2 weak → verdict 翻转为 possibly_security。
- **结论**：C3 的优先级规则（absent→weak）是 C4 verdict 升级的输入源；两者耦合。修复利润预期权重问题时，须一并审视 weak>absent 优先级对 verdict 的放大效应。

### 模块 C 阶段结论（C1-C9）

| 用例 | 输入要点 | 关键状态 | verdict | 判定 | 是否误判 |
|------|---------|---------|---------|------|---------|
| C1 | 锁仓（单 weak） | invest=weak | insufficient_info | 真克制 | 否 |
| C2 | 购买+消费词（降级） | invest=weak(downgrade) | insufficient_info | 设计决策 | 否 |
| C3 | 空投+锁仓+收益 | invest=weak(压 absent) | possibly_security | 设计决策（blanket 优先级） | 否（结果可辩护） |
| C4 | 锁仓+社区治理 | 2×weak, **profits=absent** | possibly_security | **设计缺陷：未对利润预期赋 Howey 核心权重** | 否（表象）但 rubric 与 Howey 相悖 |
| C5 | 生态 单独 | common=weak | insufficient_info | 真克制（泛词未越级 strong） | 否 |
| C6 | 增值 单独（+生态 weak） | profits=strong | possibly_security | **设计决策 + 潜在过宽**（保护系 `unknown>=3` 偶然产物，一 weak 即蒸发） | 否（但过宽风险 → #8） |
| C7a | 核心团队 | efforts=strong | insufficient_info | 设计决策 | 否 |
| C7b | 团队 单独 | efforts=unknown（漏检） | insufficient_info | **词表覆盖不全**（`核心团队`/`团队开发` 连续短语门限） | 否（但漏检 → #9） |
| C8 | strong+weak+absent 混合 | invest=strong（强压弱） | insufficient_info | 设计决策（优先级链正确） | 否 |
| C9 | 3 strong + profits=absent | profits=absent | **likely_security** | **设计缺陷：rubric 无视利润预期 absent** | **是（与 Howey 相悖）** |

> 模块 C 结论：
> - **C1-C3、C5-C8 无 weak 误判**；weak 的两类来源路径（指标本身 weak / 消费降级）均合理。
> - **C4 + C9 暴露 rubric 的根本缺陷**：`classify_howey` 仅做四态计数，**未对 Howey 核心要件"expectation of profits"赋特殊权重**。后果：① profits=absent 仍可被其它因子推成 possibly/likely_security（C4/C9）；② 叠加 C3 的 weak>absent 优先级，弱信号被进一步放大（C4 联动）。
> - 该问题**跨所有代币的判定**，非单案例边界 → 升为「待处理项清单 #7 · 设计复核」。
> - **C6（#8）与 C7b（#9）经审计提示由「次要观察」升级为清单项**：#8 与 #7 同源（rubric 对利润预期只计数、不区分语义），方向为「泛词 strong 未抑制」；#9 与 G-A3 同类（词表覆盖不全），方向为漏检。二者均已补足逐字代码路径证据（见各用例）。
> - **C1-C3、C5、C7a、C8 无问题**；C6/C7b 为设计层面的过宽/漏检风险，非当前 verdict 误判。

### C.10 跨要素泛词扫描（支撑待处理项 #10）

**任务来源**：质疑 2 指出泛词问题跨要素、跨法域普遍存在（C6 `增值` / C5 `生态` 在 Howey 要素内；D1 观察 2 发现 HK `收益权` vs SG `收益` 粒度差异）。本扫描枚举四 Howey 要素全部 strong 指标，标注「单独出现即可触发 strong 且词义泛化」者。

**方法**：`load_libraries()["howey"]` 遍历四要素 `indicators`，筛 `weight=="strong"`，逐条评估词义泛化程度（是否可在非证券语境自然出现）。

**结果 A — 泛词 strong（过宽风险，与 #8 同源）**：

| 要素 | 泛词 strong 指标 | 泛化风险 |
|------|----------------|---------|
| investment_of_money | `投资` | "投资自己的技能/时间"等非出资语境亦常见 |
| common_enterprise | `资金池` | DeFi 流动性池、众筹等非共同企业语境亦出现 |
| expectation_of_profits | `收益`、`利润`、`增值`、`回报`、`升值` | 营销泛词，单字/词即命中，无语境约束 |
| efforts_of_others | （无裸泛词；`核心团队`/`持续运营` 尚具体） | 该要素强信号相对具体，泛词风险低 |

**结果 B — 泛词缺失（漏检，与 #9/G-A3 同类，非过宽）**：
- `团队` 单体不命中（仅 `核心团队`/`团队开发` 连续短语，见 #9）。
- `生态`（common_enterprise, weak）已正确止于 weak，未越级 strong（C5 验证 ✅）。

**结论**：泛词 strong 集中于 **expectation_of_profits**（`收益/利润/增值/回报/升值`）与部分 **investment_of_money**（`投资`）、**common_enterprise**（`资金池`）。与 #7/#8 同源——rubric 对「利润预期/泛化出资」只计数、不区分语义。建议 #10 与 #7/#8 合并为同一「利润预期/泛词语义约束」设计复核。跨法域侧（HK `收益权` vs SG `收益`）见 D1 观察 2，待 D 收口后统一处理。

---

---

## 模块 D：港新判定依据来源独立性审计

> 审计对象：`data/jurisdictions/hk_sfc.jsonl`、`data/jurisdictions/sg_mas.jsonl`、`classifier.py:44-68`（`classify_jurisdiction`）、`engine.py:78-95`（`judge_jurisdiction`）。
> **核心问题**：两个法域的判定**是否真的基于各自监管文件**，还是共用一套逻辑仅改了标签？
> 纪律：逐字打印、只记录不修；判定分「真独立 / 能力缺口（假独立）/ 设计简化」；分 4 步，已执行第 1 步，第 2–4 步续做（见下）。

### D.1 数据源隔离检查（第 1 步）

**条目数说明**：指令要求「逐条打印前 5 条」，实测 `hk_sfc.jsonl` 与 `sg_mas.jsonl` **各仅 3 条**（非 5 条），故**全部打印**，无截断。

#### HK SFC（3 条）

| id | topic | framework | signal | source_url |
|----|-------|-----------|--------|------------|
| HK-SFC-001 | 证券型代币定义 (Security Token, SFO) | 证券及期货条例 (SFO) | security | `https://www.sfc.hk/en/Regulatory-functions/Intermediaries/Virtual-assets` |
| HK-SFC-002 | 虚拟资产服务提供者发牌 (VASP Licensing) | 打击洗钱条例 (AMLO) | regime | `https://www.sfc.hk/en/Regulatory-functions/Intermediaries/Licensing` |
| HK-SFC-003 | 实用/功能型代币（非证券） | SFO 除外情形 | utility | `https://www.sfc.hk/en/Regulatory-functions/Intermediaries/Virtual-assets` |

**criteria 逐字**：

```
HK-SFC-001: 若代币属 SFO 下「证券」定义（包括股份、债权证、集体投资计划权益等），则受 SFO 规管，相关活动须持牌。
HK-SFC-002: 自 2023-06-01 起，在香港经营虚拟资产交易所服务须向 SFC 申领 VASP 牌照；非证券型虚拟资产亦受此制度规管。
HK-SFC-003: 若代币仅用于访问平台功能、支付平台内商品或服务，且不赋予股权/债权/收益分配等证券权利，则通常不被认定为 SFO 下证券。
```

#### SG MAS（3 条）

| id | topic | framework | signal | source_url |
|----|-------|-----------|--------|------------|
| SG-MAS-001 | 数字支付代币服务 (DPT) | 支付服务法 (PSA) | payment | `https://www.mas.gov.sg/regulation/payments` |
| SG-MAS-002 | 证券型代币 (Security Token, SFA) | 证券与期货法 (SFA) | security | `https://www.mas.gov.sg/regulation/capital-markets` |
| SG-MAS-003 | 实用/功能型代币（非证券） | SFA 除外情形 | utility | `https://www.mas.gov.sg/regulation/capital-markets` |

**criteria 逐字**：

```
SG-MAS-001: 若代币构成 PSA 下'数字支付代币'（可用于支付商品/服务、作为交易媒介或价值储存），提供相关服务（交易、托管、跨境转账）须持牌。
SG-MAS-002: 若代币构成 SFA 下'资本市场产品'（如股份、债券、集合投资计划权益），其发行与交易平台须遵守 SFA 并持牌。
SG-MAS-003: 若代币仅提供平台内功能访问、商品/服务兑换，不赋予股权/债权/收益分配等资本市场产品特征，通常不适用 SFA。
```

#### 隔离性判定（第 1 步）

| 检查项 | 结果 | 证据 |
|--------|------|------|
| 源域隔离（sfc.hk vs mas.gov.sg） | ✅ **数据层真独立** | HK 3/3 → `sfc.hk`；SG 3/3 → `mas.gov.sg`。**零交叉引用**。 |
| 法域概念隔离（SFO/VATP vs PSA/SFA） | ✅ **无串味** | HK 仅引用 SFO / AMLO(VASP)；SG 仅引用 PSA / SFA。**HK 无一条提及 PSA/SFA/资本市场产品；SG 无一条提及 SFO/VASP/证券及期货条例**。 |
| criteria 是否各自表述 | ✅ **数据层真独立** | 6 条 criteria 文本各不相同，均锚定本法域法条概念（SFO「证券」/ VASP 牌照 / SFA「资本市场产品」/ PSA「数字支付代币」）。 |
| 引用溯源完整性（6 条 source_url 逐条抓取） | ⚠️ **3/6 有缺口（含 2 条不可验证死链）** | HK-001/003 → `Virtual-assets` 实测 **404 断链**；HK-002 → `Licensing` 通用页存活但**无法印证 AMLO/VATP**（无 VASP/AMLO/2023-06-01）；SG-001/002/003 → 存活且主题吻合（PSA/DPT、SFA/资本市场）。见观察 4 与 #D1–#D3。 |

**初步法理核查（第 4 步详查，此处仅记录观察）**：
- HK-001 以 SFO「证券」定义（股份 / 债权证 / 集体投资计划权益）为据 ✅ 与香港 SFO 附表 1「证券」定义一致。
- HK-002 将 VASP 发牌归于 **AMLO（打击洗钱条例）而非 SFO** ✅ **法律定性正确**（经独立核验，见观察 4）；但其 `source_url` 为 SFC 通用 Licensing 落地页，**无法印证该定性**（引用溯源缺陷，见观察 4）。
- SG-001 以 PSA「数字支付代币」为据 ✅；SG-002 以 SFA「资本市场产品」为据 ✅。
- 初步**未见法理串用**（港用新概念 / 新用港概念均未出现）。

#### 三项观察

- **观察 1（指标重叠，非缺陷）**：HK-001 与 SG-002 的证券类指标高度重叠——`股权 / equity / 债权 / debt / dividend / 投票权` 共 6 词相同。原因是两地证券定义在股份 / 债权 / 集体投资计划上**同源于英美证券法概念**，重叠属**法律概念同源**，而非代码共用（两文件各自维护、无引用关系）。**判定：真独立**。
- **观察 2（指标粒度差异，值得记录）**：
  - HK-001 用 `收益权 / profit rights`（窄，须带「权」）；SG-002 用 `收益`（宽，无「权」）→ **SG 的证券信号更易被「收益」二字单独触发**，与 C6「泛词触发 strong」同类问题。
  - HK-001 含 `股份 / share / 债券 / 集体投资计划 / CIS`；SG-002 含 `证券 / securities`，集体投资写作 `集体投资`（无「计划」）。
  - HK-003（utility）含 `支付商品 / 会员权益`；SG-003 含 `兑换服务`。
  - 影响：同一文本在港新可触发不同信号——这正是第 2 步「故意让结论不同」用例的构造依据。
- **观察 3（结构对称，第 3 步伏笔）**：两文件均为 3 条、均含 security + utility 两类，但**第 3 类不同**：HK 为 `regime`（VASP/AMLO），SG 为 `payment`（DPT/PSA）。signal 词汇**不共享**（HK = {security, regime, utility}；SG = {payment, security, utility}），是独立性的正面证据。但需注意 `classify_jurisdiction`（`classifier.py:44-68`）的 signals 字典**同时容纳 security / payment / utility / regime 四类并共用同一决策树**——该点属第 3 步（逻辑路径隔离）范围，**此处仅标记待查，不下结论**。
- **观察 4（引用溯源逐条核验，质疑 1 补强）**：原报告仅标注 HK-SFC-002 的 citation gap 并写「不计入 #1–#10」。用户纠正：**citation gap 必须单独成表、全量核查 6 条 source_url**。现对 6 条 `source_url` 全部实测抓取（2026-09-20），结果如下：

  | 条目 | source_url（抓取结果） | 能否支撑条目的 framework / criteria | 缺口类型 |
  |------|----------------------|----------------------------------|---------|
  | HK-SFC-001 | `.../Intermediaries/Virtual-assets` | **404（SFC 已迁移新主页，旧 URL 失效）** | **断链（broken link）** → #D2 |
  | HK-SFC-002 | `.../Intermediaries/Licensing` | 存活，但仅述 SFO 中介人发牌职能；**无 VASP / AMLO / 2023-06-01 字样** | **弱引用（generic landing page）** → #D1 |
  | HK-SFC-003 | `.../Intermediaries/Virtual-assets` | **404（同上，与 001 同一条死链）** | **断链（broken link）** → #D3 |
  | SG-MAS-001 | `.../regulation/payments` | 存活，述 PS Act 2019 / DPT / 支付服务商发牌 | ✅ 主题吻合 |
  | SG-MAS-002 | `.../regulation/capital-markets` | 存活，述 SFA / 资本市场实体发牌 | ✅ 主题吻合 |
  | SG-MAS-003 | `.../regulation/capital-markets` | 存活，同上（与 002 同页） | ✅ 主题吻合 |

  - **HK-SFC-002 法律定性正确但溯源弱**：`framework=AMLO` 定性经独立检索（LegCo 文件、SFC 通函 23EC27/23EC28、InvestHK）确认正确——HK VATP 制度确由《打击洗钱条例（修订）条例 2022》第 615 章增设、2023-06-01 生效、SFC 主责。但 `source_url` 落在 SFC「Licensing」通用页（内容仅 SFO 持牌人 / 中介人发牌），**不能印证该定性**，应替换为具体 VATP 通函 URL（如 `apps.sfc.hk/edistributionWeb/gateway/TC/circular/doc?refNo=23EC28`）。
  - **HK-SFC-001 / 003 断链是新发现**：原审计以「HK 3/3 → sfc.hk」论证数据层独立，但**未实测 URL 是否存活**；本次抓取暴露**两条死链**，且指向同一个已迁移的 `Virtual-assets` 旧路径。条目 notes 引用的「SFC 2019 声明 / 后续通函」才是应核实的真实出处，`source_url` 须更新为新站等效页或具体通函。
  - **性质**：非法律错误，是**数据质量缺口（citation gap / broken link）**，统一列入待处理项 **#D1–#D3（数据质量子表）**，与 #1–#10 的代码 / 设计缺口分开管理。

**判定（第 1 步）**：**结构层真独立 ✅；引用溯源层 3/6 有缺口 ⚠️；逻辑层待第 3 步验证**。
- **结构层（源域 / 概念 / criteria）真独立 ✅**：HK 3/3 → `sfc.hk`、SG 3/3 → `mas.gov.sg`，零交叉引用；法域概念（SFO/VATP vs PSA/SFA）无串味；6 条 criteria 各自锚定本法域法条。此即原「数据层真独立」的含义，成立。
- **引用溯源层（citation integrity）3/6 有缺口 ⚠️**：HK-001/003 的 `source_url` 实测 **404 断链**、HK-002 为**弱引用通用页**（均见观察 4 与 #D1–#D3）。结构独立 ≠ 引用可信——这两个维度须分开管理。
- **逻辑层**：`classify_jurisdiction` 共用 signals 决策树（观察 3 伏笔）是否导致逻辑串味，属第 3 步范围，此处不下结论。3 项观察已记录（指标重叠同源 / 粒度差异 / 结构对称性与第 3 步伏笔）。

> 第 2-4 步（判定结果隔离 / 逻辑路径隔离 / 法理依据核查）已批准执行，见 §D.2–D.4。

### D.2 判定结果隔离检查（第 2 步）

**方法**：构造 4 个「故意让港新结论不同」的用例，逐一调用 `analyze()`（`classifier.py:130-171`），打印 HK_SFC / SG_MAS 的 `verdict` + `signals` + 命中条目。判定标准：真独立 / 能力缺口（假独立）/ 设计简化。

**用例与逐字结果**：

| 用例 | 输入（逐字） | 来源 | 香港 SFC | 新加坡 MAS |
|------|-------------|------|---------|-----------|
| 1（港证 / 新非证） | `本代币代表公司发行的股份与债券，持有人享有 profit rights 分配。` | **构造**（审计者自造） | **likely_security**（HK-SFC-001: 股份 / 债券 / profit rights） | **insufficient_info**（零命中） |
| 2（新 DPT / 港非证） | `本代币可用于支付商品与服务，作为交易媒介与价值储存，支持跨境转账。` | **构造**（审计者自造） | **utility_token**（HK-SFC-003: 支付商品） | **payment_token**（SG-MAS-001: 支付 / 交易媒介 / 价值储存 / 转账） |
| 3（两者皆证） | `本代币为股权凭证，可在交易所交易，持有人享有投票权与分红。` | **构造**（审计者自造） | **likely_security**（HK-SFC-001: 股权 / 分红 / 投票权；HK-SFC-002: 交易所 [regime]） | **likely_security**（SG-MAS-002: 股权 / 投票权） |
| 4（两者皆非） | `本白皮书描述一个去中心化治理协议，无代币发行计划。` | **构造**（审计者自造） | **insufficient_info**（零命中） | **insufficient_info**（零命中） |

> **用例来源标注（用户质疑 4）**：以上 4 个用例**均为构造性验证——由审计者为隔离港新指标而自造文本**，**非真实案例回归**。它们**不是**从真实代币白皮书、SFC/MAS 执法文件或真实监管案例抽取的。
> - 构造性用例只能证明「**代码在特定输入下行为正确**」（隔离性 / 一致性层面的代码正确性），**不能证明「代码在真实世界 / 真实监管案例下正确」**（法理正确性）。
> - **延伸观察（已提级）**：本项目目前**不存在任何真实案例回归** —— `demo/` 三个输入亦为虚构代币（XChain / StoragePay / EcoToken，名称均杜撰）。该发现**已提级为项目级独立章节**，见 **`§项目级局限：当前无真实案例回归（构造性验证）`**，不再作为模块 D 子发现。据此 §D.2 的可主张范围限定为「**结果层构造性通过**」。
> - 因此 §D.2 的可主张范围应严格限定为「**结果层构造性通过**」，**不得**外推为对真实世界产出的验证。

**判定（第 2 步）：三层独立性结论（质疑 4 重构）**

| 层 | 状态 | 依据 |
|----|------|------|
| 数据 / 结构层 | ✅ 真独立 | D.1：源域、概念、criteria 各自独立 |
| 逻辑层 | ⏳ 待第 3 步验证 | `classify_jurisdiction`（`classifier.py:44-68`）为 HK/SG 共用同一函数 + 同一 `signals` 决策树 |
| 结果层 | ⚠️ **构造性部分通过** | 仅 4 个**自造**用例（非真实案例，见质疑 4）；用例 1 初版因子串碰撞失败（已用 `profit rights` 修复） |

- 用例 1 / 2 成功产生**港新不同 verdict**（港证券 vs 新非证；新 DPT vs 港非证），用例 3 / 4 同结论符合预期 → **engine 能为两法域返回不同判定**，非「假独立」。但**样本仅 4 个手工构造用例（覆盖率低）**，且用例 1 初版即失败，故结果层只能定级「部分验证通过」，不能写成「结果层真独立 ✅」。
- **初始设计失误 + 发现耦合（重要）**：用例 1 初版文本「…持有人可按比例获得收益权分配。」→ 两法域**均判 likely_security**。根因：SG-MAS-002 用宽指标 `收益`，`_ci_in` 子串匹配使 `收益` ∈ `收益权分配` → SG 误触发。与 **D1 观察 2** 及 **问题 4** 同源——**代码级共享缺陷**，非港新数据耦合。改用英文 `profit rights`（HK-001 独有、SG 无）后即正确隔离。
  - **含义**：港新在「数据 / 结构层」真独立，但两者指标匹配**共用同一 `_ci_in` 子串匹配器**，子串缺陷会**同时污染两法域**（如 SG `收益` 宽指标）。修复问题 4（候选 B+C）将同步改善两法域精度，无需各写一套匹配逻辑。
- **HK-SFC-002（regime / VASP）在用例 3 被 `交易所` 触发**：VASP 信号与证券信号可并存（双牌照安排），属正确行为——决策树中 `security>0` 优先于 `regime>0`（`classifier.py:50`），故仍判 likely_security，非耦合缺陷。
- **反向跨法域碰撞扫描（质疑 2）见 §D.2.1；问题 4 修复对港新独立性的耦合风险（质疑 3）见 §D.2.2。**

**结论（第 2 步）**：结构层真独立 ✅、逻辑层待第 3 步 ⏳、结果层部分验证通过 ⚠️（非「真独立已证实」）。残留风险为共享子串匹配器对宽指标的过触发（计入问题 4），非港新特有耦合。逻辑路径隔离（第 3 步）与法理依据核查（第 4 步）待续。

### D.2.1 反向跨法域碰撞扫描（质疑 2 补强）

**质疑 2 来源**：用例 1 初版失败暴露「测试设计盲区」——若仅用「港新结论不同」作通过标准，会漏掉「某法域指标因子串碰撞被另一法域文本误触发」这类隐性耦合。故对 4 个用例做**反向检查**（不仅看结论是否不同，还要看每个法域命中的指标词是否「只来自目标法域」），并对港新指标集做**全量子串碰撞扫描**。

**1) 4 个用例逐一重跑（真实引擎，打印每法域命中指标词）**：

| 用例 | 香港 SFC 命中指标词 | 新加坡 MAS 命中指标词 | 非预期跨法域触发？ |
|------|-------------------|---------------------|----------------------|
| 1（港证/新非证） | HK-001: 股份/债券/profit rights | （无） | 否 ✅ |
| 2（新DPT/港非证） | HK-003: 支付商品（utility，预期内） | SG-001: 支付/交易媒介/价值储存/转账 | 否 ✅（港 utility 为合法信号） |
| 3（两者皆证） | HK-001: 股权/分红/投票权；HK-002: 交易所 | SG-002: 股权/投票权 | 否 ✅ |
| 4（两者皆非） | （无） | （无） | 否 ✅ |
| 1-v1（坏版·复现） | HK-001: 股份/债券/收益权 | SG-002: 收益（子串碰撞） | **是 ❌**（收益 ∈ 收益权分配） |

→ 当前 4 个（修复后）用例**均未出现非预期跨法域触发**，港新预期分歧全部复现。

**2) 港新指标集全量子串碰撞扫描（关键新发现）**：对 HK 3 条 + SG 3 条的全部 indicators 做两两子串比对，除 10 个**字面重合词**（`access`/`debt`/`dividend`/`equity`/`utility`/`债权`/`功能`/`投票权`/`消费`/`股权`，属英美证券法同源概念，良性，见观察 1）外，发现 **5 处子串级重叠**：

| HK 指标 | SG 指标 | 碰撞机制 | 触发后果 |
|---------|---------|---------|---------|
| `收益权` | `收益` | `收益` ⊂ `收益权分配` | 含「收益权分配」的文本误触发 SG 证券信号（用例 1-v1 已复现） |
| `exchange` | `medium of exchange` | `exchange` ⊂ `medium of exchange` | 含英文 exchange（指 HK 交易所/VATP）误触发 SG「交易媒介」支付信号 |
| `支付商品` | `支付` | `支付` ⊂ `支付商品` | 含「支付商品」（HK utility）同时触发 SG「支付」——用例 2 即如此（双方法域均合法，机制同源） |
| `集体投资计划` | `集体投资` | `集体投资` ⊂ `集体投资计划` | 含「集体投资计划」误触发 SG 证券信号 |
| `使用功能` | `使用` / `功能` | 子串包含 | 含「使用功能」（HK utility）同时触发 SG「使用」/「功能」 |

→ **结论（质疑 2 收口）**：4 个用例通过，仅因**刻意选词**（用例 1 用 `profit rights` 而非 `收益权分配`、用例 3 用中文「交易所」而非英文 `exchange`）；一旦措辞变化，5 处子串重叠中的任一处都会重现跨法域误触发。**测试设计盲区是系统性的，非偶发**——根因与 **问题 4（子串匹配系统性缺陷）/ D1 观察 2（HK 窄 `收益权` vs SG 宽 `收益`）同源**，即两法域共用 `_ci_in` 子串匹配器且宽指标无词边界约束。
修复方向（与问题 4 合并，只记录不修）：在匹配层引入词边界 / 同句约束（候选 B+C 的匹配器级实现），并在港新指标集上消除上述 5 处子串重叠（如 SG-002 `收益` 收窄为 `收益分配`/`收益权`、SG-001 `medium of exchange` 改全词匹配）。**修复后须重跑 D.2 的 4 个用例确认港新仍隔离**（见 §D.2.2）。

### D.2.2 问题 4 修复对港新独立性的耦合风险（质疑 3）

**质疑 3 来源**：修复问题 4（候选 B+C）会改动匹配 / 降级逻辑，须评估其是否**连带影响港新判定的独立性**——若修复引入共享参数或回归，会同时作用于两法域。

**共享代码 / 结构（修复时无法只对单一法域生效）**：
- `classify_jurisdiction`（`classifier.py:44-68`）：HK 与 SG **共用同一函数** + 同一 `signals` 决策树（`{security, payment, utility, regime}`）。决策树任何改动（优先级、新增 verdict）对两法域同时生效。
- `judge_jurisdiction`（`engine.py:78-95`）→ `scan_indicators` → `_ci_in`（`extractor.py:69-73`）：**全部法域共用同一匹配管线**。匹配器级修复（如加词边界 / 同句窗口）对港新同时生效，无法单法域隔离。
- `in_negation_context`（`extractor.py`）：同上，全局共用。

**候选 B / C 的耦合面（逐一定位）**：
- **候选 C（收窄消费词表 `consumption_context`）**：该字段位于 `howey_factors.jsonl` 的 `investment_of_money`，属 **Howey 层**，**不触碰**港新 jsonl 指标。故 C 按原设计**不耦合**港新；但对港新更宽指标（SG-002 `收益`、SG-001 `medium of exchange` 等）的子串重叠（见 D.2.1）**同样需要收窄**，只是那属于「法域指标收窄」而非 Howey 消费词表。
- **候选 B（同句 / 近邻约束）**：原设计作用于 `judge_factor` 的消费降级分支（Howey 层），**不直接触碰**港新匹配。但若 B 被泛化为「`_ci_in` 加句级窗口参数」的实现，则该参数成为**港新共享阈值**——一个为 HK 指标调好的窗口值，可能对 SG 指标过宽 / 过窄（如 `交易所` vs `交易媒介` 的中距共现）。
- **真正共享的修复参数**：若问题 4 修复引入「词边界标志 / 同句窗口长度 `window_chars` / 近邻阈值」等参数，这些参数**对港新是同一组值**，无法法域差异化。即「修复问题 4」在匹配器层是**原子操作**——要么两法域一起修，要么都不修。

**耦合风险定性**：问题 4 的匹配器级修复**会同时改善港新判定精度**（消除 D.2.1 的 5 处子串重叠），这是正向耦合；但**若修复引入回归**（如窗口值定标不当），会**同时破坏港新隔离**——无法只对一处修、另一处留旧。

**处置（记录不修）**：在问题 4 修复 PR 中，**必须包含「修复后重跑 D.2 的 4 个用例 + D.2.1 的 5 处子串重叠用例」作为回归锁定**（建议新增 `tests/test_module_d_jurisdiction_isolation.py`，覆盖港新预期分歧与跨法域非触发）。本审计仅记录该要求，不实现修复。

逻辑路径隔离（第 3 步）已执行（见 §D.3）；法理依据核查（第 4 步）待续。

### D.3 逻辑路径隔离检查（第 3 步）

**方法**：通读 `classify_jurisdiction`（`classifier.py:44-68`）、其调用方 `analyze`（`classifier.py:130-171`）、上游 `judge_jurisdiction`（`engine.py:78-95`）、匹配器 `_ci_in` / `in_negation_context`（`extractor.py:69-73 / 82-103`），逐维度比对 HK 与 SG 的判定路径是否独立、是否共享可变状态。

**逐维度比对**：

| 维度 | 香港 SFC 路径 | 新加坡 MAS 路径 | 是否共享 | 隔离判定 |
|------|--------------|----------------|---------|---------|
| 判定函数 | `classify_jurisdiction`（`classifier.py:44-68`） | 同一函数 | **共享同一实现** | 实现共享（非各写一套） |
| signals 决策树 | `{security,payment,utility,regime}` + 优先级（`classifier.py:50-61`） | 同一决策树 | **共享** | 实现共享 |
| 匹配管线 | `judge_jurisdiction` → `scan_indicators` → `_ci_in` | 同一管线 | **共享** | 实现共享（子串耦合源，见 D.2.1） |
| 否定上下文 | `in_negation_context`（`extractor.py:82-103`） | 同一函数 | **共享** | 实现共享 |
| method 分支 | 默认 `"signal"`（jsonl 无 method 字段） | 默认 `"signal"` | 共享默认 | 均走 signal 路径 |
| 中间状态 `signals` / `hits` | 每次调用**局部变量**（`classifier.py:45-67`） | 局部变量 | **不共享** | 状态隔离 ✅ |
| 数据源 | `hk_sfc.jsonl`（3 条） | `sg_mas.jsonl`（3 条） | 不共享 | 数据隔离 ✅ |
| 跨法域合并 | `jurisdiction_results` 按 key 分存（`HK_SFC`/`SG_MAS`），无合并 | 同 | — | 无交叉 ✅ |

**关键结论（逻辑层）**：
- **状态隔离 ✅（无交叉污染）**：HK 与 SG 的 `signals` / `hits` 均为 `classify_jurisdiction` 的**局部变量**，每次调用重新创建；`analyze` 把结果按法域 key 分存于 `jurisdiction_results`，**两法域互不读取对方中间状态**。不存在「一法域判定结果泄露到另一法域」的状态污染——这是逻辑层真正的隔离面。
- **实现共享（非「逻辑真独立」）**：HK 与 SG **共用同一 `classify_jurisdiction` 函数 + 同一 `signals` 决策树 + 同一匹配管线**，并非「各写一套逻辑」。**判定特异性完全来自数据**（各自 jsonl 的 `indicators` / `signal` / `framework`），而非代码分支。故逻辑层**不能称作「真独立」**（那意味着两套独立实现），精确说法是「**实现共享下的状态隔离**」。
- **耦合点（与 D.2.1 / 问题4 同源）**：两法域指标同走 `_ci_in` 子串匹配器 + `in_negation_context`，故 D.2.1 发现的 **5 处子串重叠**会**同时作用**于港新——这是逻辑层唯一的真耦合，根因是**匹配器级共享**，与 问题4（子串匹配系统性缺陷）同源。修复 问题4（候选 B+C 的匹配器级实现）将同步消除该耦合，无需为港新各写匹配逻辑（与 D.2 结论一致）。
- **决策树风险**：单一 `classify_jurisdiction` 若有逻辑缺陷（如 verdict 优先级错配），会**同时影响港新**（无法只修一处）。当前决策树（`security>0`→likely_security、`security>0 & utility>0`→mixed、`payment>0 & security==0`→payment_token 等，`classifier.py:50-61`）对两法域均合理，暂无缺陷；但「单一实现」意味着回归必须双法域同测。
- **对比 EU MiCA**：`classify_mica`（`classifier.py:71-100`）是**独立函数**，说明框架**支持**「不同法域不同逻辑」；HK/SG 只是恰好都落在默认的 signal 方法上。反证：若未来需港新走不同判定逻辑，应在 `method` 字段区分（而非复制函数），当前未区分。

**判定（第 3 步）**：**逻辑层 = 状态隔离 ✅ + 实现共享（非真独立）**。但本步原结论仅回答「是否共享状态 / 是否两套实现」，**未追问更根本的问题：港新是否都适用同一套「信号分类法」**——该追问见 §D.3.1，它使 D.3 的结论从「描述现状」推进到「识别出方法论适配性差异」。法理依据核查见 §D.4。

### D.3.1 信号分类法对港新的适配性复核（质疑 2 补强）

**用户质疑 2 的核心**：D.3 得出「共用同一函数 = 实现共享」后即停止，**没有追问「港新是否都真的适合用信号分类法来判定？」** ——若两法域法律结构不同，而代码用同一套信号 + 同一决策树，可能对一法域成立、对另一法域只是简化。

**1) 法定定义结构对比（本轮逐条核验，非凭记忆）**

| 条目 | 框架 | 法定定义结构 | 判定形态 |
|------|------|------------|---------|
| HK-SFC-001 | SFO 附表 1 第 1 部「证券」 | **定义列举式**：(i) 股份 / 股额 / 债权证 / 债权股额 / 基金 / 债券 / 票据；(ii) 上述项目的权利、期权或权益（不论是否称为单位）；(iii) 权益证明书、临时证书、收据、认购或购买权证；(iv) **任何集体投资计划的权益**；(v) 通常称为证券的权益、权利或财产 | 「它是否落入法定类别？」→ **定义式判定** |
| SG-MAS-002 | SFA s.2(1)「资本市场产品」/「证券」 | **定义列举式**：资本市场产品 = 证券、**集体投资计划单位**、衍生品合约、杠杆外汇交易即期外汇合约，及 MAS 订明者；其中「证券」另列（股份 / 商业信托单位 / 所有权权益凭证、债权证…）且**不含** CIS 单位 | 「它是否落入法定类别？」→ **定义式判定** |
| SG-MAS-001 | PSA s.2(1)「数字支付代币」 | **功能特征连言式**：须**同时**满足 (a) 以单位表示；(b) **不以任何货币计价，且发行人不使之与任何货币挂钩**；(c) 是或拟成为**公众或部分公众接受**的交换媒介，用以支付商品、服务的对价或清偿债务；(d) 可以电子形式转移、储存或交易；(e) MAS 订明的其他特征 | 「它是否**全部**满足功能特征？」→ **连言式（conjunctive）判定 + 含文本外事实** |

> **核验来源**：SFO 附表 1 第 1 部第 1 条（SFC 立法文件 `Ord-9-of-2012` + AsianBondsOnline《Characteristics of the Hong Kong Bond Market》第 3 章引述）；SFA 2001 s.2(1)（AGC 新加坡法规库官方文本 + MAS「Capital Markets Services Licence」页）；PSA 2019 s.2(1)（AGC 官方文本 + Singapore Academy of Law《Crypto Conundrum Part I》+ WongPartnership《Navigating the Payment Services Act 2019》）。
> **诚实标注**：PSA 定义第 (e) 项在 AGC 合并版中带有 `[Deleted by Act 1 of 2021 wef 04/04/2024]` 标注，其**确切删除范围待进一步核验**；但 (a)–(d) 项（含关键的 (b) 非锚定、(c) 公众接受）在 2019 原文与 2024 合并版中均存在，**不影响本结论**。

**2) 结论：存在本质差异，且差异不在「港 vs 新」之间，而在「新内部」**

- **港 SFO 与新 SFA（证券型两条腿）结构同类** —— 均为**定义列举式**。用关键词指标映射法定类别（股份 / 债权证 / CIS 权益）是**粗糙但可接受**的代理；信号计数决策树对这两条腿**适配较好**。
- **新 PSA（支付型那条腿）结构不同类** —— 是**功能特征连言式**，要求**全部**要素同时满足，且含两个「信号分类法无法表达」的要件：
  - **(b) 不以任何货币计价、不与任何货币挂钩** = **排除性要件（negative limb）**。当前 SG-MAS-001 的 indicators **全为正向词**（支付 / 交易媒介 / 价值储存 / 转账 …），**没有任何指标编码「货币锚定」概念**，`classify_jurisdiction` 也**不存在排除分支**。
  - **(c) 公众或部分公众接受** = **文本外事实**（外部市场事实），不可能由白皮书文本核实，任何关键词路径**都无法验证**。
- 因此 `classify_jurisdiction` 对 payment 采用 **OR 逻辑**（`payment>0` 且 `security==0` → `payment_token`）：只要任一功能指标命中即判 DPT，**不要求功能特征连言满足**，也**无法验证「公众接受」**。

**3) 实测佐证（真实引擎跑出）——本条最强证据**

| 用例 | 输入要点 | SG MAS 判定 | 法律正解（PSA s.2(1)） | 判定 |
|------|---------|------------|----------------------|------|
| A · 美元挂钩稳定币 | 「与美元 1:1 挂钩，由发行人保证锚定美元汇率（pegged to USD）」+ 支付 / 交易媒介 / 价值储存 / 跨境转账 | **payment_token**（SG-MAS-001: 支付 / 交易媒介 / 价值储存 / 转账） | **不是 DPT** —— 不满足 (b)（已锚定法币），通常应落入 e-money 而非 DPT | **❌ 误判（假阳性）** |
| B · 无锚定支付型代币 | 「以单位计值，不与任何货币挂钩，也不由发行人与任何货币锚定」+ 同上功能描述 | **payment_token**（信号与 A **逐字相同**） | 是 DPT（满足 (a)(b)(d)，(c) 待外部事实佐证） | ✅ |

→ **A 与 B 的工具输出完全相同**（verdict 与 signals 逐字一致）：工具**无法区分**「锚定法币的稳定币」与「真正的数字支付代币」，而这在 PSA 下是**决定性的法律界线**。这不是词表粒度问题，而是「**连言式 + 排除性要件**」无法用「**正向信号 OR**」表达的**结构性错配**。

**4) 定性**：这**不是**「数据层 + 逻辑层真独立」的余量问题，而是 **实现层面的设计简化** —— 单一信号计数决策树为照顾通用性，**抹平了「定义列举式」与「功能特征连言式」两种不同法律判定结构**。据此新增 **#11 待复核项**；相关表述不再允许写成「逻辑层适配良好」。

### D.4 法理依据核查 + 10 个重合词语义比对（第 4 步）

**方法**：① 逐条核对 6 个条目的 `framework` / `criteria` 与其官方法定定义是否一致、是否完整；② 核查是否存在跨法域概念串用；③ 对 §D.2.1 扫描出的 **10 个字面重合词**逐条做**语义等价**比对（质疑 3：同源 ≠ 同义）。核验来源均为官方文本，非凭记忆（SFO 附表 1 第 1 部第 1 条；SFA 2001 s.2(1)；PSA 2019 s.2(1)）。

#### D.4.1 法定依据逐条核验

| 条目 | framework 声称 | 官方定义核验 | 判定 |
|------|---------------|------------|------|
| HK-SFC-001 | SFO「证券」 | SFO 附表 1 第 1 部第 1 条：(i) 股份/股额/债权证/债权股额/基金/债券/票据；(ii) 其权利、期权或权益（不论是否称为单位）；(iii) 权益证明书、收据、认购权证；(iv) **任何集体投资计划的权益**；(v) 通常称为证券者。条目 criteria「股份、债权证、集体投资计划权益」与 (i)(iv) 吻合 | ✅ **法理正确**，且 criteria ↔ 指标**自洽**（criteria 用「集体投资计划」、指标亦有 `集体投资计划`） |
| HK-SFC-002 | AMLO（VATP/VASP 发牌） | 前轮独立核验（LegCo 文件 / SFC 通函 23EC27、23EC28 / InvestHK）：VATP 制度由《打击洗钱条例（修订）条例 2022》在第 615 章下增设，2023-06-01 生效，SFC 主责 | ✅ 法律定性正确；⚠️ `source_url` **不可印证**（#D1） |
| HK-SFC-003 | SFO 除外情形（utility） | 与 SFC 2017 年 ICO 声明一致：严格「实用型」代币（仅提供平台使用权）不属 SFO 证券；条目 notes 已载明「若叠加收益承诺仍可能落入证券」 | ✅ **法理正确** |
| SG-MAS-001 | PSA「数字支付代币」 | PSA s.2(1)：须**同时**满足 (a) 以单位表示；(b) **不以任何货币计价且发行人不使之与任何货币挂钩**；(c) 是或拟成为**公众或部分公众接受**的交换媒介；(d) 可电子转移/储存/交易；(e) MAS 订明者。条目 criteria **仅述**「可用于支付商品/服务、作为交易媒介或价值储存」 | ⚠️ **法理不完整** —— 遗漏 (b) 排除性要件与 (c) 文本外事实；**已实测导致稳定币假阳性**（§D.3.1 用例 A）→ **#11** |
| SG-MAS-002 | SFA「资本市场产品」 | SFA s.2(1)：资本市场产品 = 证券 + **CIS 单位** + 衍生品合约 + 杠杆外汇即期外汇合约 + MAS 订明者；其中「证券」另列且不含 CIS 单位。条目 criteria「股份、债券、**集合投资计划**权益」 | ⚠️ **两点缺陷**：① **覆盖不全** —— 指标仅覆盖股份/债权/CIS，未覆盖衍生品、即期外汇、商业信托单位等 limbs；② **criteria 与指标自转不可用** —— criteria 用词「集合投资计划」无法被指标「集体投资」匹配（实测见 D.4.3 H1）→ **#12** |
| SG-MAS-003 | SFA 除外情形（utility） | 与 MAS《数字代币发行指引》一致：仅提供功能访问/兑换、无资本市场产品特征者不适用 SFA | ⚠️ **法理正确但披露不足** —— 新加坡「非 SFA」**不等于**「不受规管」：同一代币仍可能构成 PSA 下 DPT 而须持牌。工具对 SG 返回 `utility_token` 易被误读为「无需任何牌照」→ **#13** |

#### D.4.2 跨法域概念串用检查

HK 三条（`hk_sfc.jsonl`）**无任何** PSA / SFA / 资本市场产品 / DPT 表述；SG 三条（`sg_mas.jsonl`）**无任何** SFO / VATP / 证券及期货条例 / AMLO 表述。→ **无法理串用 ✅**（复验 D.1 观察，结论维持）。

#### D.4.3 10 个重合词的语义等价比对（质疑 3）

**结论先行：10 个重合词中，可确认为「完全语义等价」的为 0 个。** 分两类：

| # | 重合词 | HK 侧（条目 / framework） | SG 侧（条目 / framework） | 语义等价？ | 差异说明 |
|---|-------|--------------------------|--------------------------|-----------|---------|
| 1 | `access` | HK-SFC-003 / SFO 除外情形 | SG-MAS-003 / SFA 除外情形 | ⚠️ **半等价** | 概念同源，但**法律后果不同**：新加坡「非 SFA」仍可能受 PSA 规管（见 B3）；香港工具模型内无对应支付牌照类别 |
| 2 | `debt` | HK-SFC-001 / SFO 证券（criteria 用「**债权证**」，另有 `债券` 指标） | SG-MAS-002 / SFA 资本市场产品（criteria 用「**债券**」，仅 `债权`、**无 `债券`**） | ❌ **不等价** | ① 指标层：「公司**债券**」触发 HK、**不触发 SG**；② 法理层：债权证（debenture）与债券（bond）范围不等同，debenture 更宽 |
| 3 | `dividend` | HK-SFC-001（`dividend` **+** `分红` 双词） | SG-MAS-002（**仅** `dividend`，**无** `分红`） | ❌ **不等价** | 语言覆盖不对称：中文「分红」触发 HK、**不触发 SG**（实测 H2） |
| 4 | `equity` | HK-SFC-001 / SFO 证券 | SG-MAS-002 / SFA 资本市场产品 | ⚠️ **半等价** | 词级等价，但**所指法域范围不同**：SFA 资本市场产品**广于** SFO 证券（另含衍生品、杠杆即期外汇、CIS 单位），而 SG-002 指标仅覆盖股份/债权/CIS，**未覆盖其余 limbs** |
| 5 | `utility` | HK-SFC-003 / SFO 除外 | SG-MAS-003 / SFA 除外 | ⚠️ **半等价** | 同 B3 |
| 6 | `债权` | HK-SFC-001（与 `债券` 并存） | SG-MAS-002（仅 `债权`，无 `债券`） | ❌ **不等价** | 同 #2 |
| 7 | `功能` | HK-SFC-003 / utility | SG-MAS-003 / utility | ⚠️ **半等价** | 同 B3 |
| 8 | `投票权` | HK-SFC-001（`投票权` **+** `voting` 双词） | SG-MAS-002（**仅** `投票权`，**无** `voting`） | ❌ **不等价** | 语言覆盖不对称：英文 "voting rights" 触发 HK、**不触发 SG**（实测 H2） |
| 9 | `消费` | HK-SFC-003 / utility | SG-MAS-003 / utility | ⚠️ **半等价** | 同 B3 |
| 10 | `股权` | HK-SFC-001 / SFO 证券 | SG-MAS-002 / SFA 资本市场产品 | ⚠️ **半等价** | 同 #4 的框架广度差异 |

> **统计**：❌ **不等价 4 个词（debt / 债权 / dividend / 投票权，其中 debt 与 债权 为同一概念对 → 实为 3 个概念）**；⚠️ **半等价 6 个词**；✅ **完全等价 0 个**。
> **B3（utility 组的共同隐患）**：4 个 utility 类重合词（access / utility / 功能 / 消费）在**概念层**同源，但**法律后果层**不等价——新加坡实行 PSA 与 SFA **并行规管**，一个「非资本市场产品」的实用型代币**仍可能是 DPT 而须持牌**；工具对 SG 输出 `utility_token` 时未提示这一点。

#### D.4.4 语义不等价的实测佐证（H1 / H2）

**H1 — SG-MAS-002 的 criteria 用词无法触发自己的指标（自转不可用）**：

| 输入 | SG 实际命中 | 说明 |
|------|-----------|------|
| `本代币代表**集合投资计划**权益，持有人按比例分享收益。` | SG-MAS-002（命中词 = `收益`） | ❌ **CIS 概念未被匹配**；条目之所以仍"亮灯"，是因为句中「分享**收益**」触发了泛词 `收益` —— **归因错误**（证据片段指向收益而非 CIS 权益），若句中无「收益」二字则**完全漏检** |
| `本代币代表**集体投资计划**权益，持有人按比例分享收益。` | SG-MAS-002（命中词 = `集体投资`、`收益`） | ✅ 该译法可匹配 |

→ **根因**：criteria 用「**集合**投资计划」、indicators 用「**集体**投资」，两者非子串关系（`集体投资` ⊄ `集合投资计划`）。**条目自己的法条术语无法触发自己**，属数据/词表缺陷 → **#12**。

**H2 — 语言覆盖不对称导致的跨法域不对称触发**：

| 输入 | 概念 | HK | SG | 是否对称 |
|------|------|----|----|---------|
| `持有人享有分红权利。` | 分红 / dividend | ✅ 命中 `分红` | ❌ 零命中 | ❌ 不对称（SG 缺中文 `分红`） |
| `Holders are entitled to dividend distributions.` | dividend | ✅ `dividend` | ✅ `dividend` | ✅ |
| `持有人享有投票权，可参与治理。` | 投票权 | ✅ `投票权` | ✅ `投票权` | ✅ |
| `Holders have voting rights in the protocol.` | voting rights | ✅ `voting` | ❌ 零命中 | ❌ 不对称（SG 缺英文 `voting`） |
| `本代币代表公司发行的债券。` | 债券 / bond | ✅ `债券` | ❌ 零命中 | ❌ 不对称（SG 缺 `债券`） |
| `The token represents a corporate bond.` | bond | ❌ 零命中 | ❌ 零命中 | ⚠️ 双方共同缺口（均缺 `bond`） |

→ **结论**：同一法律概念（股息权 / 表决权 / 债权证）**因词表语言覆盖不同而在港新触发不一致**——这正是「**同源 ≠ 同义 ≠ 同效**」的实证。用户的质疑 3 **成立**。

#### D.4.5 判定（第 4 步）

- **法理串用：无 ✅** —— 港新各自的法条概念未互相借用，跨法域引用干净。
- **法理正确性：4/6 完整，2/6 不完整** —— HK-001/002/003 与 SG-003 法理正确；**SG-MAS-001（PSA）法理不完整**（遗漏 (b) 非锚定的排除性要件与 (c) 公众接受的文本外事实 → 稳定币假阳性，#11）；**SG-MAS-002（SFA）覆盖不全 + criteria 自转不可用**（#12）。
- **语义等价：0/10 完全等价** —— 10 个重合词中 3 个概念在指标层直接不等价（已实测触发不对称），余 6 个词在框架广度 / 法律后果层半等价。**D.1「观察 1」原判「法律概念同源、良性」的结论过宽**：同源成立，**"良性"不成立**——同源掩盖了词表语言覆盖差异与框架广度差异。
- **披露不足 #13**：SG `utility_token` 未提示「PSA 仍可能并行适用」，存在被误读为「无需牌照」的风险。

---

---

## 待处理项清单（跨模块汇总）

> 🔒 **清单已冻结（2026-09-22 用户裁决）**：规模 **16 项**（子表 A 代码 / 设计 #1–#13 + 子表 B 数据质量 #D1–#D3）。
> **冻结规则**：① 不再新增清单项；② 不再新增审计模块；③ **此后任何新发现一律记入独立「未来工作」节，不进入本清单**。
> **冻结理由**：清单边际收益递减——审计价值已从「发现更多缺口」转移到「结构化已发现 + 提炼元教训」。已发现的 16 项本身即是作品集的一部分，不必等到全清才发布。
> **保留 #12 / #13 的理由**：#12（SG-002 的 criteria 用词触发不了自己的指标）属**逻辑上不可接受**的硬缺陷；#13（`utility_token` 未提示 PSA 并行适用）属**合规误导风险**。「为了收口而掩盖缺陷」比缺陷本身更糟。

> 清单按**性质分两张子表**管理（质疑 1 补强）：
> - **子表 A — 代码 / 设计缺口（#1–#13）**：影响工具**逻辑 / 词表 / 判定 rubric** 的缺口（含需改代码与仅补注释两类），与「港新判定独立性」属于不同维度。
> - **子表 B — 数据质量缺口（#D1–#D3）**：影响**数据可信度 / 引用溯源**的缺口（断链、弱引用）。原被误归为「不计入 #1–#10」，现单独成表。
>
> 子表 A 含**已测试锁定**（4 个 `expectedFailure`，分属 G-A1×2、问题 4×2）与**仅记录（无测试）**两类——两类都必须在清单里，否则读者会误以为「只修那 4 个 xFail 就够了」。合计 **13 项**代码 / 设计缺口。
> 子表 B 经本次 **6 条 source_url 逐条抓取验证**发现 **3 项** citation gap（2 断链 + 1 弱引用，见观察 4）。

### 子表 A：代码 / 设计缺口（#1–#13）

| # | 项 | 测试状态 | 处置类型 | 严重性 | 测试 / 记录位置 | 修复 / 标注方向 | 依赖关系 |
|---|----|---------|---------|--------|----------------|----------------|---------|
| 1 | **G-A1**：absent 被 negation 误吞（架构级双重否定 + 否定窗口忽略句读） | ✅ 已锁定（2 xFail） | 修复代码 | 高 | `test_module_a_gaps.py::test_absent_independent_use_with_neg_context`<br>`test_module_b.py::TestModuleAGA1TwoDimensionFixGuard::test_ga1_path_a` | 双维度约束：`absent` 跳过 negation（weight 维度）+ property/element 二分（semantics 维度） | 依赖 property/element 6/8 分类（已完成，§B3a） |
| 2 | **问题 4**：consumption_context 子串匹配系统性误降级 | ✅ 已锁定（2 xFail） | 修复代码 | 高 | `test_module_b.py::test_b4_substring_collision_no_false_downgrade`<br>`test_module_b.py::TestModuleBProblem4Systematic::test_b4_consumer_rights_no_false_downgrade` | 候选 B+C 组合（同句/近邻约束 + 收窄消费词表，移除 `购买服务` 拼接词），见 §B.2.1 | 独立 |
| 3 | **G-A3**：投资资金缺劳务/算力/流动性对价词（Howey Joiner 扩展未落地到指标） | ⚠️ 仅记录（无测试） | 修复代码（补词表） | 中高 | 文档 §A3（危害态 case2b 已证明真实错分） | 补 `算力/劳务/贡献/挖矿/流动性/提供流动性` 等中文同义词（strong/weak） | 独立 |
| 4 | **问题 2**：dual_context 触发过窄（词表锁定 `purchase_set`） | ⚠️ 仅记录（无测试） | 修复代码（重构） | 中高 | 文档 §B.1（证据：B3 认购不标 / B3b 购买标） | dual_context 触发从「购买字面」解耦到「投资资金要素语义」——按要素/权重判定，而非 `pattern` 字面匹配 | 与问题 3 同源（`purchase_set` 硬编码，§B.6），**应合并重构** |
| 5 | **问题 3**：consumption 降级范围过窄（仅绑定 `purchase_set`） | ⚠️ 仅记录（无测试） | 修复代码（重构） | 中 | 文档 §B.1（证据：B2 正确降 weak / B7 无误伤） | 消费降级适用于**全部**投资资金 strong 指标（`认购/投资/出资` 等），而非仅 `purchase_set` | 与问题 2 同源（`purchase_set` 硬编码，§B.6），**应合并重构** |
| 6 | **B5**：`锁仓`/`lock`=weak 属法律争议简化（**非代码缺陷**） | ⚠️ 仅记录（无测试） | 补注释（非代码） | 中 | 文档 §B.5 | 补 `dispute_note` 标注法律边界（记录不修数据） | 独立 |
| 7 | **C4（模块 C）**：verdict rubric 未对 Howey 核心要件「expectation of profits」赋特殊权重 | ⚠️ 仅记录（无测试） | 设计复核（非代码修复） | 中高 | 文档 §模块C（C4/C9 用例 + C3/C4 联动） | 在 `classify_howey` 引入「利润预期」阈值约束（如 profits=absent 时封顶 verdict ≤ likely_not_security / 不允许 strong 主导）；并复核 weak>absent 优先级对 verdict 的放大；属**跨所有代币的判定问题，非单案例边界** | 与 C3 的 weak>absent 优先级耦合，应一并审视 |
| 8 | **C6（模块 C）**：`增值`/`收益`/`利润` 等泛词单独触发 profits=strong，且未做语境约束（非孤立则直接推高 verdict） | ⚠️ 仅记录（无测试） | 设计复核 | 中高 | 文档 §模块C C6（探针 P1/P2）+ §C.10 跨要素泛词扫描 | 复核「泛词 strong」的抑制机制：如给 `增值/升值/收益/利润` 加语境约束（须与「代币/持币/价格」共现），或降为 weak；现行「保护」实为 `unknown>=3` 信息不足兜底，非针对利润预期设计，任一 weak 出现即蒸发 | 与 #7 同源（rubric 对利润预期只计数、不区分语义），**建议与 #7 合并设计复核** |
| 9 | **C7b（模块 C）**：efforts 要素缺裸 `团队`（仅 `核心团队`/`团队开发` 连续短语命中） | ⚠️ 仅记录（无测试） | 修复代码（补词表） | 低 | 文档 §模块C C7b（探针 P3/P4/P5） | 补 `团队`（weak 或 strong，需定权重）等 efforts 词表；注意 P5 显示 `持续运营` 等其它 strong 通路可部分补救，故仅当文本只提「团队」时漏检 | 与 G-A3 同类（词表覆盖不全，不同要素），**可合并为一个「补词表」PR**，二者不互相依赖 |
| 10 | **C.10（模块 C）**：跨要素「泛词 strong 未做语境约束」系统性扫描——`投资`/`资金池`/`收益`/`利润`/`增值`/`回报`/`升值` 等单独出现即可触发 strong，词义泛化、易在营销文本误触发 | ⚠️ 仅记录（无测试；扫描见 §C.10） | 设计复核 | 中 | 文档 §C.10 跨要素泛词扫描 | 与 #8 同源，扩大覆盖面：跨四要素统一评估「泛词 strong」抑制机制；可并入 #7/#8 的设计复核 PR | 与 #7/#8 同源（rubric 对利润预期/泛词只计数、不区分语义），**建议并入同一设计复核** |
| 11 | **D.3.1（模块 D）**：信号分类法对 SG PSA DPT 的适配性缺陷——PSA「数字支付代币」为**功能特征连言式**定义（须同时满足 (a)–(e)，含 (b) 非货币锚定这一**排除性要件**、(c) 公众接受这一**文本外事实**），而 `classify_jurisdiction` 对 payment 仅用**正向信号 OR** 判定，无法表达排除要件与连言结构；实测用例 A/B 输出逐字相同（稳定币与真 DPT 不可区分） | ⚠️ 仅记录（无测试；实测证据见 §D.3.1 用例 A/B） | 设计复核 | 中 | 文档 §D.3.1（SFO/SFA/PSA 官方法定义核验 + 稳定币 A/B 实测） | 为 payment 分支引入「连言 + 排除」能力：新增 `negative_indicators`（挂钩 / 锚定 / pegged / 计价等）与 required-all 特征组，或为 PSA 单独提供功能特征判定路径；并须在报告中明示「公众接受」为**不可由文本判定**的事实，转人工核实 | 与 #2（问题4 子串）共享决策树，但**根因不同**（判定结构错配，非匹配器缺陷） |
| 12 | **D.4（模块 D）**：港新词表语义对齐缺陷——① SG-MAS-002 的 criteria 用词「**集合**投资计划」无法被其指标「**集体**投资」匹配（条目自己的法条术语触发不了自己，实测 H1：仅靠泛词 `收益` 偶然命中，**归因错误**）；② 语言覆盖不对称：SG-002 缺中文 `分红`、缺英文 `voting`、缺 `债券`，致「分红 / voting rights / 债券」仅触发 HK（实测 H2） | ⚠️ 仅记录（无测试；实测见 §D.4.4） | 修复代码 / 数据（补词表 + 术语对齐） | 中 | 文档 §D.4.3 / §D.4.4 | ① 统一 SG 术语为「集体投资计划」或同时收 `集体投资`/`集合投资`；② 补齐 SG-002 的 `分红`/`voting`/`债券`，HK-001 补 `bond`；③ 建立「criteria 术语 ↔ indicators」一致性检查（可用测试断言：criteria 中出现的法条术语必须能被自身 indicators 命中） | 与 #9（补词表）同类，可合并为一个「词表对齐」PR |
| 13 | **D.4（模块 D）**：`utility_token` 披露不足——新加坡 PSA 与 SFA **并行规管**，一个「非资本市场产品」的实用型代币**仍可能构成 DPT 而须持牌**；工具对 SG 输出 `utility_token` 未提示该并行风险，易被用户误读为「无需任何牌照」 | ⚠️ 仅记录（无测试） | 补注释 / 报告披露 | 中 | 文档 §D.4.1（SG-MAS-003 行）、§D.4.3 B3 | 在 SG-MAS-003 的 `notes` / `dispute_note` 增补「非 SFA ≠ 不受规管，PSA 可能并行适用」；并在报告 jurisdiction 段落对 SG 的 `utility_token` 自动追加该提示 | 与 #11 同源（PSA 并行规管），但#11 是判定结构、#13 是输出披露，可分开修 |

### 子表 B：数据质量缺口（#D1–#D3）

> 本轮按用户「质疑 1」要求**按性质分档**——**弱引用 ≠ 死链**，二者不可并列同档。

| # | 条目 | 问题 | 验证方式 | 严重性 | 修复方向 | 依赖 |
|---|------|------|---------|--------|---------|------|
| D1 | HK-SFC-002 | `source_url` 为 SFC「Licensing」通用落地页，**URL 存活但页面主题不匹配**（无 VASP / AMLO / 2023-06-01 字样）→ 属**弱引用**；法理定性经独立核验仍正确，仅「引用不可印证」 | WebFetch 抓取该 URL（2026-09-20）→ 仅述 SFO 中介人发牌职能 | **中**（弱引用：可修，改 URL 即可） | 替换为具体 VATP 发牌通函 URL（如 `apps.sfc.hk/edistributionWeb/gateway/TC/circular/doc?refNo=23EC28`）；条目加「引用待核实」标记 | 独立 |
| D2 | HK-SFC-001 | `source_url`（`.../Intermediaries/Virtual-assets`）**实测 404 断链** → 整个引用**不可验证**：任何读者点开均得「页面不存在」，该条目法理依据在报告层面**完全不可追溯**。非「弱」，是**不可用** | WebFetch 抓取（2026-09-20）→ 404，提示重定向至新站 | **高**（死链：不可验证，非「页面错配」） | 更新为新站等效页或具体通函（条目 notes 已引「SFC 2019 声明 / 后续通函」，应取其真实 URL） | 独立 |
| D3 | HK-SFC-003 | `source_url` 与 001 **同一条死链**（`.../Intermediaries/Virtual-assets`）→ 404，同样不可验证 | WebFetch 抓取（2026-09-20）→ 404 | **高**（死链） | 同 D2，更新为可用 URL | 独立 |

> **严重性差异说明（用户质疑 1 纠正）**：原报告把 D1（弱引用）与 D2/D3（死链）并列于「数据质量缺口」而**未分档**，属**低估**。二者性质不同：
> - **弱引用（D1）**：URL **存活**，仅页面主题不匹配 → 读者仍能打开权威机构页面，只是无法印证具体条款；修复成本 = 改 URL，读者受损有限。
> - **死链（D2/D3）**：URL **404，整个引用不可验证** → 读者点开得到「页面不存在」，该条目的法理依据**在报告层面完全不可追溯**，可信度直接崩坏。故严重性应**高于**弱引用。
>
> **系统性判断（非偶发）**：HK-001 与 HK-003 **两条** `source_url` 指向同一条已失效旧路径，说明成因是 **SFC 官网迁移后未同步更新引用**，属「**引用维护缺失**」的系统性问题，而非个别条目疏漏。
> **建议机制**：在 CI 增加「**引用存活定期巡检**」——定时任务对全部 6 条 `source_url` 做 HEAD/GET 探测，返回非 2xx（尤其 404）即告警并自动开 issue，把「一次性人工核验」升级为「**持续可验证**」。三步同步：① 修复 D1–D3 的 URL；② 加巡检 job；③ 纳入 README「已知限制」节披露（性质为数据质量缺陷，非法律错误、非代码缺陷）。

> 子表 A 口径说明：
> - 4 个 xFail 中 G-A1 占 2（双路径锁定）、问题 4 占 2（双场景锁定），故「4 测试 = 2 代码缺口」，**不等于「只有 2 个缺口」**。
> - 问题 2 / 问题 3 是模块 B 发现的**真实缺口**（方向为「范围过窄 / 词表锁定」→ **漏判**，与问题 4 的「误降级」→ **误判**方向相反），只是**尚未写测试**，故列入「仅记录」而非略去。二者**共享同一根因**（`purchase_set` 硬编码，§B.6），建议合并为一个重构项。
> - G-A3 虽仅记录，但其危害态 case2b 已证明会真实翻转 verdict（§A3），**优先级仅次于 G-A1**，建议优先补 xFail 锁定。
> - B5 本质是「已知法律不确定性」而非代码缺陷，列入是为完整呈现「待处理项全貌」（其处置 = 补 `dispute_note`，非改代码）。
> - **C4（#7）是模块 C 揭示的 rubric 级设计缺陷**：`classify_howey` 仅做四态计数，**不对 Howey 核心要件"expectation of profits"赋特殊权重**，导致 profits=absent 仍可被其它因子推成 possibly/likely_security（C4/C9）。这是**跨所有代币的判定问题，非单案例边界**，且 C3 的 weak>absent 优先级进一步放大该效应——修复时须与 C3 联动审视。
> - **C6（#8）与 C7b（#9）是 C5-C9 用例产出后补入的两项**（原报告仅作「设计观察」记录，经审计提示后升级为清单项）：#8 与 #7 **同源**（rubric 对利润预期只计数、不区分语义），方向相反：#7 是 profits=absent 被无视（应降未降），#8 是 profits=strong 由泛词触发（应抑制未抑制）。二者建议合并设计复核。#9 与 G-A3 同类（词表覆盖不全），但发生在 efforts 要素、方向为**漏检**；严重性低（P5 证明 `持续运营` 等其它 strong 通路可部分补救），可与 G-A3 合并为一个「补词表」PR。#10 是 #8 的**跨要素扩大版**（系统扫描），与 #7/#8 同源，建议并入同一「利润预期/泛词语义约束」设计复核 PR，不与 #9（补词表）混淆。
> - **本轮一并修正一处我先前写错的表述**：C6 原写「`增值` 为唯一强信号时因 3-unknown 规则落 likely_not_security」——实测为 **insufficient_info**（`unknown>=3` 分支优先于 `strong+weak<=1`）。该错误已撤回并补入探针证据（P1/P2），说明「保护」是信息不足兜底的**偶然产物**而非设计。该错误已撤回并补入探针证据（P1/P2），说明「保护」是信息不足兜底的**偶然产物**而非设计。

### 修复路线图（Roadmap）

> 「有路线图的 16 项」≠「无路线图的 16 项」：前者是有序 backlog，后者才是一堆烂摊子。

**当前状态三分**：

| 状态 | 数量 | 说明 |
|------|------|------|
| ✅ **已修复** | **0 项** | 本审计按纪律「**只记录不修**」，全部缺口原样保留 |
| 🔒 **已测试锁定**（`expectedFailure`，等修复） | **2 项** | #1 G-A1、#2 问题 4 —— 共 4 个 xFail（G-A1×2 + 问题 4×2） |
| 📝 **仅记录**（无测试） | **14 项** | #3–#13（11 项）+ #D1–#D3（3 项） |

**路线图**：

| 优先级 | 项 | 时间承诺 |
|--------|-----|---------|
| **Phase 1（高）** | #1 G-A1、#2 问题 4、#D2（HK-001 死链）、#D3（HK-003 死链） | 下个 release 前 |
| **Phase 2（中高）** | #3 G-A3、#4 问题 2、#5 问题 3、#7 C4 | 后续 |
| **Phase 3（设计复核 · 长期，可能重构）** | #8 C6、#10 C.10、#11 信号分类法适配性、#12 词表语义对齐、#13 utility 披露 | 长期 |
| **不承诺修复（记录即可）** | #6 B5（法律争议，处置 = 补 `dispute_note`）、#9 C7b（补词表，可合并）、#D1（弱引用，改 URL 即可） | 记录即可 |

> **分档理由**：#D2 / #D3 进 Phase 1，因**死链 = 引用不可验证**（严重性高）而修复成本极低（换 URL）；#D1 仅为弱引用、影响可控，故列「不承诺」。#11–#13 属设计层，修复可能触发重构，须与 #2 的匹配器修复一并评估（耦合关系见 §D.2.2）。

---

## 未来工作（Future Work）—— 冻结后新发现的归属地

> 本节独立于上面**已冻结**的「待处理项清单（#1–#13 / #D1–#D3）」。按 2026-09-22 用户裁决：审计**不再新增清单项、不再新增审计模块**；此后发现的任何新问题一律记入本节，**不进清单、不改编号**。
> 本节仅作记录，**不代表承诺修复**，也不改变 README「已知缺口」节的计数口径。

| # | 发现 | 来源 | 记录日期 | 备注 |
|---|------|------|---------|------|
| （暂无） | —— | —— | 2026-09-22 | 本节于清单冻结时建立，当前为空 |

> 记入规则：每条须含「发现 + 来源 + 日期 + 是否为已冻结项的新实例」。若新发现只是已冻结项的**新实例**，应追加到对应清单项的「实例」说明中，而非在本节新增条目。

---

本轮澄清暴露的薄弱环节，与前序「能力缺口伪装成克制 / 验证不充分包装成验证完成 / 新回归包装成已知限制 / 修复引入的回归藏在自测盲区」同源，属**第五模式：边界数据与边界例子未严格自检**。审计报告须内置以下三条红线：

1. **统计必须先验证定义，再下数字。** 凡引用「含某类关键词的比例」「命中某规则的数量」等统计，必须先逐字打印其依赖的词表 / 规则定义，再核对每一项归属。本轮原「5/14(35.7%) 含否定词」既把不在词表的 `独立`/`去` 算入，又把「字面自含否定词」错当成 `negated=True` 的触发机制（实为命中词前 16 字窗口检测）——统计与机制双重错误，已撤回。
2. **跨句 / 跨主语的例子必须真的跨句。** 用于演示「否定窗口吞掉无关命中」的例子，必须让否定词与受害指标分属不同分句 / 不同主语（如 `项目方不保留私钥，持币者按比例获得分红` → `分红` 被误吞）。同句内「不提供分红」的 `分红` 被否是**正确行为**，不得作为 bug 示例。
3. **已知缺陷测试必须标 `expectedFailure`，不能破坏 CI。** 记录「修复前应 FAIL」的回归锁定用例，用 `@unittest.expectedFailure` 包裹（CI 保持全绿；修复后删除装饰器转正常通过），严禁以裸 FAIL 留在默认测试集。

## 审计元教训（五模式闭环）

回顾本会话五轮审计，反复出现的同一失败模式：

1. 能力缺口伪装成克制
2. 验证不充分包装成验证完成
3. 新回归包装成已知限制
4. 修复引入的回归藏在自测盲区
5. 边界数据和例子未严格自检
6. **主动性可训练，但系统性整合仍需外部审计**（元观察，待纳入最终 README「元教训」节）。本会话模块 B 相比模块 A 质量明显提升——AI 主动承认了三处定性错误、并自行发现并升级了问题 4 的系统性。但「跨模块待修复清单」这类**整合视角**并未自发产生，仍依赖外部审计提示。**结论**：AI 的**单点自查能力可通过训练提升**，但**跨模块 / 跨会话的系统性整合（缺口全景、依赖关系、优先级）仍必须由外部审计纪律保证**。这一观察比任何技术细节更能说明「AI 辅助合规工具开发需要什么样的审计纪律」，建议作为 README「元教训」节的首条。

7. **单点自查可训练，但根本原因的深挖仍需外部审计引导**（元观察，与 #6 互补，待纳入最终 README「元教训」节）。模块 C 的 C4 由 AI **主动**发现「2 weak ≡ 2 strong」的表象异常，却停在「权重偏重」层，未向「rubric 未对 Howey 核心要件（利润预期）赋特殊权重」深挖——后者需 Howey Test 的法理判断（跨领域专业知识）才能识别。本会话该模式已重复 6–7 次：**AI 倾向于停在「发现异常」层，而「异常背后的法理 / 设计缺陷」需要外部审计以专业判断引导**。与 #6 互补：#6 是「广度」（跨模块整合缺位），本条是「深度」（根因深挖缺位）。两者共同说明——AI 辅助合规工具开发，**单点发现可训练，但根因深挖与系统整合均需人类审计纪律兜底**。

8. **（元观察 3 · 结论乐观偏差）结论措辞须与证据强度匹配——AI 天然倾向于把「未推翻」写成「已证实」。本会话该模式已第 7–8 次出现：模块 D 第 2 步初稿写「结果层真独立 ✅」，实则仅 4 个手工用例且 1 个初版失败（质疑 4 已重构为「部分验证通过 ⚠️」）；又曾把 HK-002 的 citation gap 标「不计入 #1–#10」弱化其可见性（质疑 1 已单列成 #D1–#D3）。与 #6（广度：跨模块整合缺位）、#7（深度：根因深挖缺位）并列，本条是**第三类——结论-证据匹配度缺位**。校准方法（建议纳入 README「元教训」）：任何「✅ / 真独立 / 已证实」类结论，须反向自问「支撑它的样本量 / 失败案例 / 反例检索是否充分」，否则降级为「部分验证 / 待续」。

**§8 子观察（本轮第 2 个实例 · 乐观偏差的隐蔽形式）**：本轮偏差**不是「夸大结论」**，而是「**结论停在表层，未追问下一层**」。三个具象表现：
- **严重性未分档**：发现 404 死链后，把它与「弱引用」并列同档（都称「数据质量缺口」），未继续追问「死链与弱引用的**性质差异**是什么？严重性是否相同？」→ 用户指出后已拆档（弱引用 = 中 / 死链 = **高**）。
- **只描述现状、未追适用性**：D.3 得出「实现共享下的状态隔离」这一诚实描述后即停止，未追问「**共享的这套信号分类法，对两个法域的法律结构是否都适配？**」→ 用户指出后追问，立即发现 PSA **连言式** vs SFO/SFA **定义式**的本质差异（§D.3.1），并由稳定币 A/B 实测坐实为**假阳性**。
- **用「同源」当「同义」**：10 个重合词以「英美证券法同源、良性」一句话带过，未追问「**同源是否等于同义？两法域的 criteria 是否语义等价？**」→ 用户指出后逐条比对，发现**指标语言不对齐**等问题（见 §D.4）。

**校准方法（建议纳入 README「元教训」）**：每个结论落笔后，**强制追问一次「这个结论的下一层问题是什么？」** ——尤其当结论使用「**同源 / 同类 / 共享 / 良性 / 可接受 / 适配较好**」这类**收束性措辞**时，这些词往往是**停止追问的信号**，而不是「追问已完成」的信号。

五次均非「恶意做错」，而是 AI 的天然倾向——**倾向于给出「看起来完整」的答案，而非「实际完整」的答案**。本项目通过五轮审计逐步识别并修正了该模式，沉淀为「审计方法学纪律」三条红线（见上节）。这段话本身比任何技术细节更能体现专业深度，建议纳入 README 或博客的「审计方法论」小节。

> 注：以上仅记录，未修改任何代码 / 数据。模块 B 已收口（含两处补强 1/2 与问题4 系统性升级）；模块 C 已完成（C1-C9 + C4 深挖第二层 + C3/C4 联动 + 待处理项 #7 + 元教训 #7）；**模块 D 已收口（D.1 数据源 / D.2 判定结果 / D.2.1 跨法域碰撞 / D.2.2 耦合风险 / D.3 逻辑路径 / D.3.1 信号分类法适配性 / D.4 法理依据 + 语义比对，新增 #11–#13）**。模块 E 与最终收口（README「元教训」节 + 三项目 release）待续。
