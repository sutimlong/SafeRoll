# SafeRoll

SafeRoll 是一款專為影視工作者與資料管理員設計的「安全媒體檔案備份與校驗軟體」(Secure Media Offload)。它提供了直覺的使用者介面，確保資料在轉移過程中的絕對完整性，避免任何檔案遺失或損壞，讓備份工作更加安心。

## ✨ 特色功能

- **多種攝影機結構自動識別**：自動識別 Sony, RED, ARRI, Blackmagic (BMD), Canon/DCIM 等專業攝影機的檔案結構。
- **三重安全備份與校驗**：支援 MD5 與 xxhash64 雙重雜湊演算法（可選），確保資料一比特不差。
- **視覺化進度與速度**：即時顯示複製進度、傳輸速度 (MB/s)、剩餘時間 (ETA)，讓您精確掌握備份進度。
- **衝突檔案處理機制**：可自訂檔案名稱衝突時的處理方式（如：自動更名加序號、跳過相同 Checksum 檔案、嚴格報警並中止）。
- **專業備份報告匯出**：備份完成後，可自動匯出包含每個檔案的 MD5/xxhash64 校驗碼及狀態的 PDF 與 CSV 報告，方便日後稽核。

## 🛡️ 檔案驗證方式及流程

SafeRoll 在進行高安全級別的備份時，會執行嚴謹的 **三階段校驗流程 (3-Phase Verification)**：

1. **第一階段 (Global Copy)**：
   將檔案從來源端以高效的區塊串流 (16MB Chunk Size) 複製到目標端，並即時回報複製進度與速度。
2. **第二階段 (Global Source Hash)**：
   讀取原始來源檔案，計算並生成其 `MD5` 或 `xxhash64` 雜湊值 (Hash)，作為後續比對的基準。
3. **第三階段 (Global Dest Hash & Verify)**：
   讀取剛複製到目標端的檔案，重新計算雜湊值，並與第二階段的基準值進行比對。
   - 若雜湊值完全一致，該檔案狀態標記為 `OK`。
   - 若發生不一致或讀寫異常，將標記錯誤（如 `MD5 Error`）並可觸發警報，確保有損壞的檔案不會被略過。

此種 Source 與 Dest 獨立讀取計算的方法，能有效排除因系統快取 (Cache) 造成的「假性成功」，是業界公認最安全的資料轉移方式。

## 🛠️ 核心框架與工具

SafeRoll 的開發結合了現代 Web 前端技術與強大的 Python 後端：

- **核心框架**：基於 [`pywebview`](https://pywebview.flowrl.com/) 框架，將 Python 邏輯與 HTML/CSS/JS 前端 UI 完美結合，提供跨平台且輕量化的桌面應用程式體驗。
- **雜湊與校驗引擎**：
  - Python 內建的 `hashlib`：用於計算標準的 MD5 雜湊。
  - [`xxhash`](https://pypi.org/project/xxhash/)：提供極速的 xxhash64 雜湊計算，能利用硬體加速達到極高的校驗效能。
- **報告生成工具**：
  - `fpdf2`：用於生成包含字體支援 (Arial Unicode) 的高品質 PDF 備份報告。
  - Python 內建 `csv` 模組：用於匯出標準格式的 CSV 報告。

## 📥 下載與安裝

您可以直接從 GitHub 的 **Releases** 頁面下載最新編譯好的 SafeRoll 應用程式：

1. 前往本專案的 [Releases 頁面](../../releases)（或點擊 GitHub 右側的 Releases 區塊）。
2. 在最新的發布版本 (Latest Release) 中，尋找適合您作業系統的檔案：
   - macOS 使用者請下載 `.dmg` 或 macOS 版壓縮檔。
   - Windows 使用者請下載 `.exe` 安裝檔。
3. 下載完成後，解壓縮或掛載映像檔，即可直接開啟執行，不須額外設定環境！

---
*備份有價資料，請務必開啟校驗功能，讓 SafeRoll 守護您的每一格畫面。*
