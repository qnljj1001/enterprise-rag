"""导出 OpenAPI 契约。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enterprise_rag.main import create_app  # noqa: E402


def main() -> None:
    app = create_app()
    target = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
    target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已导出：{target}")


if __name__ == "__main__":
    main()
