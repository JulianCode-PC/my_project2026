import pymupdf

'''
拿到一行程式 只用一個表格回答：

這行的輸入是什麼型別？ 在記憶體裡是什麼資料種類？

這行做了什麼轉換？是「呼叫方法」？「運算」？「轉型」

輸出變成什麼型別？結果現在是什麼？


🚫 這三步會幫你擋掉什麼？

❌ API 設計哲學
❌ 背景原理
❌ 歷史原因
❌ 內部實作

這些都是等要優化或出問題時才看的。


程式語言其實有兩個「腦模式」
| 模式          | 問的問題      | 什麼時候用        |
| ----------- | --------- | ------------ |
| 🧩 **機械模式** | 這行資料怎麼變形？ | 卡住、除錯、看不懂語法時 |
| 🧠 **理解模式** | 為什麼要這樣寫？  | 功能已經能跑、想變強時  |


'''


#open()讓檔案變成"可以被操作的物件"，因為原本他只是一串二位元資料
doc = pymupdf.open("streaming.pdf") #要雙引號表示字串

'''
讀取硬碟上的 PDF
解析 PDF 結構（頁面、字型、圖片、metadata…）
建立一個 Document 類別的實例，且把這個實例交給變數 doc
'''

#在此的open()是python內建的函式，可以開啟檔案、指定開檔案的mode, "wb"表示開啟一個可以寫入的二進位檔案, w是寫入模式
out = open("output.txt", "wb") # create a text output file 


#PyMuPDF 的 Document 物件實作了「可迭代協定」，因此可以直接用 for 迴圈來逐頁讀取 PDF，doc 看起來不像 list，但它「行為像 list」
for page in doc:
    #先從page物件取得文字內容，再用encode("utf8")把字串轉成utf8編碼的位元組(bytes)
    text = page.get_text().encode("utf8") 
    
    
    '''
        | 步驟   | 正確答案                   |
        | ---- | ---------------------- |
        | 輸入型別 | `str` 或 `bytes`（看檔案模式） |
        | 轉換   | 無                      |
        | 輸出   | 資料被寫入磁碟檔案              |

    
    '''

    out.write(text) # write text of page
    
    '''
        | 步驟   | 答案           |
        | ---- | ------------ |
        | 輸入型別 | `bytes`      |
        | 轉換   | 無            |
        | 輸出   | `0x0C` 被寫入檔案 |

    '''
    
    out.write(bytes((12,))) # write page delimiter (form feed 0x0C)



out.close()

