"""命令行入口：token-classifier

用法示例：
  python -m token_classifier --file demo/demo_security_token.md --token-name "XXX Token"
  python -m token_classifier --text "用户以 ETH 认购..." --format json
"""
import argparse
import os
import sys

from .extractor import load_libraries
from .classifier import analyze
from .report import build_markdown, build_json, summarize

VALID_JURISDICTIONS = ["HK_SFC", "SG_MAS"]


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="token-classifier",
        description="代币监管定性器：输入代币机制描述，输出 Howey 四要素分级定性 + 多法域分析线索（离线、零依赖）。",
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", "-f", help="代币机制描述文件路径（.md/.txt）")
    src.add_argument("--text", "-t", help="直接传入代币机制描述文本")

    parser.add_argument("--token-name", "-n", default="未命名代币", help="代币名称（用于报告标题）")
    parser.add_argument(
        "--jurisdictions", "-j", nargs="+", default=VALID_JURISDICTIONS,
        choices=VALID_JURISDICTIONS, help="要分析的法域（默认港+新）",
    )
    parser.add_argument("--format", choices=["md", "json"], default="md", help="输出格式")
    parser.add_argument("--output", "-o", help="输出到文件（不指定则打印到 stdout）")
    args = parser.parse_args(argv)

    if args.file:
        if not os.path.isfile(args.file):
            print(f"错误：文件不存在：{args.file}", file=sys.stderr)
            return 2
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = args.text

    libs = load_libraries()
    analysis = analyze(text, libs, args.jurisdictions)

    summary = summarize(text)
    if args.format == "json":
        report = build_json(args.token_name, analysis, libs, args.jurisdictions, summary=summary)
    else:
        report = build_markdown(args.token_name, analysis, libs, args.jurisdictions, summary=summary)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已写入：{args.output}", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
