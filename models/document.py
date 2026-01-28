from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .case import Case


class Document:
    def __init__(self, doc_id: str, case_id: str, content: str, created_at: datetime | None = None):
        self.doc_id = doc_id
        self.case_id = case_id
        self.content = content
        self.created_at = created_at or datetime.now()

    def belongs_to(self, case: "Case") -> bool:
        return self.case_id == case.case_id

    def __repr__(self) -> str:
        return (
            f"Document(doc_id={self.doc_id}, case_id={self.case_id}, "
            f"created_at={self.created_at})"
        )
