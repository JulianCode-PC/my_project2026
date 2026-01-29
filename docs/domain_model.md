# Domain Model

## Case
- 說明：代表一件專利案件
- 責任：容納文件、事件、期限與任務

Case 不會「變成」Document / Event / Task
Case 是「把它們收在同一個籃子裡」

「容納」是關聯與歸屬。Case負責說清楚：這些東西「屬於同一件專利案」


📁 想像一個事務所的「實體案件資料夾」

Case = 資料夾本身

Document = 裡面的文件

Event = 文件造成的程序狀態（貼在文件上的便條）

Deadline = 資料夾上貼的紅色期限標籤

Task = 夾在裡面的待辦清單

👉 資料夾沒有變成文件
👉 但所有文件都「屬於這個資料夾」


## Document
- 說明：外部或內部文件
- 來源：局方 / 代理人 / 客戶

要知道自己是什麼文件，知道從哪來，什麼時候進來，知道外部怎麼稱呼我


## Event
- 說明：Document 被理解後的程序事件
- 例子：OA_RECEIVED

## Deadline
- 說明：Event 產生的法定時間義務

## Task
- 說明：為回應 Event/Deadline 所需的行動


Case

1 ── N Document

1 ── N Event

1 ── N Deadline

1 ── N Task



## Lifecycle / Flow

- Document → 產生 Event  
- Event → 產生 Deadline  
- Event / Deadline → 產生 Task（工作包）

總結：

「Document 是輸入，Event 是理解後的程序節點，  
Deadline 是法定義務，Task 是行動。」

