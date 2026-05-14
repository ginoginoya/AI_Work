let currentController = null; // 用於儲存目前的 AbortController，以便中斷請求
let isContextMode = false; // 對話連貫模式開關

// 切換連貫對話模式
function toggleSettings() {
    isContextMode = !isContextMode;
    const btn = document.getElementById('settings-btn');
    if (isContextMode) {
        btn.innerText = "連貫對話：開";
        btn.style.background = "#28a745"; // 綠色
    } else {
        btn.innerText = "連貫對話：關";
        btn.style.background = "#6c757d"; // 灰色
    }
}

// 切換漢堡選單顯示/隱藏
function toggleMenu() {
    document.getElementById("dropdown-menu").classList.toggle("show");
}

// 點擊選單以外的地方自動關閉選單
window.addEventListener('click', function(event) { // 監聽整個視窗的點擊事件
    if (!event.target.closest('.menu-container')) { // 檢查點擊的目標是否不在選單容器及其子元素內
        const dropdowns = document.getElementsByClassName("dropdown-content"); // 取得頁面中所有的下拉選單內容
        for (let i = 0; i < dropdowns.length; i++) { // 遍歷每一個選單元素
            const openDropdown = dropdowns[i]; // 取得目前的選單物件
            if (openDropdown.classList.contains('show')) { // 判斷該選單目前是否正在顯示中 (帶有 show 類別)
                openDropdown.classList.remove('show'); // 如果正在顯示，則移除 show 類別將其隱藏
            }
        }
    }
});

// 定義停止等待的函式
function stopWaiting() {
    if (currentController) {
        currentController.abort(); // 中斷正在進行的 fetch 請求
        console.log("使用者手動中斷了 API 請求。");
    }
}

// 定義向後端發問的非同步函式
async function askQuestion() {
    const inputBase = document.getElementById('user-input'); // 取得輸入框物件
    const btn = document.getElementById('send-btn'); // 取得按鈕物件
    const stopBtn = document.getElementById('stop-btn'); // 取得停止按鈕物件
    const query = inputBase.value.trim(); // 取得輸入內容並修剪前後空白
    if (!query) return; // 如果內容為空則不執行

    // --- 鎖定 UI 並顯示等待狀態 ---
    inputBase.disabled = true;
    btn.disabled = true;
    stopBtn.style.display = 'inline-block'; // 顯示停止按鈕

    const history = document.getElementById('chat-history'); // 取得對話紀錄區域物件
    history.innerHTML += `<div class="message user-msg">${query}</div>`; // 將使用者問題插入畫面
    inputBase.value = ''; // 送出後清空輸入框內容

    // 插入「思考中」提示
    const loadingId = 'loading-' + Date.now();
    history.innerHTML += `<div id="${loadingId}" class="message ai-msg loading-dots">AI 正在思考中</div>`;
    
    history.scrollTop = history.scrollHeight - history.clientHeight; // 捲動到可見區域的最底部

    currentController = new AbortController(); // 初始化新的控制標記
    
    // --- 連貫對話邏輯：組裝歷史紀錄 ---
    let historyToSend = null;
    if (isContextMode) {
        const messages = document.querySelectorAll('#chat-history .message');
        let fullContext = "";
        // 抓取除了剛才最後加入的那句話以外的所有對話作為「歷史」
        messages.forEach((msg, index) => {
            if (index < messages.length - 1) { // 排除最後一則（即當前問題）
                const role = msg.classList.contains('user-msg') ? "使用者" : "助手";
                let cleanText = msg.innerText.replace(/開啟 PDF 檔案/g, "").trim();
                fullContext += `${role}: ${cleanText}\n\n`;
            }
        });
        historyToSend = fullContext;
    }

    try {
        // 雙重傳送：query 用於搜尋，history 提供上下文
        let url = `${window.location.origin}/ask?query=${encodeURIComponent(query)}`;
        if (historyToSend) {
            url += `&history=${encodeURIComponent(historyToSend)}`;
        }

        const response = await fetch(url, {
            signal: currentController.signal
        });

        const data = await response.json(); // 解析後端回傳的 JSON 資料

        // 移除「思考中」提示
        const loadingEl = document.getElementById(loadingId);
        if (loadingEl) loadingEl.remove();

        // --- 核心邏輯優化：先轉 Markdown，再插按鈕 ---
        // 這樣可以避免按鈕的 HTML 標籤被 marked 解析器給轉義 (Escape) 成純文字
        let htmlContent = marked.parse(data.ai_answer);

        // 正則表達式：尋找以 Data\ 開頭且以 .pdf 結尾的相對路徑字串
        const pathRegex = /Data\\[^ \n\(\)]+\.pdf/gi;
        htmlContent = htmlContent.replace(pathRegex, (match) => {
            const safePath = match.replace(/\\/g, '/'); // 將反斜線轉為網頁標準斜線
            // 回傳「路徑文字 + 開啟按鈕」
            return safePath + `<button class="open-btn" onclick="openPDF('${safePath}')">開啟 PDF 檔案</button>`;
        });

        history.innerHTML += `<div class="message ai-msg">${htmlContent}</div>`; // 在畫面顯示處理過的回答
        history.scrollTop = history.scrollHeight - history.clientHeight; // 回答後再次捲動置底

        const refList = document.getElementById('ref-list'); // 取得右側參考資料列表物件
        refList.innerHTML = ''; // 清空之前的搜尋結果

        // 更新右上角參考資料筆數顯示
        const refCountEl = document.getElementById('ref-count');
        refCountEl.innerText = ` - 共 ${data.references.length} 筆`;

        if (data.references.length === 0) { // 如果後端回傳的參考資料長度為 0
            refList.innerHTML = '<p>未找到符合門檻的參考資料。</p>'; // 顯示提示文字
        }

        // 跑迴圈遍歷每一筆參考資料，並動態產生 HTML 卡片
        data.references.forEach(ref => {
            refList.innerHTML += `
                <div class="ref-card">
                    <strong>來源: ${ref.filename}</strong><br> <!-- 顯示手冊來源名稱 -->
                    <small>相似度分數: ${ref.score}</small> <!-- 顯示檢索相似度 -->
                    <p>${ref.content.substring(0, 150)}...</p> <!-- 截取內容前 150 字作為摘要 -->
                    <button class="open-btn" onclick="openPDF('${ref.path.replace(/\\/g, '/')}')">開啟 PDF 檔案</button>
                </div>
            `;
        });

        // 存檔
        saveChatData();
    } catch (e) {
        // 發生錯誤時也要移除「思考中」提示
        const loadingEl = document.getElementById(loadingId);
        if (loadingEl) loadingEl.remove();
        
        console.error("連線出錯：", e); // 在開發者工具印出錯誤訊息
        
        // 區分是「手動中斷」還是「網路錯誤」
        if (e.name === 'AbortError') {
            history.innerHTML += `<div class="message ai-msg text-orange">已手動停止等待。</div>`;
        } else {
            history.innerHTML += `<div class="message ai-msg text-red">錯誤：無法連線至後端伺服器。</div>`;
        }
        // 錯誤訊息也存檔
        saveChatData();
    } finally {
        // --- 結束請求：解鎖 UI 並隱藏停止按鈕 ---
        currentController = null;
        inputBase.disabled = false;
        btn.disabled = false;
        stopBtn.style.display = 'none'; // 隱藏停止按鈕
        inputBase.focus();
        history.scrollTop = history.scrollHeight - history.clientHeight;
    }
}

// 定義開啟 PDF 的函式
async function openPDF(safePath) {
    // 偵測目前是否為遠端連線 (如果主機名不是 localhost，就視為遠端 iPad)
    const isRemote = !window.location.hostname.includes('127.0.0.1') && !window.location.hostname.includes('localhost');

    if (isRemote) {
        // 【iPad/遠端模式】：拆分路徑分別編碼，保留斜線 "/" 作為路徑分隔符
        const encodedPath = safePath.split('/').map(encodeURIComponent).join('/');
        const pdfUrl = `${window.location.origin}/pdf_view/${encodedPath}`;
        window.open(pdfUrl, '_blank');
    } else {
        // 【桌機本機模式】：維持原本呼叫 API 開啟本地檔案的行為
        try {
            const response = await fetch(`${window.location.origin}/open-pdf?path=${encodeURIComponent(safePath)}`);
            const result = await response.json();
            if (result.status === "error") alert("開啟失敗：" + result.message);
        } catch (e) {
            alert("無法與後端通訊，請檢查 FastAPI 是否執行中。");
        }
    }
}


// 實作下載對話紀錄的函式
function downloadChat() {
    // 取得存放所有對話氣泡的容器物件
    const history = document.getElementById('chat-history');
    
    // 1. 抓取所有 class 為 message 的元素
    // 2. 使用 Array.from 將 NodeList 轉為陣列以便使用 .map() 處理
    const content = Array.from(history.querySelectorAll('.message')).map(msg => {
        // 直接取得文字內容，並移除「開啟 PDF 檔案」這幾個字 (按鈕上的標籤文字)
        const cleanText = msg.innerText.replace(/開啟 PDF 檔案/gi, '');

        let roleLabel = ''; // 建立一個變數來存放身份標籤
        
        // 使用 switch 進行嚴謹的身份判斷
        switch (true) {
            case msg.classList.contains('user-msg'): // 如果具備使用者訊息的 class
                roleLabel = '【使用者】：\n'; // 設定標籤為使用者
                break;
            case msg.classList.contains('ai-msg'):   // 如果具備 AI 助理訊息的 class
                roleLabel = '【AI 助理】：\n'; // 設定標籤為 AI 助理
                break;
            default:                                 // 若都不符合 (例外狀況)
                roleLabel = '';                       // 保持標籤為空，不修改文字內容
                break;
        }
        
        // 回傳「身份標籤 + 處理過後的純文字」
        return roleLabel + cleanText;
    }).join('\n\n------------------\n\n'); // 每則訊息之間用分隔線與雙換行區隔
    
    // 如果處理後的內容完全是空的 (沒有對話)
    if (!content.trim()) {
        alert("目前沒有對話紀錄可以下載。"); // 跳出警告提示
        return; // 中止下載流程
    }

    // 建立一個 Blob 物件 (將文字內容轉換為二進位檔案格式)
    const blob = new Blob([content], { type: 'text/plain' }); 
    // 將這個 Blob 物件轉換為瀏覽器可以識別的暫時性 URL (網址)
    const url = URL.createObjectURL(blob); 
    
    // 建立一個隱藏的 <a> 標籤 (超連結元素) 用來觸發下載
    const a = document.createElement('a'); 
    // 取得當前時間並將特殊字元 (斜線、冒號、空白) 替換為橫槓，以免檔名報錯
    const timestamp = new Date().toLocaleString().replace(/[\/: ]/g, '-'); 
    // 將超連結的網址指向我們剛剛建立的 Blob URL
    a.href = url; 
    // 設定下載的檔案名稱，包含時間戳記
    a.download = `PLC_Chat_History_${timestamp}.txt`; 
    // 將此標籤暫時加入到網頁中 (有些瀏覽器要求必須在 DOM 內才能點擊)
    document.body.appendChild(a); 
    // 模擬使用者點擊這個連結，這會啟動瀏覽器的下載行為
    a.click(); 
    
    // 下載啟動後，立刻將剛才建立的標籤從網頁中移除
    document.body.removeChild(a); 
    // 釋放剛才建立的暫時性網址，以節省瀏覽器的記憶體空間
    URL.revokeObjectURL(url); 
}

// --- 5. 行動版/iPad 視窗校正邏輯 ---
// 監測視覺視窗變化 (解決鍵盤彈出/收起造成的位移與空白問題)
if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => {
        // 給瀏覽器一點時間完成鍵盤動畫
        setTimeout(() => {
            // 抓取最精確的可視區域高度
            let vHeight = `${window.innerHeight}px`;
            if (window.innerHeight > window.visualViewport.height * 1.5)
            {
                vHeight = `${window.visualViewport.height}px`;
            }
            
            // 套用高度設定
            document.documentElement.style.height = vHeight;
            document.body.style.height = vHeight;

            // 強制歸位
            window.scrollTo(0, 0);
        }, 50);
    });
}

// --- 6. 對話持久化邏輯 (LocalStorage) ---

// 儲存對話與參考資料至瀏覽器
function saveChatData() {
    const history = document.getElementById('chat-history').innerHTML;
    const refList = document.getElementById('ref-list').innerHTML;
    const refCount = document.getElementById('ref-count').innerText;
    
    localStorage.setItem('chatHistory', history);
    localStorage.setItem('refList', refList);
    localStorage.setItem('refCount', refCount);
}

// 載入存檔
function loadChatData() {
    const history = localStorage.getItem('chatHistory');
    const refList = localStorage.getItem('refList');
    const refCount = localStorage.getItem('refCount');
    
    if (history) document.getElementById('chat-history').innerHTML = history;
    if (refList) document.getElementById('ref-list').innerHTML = refList;
    if (refCount) document.getElementById('ref-count').innerText = refCount;
    
    // 自動捲動到底部
    const chatHistory = document.getElementById('chat-history');
    if (chatHistory) {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}

// 清除所有對話紀錄
function clearChat() {
    if (confirm("確定要清除所有對話紀錄與參考資料嗎？")) {
        // 還原 UI 至初始狀態
        document.getElementById('chat-history').innerHTML = '<div class="message ai-msg">您好！我是永宏 PLC 技術支援助手。請問有什麼我可以幫您的？</div>';
        document.getElementById('ref-list').innerHTML = '<p class="text-gray">提問後，相關手冊片段將顯示於此。</p>';
        document.getElementById('ref-count').innerText = '';
        
        // 清除 LocalStorage
        localStorage.removeItem('chatHistory');
        localStorage.removeItem('refList');
        localStorage.removeItem('refCount');
    }
}

// 網頁啟動時載入
window.addEventListener('load', loadChatData);






