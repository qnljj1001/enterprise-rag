"""重置 E2E 数据库（危险：仅限测试环境）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enterprise_rag.config import get_settings  # noqa: E402
from enterprise_rag.db import Database  # noqa: E402


def main() -> None:
    settings = get_settings()
    if settings.app_env not in {"test", "dev"}:
        raise SystemExit("只允许在 test/dev 环境重置")
    db = Database(settings.database_url)
    db.drop_all()
    db.create_all()
    print("数据库已重置")


if __name__ == "__main__":
    main()
