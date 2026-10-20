"""导出只读 Wiki 为 Markdown 文件。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enterprise_rag.config import get_settings  # noqa: E402
from enterprise_rag.db import Database  # noqa: E402
from enterprise_rag.models import Document, KnowledgeBase  # noqa: E402
from enterprise_rag.services.wiki import build_document_wiki, build_kb_wiki  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kb-id", required=True)
    parser.add_argument("--out", default="wiki")
    args = parser.parse_args()
    settings = get_settings()
    db = Database(settings.database_url)
    session = db.SessionLocal()
    out_dir = Path(args.out) / args.kb_id
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        kb = session.get(KnowledgeBase, args.kb_id)
        if kb is None:
            raise SystemExit("知识库不存在")
        _, markdown = build_kb_wiki(session, kb.id)
        (out_dir / "index.md").write_text(markdown, encoding="utf-8")
        for document in session.query(Document).filter(Document.kb_id == kb.id).all():
            _, doc_markdown = build_document_wiki(session, document.id)
            (out_dir / f"{document.id}.md").write_text(doc_markdown, encoding="utf-8")
        print(f"已导出到 {out_dir}")
    finally:
        session.close()
        db.dispose()


if __name__ == "__main__":
    main()
