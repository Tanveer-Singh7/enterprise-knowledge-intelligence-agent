import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datasets import load_dataset
from app.db.session import SessionLocal
from app.models import Document

ds = load_dataset(
    "onyx-dot-app/EnterpriseRAG-Bench",
    "questions",
    split="test",
    streaming=True,
)

db = SessionLocal()

try:
    document_ids = {
        doc.external_id
        for doc in db.query(Document.external_id)
        .filter(Document.external_id.isnot(None))
        .all()
    }

    total_confluence = 0
    matched = 0

    for row in ds:
        if "confluence" not in row["source_types"]:
            continue

        total_confluence += 1

        if any(doc_id in document_ids for doc_id in row["expected_doc_ids"]):
            matched += 1

    print("Confluence questions:", total_confluence)
    print("Questions with matching expected documents:", matched)
    print("Coverage:", f"{matched / total_confluence:.1%}")
finally:
    db.close()
