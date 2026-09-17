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

多法域（香港 SFC / 新加坡 MAS）**分别判定**，不做统一全球结论。

---

## 事实库（每条均附来源 + 核验日期）

| 文件 | 内容 |
|------|------|
| `data/howey_factors.jsonl` | Howey 四要素，含双语指标 + 权重 + SEC 框架来源 |
| `data/jurisdictions/hk_sfc.jsonl` | 香港 SFC：SFO 证券定义 / VASP 发牌 / 实用型除外 |
| `data/jurisdictions/sg_mas.jsonl` | 新加坡 MAS：PSA 数字支付代币 / SFA 证券型 / 实用型除外 |
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
- MVP 聚焦**香港 SFC + 新加坡 MAS**；美国 SEC（Howey 判例库）与 EU MiCA 为后续扩展方向。
- 事实库为 AI 策展 + 初步核对，尚未逐条经执业律师具名核验；如用于实务，请先完成核验台账。

---

## 作品集关系

| 项目 | 合规领域 | 判定性质 |
|------|----------|----------|
| [oss-license-checker](https://github.com/vickywu97/oss-license-checker) | 知产 / 开源法务 | 硬规则（兼容矩阵） |
| [privacy-policy-checker](https://github.com/vickywu97/privacy-policy-checker) | 数据 / 隐私法务 | 半硬规则（检查项） |
| **token-classifier** | Web3 / 加密法务 | 软规则（Howey 四要素） |

三者共同构成「法律 + 工程」完整作品集，均由律师 + 税务师 + 专利代理师 + 代码能力交集构建。
