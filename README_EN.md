[![CI](https://github.com/vickywu97/token-classifier/actions/workflows/ci.yml/badge.svg)](https://github.com/vickywu97/token-classifier/actions/workflows/ci.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

# token-classifier

**Offline token regulatory classifier** — input a token-mechanism description (whitepaper summary / tokenomics / questionnaire); it outputs a graded classification, per-factor evidence, and risk notes under the **Howey Test four factors** + **Hong Kong SFC / Singapore MAS** regulatory frameworks.

> One of three job-hunting portfolio pieces (open-source compliance → data compliance → Web3 compliance).
> Positioning: a **productivity-type** tool for Web3 / crypto / cross-border legal roles — structuring cross-border regulatory frameworks into reproducible judgment + evidence chains.

---

## Why build it

Before issuing a token, every Web3 project must answer one question: **"Will this token be classified as a security?"** A wrong call has severe consequences (SEC enforcement, exchange delisting, blocked financing), yet a single legal-classification consultation runs tens to hundreds of thousands. Existing tools (TokenSniffer, RugCheck) only do contract-security audits, not legal classification; general AI fabricates statutes (the author's `legal-hallucination-bench` has proven it unreliable in legal scenarios).

This tool outputs only **analysis leads** (graded classification + per-factor evidence), **not binary legal conclusions**, and is zero-dependency, offline, and reproducible.

---

## Quick start

```bash
# Option 1: run directly (no install, standard library only)
python -m token_classifier --file demo/demo_security_token.md --token-name "XChain Token"

# Option 2: pass text directly
python -m token_classifier --text "Users subscribe in ETH, promising 15% annual dividends, operated by a core team" --format json

# Only one jurisdiction
python -m token_classifier -f demo/demo_utility_token.md -j HK_SFC

# Multiple jurisdictions (default: HK + SG + US SEC + EU MiCA)
python -m token_classifier -f demo/demo_security_token.md -j HK_SFC SG_MAS US_SEC EU_MICA
```

Dependencies: **Python 3.8+, standard library, zero third-party dependencies**.

---

## Judgment design (two stages)

**Stage 1: independent Howey four-factor scoring** (each factor, four states)
| State | Meaning |
|-------|---------|
| `strong` | clearly satisfied |
| `weak` | partially satisfied / disputed |
| `absent` | not satisfied |
| `unknown` | insufficient information |

**Stage 2: composite classification**
| Classification | Condition |
|---------------|-----------|
| `likely_security` 🔴 | ≥3 strong |
| `possibly_security` 🟡 | 2 strong + 2 weak, or key dispute present |
| `likely_not_security` 🟢 | majority of factors absent |
| `insufficient_info` ⚪ | too many unknown |

Multiple jurisdictions (Hong Kong SFC / Singapore MAS) are **judged separately** — no single global conclusion.

---

## Fact library (each with source + verification date)

| File | Content |
|------|---------|
| `data/howey_factors.jsonl` | Howey four factors, bilingual indicators + weights + SEC framework source |
| `data/jurisdictions/hk_sfc.jsonl` | Hong Kong SFC: SFO security definition / VASP licensing / utility exclusion |
| `data/jurisdictions/sg_mas.jsonl` | Singapore MAS: PSA digital payment token / SFA security-type / utility exclusion |
| `data/jurisdictions/us_sec.jsonl` | US SEC: applies the Howey test (same source as the composite classification); outputs security/non-security tendency + registration-regime notes |
| `data/jurisdictions/eu_mica.jsonl` | EU MiCA: crypto-asset four-way classification (security-type→MiFID II / EMT / ART / utility) |
| `data/token_types.jsonl` | four-level classification definitions (emoji + risk level) |

Each record carries `source_url` and `source_accessed_at`. Regulatory frameworks are compiled from public information and may lag — always defer to the latest official regulator publications.

---

## Report

- **Legal version (Markdown)**: composite classification + Howey four-factor evidence table + per-jurisdiction judgment + dual disclaimer.
- **Engineering version (JSON)**: structured output for CI / downstream system parsing.

```bash
python -m token_classifier -f demo/demo_security_token.md -o report.md     # Markdown
python -m token_classifier -f demo/demo_security_token.md --format json     # JSON
```

---

## Tests

```bash
python -m unittest discover -s tests
```

Coverage: fact-library loading, evidence extraction, four-state judgment, Howey composite classification, per-jurisdiction verdicts, three demo integrations (security / utility / disputed).

---

## Limitations & disclaimer

- **This tool's output is automated analysis leads, not legal advice.** Final classification must be made by a licensed attorney combining complete facts (issuance method, marketing language, governance structure, actual use, secondary-market arrangements, etc.).
- **Regulatory frameworks are compiled from public information**, with verification dates, and may lag the latest enforcement dynamics and regulatory guidance — always defer to official regulator publications.
- MVP focuses on **Hong Kong SFC + Singapore MAS**; U.S. SEC (Howey case law) and EU MiCA are future extensions.
- The fact library is AI-curated + preliminarily checked, not yet verified item-by-item by a named attorney; if used in practice, complete the verification ledger first.

---

## Portfolio relationship

| Project | Compliance domain | Judgment nature |
|---------|-------------------|-----------------|
| [oss-license-checker](https://github.com/vickywu97/oss-license-checker) | IP / open-source legal | Hard rules (compatibility matrix) |
| [privacy-policy-checker](https://github.com/vickywu97/privacy-policy-checker) | Data / privacy legal | Semi-hard rules (checklist) |
| **token-classifier** | Web3 / crypto legal | Soft rules (Howey four factors) |

Together they form a complete "legal + engineering" portfolio, all built at the intersection of lawyer + tax adviser + patent attorney + coding ability.
