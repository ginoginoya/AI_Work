import os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # 切換至根目錄
sys.path.append(os.path.join(os.getcwd(), 'RAG_ETL')) # 修正匯入路徑

import fitz  # PyMuPDF


def batch_process_manuals(base_path: str):
    all_data = [] # 用來存儲每一份文件的內容
    
    print(f"開始掃描資料夾：{base_path}")
    
    # os.walk 會遍歷路徑下的所有資料夾與檔案
    # root: 目前正在掃描的資料夾路徑 (字串)
    # dirs: 該路徑下所有的子資料夾名稱 (列表)
    # files: 該路徑下所有的檔案名稱 (列表)
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith(".pdf"):
                # 組合出完整的路徑
                full_path = os.path.join(root, file)
                print(f"正在處理：{full_path}")
                
                try:
                    doc = fitz.open(full_path) # 調用 PyMuPDF 庫開啟指定路徑的 PDF 文件，並將其內容讀入內存供後續處理
                    text = ""
                    for page in doc:
                        text += page.get_text()
                    
                    # 存成結構化的字典，方便以後知道這段話是從哪來的
                    all_data.append({
                        "content": text,
                        "filename": file,
                        "path": full_path
                    })

                    doc.close()
                except Exception as e:
                    print(f"讀取 {file} 失敗：{e}")
                    
    return all_data

if __name__ == "__main__":
    # 設定你的 Data 資料夾路徑
    data_folder = "Data" 
    
    results = batch_process_manuals(data_folder)
    
    print(f"\n--- 掃描完成 ---")
    print(f"共讀取了 {len(results)} 份 PDF 文件")
    
    # 測試：印出第一份文件的名稱與字數
    if results:
        print(f"第一份文件：{results[0]['filename']}")
        print(f"總字數：{len(results[0]['content'])} 字")
        print(f"\n--- 結構檢查 ---")
        print(f"資料型別: {type(results)}")
        print(f"第一筆資料的 Key: {results[0].keys()}")
        # 這裡很關鍵：我們印出前 100 個字，看看表格轉文字後有沒有變成亂碼
        print(f"內容範例: {results[0]['content'][:100]}")