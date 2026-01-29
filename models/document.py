import uuid
from datetime import datetime


class Document:
    def __init__(self):
        self.document_id = str(uuid.uuid4())   # 內部文件識別
        self.case_id = None                    # 歸屬哪一個 Case（關聯用）

        # 來源與性質
        self.source = None                     # OFFICE / AGENT / CLIENT / INTERNAL
        self.document_type = None              # OA / GAZETTE / RECEIPT / NOTICE ...
        
        # 時間
        self.received_date = None              # 文件實際收到日（docketing 核心）
        self.created_at = datetime.now()       # 系統建立時間
        
        # 外部識別
        self.external_reference = None         # 公告號、官方文件號、信件編號等
        
        # 顯示與內容
        self.title = None                      # 顯示用標題
        self.file_path = None                  # 檔案位置（或 URL）
        self.raw_text = None                   # 原始文字（給 parser / AI 用）
        
        # 狀態
        self.status = "NEW"                    # NEW / PARSED / ARCHIVED
