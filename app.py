# app.py
# Usage (PowerShell / CMD):
#   python app.py "C:\path\to\your_oa.pdf"
#
# If needed:
#   pip install pdfplumber PyPDF2

import sys
import re
from datetime import date, timedelta

from models.case import Case
from models.document import Document
from models.event import Event
from models.deadline import Deadline
from models.task import Task


# ----------------------------
# PDF text extraction
# ----------------------------

def extract_pdf_text(pdf_path: str) -> str:
    text_chunks = []

    # Try pdfplumber first (usually better)
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_chunks.append(page_text)
        full = "\n".join(text_chunks).strip()
        if full:
            return full
    except Exception as e:
        print(f"[pdfplumber failed] {e}")

    # Fallback to PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        for p in reader.pages:
            page_text = p.extract_text() or ""
            if page_text.strip():
                text_chunks.append(page_text)
        return "\n".join(text_chunks).strip()
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {e}")


# ----------------------------
# Heuristic helpers (MVP)
# ----------------------------

def find_first_date(text: str):
    """
    Find a likely date in formats:
      YYYY/MM/DD, YYYY-MM-DD, YYYY.MM.DD
    Return the first match as datetime.date.
    """
    patterns = [
        r"(20\d{2})[\/\-.](0[1-9]|1[0-2])[\/\-.](0[1-9]|[12]\d|3[01])",
        r"(19\d{2})[\/\-.](0[1-9]|1[0-2])[\/\-.](0[1-9]|[12]\d|3[01])",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return date(y, mo, d)
            except ValueError:
                return None
    return None


def guess_doc_type(text: str) -> str:
    """
    Very rough OA detection. Expand keywords later.
    """
    t = text.lower()

    # English OA keywords
    if "office action" in t or "non-final" in t or "final office action" in t:
        return "OA"

    # Taiwan/Chinese OA-ish keywords
    if ("審查意見" in text) or ("通知書" in text and ("審查" in text or "核駁" in text or "補正" in text)):
        return "OA"

    # Gazette / publication-ish
    if ("公報" in text) or ("公告" in text) or ("證書號" in text):
        return "GAZETTE"

    return "UNKNOWN"


def guess_application_number(text: str):
    """
    Try to extract application number.
    Example: 申請號 114139326 E
    """
    m = re.search(r"申請號\s*[:：]?\s*([0-9A-Za-z ]{6,})", text)
    if m:
        return m.group(1).strip()

    m = re.search(r"Application\s*No\.?\s*[:：]?\s*([0-9A-Za-z\-\/ ]{6,})", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return None


# ----------------------------
# Minimal "parser" pipeline
# ----------------------------

def intake_document_into_case(case: Case, pdf_path: str) -> Document:
    raw = extract_pdf_text(pdf_path)

    doc = Document()
    doc.case_id = case.case_id
    doc.source = "OFFICE"
    doc.file_path = pdf_path
    doc.raw_text = raw

    doc.document_type = guess_doc_type(raw)
    doc.title = f"{doc.document_type} PDF"
    doc.received_date = date.today()
    doc.external_reference = None
    doc.status = "NEW"

    found = find_first_date(raw)
    if found:
        doc.title = f"{doc.document_type} PDF (found date {found.isoformat()})"

    case.documents.append(doc)
    return doc


def document_to_event(case: Case, doc: Document):
    if doc.document_type != "OA":
        return None

    event = Event()
    event.case_id = case.case_id
    event.document_id = doc.document_id
    event.event_type = "OA_RECEIVED"

    guessed = find_first_date(doc.raw_text or "")
    event.event_date = guessed if guessed else (doc.received_date or date.today())

    event.description = "OA detected from PDF text (MVP heuristic)"
    event.status = "OPEN"
    event.metadata = {"parser": "mvp_heuristic"}

    case.events.append(event)
    doc.status = "PARSED"
    return event


def event_to_deadline(case: Case, event: Event):
    if event.event_type != "OA_RECEIVED":
        return None

    dl = Deadline()
    dl.case_id = case.case_id
    dl.event_id = event.event_id
    dl.deadline_type = "OA_RESPONSE_DUE"

    base = event.event_date or date.today()
    dl.due_date = base + timedelta(days=90)  # MVP rule
    dl.rule_basis = "MVP: OA response due = event_date + 90 days"
    dl.status = "PENDING"
    dl.metadata = {"base_date": base.isoformat()}

    case.deadlines.append(dl)
    return dl


def deadline_to_task(case: Case, dl: Deadline, event: Event | None = None):
    task = Task()
    task.case_id = case.case_id
    task.deadline_id = dl.deadline_id
    task.event_id = event.event_id if event else None

    task.task_type = "DRAFT_OA_RESPONSE"
    task.title = "Draft OA response"
    task.description = "Prepare draft response to OA (MVP)"
    task.priority = "HIGH"
    task.status = "TODO"

    task.due_date = (dl.due_date - timedelta(days=14)) if dl.due_date else None

    case.tasks.append(task)
    return task


# ----------------------------
# Main
# ----------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python app.py <path_to_oa_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Create case (later you can load from DB)
    case = Case()
    case.jurisdiction = "TW"
    case.application_number = None
    case.filing_date = None

    # Intake PDF -> Document
    doc = intake_document_into_case(case, pdf_path)

    # Enrich case identity (optional)
    app_no = guess_application_number(doc.raw_text or "")
    if app_no and not case.application_number:
        case.application_number = app_no

    # Document -> Event
    event = document_to_event(case, doc)
    if not event:
        print("❌ This PDF was not detected as OA (document_type != OA).")
        print(f"Detected document_type = {doc.document_type}")
        snippet = (doc.raw_text or "")[:500].replace("\n", " ")
        print(f"Text snippet: {snippet}...")
        return

    # Event -> Deadline
    dl = event_to_deadline(case, event)
    if not dl:
        print("❌ No deadline rule matched for this event.")
        return

    # Deadline -> Task
    task = deadline_to_task(case, dl, event)

    # Print summary
    print("\n=== PARSE RESULT ===")
    print(f"Case ID: {case.case_id}")
    print(f"Jurisdiction: {case.jurisdiction}")
    print(f"Application No.: {case.application_number}")
    print()

    print("Document:")
    print(f"  document_id: {doc.document_id}")
    print(f"  type: {doc.document_type}")
    print(f"  title: {doc.title}")
    print(f"  received_date: {doc.received_date}")
    print(f"  file_path: {doc.file_path}")
    print()

    print("Event:")
    print(f"  event_id: {event.event_id}")
    print(f"  type: {event.event_type}")
    print(f"  event_date: {event.event_date}")
    print()

    print("Deadline:")
    print(f"  deadline_id: {dl.deadline_id}")
    print(f"  type: {dl.deadline_type}")
    print(f"  due_date: {dl.due_date}")
    print(f"  rule_basis: {dl.rule_basis}")
    print()

    print("Task:")
    print(f"  task_id: {task.task_id}")
    print(f"  type: {task.task_type}")
    print(f"  title: {task.title}")
    print(f"  internal due_date: {task.due_date}")
    print(f"  status: {task.status}")
    print("\nDone.")


if __name__ == "__main__":
    main()
