from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware # 新增：處理跨來源請求
from fastapi.staticfiles import StaticFiles # 新增：處理靜態檔案掛載

import os
import chromadb
import requests
import subprocess # 新增：用於執行系統指令，目前僅保留未使用
from chromadb.utils import embedding_functions
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse  # 加上 HTMLResponse

app = FastAPI()

# --- 1. CORS 設定：允許前端 HTML 訪問 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 面試展示用，允許所有來源
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. 初始化資料庫 ---
client = chromadb.PersistentClient(path=os.path.join(".", "my_fatek_db"))
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)
collection = client.get_collection(name="plc_manuals", embedding_function=emb_fn)

LLM_API_URL = "http://localhost:1234/v1/chat/completions"

def call_llm(user_query, context_fragments, history=None):
    context_text = "\n\n".join([f"--- 來源: {f['path']} ---\n{f['content']}" for f in context_fragments])
    system_prompt = """
你是一位專精於永宏 (Fatek) FBs 系列 PLC 的技術支援工程師。
請根據下方提供的『手冊片段』內容，用專業且簡潔的中文回答使用者的問題。
規則：
1. 相關性檢查：如果使用者的問題與 PLC 技術、編程或手冊內容無關，請禮貌地告知無法回答，並且「絕對不要」提供任何參考來源或路徑。
2. 當你根據手冊內容回答時，請註明參考來源，並列出完整路徑。
3. 保持客觀。
4. 請直接使用普通文字與符號描述數值與單位（例如 100~240V），禁止使用 LaTeX 或 $ 符號包裹的數學公式格式。
""".strip()

    # 組裝發送給 AI 的內容
    prompt_content = f"【手冊片段】：\n{context_text}\n\n"
    if history:
        prompt_content += f"【對話上下文】：\n{history}\n\n"
    prompt_content += f"【目前問題】：\n{user_query}"

    payload = {
        "model": "gemma-4-e4b-it-text-only",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_content}
        ],
        "temperature": 0.1
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI 服務連線失敗: {str(e)}"

# --- 3. API 路由 ---

@app.get("/ask")
def ask_question(query: str = Query(..., title="搜尋問題"), 
                 history: str = Query(None, title="對話歷史")):
    """
    API 入口：使用 query 搜尋，並將搜尋結果與 history 一併交由 AI 生成回答
    """
    # 1. 檢索 (只用最新的問題去搜尋，避免歷史訊息干擾搜尋準確度)
    results = collection.query(query_texts=[query], n_results=50, include=["documents", "metadatas", "distances"])
    THRESHOLD = 0.7
    formatted_results = []
    for i in range(len(results['ids'][0])):
        dist = results['distances'][0][i]
        if dist <= THRESHOLD:
            formatted_results.append({
                "content": results['documents'][0][i],
                "source": results['metadatas'][0][i]['source'],
                "path": results['metadatas'][0][i]['path'],
                "score": round(dist, 4)
            })
    
    # 2. 生成 (將搜尋結果與對話歷史一併傳給 LLM)
    # 如果完全沒搜到資料，且也沒有歷史對話作為參考，則直接回傳找不到
    if not formatted_results and not history:
        final_answer = "抱歉，找不到相關資訊。"
    else:
        final_answer = call_llm(query, formatted_results, history)
    
    return {
        "ai_answer": final_answer, 
        "references": formatted_results
    }

# 新增：點擊開啟 PDF 功能
@app.get("/open-pdf")
def open_pdf(path: str = Query(..., 
                               title="PDF 檔案相對路徑", 
                               description="傳入由 ChromaDB 檢索出的 path 欄位，系統將自動轉換為絕對路徑並開啟檔案")):
    """
    透過作業系統開啟指定路徑的 PDF 檔案
    """
    try:
        # 取得絕對路徑
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            # Windows 指令：使用預設程式開啟檔案
            os.startfile(abs_path)
            return {"status": "success", "message": f"已開啟 {abs_path}"}
        else:
            return {"status": "error", "message": "找不到檔案路徑"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 4. 專業檔案瀏覽功能 (Auto-Index 極簡版) ---
class AutoIndexStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        full_path = os.path.join(self.directory, path)
        if os.path.isdir(full_path):
            links = "".join([f'<li><a href="{f}/">{f}</a></li>' for f in os.listdir(full_path)])
            return HTMLResponse(f"<ul>{links}</ul>")
        return await super().get_response(path, scope)

# 新增：處理 /doc 沒加斜線的情況，自動補上斜線跳轉
@app.get("/doc")
async def doc_redirect():
    return RedirectResponse(url="/doc/")

# 掛載到 /doc 路徑
app.mount("/doc", AutoIndexStaticFiles(directory="."), name="doc")

# --- 4. 靜態檔案掛載 (讓 iPad 可以看到前端與 PDF) ---
# 將 pdf_view 掛載到根目錄 "."，確保傳入的 Data/xxx.pdf 路徑能正確對應
app.mount("/pdf_view", StaticFiles(directory="."), name="pdf_view")

# 最後掛載根目錄，提供 index.html, script.js, style.css 等前端檔案
# html=True 代表預設會尋找 index.html
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # host 設為 "0.0.0.0" 才能接受來自 Tailscale 的連線
    print("正在啟動伺服器，iPad 請連線至 http://100.99.48.61:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
