import os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # 切換至根目錄
sys.path.append(os.path.join(os.getcwd(), 'RAG_ETL')) # 修正匯入路徑

# 匯入我們先前寫好的模組功能
from batch_read_pdf import batch_process_manuals
from batch_chunk_text import create_chunks_with_metadata
from vector_storage import save_to_vector_db

def start_pipeline():
    print("啟動 RAG 資料處理流水線...")
    
    # 1. Extract (提取)：讀取 Data 資料夾下的所有 PDF
    raw_data = batch_process_manuals("Data")
    if not raw_data:
        print("錯誤：在 Data 資料夾中找不到 PDF 檔案。")
        return

    # 2. Transform (轉換)：將長文切塊並貼上 Metadata
    print(f"\n正在對 {len(raw_data)} 份文件進行切塊處理...")
    processed_chunks = create_chunks_with_metadata(raw_data)
    print(f"轉換完成，共產生 {len(processed_chunks)} 個知識碎片。")

    # 3. Load (載入)：存入 ChromaDB 向量資料庫
    print("\n正在將數據載入向量資料庫 (包含向量化運算)...")
    save_to_vector_db(processed_chunks)
    
    print("\n全自動化 Pipeline 執行完畢！你的 PLC 知識庫已準備就緒。")

if __name__ == "__main__":
    start_pipeline()