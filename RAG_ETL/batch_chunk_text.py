import os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # 切換至根目錄
sys.path.append(os.path.join(os.getcwd(), 'RAG_ETL')) # 修正匯入路徑

# ETL = Extract（提取）、Transform（轉換）、Load（載入），Recursive (遞迴的)
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 假設你昨天的檔名是 batch_read_pdf.py
from batch_read_pdf import batch_process_manuals 

def create_chunks_with_metadata(all_pdf_data):
    # 1. 初始化切割器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    
    final_chunks = []
    
    # 2. 處理每一份 PDF
    for pdf in all_pdf_data:
        # 將該 PDF 的長文本切成多個片段
        chunks = text_splitter.split_text(pdf["content"])
        
        # 3. 為每一個片段貼上標籤
        for chunk_text in chunks:
            final_chunks.append({
                "content": chunk_text,
                "metadata": {
                    "filename": pdf["filename"],
                    "path": pdf["path"]
                }
            })
            
    return final_chunks

if __name__ == "__main__":
    # 執行昨天的批次讀取
    raw_data = batch_process_manuals("Data")
    
    # 執行切塊整合
    processed_chunks = create_chunks_with_metadata(raw_data)
    
    print(f"原本共有 {len(raw_data)} 份文件")
    print(f"現在切成了 {len(processed_chunks)} 個知識片段")
    
    if processed_chunks:
        print("\n--- 第一個片段範例 ---")
        print(f"來源文件: {processed_chunks[0]['metadata']['filename']}")
        print(f"內容長度: {len(processed_chunks[0]['content'])}")
        print(f"內容前100字: {processed_chunks[0]['content'][:100]}")
