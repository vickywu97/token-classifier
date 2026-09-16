"""token-classifier：代币监管定性器（离线、零依赖）。

输入代币机制描述，输出 Howey 四要素分级定性 + 香港 SFC / 新加坡 MAS 多法域分析线索。
仅输出分析线索，不构成法律意见。
"""

__version__ = "0.1.0"
__all__ = ["extractor", "engine", "classifier", "report", "cli"]
