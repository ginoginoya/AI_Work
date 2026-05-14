from fastapi import FastAPI, Query # 從 fastapi 套件匯入主程式類別與查詢參數類別
from fastapi.middleware.cors import CORSMiddleware # 匯入跨來源資源共享 (CORS) 中間件，處理網頁安全性限制
from fastapi.staticfiles import StaticFiles # 匯入處理靜態檔案（如 HTML, CSS, JS）掛載的類別

import os # 匯入系統作業相關模組（路徑處理、環境變數）
import chromadb # 匯入向量資料庫 ChromaDB 模組
import requests # 匯入 HTTP 請求模組，用來與外部 AI 伺服器溝通
import subprocess # 匯入子程序模組，可用於執行系統指令（目前保留備用）
from chromadb.utils import embedding_functions # 從 ChromaDB 匯入嵌入向量產生函數的工具
from fastapi.responses import HTMLResponse, RedirectResponse # 匯入 FastAPI 的網頁與跳轉回應類別
from dotenv import load_dotenv # 匯入讀取 .env 環境變數檔案的工具

# 讀取當前目錄下的 .env 檔案並將設定值載入到系統環境變數中
load_dotenv() 

# 建立 FastAPI 應用程式實例
app = FastAPI() 

# --- 1. CORS 設定：允許前端 HTML 透過瀏覽器跨來源訪問 API ---
app.add_middleware(
    CORSMiddleware, # 使用 CORS 中間件
    allow_origins=["*"], # 允許所有來源 (Origins) 的請求，方便面試與測試展示
    allow_methods=["*"], # 允許所有 HTTP 方法 (GET, POST, 等)
    allow_headers=["*"], # 允許所有的 HTTP 標頭 (Headers)
)

# --- 2. 初始化 ChromaDB 向量資料庫 ---
client = chromadb.PersistentClient(path=os.path.join(".", "my_fatek_db")) # 建立或連接到本地的向量資料庫資料夾
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction( # 初始化文本轉向量的模型
    model_name="paraphrase-multilingual-MiniLM-L12-v2" # 使用支援多國語言的 MiniLM 模型
)
# 從資料庫中取得指定的資料集 (Collection)，並套用向量轉換函數
collection = client.get_collection(name=os.getenv("COLLECTION_NAME", "plc_manuals"), embedding_function=emb_fn) 

# 從環境變數讀取 AI 模型的 API 地址，預設為本地 LM Studio 地址
LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:1234/v1/chat/completions") 
LLM_MODEL = os.getenv("LLM_MODEL_NAME", "gemma-4-e4b-it-text-only") # 從環境變數讀取要使用的 AI 模型名稱

# 定義呼叫 AI 模型生成回答的函式
# user_query:使用者輸入的問題
# context_fragments:從ChromaDB檢索出的相關手冊片段
# history:對話歷史(目前未開放功能)
def call_llm(user_query, context_fragments, history=None): 
    system_prompt = """
你是一位專精於永宏 (Fatek) FBs 系列 PLC 的技術支援工程師。
請根據下方提供的『手冊片段』內容，用專業且簡潔的中文回答使用者的問題。
規則：
1. 相關性檢查：如果使用者的問題與 PLC 技術、編程或手冊內容無關，請禮貌地告知無法回答，並且「絕對不要」提供任何參考來源或路徑。
2. 當你根據手冊內容回答時，請註明參考來源，並列出完整路徑。
3. 保持客觀。
4. 請直接使用普通文字與符號描述數值與單位（例如 100~240V），禁止使用 LaTeX 或 $ 符號包裹的數學公式格式。
""".strip() # 定義 AI 的角色與回話規範。.strip() 是為了刪除字串前後多餘的空格或換行。

    # 組裝發送給 AI 的 Prompt 內容，包含完整路徑、手冊內容、對話歷史紀錄與目前問題
    context_text = "\n\n".join([f"--- 來源: {frag['path']} ---\n{frag['content']}" for frag in context_fragments]) 
    prompt_content = f"【手冊片段】：\n{context_text}\n\n" 
    if history: # 如果有過去的對話歷史，也一併加入
        prompt_content += f"【對話上下文】：\n{history}\n\n" 
    prompt_content += f"【目前問題】：\n{user_query}" 

    # 準備發送給 AI 伺服器的 JSON 資料
    payload = { 
        "model": LLM_MODEL, # 使用全域變數中設定的模型名稱，是字串格式
        "messages": [ # 對話訊息列表
            {"role": "system", "content": system_prompt}, # 傳入系統指令
            {"role": "user", "content": prompt_content} # 傳入使用者問題與背景
        ],
        "temperature": 0.1 # 設定亂數程度，越低代表回答越精確、不胡扯
    }
    try: # 嘗試執行 HTTP 請求
        response = requests.post(LLM_API_URL, json=payload, timeout=60) # 發送 POST 請求到 AI 伺服器
        response.raise_for_status() # 如果 HTTP 狀態碼不是 200，會拋出例外，raise在這裡是拋出的意思，不是舉起來的意思
        # 回傳 AI 生成的文字內容，此內容為純文字，其中choices是一維陣列，message是一個字典，content也是一個字典，其值是字串
        return response.json()['choices'][0]['message']['content']
    except Exception as e: # 如果連線或處理出錯
        return f"AI 服務連線失敗: {str(e)}" # 回傳錯誤訊息

# --- 3. API 路由定義 ---

@app.get("/ask") # 定義一個 GET 類型的 API 路徑 "/ask"
def ask_question(query: str = Query(..., title="搜尋問題"), # 接收 query 參數，並設定標題
                 history: str = Query(None, title="對話歷史")): # 接收可選的 history 參數
    """
    API 入口：使用 query 搜尋，並將搜尋結果與 history 一併交由 AI 生成回答
    """
    # 1. 向 ChromaDB 檢索最相關的 50 個手冊片段
    results = collection.query(query_texts=[query], n_results=50, include=["documents", "metadatas", "distances"]) 
    THRESHOLD = 0.7 # 設定相似度閾值（距離越短越相似）
    
    # 整理檢索結果，只過濾出距離小於等於閾值的內容
    formatted_results = [ 
        {
            "content": doc, # 片段內容
            # .get("key", default) 意思是：嘗試抓取 key，抓不到就回傳 default，避免直接用 [key] 抓不到時會導致伺服器當機 (KeyError)
            "filename": meta.get("filename", "未知檔案"), # 來源檔案名稱 (安全抓取，避免資料缺失報錯)
            "path": meta.get("path", ""), # 檔案相對路徑 (安全抓取，避免資料缺失報錯)
            "score": round(dist, 4) # 相似度分數
        }
        # documents, metadatas, distances 各自原始是二維陣列，
        # 因為 query_texts 是一維陣列，長度為1，唯一的資料是query_texts[0]=query
        # 所以結果只會放在documents, metadatas, distances各自的[0]中
        # 又因為 n_results=50，所以，documents[0], metadatas[0], distances[0]這將會是長度50的一維陣列
        for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
        if dist <= THRESHOLD # 過濾掉不相關的結果
    ]
    
    # 2. 生成最終答案 (將搜尋結果與對話歷史一併傳給 LLM 函式)
    if not formatted_results and not history: # 如果沒搜到資料且沒歷史紀錄
        final_answer = "抱歉，找不到相關資訊。" # 直接告知找不到
    else: # 否則請 AI 根據資料回答
        final_answer = call_llm(query, formatted_results, history) # 搜尋結果是字串格式
    
    return { # 回傳最終 JSON 結果給前端
        "ai_answer": final_answer, # 供給聊天介面顯示
        "references": formatted_results # 供給參考來源顯示
    }

# 新增：讓前端可以請求後端開啟本地 PDF 檔案的功能
@app.get("/open-pdf") 
def open_pdf(path: str = Query(..., 
                               title="PDF 檔案相對路徑", 
                               description="傳入由 ChromaDB 檢索出的 path 欄位，系統將自動轉換為絕對路徑並開啟檔案")):
    """
    透過伺服器主機的作業系統開啟指定路徑的 PDF 檔案
    """
    try:
        abs_path = os.path.abspath(path) # 將相對路徑轉換為電腦上的完整絕對路徑
        
        if not os.path.exists(abs_path): # 檢查該檔案是否真的存在
            return {"status": "error", "message": "找不到檔案路徑"}
            
        os.startfile(abs_path) # 調用 Windows 的「開啟檔案」預設程式
        return {"status": "success", "message": f"已開啟 {abs_path}"} # 回傳成功訊息
    except Exception as e: # 若發生權限或系統錯誤
        return {"status": "error", "message": str(e)} # 回傳錯誤原因

# --- 4. 專業檔案瀏覽功能：自定義靜態檔案類別以支援目錄清單 ---
class AutoIndexStaticFiles(StaticFiles): 
    async def get_response(self, path: str, scope): # 複寫獲取回應的方法
        full_path = os.path.join(self.directory, path) # 拼湊出完整路徑
        if os.path.isdir(full_path): # 如果使用者要求的是一個目錄而非檔案
            # 產生該目錄下所有檔案的超連結列表
            links = "".join([f'<li><a href="{fd}/">{fd}</a></li>' for fd in os.listdir(full_path)]) 
            return HTMLResponse(f"<ul>{links}</ul>") # 回傳 HTML 格式的目錄清單
        return await super().get_response(path, scope) # 若是檔案，則使用原本的靜態檔案處理邏輯

# 新增：處理使用者進入 /doc 沒加結尾斜線時的情況
@app.get("/doc") 
async def doc_redirect(): 
    return RedirectResponse(url="/doc/") # 強制導向到 /doc/ 以確保路徑正確

# 將 AutoIndex 功能掛載到 /doc 路徑下，指向專案根目錄
app.mount("/doc", AutoIndexStaticFiles(directory="."), name="doc") 

# --- 5. 靜態檔案掛載：讓外部裝置（如 iPad）能讀取前端網頁與 PDF ---

# 掛載 pdf_view，讓 http://ip:8000/pdf_view/Data/xxx.pdf 可以被讀取
app.mount("/pdf_view", StaticFiles(directory="."), name="pdf_view") 

# 最後掛載根目錄，當存取 http://ip:8000/ 時，預設會找 index.html
app.mount("/", StaticFiles(directory=".", html=True), name="static") 

