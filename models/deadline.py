import uuid
from datetime import datetime


class Deadline:
    def __init__(self):
        self.deadline_id = str(uuid.uuid4())  # 內部期限識別
        self.case_id = None                   # 歸屬案件
        self.event_id = None                  # 由哪個 Event 產生

        self.deadline_type = None             # 例：OA_RESPONSE_DUE / ISSUE_FEE_DUE / APPEAL_DUE
        self.due_date = None                  # 到期日（核心）
        self.grace_due_date = None            # 緩衝/延長後到期日（可選）
        
        self.created_at = datetime.now()
        self.status = "PENDING"               # PENDING / MET / MISSED / CANCELLED
        
        self.rule_basis = None                # 法源/規則依據（可選：例如「OA 3 months」）
        self.metadata = {}                    # 計算過程、延長資訊、國別計算參數等
