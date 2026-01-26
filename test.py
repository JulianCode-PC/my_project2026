#!/usr/bin/env python3
"""
Minimal OA Analyzer (single-file MVP)

What it does (PPT-level):
1) "OCR/Extract text" from a PDF (text-based PDFs supported via PyPDF2)
2) Classify whether it's an Office Action (OA)
3) Extract a mailing date (best-effort) and compute a due date (default +3 months)
4) Produce a short issues summary + next-step plan
5) Output a single JSON result (good for demo + PPT screenshots)

Limitations:
- If the PDF is scanned (no embedded text), PyPDF2 may return empty text.
  In that case we still run classification but results may be poor.
- Date/Deadline rules differ by jurisdiction and OA type; this is an MVP heuristic.

Usage:
  python oa_mvp.py input.pdf
  python oa_mvp.py input.pdf --out result.json
  python oa_mvp.py input.pdf --months 3
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import List, Optional, Tuple

# --- Optional deps ---
try:
    from PyPDF2 import PdfReader  # type: ignore
except Exception as e:
    PdfReader = None

try:
    from dateutil.relativedelta import relativedelta  # type: ignore
except Exception:
    relativedelta = None


# -------------------------
# Data objects (ultra-min)
# -------------------------

@dataclass
class InputDocument:
    doc_id: str
    file_name: str
    file_path: str
    file_uri: str
    received_at: str
    ocr_text: str
    ocr_confidence: Optional[float] = None
    status: str = "analyzed"


@dataclass
class OARecord:
    oa_id: str
    doc_id: str
    is_oa: bool
    oa_type: str  # non_final / final / unknown
    mailing_date: Optional[str]
    due_date: Optional[str]
    issues_summary: List[str]
    confidence: Optional[float] = None
    case_ref: Optional[str] = None  # optional placeholder (future Case)


@dataclass
class NextStepPlan:
    plan_id: str
    oa_id: str
    recommended_path: str  # argue / amend / need_more_info
    action_items: List[str]
    required_inputs: List[str]
    risk_note: str
    created_at: str


@dataclass
class OAResult:
    input_document: InputDocument
    oa_record: OARecord
    next_step_plan: NextStepPlan


# -------------------------
# Helpers
# -------------------------

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def simple_id(prefix: str, base: str) -> str:
    # deterministic-ish id for demos
    base_clean = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    if not base_clean:
        base_clean = "x"
    return f"{prefix}_{base_clean[:40]}"


def extract_text_from_pdf(path: str) -> str:
    if PdfReader is None:
        raise RuntimeError("PyPDF2 is not installed. Install with: pip install PyPDF2")

    reader = PdfReader(path)
    parts: List[str] = []
    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        # normalize whitespace but keep some line breaks
        t = re.sub(r"\r", "\n", t)
        parts.append(t)
    text = "\n\n".join(parts)
    # lightly normalize
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def classify_is_oa(text: str) -> Tuple[bool, float]:
    """
    Heuristic OA classifier.
    """
    if not text:
        return False, 0.2

    t = text.lower()

    signals = [
        ("office action", 2.0),
        ("non-final", 1.0),
        ("final", 0.8),
        ("rejection", 0.8),
        ("claims", 0.5),
        ("35 u.s.c.", 1.2),
        ("102", 0.6),
        ("103", 0.6),
        ("112", 0.6),
        ("time period for reply", 1.5),
        ("reply is required", 1.0),
    ]

    score = 0.0
    for s, w in signals:
        if s in t:
            score += w

    # normalize to 0..1-ish
    conf = max(0.0, min(1.0, score / 6.0))
    is_oa = conf >= 0.35  # MVP threshold

    return is_oa, conf


def classify_oa_type(text: str) -> str:
    if not text:
        return "unknown"
    t = text.lower()
    # simplistic
    if "non-final" in t or "nonfinal" in t:
        return "non_final"
    if "final" in t and "non-final" not in t and "nonfinal" not in t:
        return "final"
    return "unknown"


_DATE_PATTERNS = [
    # MM/DD/YYYY or M/D/YYYY
    r"\b(?P<m>\d{1,2})/(?P<d>\d{1,2})/(?P<y>\d{4})\b",
    # YYYY-MM-DD
    r"\b(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})\b",
    # Month DD, YYYY
    r"\b(?P<mon>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+(?P<d>\d{1,2}),\s*(?P<y>\d{4})\b",
]

_MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

def _parse_date_match(m: re.Match) -> Optional[date]:
    gd = m.groupdict()
    try:
        if gd.get("mon"):
            mon = gd["mon"].lower()
            mon = mon.replace("sept", "sep")
            mm = _MONTH_MAP[mon]
            dd = int(gd["d"])
            yy = int(gd["y"])
            return date(yy, mm, dd)
        yy = int(gd["y"])
        mm = int(gd["m"])
        dd = int(gd["d"])
        return date(yy, mm, dd)
    except Exception:
        return None


def extract_mailing_date(text: str) -> Optional[date]:
    """
    Best-effort:
    Prefer dates near common labels like "Mail Date", "Mailed", "Notification Date", etc.
    Fall back to earliest plausible date in the document.
    """
    if not text:
        return None

    # 1) Look near labels
    label_windows = [
        r"mail(?:ing)?\s+date",
        r"mailed",
        r"notification\s+date",
        r"date\s+mailed",
        r"date:",
    ]
    lowered = text.lower()

    # Create windows around labels (±250 chars) and search dates there
    for label in label_windows:
        for lm in re.finditer(label, lowered):
            start = max(0, lm.start() - 250)
            end = min(len(text), lm.end() + 250)
            chunk = text[start:end]
            d = _find_first_date(chunk)
            if d:
                return d

    # 2) fallback: first date anywhere (often appears on header)
    return _find_first_date(text)


def _find_first_date(text: str) -> Optional[date]:
    candidates: List[Tuple[int, date]] = []
    for pat in _DATE_PATTERNS:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            d = _parse_date_match(m)
            if d:
                # store position to pick earliest appearance
                candidates.append((m.start(), d))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def add_months(base: date, months: int) -> date:
    if relativedelta is None:
        # fallback: crude month addition (not perfect)
        y = base.year
        m = base.month + months
        d = base.day
        while m > 12:
            y += 1
            m -= 12
        # clamp day
        import calendar
        last = calendar.monthrange(y, m)[1]
        d = min(d, last)
        return date(y, m, d)
    return base + relativedelta(months=months)


def compute_due_date(mailing: Optional[date], received_at: str, months: int) -> Tuple[Optional[date], str]:
    """
    MVP rule:
    - If mailing_date exists: due = mailing_date + months
    - else: due = received_at_date + months, but mark as unknown basis
    """
    basis = "mailing_date"
    base = mailing
    if base is None:
        basis = "received_at"
        try:
            base = datetime.fromisoformat(received_at).date()
        except Exception:
            return None, "unknown"
    return add_months(base, months), basis


def extract_issues_summary(text: str, max_items: int = 5) -> List[str]:
    """
    Heuristic bullets for PPT:
    - detect 102/103/112 mentions
    - detect 'claims X are rejected'
    - detect 'prior art' citations patterns
    """
    if not text:
        return ["No text extracted (scanned PDF or OCR missing)."]

    bullets: List[str] = []
    t = text

    # Claims rejected lines
    claim_lines = re.findall(r"(claims?\s+[\d,\-\s]+?\s+(?:is|are)\s+rejected[^.\n]*)", t, flags=re.IGNORECASE)
    for line in claim_lines[:2]:
        bullets.append(_clean_bullet(line))

    # Grounds
    grounds = []
    for g in ["102", "103", "112"]:
        if re.search(rf"\b{g}\b", t):
            grounds.append(g)
    if grounds:
        bullets.append(f"Possible statutory grounds mentioned: {', '.join(grounds)}.")

    # "35 U.S.C." lines
    usc = re.findall(r"(35\s+u\.?s\.?c\.?\s*§?\s*\d+[^.\n]*)", t, flags=re.IGNORECASE)
    if usc:
        bullets.append(_clean_bullet(usc[0]))

    # Prior art refs (very rough): e.g., "Smith et al." or "US 8,123,456"
    pa_pat = r"\bUS\s*\d{1,2}[, ]?\d{3}[, ]?\d{3}\b|\b\d{1,2},\d{3},\d{3}\b"
    pa = re.findall(pa_pat, t)
    if pa:
        uniq = []
        for x in pa:
            x = re.sub(r"\s+", " ", x).strip()
            if x not in uniq:
                uniq.append(x)
        bullets.append(f"Cited references detected (partial): {', '.join(uniq[:3])}{'…' if len(uniq)>3 else ''}")

    if not bullets:
        bullets.append("OA detected but no clear rejection lines found; needs human review.")

    return bullets[:max_items]


def _clean_bullet(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    if len(s) > 180:
        s = s[:177].rstrip() + "…"
    return s


def recommend_next_steps(is_oa: bool, oa_type: str, mailing_date: Optional[date]) -> Tuple[str, List[str], List[str], str]:
    """
    Very coarse strategy suggestions for PPT/demo.
    """
    if not is_oa:
        return (
            "need_more_info",
            ["Confirm document type manually (system confidence low)."],
            ["Original PDF", "Any cover letter / transmittal metadata"],
            "Document may not be an Office Action; verify classification."
        )

    action_items = [
        "Confirm mailing/notification date and response deadline.",
        "Identify rejected claims and map each rejection to claim elements.",
        "Collect cited references and compare against specification/claims.",
    ]
    required_inputs = [
        "Current claims set (latest filed claims)",
        "Specification / drawings",
        "Prior art / cited references (if not in OA PDF)",
        "Client goals (broad coverage vs quick allowance)",
    ]

    # pick path
    if oa_type == "final":
        path = "need_more_info"
        action_items.insert(1, "Decide whether to amend, appeal, request continued examination (RCE), or interview examiner.")
        risk = "Final OA detected; response strategy may require additional procedural choices."
    else:
        path = "amend"
        action_items.insert(1, "Draft amendment options (narrowing vs minimal changes) and/or argument outline.")
        risk = "Non-final/unknown OA; choose argue vs amend after reviewing grounds."

    if mailing_date is None:
        risk = "Mailing date not confidently extracted; deadline may be inaccurate until confirmed."

    return path, action_items, required_inputs, risk


def build_result(pdf_path: str, months: int, case_ref: Optional[str]) -> OAResult:
    file_name = pdf_path.split("/")[-1]
    doc_id = simple_id("doc", file_name)
    received = now_iso()

    text = extract_text_from_pdf(pdf_path)
    # For scanned PDFs, this may be empty. We'll still proceed.

    input_doc = InputDocument(
        doc_id=doc_id,
        file_name=file_name,
        file_path=pdf_path,
        file_uri=pdf_path,  # simple local demo
        received_at=received,
        ocr_text=text,
        ocr_confidence=None,
        status="analyzed",
    )

    is_oa, conf = classify_is_oa(text)
    oa_type = classify_oa_type(text)
    mailing = extract_mailing_date(text) if is_oa else None

    due_dt, basis = compute_due_date(mailing, received, months)
    issues = extract_issues_summary(text)

    oa_id = simple_id("oa", file_name)
    oa_rec = OARecord(
        oa_id=oa_id,
        doc_id=doc_id,
        is_oa=is_oa,
        oa_type=oa_type,
        mailing_date=mailing.isoformat() if mailing else None,
        due_date=due_dt.isoformat() if due_dt else None,
        issues_summary=issues,
        confidence=conf,
        case_ref=case_ref,
    )

    path, items, reqs, risk = recommend_next_steps(is_oa, oa_type, mailing)

    # Add a small deadline note if we used received_at as basis
    if is_oa and basis != "mailing_date":
        risk = f"{risk} (Due date computed using {basis} as fallback.)"

    plan = NextStepPlan(
        plan_id=simple_id("plan", file_name),
        oa_id=oa_id,
        recommended_path=path,
        action_items=items,
        required_inputs=reqs,
        risk_note=risk,
        created_at=now_iso(),
    )

    return OAResult(input_document=input_doc, oa_record=oa_rec, next_step_plan=plan)


def main() -> int:
    ap = argparse.ArgumentParser(description="Minimal OA Analyzer (single-file MVP)")
    ap.add_argument("pdf", help="Path to OA PDF")
    ap.add_argument("--out", default="", help="Output JSON path (optional)")
    ap.add_argument("--months", type=int, default=3, help="Default response period in months (MVP)")
    ap.add_argument("--case-ref", default=None, help="Optional placeholder for case reference/name")
    args = ap.parse_args()

    try:
        res = build_result(args.pdf, args.months, args.case_ref)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    payload = asdict(res)
    s = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(s)
        print(f"[OK] Wrote: {args.out}")
    else:
        print(s)

    # Friendly hint if likely scanned PDF
    if not res.input_document.ocr_text:
        print(
            "\n[NOTE] No embedded text extracted. If this is a scanned PDF, "
            "add an OCR step (e.g., pytesseract) or use a PDF OCR service.",
            file=sys.stderr
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
