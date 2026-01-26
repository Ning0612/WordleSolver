/**
 * Wordle Solver Web App
 * 使用 Pyodide 執行 Python 核心模組
 */

// ===== 全域狀態 =====
const STATE = {
  pyodide: null,              // Pyodide 實例
  currentRow: 0,              // 當前行（0-5）
  currentCol: 0,              // 當前列（0-4）
  grid: [],                   // 30 個格子元素
  history: [],                // 歷史記錄 [{guess, feedback}]
  candidates: null,           // 候選單字
  recommendations: [],        // 推薦清單
};

// ===== DOM 元素 =====
const DOM = {
  loadingIndicator: null,
  mainContent: null,
  grid: null,
  submitBtn: null,
  resetBtn: null,
  candidateList: null,
  explorationList: null,
  errorMessage: null,
};

// ===== 效能監控 =====
const PERF = {
  pyodideLoadStart: 0,
  pyodideLoadEnd: 0,
  computeStart: 0,
  computeEnd: 0,
};

// ===== 載入初始推薦 =====
async function loadInitialRecommendations() {
  console.log('[Init] Loading initial recommendations...');

  try {
    const result = await STATE.pyodide.runPythonAsync(`
import json
# 獲取初始推薦（使用空的約束條件）
empty_constraint = Constraint()
recommendations = _recommender.recommend(
    candidates=_word_list,
    constraint=empty_constraint,
    round_number=1,
    top_n=10
)
json.dumps({
    'candidates_count': len(_word_list),
    'candidates': recommendations['candidates'][:5],
    'explorations': recommendations['explorations'][:5]
})
    `);

    const data = JSON.parse(result);
    console.log('[Init] Initial recommendations loaded:', data);

    // 更新 UI (傳入候選單字總數)
    updateRecommendations(data.candidates, data.explorations, data.candidates_count);
  } catch (error) {
    console.error('[Init] Failed to load initial recommendations:', error);
    // 不影響主流程，只記錄錯誤
  }
}

// ===== 初始化 =====
async function init() {
  console.log('[Init] Starting initialization...');

  // 取得 DOM 元素
  DOM.loadingIndicator = document.getElementById('loading-indicator');
  DOM.mainContent = document.getElementById('main-content');
  DOM.grid = document.getElementById('wordle-grid');
  DOM.submitBtn = document.getElementById('submit-btn');
  DOM.resetBtn = document.getElementById('reset-btn');
  DOM.candidateList = document.getElementById('candidate-list');
  DOM.explorationList = document.getElementById('exploration-list');
  DOM.errorMessage = document.getElementById('error-message');

  // 建立網格
  createGrid();

  // 綁定事件
  DOM.submitBtn.addEventListener('click', handleSubmit);
  DOM.resetBtn.addEventListener('click', handleReset);
  setupKeyboard();
  setupGridEventDelegation();  // 使用事件委派優化網格點擊
  setupInstructions();  // 設定使用說明摺疊功能


  // 載入 Pyodide
  try {
    await initPyodide();
    console.log('[Init] Pyodide loaded successfully');

    // 顯示主要內容
    DOM.loadingIndicator.classList.add('hidden');
    DOM.mainContent.classList.remove('hidden');

    // 載入初始推薦
    await loadInitialRecommendations();

    // 註冊 Service Worker
    await registerServiceWorker();
  } catch (error) {
    showError(`Loading failed: ${error.message}`);
    console.error('[Init] Error:', error);
  }
}

// ===== 建立網格 =====
function createGrid() {
  for (let row = 0; row < 6; row++) {
    for (let col = 0; col < 5; col++) {
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.dataset.row = row;
      cell.dataset.col = col;
      cell.dataset.state = '';  // '', 'gray', 'yellow', 'green'

      // ⚠️ 已移除單獨的事件監聽器,改用事件委派 (見 setupGridEventDelegation)

      DOM.grid.appendChild(cell);
      STATE.grid.push(cell);
    }
  }
}

// ===== 設定網格事件委派 =====
// 優化: 使用事件委派替代 30 個獨立監聽器,減少記憶體佔用
function setupGridEventDelegation() {
  DOM.grid.addEventListener('click', (e) => {
    const cell = e.target.closest('.cell');
    if (!cell) return;

    const row = parseInt(cell.dataset.row, 10);
    const col = parseInt(cell.dataset.col, 10);
    handleCellClick(row, col);
  });
}

// ===== 設定使用說明摺疊功能 =====
function setupInstructions() {
  const instructionsSection = document.getElementById('instructions');
  const instructionsToggle = document.getElementById('instructions-toggle');

  if (!instructionsSection || !instructionsToggle) return;

  // 從 localStorage 讀取狀態（預設為展開）
  const isCollapsed = localStorage.getItem('instructionsCollapsed') === 'true';

  if (isCollapsed) {
    instructionsSection.classList.add('collapsed');
  }

  // 點擊切換
  instructionsToggle.addEventListener('click', () => {
    const willCollapse = !instructionsSection.classList.contains('collapsed');

    if (willCollapse) {
      instructionsSection.classList.add('collapsed');
    } else {
      instructionsSection.classList.remove('collapsed');
    }

    // 儲存狀態到 localStorage
    localStorage.setItem('instructionsCollapsed', willCollapse.toString());
  });
}


// ===== 格子點擊處理 =====
function handleCellClick(row, col) {
  const cell = STATE.grid[row * 5 + col];

  // 如果格子為空，聚焦到這個格子等待輸入
  if (!cell.textContent) {
    focusCell(row, col);
    return;
  }

  // 如果格子有字母，切換顏色（gray → yellow → green → 空）
  cycleColor(cell);
}

// ===== 循環切換顏色 =====
function cycleColor(cell) {
  // 只在灰色、橘色、藍色之間切換（不包含空白狀態）
  const states = ['gray', 'yellow', 'green'];
  const current = cell.dataset.state || 'gray';
  const currentIndex = states.indexOf(current);
  const nextIndex = (currentIndex + 1) % states.length;
  const nextState = states[nextIndex];

  cell.dataset.state = nextState;

  // 動畫效果
  cell.classList.add('active');
  setTimeout(() => cell.classList.remove('active'), 300);
}

// ===== 聚焦格子 =====
function focusCell(row, col) {
  // 移除所有 active 樣式
  STATE.grid.forEach(cell => cell.classList.remove('active'));

  // 加到目標格子
  const cell = STATE.grid[row * 5 + col];
  cell.classList.add('active');

  STATE.currentRow = row;
  STATE.currentCol = col;
}

// ===== 設定鍵盤 =====
function setupKeyboard() {
  // 虛擬鍵盤
  document.querySelectorAll('.key').forEach(key => {
    key.addEventListener('click', () => {
      handleKeyPress(key.dataset.key);
    });
  });

  // 實體鍵盤
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace') {
      handleKeyPress('Backspace');
    } else if (e.key === 'Enter') {
      handleSubmit();
    } else if (e.key === ' ') {
      // Space 切換當前格子顏色
      e.preventDefault();
      const cell = STATE.grid[STATE.currentRow * 5 + STATE.currentCol];
      if (cell.textContent) {
        cycleColor(cell);
      }
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      moveLeft();
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      moveRight();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      moveUp();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      moveDown();
    } else if (/^[a-zA-Z]$/.test(e.key)) {
      handleKeyPress(e.key.toUpperCase());
    }
  });
}

// ===== 處理按鍵 =====
function handleKeyPress(key) {
  if (key === 'Backspace') {
    // 刪除當前格子字母
    const cell = STATE.grid[STATE.currentRow * 5 + STATE.currentCol];
    if (cell.textContent) {
      cell.textContent = '';
      cell.dataset.state = '';
    } else if (STATE.currentCol > 0) {
      // 如果當前格子為空，刪除上一格
      STATE.currentCol--;
      const prevCell = STATE.grid[STATE.currentRow * 5 + STATE.currentCol];
      prevCell.textContent = '';
      prevCell.dataset.state = '';
      focusCell(STATE.currentRow, STATE.currentCol);
    }
  } else if (key === 'Enter') {
    handleSubmit();
  } else if (key === 'ArrowLeft') {
    moveLeft();
  } else if (key === 'ArrowRight') {
    moveRight();
  } else if (key === 'ArrowUp') {
    moveUp();
  } else if (key === 'ArrowDown') {
    moveDown();
  } else if (key === ' ') {
    // Space 切換顏色
    const cell = STATE.grid[STATE.currentRow * 5 + STATE.currentCol];
    if (cell.textContent) {
      cycleColor(cell);
    }
  } else {
    // 輸入字母
    if (STATE.currentCol < 5) {
      const cell = STATE.grid[STATE.currentRow * 5 + STATE.currentCol];
      cell.textContent = key;
      // 自動設定為灰色狀態
      cell.dataset.state = 'gray';

      // 自動移到下一格
      if (STATE.currentCol < 4) {
        STATE.currentCol++;
        focusCell(STATE.currentRow, STATE.currentCol);
      }
    }
  }
}

// ===== 箭頭鍵移動 =====
function moveLeft() {
  if (STATE.currentCol > 0) {
    STATE.currentCol--;
    focusCell(STATE.currentRow, STATE.currentCol);
  }
}

function moveRight() {
  if (STATE.currentCol < 4) {
    STATE.currentCol++;
    focusCell(STATE.currentRow, STATE.currentCol);
  }
}

function moveUp() {
  if (STATE.currentRow > 0) {
    STATE.currentRow--;
    focusCell(STATE.currentRow, STATE.currentCol);
  }
}

function moveDown() {
  if (STATE.currentRow < 5) {
    STATE.currentRow++;
    focusCell(STATE.currentRow, STATE.currentCol);
  }
}

// ===== 前端驗證函數 =====
/**
 * 驗證單個回合的反饋是否有邏輯衝突
 * @param {string} guess - 猜測的單字（5個字母）
 * @param {Array<string>} feedback - 反饋顏色數組 ['gray', 'yellow', 'green', ...]
 * @returns {string|null} - 錯誤訊息，如果沒有錯誤則返回 null
 */
function validateFeedback(guess, feedback) {
  // 統計每個字母的顏色狀態
  const letterStatus = {}; // { 'a': { green: 1, yellow: 0, gray: 2 } }

  for (let i = 0; i < 5; i++) {
    const letter = guess[i];
    const color = feedback[i];

    if (!letterStatus[letter]) {
      letterStatus[letter] = { green: 0, yellow: 0, gray: 0 };
    }

    letterStatus[letter][color]++;
  }

  // 檢查每個字母的邏輯一致性
  for (const [letter, status] of Object.entries(letterStatus)) {
    const hasPositive = status.green > 0 || status.yellow > 0; // 表示字母存在
    const hasGray = status.gray > 0; // 表示字母不存在或已達上限

    // 簡單檢測：如果只有 1 個該字母，但既是綠色/黃色又是灰色，這是錯誤
    const totalCount = status.green + status.yellow + status.gray;
    if (totalCount === 1 && hasPositive && hasGray) {
      // 不可能同時是存在和不存在（單個字母的情況）
      return `⚠️ Letter '${letter.toUpperCase()}' has conflicting color markings`;
    }

    // 對於重複字母（totalCount > 1），允許部分是綠色/黃色，部分是灰色
    // 這表示答案中該字母的數量 = 綠色數 + 黃色數
    // 後端會處理這種複雜邏輯
  }

  return null; // 沒有發現明顯錯誤
}

// ===== 提交當前行 =====
async function handleSubmit() {
  console.log('[Submit] Submitting all complete rows');

  // 掃描所有 6 行，找出完整的 5 字母行
  const completeRows = [];
  for (let row = 0; row < 6; row++) {
    const startIdx = row * 5;
    const rowCells = STATE.grid.slice(startIdx, startIdx + 5);
    const guess = rowCells.map(cell => cell.textContent).join('').toLowerCase();
    const feedback = rowCells.map(cell => cell.dataset.state);

    // 只處理完整的 5 字母行
    if (guess.length === 5 && guess.match(/^[a-z]{5}$/)) {
      // 檢查是否所有字母都已標記顏色
      if (feedback.every(state => state && state !== '')) {
        completeRows.push({ row, guess, feedback });
      } else {
        showError(`Row ${row + 1} has unmarked letters. Please mark all letters with colors.`);
        return;
      }
    }
  }

  // 如果沒有完整行，提示用戶
  if (completeRows.length === 0) {
    showError('Please enter at least one complete 5-letter word and mark colors.');
    return;
  }

  console.log('[Submit] Found', completeRows.length, 'complete rows');

  // ===== 前端預先驗證（避免不必要的後端計算）=====
  for (const { row, guess, feedback } of completeRows) {
    const validationError = validateFeedback(guess, feedback);
    if (validationError) {
      showError(`Row ${row + 1} marking error: ${validationError}`);
      return;
    }
  }

  // 呼叫 Python 核心處理所有完整行
  try {
    DOM.submitBtn.disabled = true;
    DOM.submitBtn.textContent = 'Calculating...';

    PERF.computeStart = performance.now();

    // 重置 Python 狀態並處理所有行
    await STATE.pyodide.runPythonAsync('reset_game()');

    for (const { guess, feedback } of completeRows) {
      await submitRound(guess, feedback);
    }

    PERF.computeEnd = performance.now();

    console.log(`[Perf] 計算時間: ${(PERF.computeEnd - PERF.computeStart).toFixed(0)}ms`);

    // 移動到下一空行
    let nextRow = 0;
    for (let row = 0; row < 6; row++) {
      const startIdx = row * 5;
      const rowCells = STATE.grid.slice(startIdx, startIdx + 5);
      const guess = rowCells.map(cell => cell.textContent).join('');
      if (guess.length < 5) {
        nextRow = row;
        break;
      }
    }

    STATE.currentRow = nextRow;
    STATE.currentCol = 0;
    focusCell(STATE.currentRow, STATE.currentCol);

  } catch (error) {
    // 從 Pyodide Traceback 中提取最後一行的錯誤訊息
    let errorMsg = error.message;

    // 如果是 Traceback，提取最後一行（真正的錯誤訊息）
    if (errorMsg.includes('Traceback')) {
      const lines = errorMsg.split('\n');
      // 找到最後一個非空行（通常是 ValueError: ... 這一行）
      for (let i = lines.length - 1; i >= 0; i--) {
        const trimmed = lines[i].trim();
        if (trimmed && (trimmed.startsWith('ValueError') ||
          trimmed.startsWith('Error') ||
          trimmed.startsWith('Exception'))) {
          errorMsg = trimmed;
          break;
        }
      }
    }

    // 檢測是否為用戶設定錯誤
    if (errorMsg.includes('Impossible constraint') ||
      errorMsg.includes('約束條件矛盾') ||
      (errorMsg.includes('min=') && errorMsg.includes('max='))) {
      // 約束條件衝突（例如同一字母既是黃色又是灰色）
      errorMsg = `⚠️ Color marking error\n\nThis is usually because the same letter has conflicting color markings (e.g., marked as both yellow and gray).\nPlease check your color markings.`;
    } else if (errorMsg.includes('Conflicting')) {
      // Other conflict errors (green position conflicts, green/yellow conflicts, etc.)
      errorMsg = `⚠️ Color marking error\n\nPlease check your color markings.`;
    } else if (errorMsg.includes('empty') ||
      errorMsg.includes('no candidates') ||
      errorMsg.includes('找不到符合條件的候選單字') ||
      errorMsg.includes('IndexError')) {
      // 沒有候選單字（可能是標記錯誤或答案不在詞庫中）
      errorMsg = `⚠️ No matching words found\n\nThis could be because:\n1. Color markings are incorrect, causing contradictory conditions\n2. The answer is not in this dictionary (this dictionary contains common 5-letter English words)\n\nPlease check your color markings.`;
    }

    showError(`Calculation error: ${errorMsg}`);
    console.error('[Submit] 完整錯誤訊息:', error);  // 完整錯誤仍記錄在 console 供除錯
  } finally {
    DOM.submitBtn.disabled = false;
    DOM.submitBtn.textContent = 'Submit Current Row';
  }
}

// ===== 重置遊戲 =====
async function handleReset() {
  console.log('[Reset] Resetting game');

  // 清空網格
  STATE.grid.forEach(cell => {
    cell.textContent = '';
    cell.dataset.state = '';
    cell.classList.remove('active');
  });

  // 重置狀態
  STATE.currentRow = 0;
  STATE.currentCol = 0;
  STATE.history = [];
  STATE.candidates = null;
  STATE.recommendations = [];

  // 重置 Python 狀態
  if (STATE.pyodide) {
    await STATE.pyodide.runPythonAsync('reset_game()');
  }

  // 更新 UI
  DOM.candidateList.innerHTML = '';
  DOM.explorationList.innerHTML = '';

  focusCell(0, 0);

  // 載入初始推薦
  await loadInitialRecommendations();
}

// ===== 顯示錯誤訊息 =====
let errorTimeout = null;

function showError(message) {
  // 清除之前的計時器
  if (errorTimeout) {
    clearTimeout(errorTimeout);
    errorTimeout = null;
  }

  // 支援多行訊息（將 \n 轉為 <br>）
  const formattedMessage = message.replace(/\n/g, '<br>');

  // 添加關閉按鈕
  DOM.errorMessage.innerHTML = `
    ${formattedMessage}
    <button class="error-close" aria-label="Close error message" title="Click to close">×</button>
  `;
  DOM.errorMessage.classList.remove('hidden');

  // 綁定關閉按鈕事件
  const closeBtn = DOM.errorMessage.querySelector('.error-close');
  const hideError = () => {
    DOM.errorMessage.classList.add('hidden');
    if (errorTimeout) {
      clearTimeout(errorTimeout);
      errorTimeout = null;
    }
  };

  closeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    hideError();
  });

  // 點擊錯誤訊息區域也可關閉
  DOM.errorMessage.addEventListener('click', hideError, { once: true });

  // 15 秒後自動隱藏（給予足夠時間閱讀）
  errorTimeout = setTimeout(() => {
    hideError();
  }, 15000);
}

// ===== Pyodide 初始化 =====
async function initPyodide() {
  console.log('[Pyodide] Starting to load Pyodide...');
  PERF.pyodideLoadStart = performance.now();

  // 步驟 1: 載入 Pyodide
  STATE.pyodide = await loadPyodide({
    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/"
  });
  console.log('[Pyodide] Pyodide loaded');

  // 步驟 2: 載入字典
  console.log('[Pyodide] Loading dictionary...');
  const dictResponse = await fetch('assets/five_letter_words.json');
  if (!dictResponse.ok) {
    throw new Error(`Cannot load dictionary: ${dictResponse.status} ${dictResponse.statusText}`);
  }
  const words = await dictResponse.json();
  console.log(`[Pyodide] Dictionary loaded: ${words.length} words`);

  // 將字典存到 Python 全域變數
  STATE.pyodide.globals.set('WORD_LIST', words);

  // 步驟 3: 載入 Python 核心模組
  console.log('[Pyodide] Loading Python core modules...');

  const modules = [
    'constraints.py',
    'dictionary.py',
    'solver.py',
    'stats.py',
    'recommender.py'
  ];

  // 使用 Pyodide FS 寫入檔案後 import（正確的模組載入方式）
  // 支援本地測試 (../src/) 和 GitHub Pages 部署 (src/)
  const possiblePaths = ['../src/', 'src/'];

  for (const moduleName of modules) {
    let code = null;
    let loadedFrom = null;

    // 嘗試不同路徑
    for (const basePath of possiblePaths) {
      try {
        const response = await fetch(`${basePath}${moduleName}`);
        if (response.ok) {
          code = await response.text();
          loadedFrom = basePath;
          break;
        }
      } catch (e) {
        // 繼續嘗試下一個路徑
        continue;
      }
    }

    if (!code) {
      throw new Error(`Cannot load ${moduleName}: tried paths ${possiblePaths.join(', ')}`);
    }

    // 寫入 Pyodide 虛擬檔案系統
    STATE.pyodide.FS.writeFile(`/home/pyodide/${moduleName}`, code);
    console.log(`[Pyodide] Loaded: ${moduleName} (from ${loadedFrom})`);
  }

  // 步驟 4: 初始化 WordleCore
  console.log('[Pyodide] Initializing WordleCore...');
  await STATE.pyodide.runPythonAsync(`
import sys
sys.path.insert(0, '/home/pyodide')

from constraints import Constraint, FeedbackRound, FeedbackColor
from solver import filter_candidates
from recommender import WordRecommender
from stats import LetterStats

# 建立全域實例
_word_list = WORD_LIST
_stats = LetterStats(_word_list)
_recommender = WordRecommender(_word_list, _stats)

# 全域狀態
_current_constraint = None
_history = []

def submit_round(guess, feedback_colors):
    """提交一輪猜測"""
    global _current_constraint, _history
    
    # 轉換顏色字串為 FeedbackColor enum
    color_map = {
        'gray': FeedbackColor.GRAY,
        'yellow': FeedbackColor.YELLOW,
        'green': FeedbackColor.GREEN
    }
    feedback = [color_map[c] for c in feedback_colors]
    
    # 建立 FeedbackRound 並轉為 Constraint
    round_obj = FeedbackRound(guess=guess, feedback=feedback)
    constraint = round_obj.to_constraint()
    
    # 合併 constraint
    if _current_constraint is None:
        _current_constraint = constraint
    else:
        _current_constraint = _current_constraint.merge(constraint)
    
    # Phase 1: 過濾候選
    candidates = filter_candidates(_word_list, _current_constraint)
    
    # 驗證: 檢查是否有候選單字（在計算推薦前）
    if len(candidates) == 0:
        raise ValueError(
            "找不到符合條件的候選單字。"
            "這可能是因為顏色標記有誤，或答案不在詞庫中。"
        )
    
    # Phase 2: 推薦
    round_number = len(_history) + 1
    recommendations = _recommender.recommend(
        candidates=candidates,
        constraint=_current_constraint,
        round_number=round_number,
        top_n=10
    )
    
    # 記錄歷史
    _history.append({'guess': guess, 'feedback': feedback_colors})
    
    return {
        'candidates': candidates,
        'candidates_count': len(candidates),
        'recommendations': recommendations
    }

def reset_game():
    """重置遊戲狀態"""
    global _current_constraint, _history
    _current_constraint = None
    _history = []

# 計算初始推薦
print('[Python] Python 核心初始化完成')
  `);

  PERF.pyodideLoadEnd = performance.now();
  console.log(`[Perf] Pyodide 載入時間: ${(PERF.pyodideLoadEnd - PERF.pyodideLoadStart).toFixed(0)}ms`);
  console.log('[Pyodide] Initialization complete');
}

// ===== 提交一輪到 Python 核心 =====
async function submitRound(guess, feedback) {
  console.log('[Python] 呼叫 submit_round:', guess, feedback);

  // 呼叫 Python 函數
  const result = await STATE.pyodide.runPythonAsync(`
import json
result = submit_round("${guess}", ${JSON.stringify(feedback)})
# recommendations 是 dict: {candidates: [...], explorations: [...]}
json.dumps({
    'candidates_count': result['candidates_count'],
    'candidates': result['recommendations']['candidates'][:5],
    'explorations': result['recommendations']['explorations'][:5]
})
  `);

  // 解析結果
  const data = JSON.parse(result);
  console.log('[Python] 結果:', data);

  // 更新 UI (傳入候選單字總數)
  updateRecommendations(data.candidates, data.explorations, data.candidates_count);

  // 記錄歷史
  STATE.history.push({ guess, feedback });
}

// ===== 更新推薦清單 =====
// 優化: 使用 DocumentFragment 批次插入,減少 reflow 次數 (10次 → 2次)
function updateRecommendations(candidates, explorations, candidatesCount = null) {
  console.log('[UI] Updating recommendations:', candidates.length, 'candidates,', explorations.length, 'explorations');

  // 更新候選單字數量顯示
  const candidateCountEl = document.getElementById('candidate-count');
  if (candidateCountEl) {
    // 如果有提供 candidatesCount，使用它；否則使用 candidates.length
    const count = candidatesCount !== null ? candidatesCount : candidates.length;
    candidateCountEl.textContent = count > 0 ? `${count} ` : '';
  }

  // 檢查是否只有唯一候選
  if (candidates.length === 1) {
    const [word, score] = candidates[0];
    setTimeout(() => {
      alert(`🎉 Unique answer found!\n\nThe answer is likely: ${word.toUpperCase()}\n\nConfidence score: ${score.toFixed(1)}`);
    }, 100);
  }

  // 使用 DocumentFragment 批次建立候選欄項目
  const candidateFragment = document.createDocumentFragment();
  candidates.forEach(([word, score], index) => {
    const item = document.createElement('div');
    item.className = 'rec-item candidate';
    item.innerHTML = `
      <span class="rec-word">${index + 1}. ${word.toUpperCase()}</span>
    `;

    item.addEventListener('click', () => {
      fillCurrentRow(word);
    });

    candidateFragment.appendChild(item);
  });

  // 使用 DocumentFragment 批次建立探索欄項目
  const explorationFragment = document.createDocumentFragment();
  explorations.forEach(([word, score], index) => {
    const item = document.createElement('div');
    item.className = 'rec-item exploration';
    item.innerHTML = `
      <span class="rec-word">${index + 1}. ${word.toUpperCase()}</span>
    `;

    item.addEventListener('click', () => {
      fillCurrentRow(word);
    });

    explorationFragment.appendChild(item);
  });

  // 一次性插入 DOM (只觸發 2 次 reflow,而非 10 次)
  DOM.candidateList.innerHTML = '';
  DOM.candidateList.appendChild(candidateFragment);
  DOM.explorationList.innerHTML = '';
  DOM.explorationList.appendChild(explorationFragment);
}


// ===== 自動填入推薦單字 =====
function fillCurrentRow(word) {
  const startIdx = STATE.currentRow * 5;
  const row = STATE.grid.slice(startIdx, startIdx + 5);

  word.split('').forEach((letter, i) => {
    row[i].textContent = letter.toUpperCase();
    // 自動設定為灰色狀態（預設為不存在）
    row[i].dataset.state = 'gray';
  });

  focusCell(STATE.currentRow, 0);
}

// ===== 註冊 Service Worker =====
async function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      // 使用相對路徑，適配 GitHub Pages 子路徑部署
      const registration = await navigator.serviceWorker.register('sw.js', { scope: './' });
      console.log('[SW] 註冊成功:', registration.scope);

      // 監聽更新
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // 有新版本可用
            if (confirm('New version available. Reload now?')) {
              newWorker.postMessage('skipWaiting');
              window.location.reload();
            }
          }
        });
      });
    } catch (error) {
      console.error('[SW] 註冊失敗:', error);
    }
  }
}

// ===== 啟動應用 =====
document.addEventListener('DOMContentLoaded', init);
