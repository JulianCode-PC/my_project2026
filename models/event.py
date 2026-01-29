import uuid
from datetime import datetime


class Event:
    def __init__(self):
        self.event_id = str(uuid.uuid4())     # 內部事件識別
        self.case_id = None                   # 歸屬案件
        self.document_id = None               # 由哪份 Document 觸發（可為 None，例如人工建立）

        self.event_type = None                # 例：OA_RECEIVED / GRANT_PUBLISHED / FILING_RECEIPT_RECEIVED
        self.event_date = None                # 事件發生日（通常等於文件日期或收到日）
        self.created_at = datetime.now()      # 系統建立時間

        self.description = None               # 人類可讀描述（optional）
        self.status = "OPEN"                  # OPEN / CLOSED / VOID
        self.metadata = {}                    # 存 parser 產出的額外資訊（例如 OA 種類、局方欄位）
