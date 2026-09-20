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

## 审计方法学纪律（本轮四澄清沉淀）

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

五次均非「恶意做错」，而是 AI 的天然倾向——**倾向于给出「看起来完整」的答案，而非「实际完整」的答案**。本项目通过五轮审计逐步识别并修正了该模式，沉淀为「审计方法学纪律」三条红线（见上节）。这段话本身比任何技术细节更能体现专业深度，建议纳入 README 或博客的「审计方法论」小节。

> 注：以上仅记录，未修改任何代码 / 数据。模块 B–E 待续。
