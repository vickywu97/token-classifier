[![CI](https://github.com/vickywu97/token-classifier/actions/workflows/ci.yml/badge.svg)](https://github.com/vickywu97/token-classifier/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

# token-classifier

**离线代币监管定性器** —— 输入一段代币机制描述（白皮书摘要 / 代币经济学 / 问卷），按 **Howey Test 四要素** + **香港 SFC / 新加坡 MAS** 监管框架，输出分级定性、逐要素证据与风险提示。

> 三个求职型作品之一（开源合规 → 数据合规 → Web3 合规）。
> 定位：Web3 / 加密 / 跨境法务岗的**生产力型**工具——把跨境监管框架结构化成可复现的判定 + 证据链。

---

## 为什么做

Web3 项目发币前几乎都要回答一个问题：**「这个代币会不会被认定为证券？」** 误判后果严重（SEC 执法、交易所下架、融资受阻），但律所单次定性咨询动辄数万至数十万。现有工具（TokenSniffer、RugCheck）只做合约安全审计，不做法律定性；通用 AI 又会编造法条（本项目作者的 `legal-hallucination-bench` 已证明其在法律场景不可靠）。

本工具只输出**分析线索**（分级定性 + 逐要素证据），**不输出二元法律结论**，且零依赖、离线、可复现。

---

## 快速开始

```bash
# 方式一：直接运行（无需安装，标准库即可）
python -m token_classifier --file demo/demo_security_token.md --token-name "XChain Token"

# 方式二：直接传文本
python -m token_classifier --text "用户以 ETH 认购，承诺年化 15% 分红，由核心团队持续运营" --format json

# 只看某一法域
python -m token_classifier -f demo/demo_utility_token.md -j HK_SFC

# 指定多法域（默认港 + 新 + 美 SEC + 欧 MiCA）
python -m token_classifier -f demo/demo_security_token.md -j HK_SFC SG_MAS US_SEC EU_MICA
```

依赖：**Python 3.8+，标准库，零第三方依赖**。

---

## 判定设计（两阶段）

**第一阶段：Howey 四要素独立评分**（每个要素四态）
| 状态 | 含义 |
|------|------|
| `strong` | 明确满足 |
| `weak` | 部分满足 / 有争议 |
| `absent` | 不满足 |
| `unknown` | 信息不足 |

**第二阶段：综合定性**
| 定性 | 条件 |
|------|------|
| `likely_security` 🔴 | ≥3 个 strong |
| `possibly_security` 🟡 | 2 strong + 2 weak，或存在关键争议 |
| `likely_not_security` 🟢 | 多数要素 absent |
| `insufficient_info` ⚪ | unknown 过多 |

多法域（香港 SFC / 新加坡 MAS / 美国 SEC / 欧盟 MiCA）**分别判定**，不做统一全球结论。

---

## 事实库（每条均附来源 + 核验日期）

| 文件 | 内容 |
|------|------|
| `data/howey_factors.jsonl` | Howey 四要素，含双语指标 + 权重 + SEC 框架来源 |
| `data/jurisdictions/hk_sfc.jsonl` | 香港 SFC：SFO 证券定义 / VASP 发牌 / 实用型除外 |
| `data/jurisdictions/sg_mas.jsonl` | 新加坡 MAS：PSA 数字支付代币 / SFA 证券型 / 实用型除外 |
| `data/jurisdictions/us_sec.jsonl` | 美国 SEC：采用 Howey 测试（与综合定性同源），输出证券/非证券倾向与注册制度提示 |
| `data/jurisdictions/eu_mica.jsonl` | 欧盟 MiCA：加密资产四分类（证券型→MiFID II / EMT / ART / 实用型） |
| `data/token_types.jsonl` | 四级定性定义（emoji + 风险等级） |

每条记录附 `source_url` 与 `source_accessed_at`。监管框架基于公开信息整理，可能滞后，请以监管机构官方最新发布为准。

---

## 报告

- **法务版（Markdown）**：综合定性 + Howey 四要素证据表 + 各法域判定 + 双重免责声明。
- **工程版（JSON）**：结构化输出，便于 CI / 下游系统解析。

```bash
python -m token_classifier -f demo/demo_security_token.md -o report.md     # Markdown
python -m token_classifier -f demo/demo_security_token.md --format json     # JSON
```

CI 门禁：当综合定性达到证券风险级别时以非零码退出，可直接接入流水线：

```bash
# 若定性为 possibly_security 或 likely_security，则 exit 1
python -m token_classifier -f demo/demo_security_token.md --fail-on possibly_security
```

---

## 测试

```bash
python -m unittest discover -s tests
```

覆盖：事实库加载、证据提取、四态判定、Howey 综合定性、各法域 verdict、三个 demo 集成（证券 / 实用 / 争议）。

---

## 局限与免责

- **本工具输出为自动化分析线索，不构成法律意见。** 最终定性须由执业律师结合完整事实（发行方式、营销话术、治理结构、实际用途、二级市场安排等）判断。
- **监管框架基于公开信息整理**，附核验日期，可能滞后于最新执法动态与监管指引，请以各监管机构官方最新发布为准。
- 已实现 **香港 SFC + 新加坡 MAS + 美国 SEC（Howey 框架特征 5 条，us_sec.jsonl）+ 欧盟 MiCA（四类划分）** 四法域默认判定；完整 SEC 执法判例库（SEC v. Ripple / Telegram 等 litigation releases）为 Phase 2 扩展方向。
- 事实库为 AI 策展 + 初步核对，尚未逐条经执业律师具名核验；如用于实务，请先完成核验台账。

---

## 这套工具是怎么被审计出来的

本工具附带一份完整的诚实性审计报告：[`docs/HONESTY_AUDIT.md`](docs/HONESTY_AUDIT.md)。

审计的目标不是「证明工具没问题」，而是区分两件事：**真克制**（输入信息确实缺失，工具如实报 `unknown`）与**能力缺口**（输入已含相关信息，但代码没读到 / 误读，伪装成克制）。

审计过程沉淀了 **8 条元教训**。它们不只是本项目的注脚，而是一套可复用的「**AI 辅助合规工具审计方法论**」。

### 一、五种「包装」模式（AI 倾向于把不完整包装成完整）

| # | 模式 | 本项目实例 | 可验证位置（能点开、能核对） |
|---|------|-----------|---------------------------|
| 1 | 能力缺口 → 包装成「克制」 | 投资资金要素漏了劳务 / 算力 / 流动性对价词，工具报 `unknown` 看似「信息不足」，实为词表没覆盖 | `docs/HONESTY_AUDIT.md §A1`（G-A1）、`§A3`（G-A3）；xFail 锁定于 `tests/test_module_a_gaps.py`、`tests/test_module_b.py` |
| 2 | 验证不充分 → 包装成「验证完成」 | 模块 A 初版「5/14 含否定词」的统计：既把不在词表的词算入，又搞错了否定的触发机制——统计与机制双重错误 | `docs/HONESTY_AUDIT.md §审计元教训 第 1 条`（含该统计的撤回记录） |
| 3 | 新回归 → 包装成「已知限制」 | B5「锁仓 = weak」被写成法律争议，实为简化未标注 | `docs/HONESTY_AUDIT.md §B.5` |
| 4 | 修复引入的回归 → 藏在自测盲区 | 问题 4 的子串匹配缺陷在自造用例下不显现，换一个高频词（「消费者权益」）即误判 | `docs/HONESTY_AUDIT.md §B.2.1`（问题 4 系统性）、`§D.2`（用例 1 初版失败）、`§D.2.1`（5 处跨法域子串重叠扫描）；commit `ccfeea7` |
| 5 | 边界数据 / 例子 → 未严格自检 | 演示「否定窗口吞掉命中」的例子若否定词与指标同句，则被否是**正确**行为，不能当 bug 用 | `docs/HONESTY_AUDIT.md §审计元教训 第 2 条` 与「三条红线」节 |

> 每条元教训都附**可验证位置**——抽象口号可以被事后编造，带引用的实例可以被点开核对。这是合规报告的核心纪律。

### 二、两种「能力边界」

6. **主动性可训练，但跨模块系统性整合仍需外部审计。** 模块 B 相比模块 A 质量明显提升——AI 会主动承认定性错误、自行发现并升级问题 4 的系统性。但「跨模块待修复清单」这类**整合视角**不会自发产生，仍依赖外部审计提示。
7. **单点自查可训练，但根因深挖仍需外部审计引导。** 模块 C 的 C4 由 AI **主动**发现「2 weak ≡ 2 strong」的表象异常，却停在「权重偏重」层，未向「rubric 未对 Howey 核心要件（利润预期）赋特殊权重」深挖——后者需要法理判断（跨领域专业知识）才能识别。

> #6 是「**广度**」问题（跨模块整合缺位），#7 是「**深度**」问题（根因深挖缺位）。

### 三、一个「隐蔽形式」

8. **乐观偏差的隐蔽形式：不是夸大结论，而是用看起来合理的措辞掩盖未追问的下一层。** 三个具象表现：

| 表现 | 本项目实例 |
|------|-----------|
| **严重性未分档** | 把 404 死链与「弱引用」并列同档，未追问二者性质差异（死链 = **不可验证**；弱引用 = 可修，改 URL 即可） |
| **只描述现状、未追适用性** | 得出「实现共享下的状态隔离」后即停止，未追问「共享的这套信号分类法，对两个法域的法律结构是否都适配？」——追问后发现 **PSA 连言式 vs SFO/SFA 定义式**的本质差异，并由稳定币 A/B 实测坐实为**假阳性** |
| **用「同源」当「同义」** | 10 个港新重合词以「英美证券法同源、良性」一句话带过，未追问「同源是否等于同义？」——逐条比对后确认为 **0/10 完全等价** |

**校准方法**：每个结论落笔后，强制追问一次「**这个结论的下一层问题是什么？**」。尤其当结论使用「同源 / 同类 / 共享 / 良性 / 可接受 / 适配较好」这类**收束性措辞**时——这些词往往是**停止追问的信号**，而不是「追问已完成」的信号。

### 这套方法论的价值

在 AI 辅助开发中，最大的风险不是「做错」，而是「**用看起来完整的答案掩盖不完整**」。

这套审计纪律的价值**不在于「零缺陷」，而在于「可持续地发现自身缺陷」**——对一个合规工具而言，可信度来自「**知道自己哪里不可靠**」，而不是「声称自己完美」。

---

## 作品集关系

| 项目 | 合规领域 | 判定性质 |
|------|----------|----------|
| [oss-license-checker](https://github.com/vickywu97/oss-license-checker) | 知产 / 开源法务 | 硬规则（兼容矩阵） |
| [privacy-policy-checker](https://github.com/vickywu97/privacy-policy-checker) | 数据 / 隐私法务 | 半硬规则（检查项） |
| **token-classifier** | Web3 / 加密法务 | 软规则（Howey 四要素） |

三者共同构成「法律 + 工程」完整作品集，均由律师 + 税务师 + 专利代理师 + 代码能力交集构建。
