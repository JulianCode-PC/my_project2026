from datetime import datetime
from typing import Optional

from .document import Document


class Case:
    def __init__(self, case_id: str, title: str, created_at: datetime | None = None):
        self.case_id = case_id
        self.title = title
        self.created_at = created_at or datetime.now()
        self.documents: list[Document] = []

    def add_document(self, doc: Document) -> None:
        if doc.case_id != self.case_id:
            raise ValueError(
                f"Document {doc.doc_id} case_id={doc.case_id} "
                f"does not match Case {self.case_id}"
            )
        self.documents.append(doc)

    def list_documents(self) -> list[Document]:
        return list(self.documents)

    def find_document(self, doc_id: str) -> Optional[Document]:
        for d in self.documents:
            if d.doc_id == doc_id:
                return d
        return None

    def __repr__(self) -> str:
        return f"Case(case_id={self.case_id}, title={self.title}, documents={len(self.documents)})"
