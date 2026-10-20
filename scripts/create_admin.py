"""创建或更新管理员账号。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enterprise_rag.config import get_settings  # noqa: E402
from enterprise_rag.db import Database  # noqa: E402
from enterprise_rag.models import User  # noqa: E402
from enterprise_rag.security import hash_password  # noqa: E402


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default=settings.admin_username)
    parser.add_argument("--password", default=settings.admin_password)
    args = parser.parse_args()
    if len(args.password) < 8:
        raise SystemExit("密码至少 8 位")
    db = Database(settings.database_url)
    db.create_all()
    session = db.SessionLocal()
    try:
        user = session.query(User).filter(User.username == args.username).first()
        if user is None:
            user = User(
                username=args.username,
                password_hash=hash_password(args.password),
                role="admin",
                is_active=True,
            )
            session.add(user)
            print(f"已创建管理员：{args.username}")
        else:
            user.role = "admin"
            user.password_hash = hash_password(args.password)
            user.is_active = True
            print(f"已更新管理员：{args.username}")
        session.commit()
    finally:
        session.close()
        db.dispose()


if __name__ == "__main__":
    main()
