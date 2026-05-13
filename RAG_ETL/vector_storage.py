import os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # 切換至根目錄
sys.path.append(os.path.join(os.getcwd(), 'RAG_ETL')) # 修正匯入路徑

import chromadb
from chromadb.utils import embedding_functions


def save_to_vector_db(processed_chunks):
    """
    將切好的知識片段存入向量資料庫。
    processed_chunks: 格式為 [{'content': '...', 'metadata': {...}}, ...]
    """
    
    # 1. 初始化資料庫存放位置 (就像 SQLite，這會在你的專案下建立一個資料夾)
    # 這裡的 path "./my_fatek_db" 就是資料庫檔案存放的路徑
    client = chromadb.PersistentClient(path=os.path.join(".","my_fatek_db"))

    # 2. 設定 Embedding Model (這就是「翻譯官」，負責把文字轉成數字座標)
    # model_name 必須支援中文，這裡選用業界常用的多國語言模型
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )

    # 3. 建立或取得一個 Collection (這對應 SQL 的 Table)
    # name="plc_manuals" 就是 Table Name
    # 先刪除資料表，再新增空的資料表，確保資料表不會有舊的資料
    try:
        # 如果表已經存在，就先刪除它
        client.delete_collection(name="plc_manuals")
        print("已清理舊的資料庫表 'plc_manuals'")
    except:
        # 如果表本來就不存在，會噴錯，我們直接忽略它即可
        pass
    # 接著再建立新表
    collection = client.get_or_create_collection(name="plc_manuals", embedding_function=emb_fn)

    # 4. 準備寫入資料 (ChromaDB 要求將欄位拆開傳入)
    # 使用列表推導式 (List Comprehension) 提取資料，類似 Java 的 Stream map
    ids = [f"id_{i}" for i in range(len(processed_chunks))]
    documents = [c["content"] for c in processed_chunks]
    metadatas = [c["metadata"] for c in processed_chunks]

    # 5. 執行寫入 (這就是 SQL 的 INSERT)
    # add 方法會自動呼叫 emb_fn 幫你算好向量並存檔
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    
    print(f"--- 載入完成 ---")
    print(f"成功將 {len(documents)} 筆片段存入向量資料庫 'plc_manuals'")

if __name__ == "__main__":
    # 1. 準備測試資料
    test_data = [
        {
            "content": "永宏 FBs 系列 PLC 具備高速計數功能。",
            "metadata": {"source": "test.pdf", "path": "D:/test.pdf"}
        }
    ]
    
    # 2. 執行儲存 (這會觸發你的刪除舊表邏輯)
    save_to_vector_db(test_data)

    # 3. 立即進行查詢驗證
    print("\n--- 開始查詢驗證 ---")
    client = chromadb.PersistentClient(path=os.path.join(".", "my_fatek_db"))
    
    # 注意：這裡不需要再傳入 embedding_function，因為我們只是要讀取既有的 collection
    collection = client.get_collection(name="plc_manuals")
    
    # 取得目前資料庫內所有的資料
    results = collection.get()
    
    print(f"目前資料庫內的總筆數: {len(results['ids'])}")
    
    if len(results['ids']) > 0:
        print(f"第一筆索引: {results['ids'][0]}")
        print(f"第一筆內容: {results['documents'][0]}")
        print(f"第一筆元數據: {results['metadatas'][0]}")
    
    # 4. 驗證重複性
    if len(results['ids']) == 1:
        print("\n驗證成功：資料庫已清空並重新寫入，目前只有最新的一筆資料。")
    else:
        print(f"\n警告：資料庫內有 {len(results['ids'])} 筆資料，代表舊資料未刪除乾淨。")