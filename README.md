# Fatek PLC AI 助手 (RAG 系統)

這是一個基於 RAG (Retrieval-Augmented Generation) 技術的永宏 PLC 技術支援助手。它可以讀取 PDF 手冊內容，並透過本地 LLM 提供專業的技術問答。

---

## 🚀 快速上手步驟

### 1. 部署 Python 環境 (venv)
首先，確保你的電腦已安裝 Python 3.10 或以上版本。
在專案根目錄開啟終端機（或透過 `run_project.bat` 自動處理），手動步驟如下：
```powershell
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境 (Windows)
.\venv\Scripts\activate

# 安裝所需套件
pip install -r requirements.txt
```

### 2. 設定 LM Studio 環境
本專案依賴 LM Studio 提供 AI 推理服務：
1.  下載並安裝 [LM Studio](https://lmstudio.ai/)。
2.  在 LM Studio 中搜尋並下載 `gemma-4-e4b-it-text-only` 模組（或專案指定的相應模組）。
3.  切換至 **Local Server** 頁籤（左側雙箭頭圖示）。
4.  在上方選單選擇載入該模組。
5.  確保 **Port** 設定為 `1234`，然後點擊 **Start Server**。

### 3. 設定環境變數 (.env)
1.  將 `.env.example` 複製一份並重新命名為 `.env`。
2.  開啟 `.env` 檔案，確認其中的 `LLM_API_URL` 與 LM Studio 的設定一致。
3.  專案啟動時會自動讀取此檔案中的參數。

### 4. 準備知識庫資料 (PDF)
1.  在專案根目錄下建立一個名為 `Data` 的資料夾。
2.  將你所有的永宏 PLC 相關 PDF 手冊放入 `Data` 資料夾中。
3.  這些檔案將作為 AI 的知識來源。

### 4. 執行資料處理流水線 (ETL)
在啟動主程式前，必須先將 PDF 內容轉換為向量資料庫：
```powershell
python RAG_ETL/run_pipeline.py
```
*這會自動讀取 `Data` 資料夾、切割文字、並存入 `my_fatek_db` 向量資料庫中。*

### 5. 啟動專案
所有設定完成後，直接雙擊執行根目錄下的：
`run_project.bat`

系統會自動：
*   檢查 venv 環境。
*   嘗試載入 LM Studio 模組。
*   啟動 FastAPI 後端伺服器 (Port 8000)。
*   自動在瀏覽器開啟控制面板 `http://localhost:8000`。

---

## 📂 專案架構說明
*   `main.py`: FastAPI 後端主程式。
*   `RAG_ETL/`: 包含 PDF 讀取、文字切塊、向量儲存的腳本。
*   `Data/`: (需手動建立) 存放原始 PDF 手冊。
*   `my_fatek_db/`: 自動生成的向量資料庫儲存路徑。
*   `index.html / script.js / style.css`: 前端互動介面。

---

## 🛠️ 常見問題
*   **連線失敗**：請確認 LM Studio 的 Server 是否已啟動，且 Port 為 1234。
*   **找不到 PDF**：請確認 PDF 檔案是否放在 `Data` 資料夾內，且副檔名為小寫 `.pdf`。
*   **iPad 連線**：若要從 iPad 存取，請確保 iPad 與電腦在同一網路下（或使用 Tailscale），並連線至電腦的 IP 地址。
