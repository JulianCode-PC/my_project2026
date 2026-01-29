import uuid
from datetime import datetime


class Task:
    def __init__(self):
        self.task_id = str(uuid.uuid4())      # 內部任務識別
        self.case_id = None                   # 歸屬案件
        self.event_id = None                  # 這個 task 是回應哪個事件（可選）
        self.deadline_id = None               # 這個 task 主要對應哪個期限（可選）

        self.task_type = None                 # 例：DRAFT_OA_RESPONSE / REVIEW / FILE_RESPONSE / PAY_FEE
        self.title = None                     # 顯示用標題
        self.description = None               # 任務細節
        
        self.assignee = None                  # 指派給誰（先用字串即可）
        self.priority = "NORMAL"              # LOW / NORMAL / HIGH / URGENT
        
        self.created_at = datetime.now()
        self.due_date = None                  # 工作內部期限（可等於 deadline due date 或更早）
        self.status = "TODO"                  # TODO / DOING / DONE / CANCELLED / BLOCKED
        
        self.metadata = {}                    # 任務表單欄位、交付物連結等
