#uuid 是 Python 內建模組
#用來產生「全世界幾乎不會重複的唯一識別碼」。
import uuid 


class Case:
    def __init__(self):
        self.case_id = str(uuid.uuid4()) #內部系統識別
        self.jurisdiction = None #專利局/管轄機關
        self.application_number = None #法律識別
        self.filing_date = None #申請日
        self.documents = [] #一個Case會有很多文件，用list
        self.events = [] 
        self.deadlines = [] #一個event會有多個狀態, 且Deadline有自己的狀態
        self.tasks = [] #法律義務跟工作職務分離

        


'''
class Case:
    def __init__(self):
        self.case_id = str(uuid.uuid4())  # 系統自己產
        #3f2c1d8a-9b6f-4c42-8c3e-2b8d9e7f91a1
        self.jurisdiction = None
        self.application_number = None
        self.filing_date = None

        self.documents = []
        self.events = []
        self.deadlines = []
        self.tasks = []
'''