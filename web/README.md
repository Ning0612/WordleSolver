← [Back to Main Project](../README.md) | [Desktop Version](../README.md#quick-start)

# Wordle Solver Web 版本

GitHub Pages + Pyodide 實作的 Wordle 解題助手。

## 快速開始

### 本地測試

```bash
# 在 web/ 目錄啟動本地伺服器
cd web
python -m http.server 8000

# 或使用專案的虛擬環境
../.venv/Scripts/python.exe -m http.server 8000
```

然後在瀏覽器訪問 http://localhost:8000

### 使用方式

1. **輸入字母**：
   - 使用虛擬鍵盤或實體鍵盤輸入 5 個字母

2. **標記顏色**：
   - 點擊格子切換顏色：空 → 灰 → 黃 → 綠
   - 或使用空白鍵切換當前格子顏色

3. **提交猜測**：
   - 點擊「提交當前行」或按 Enter 鍵
   - 系統會計算並顯示推薦單字

4. **使用推薦**：
   - 點擊推薦單字可自動填入當前行

5. **重新開始**：
   - 點擊「重新開始」清空所有內容

## 檔案結構

```
web/
├── index.html              # 主頁面
├── styles.css              # 樣式表
├── app.js                  # 前端邏輯 + Pyodide 整合
├── manifest.json           # PWA 配置
├── sw.js                   # Service Worker
├── assets/
│   └── five_letter_words.json   # 字典檔案
└── README.md               # 本檔案

註: Web 版本使用 ../src/ 目錄的 Python 核心模組
```

## 技術架構

- **前端**: Vanilla JavaScript (ES6+)
- **Python 執行環境**: Pyodide 0.25+
- **UI**: CSS Grid/Flexbox (響應式)
- **PWA**: Service Worker + Manifest
- **部署**: GitHub Pages (自動化)

## 效能指標

- **首次載入**: 3-5 秒（4G 網路）
- **第二次訪問**: <1 秒（Service Worker 快取）
- **計算時間**: <100ms/輪
- **記憶體佔用**: <150MB

## PWA 功能

- ✅ 離線使用（Service Worker）
- ✅ 可安裝到主畫面（Android）
- ✅ 獨立視窗運行
- ✅ 自動更新提示

## 瀏覽器支援

| 瀏覽器 | 最低版本 | 狀態 |
|--------|---------|------|
| Chrome | 90+ | ✅ 完全支援 |
| Edge | 90+ | ✅ 完全支援 |
| Firefox | 88+ | ✅ 完全支援 |
| Safari | 14+ | ⚠️ 載入較慢 |

## 部署

推送到 GitHub 後會自動透過 GitHub Actions 部署到 GitHub Pages。

部署 URL: `https://<username>.github.io/wordle-solver/`

## 已知問題

1. **iOS Safari 載入較慢**: 10-15 秒（Pyodide 支援較差）
2. **首次載入需要網路**: 下載 Pyodide 和字典

## 開發指南

詳細開發指南請參考：`docs/github-pages-pyodide-guide.md`

## 授權

與主專案相同。
