"""预加载 bge-m3：首次下载模型并编码一条样例。"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enterprise_rag.config import get_settings  # noqa: E402
from enterprise_rag.infra.embedder import build_embedder  # noqa: E402


def main() -> None:
    settings = get_settings()
    embedder = build_embedder(settings)
    started = time.perf_counter()
    vectors = embedder.embed(["西部计划志愿者服务期一般为 1 至 3 年。"])
    print(f"编码完成：dim={len(vectors[0])}，耗时 {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    main()
