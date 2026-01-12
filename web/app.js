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
  console.log('[Init] 載入初始推薦...');

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
    'candidates': recommendations['candidates'][:5],
    'explorations': recommendations['explorations'][:5]
})
    `);

    const data = JSON.parse(result);
    console.log('[Init] 初始推薦載入完成:', data);

    // 更新 UI
    updateRecommendations(data.candidates, data.explorations);
  } catch (error) {
    console.error('[Init] 載入初始推薦失敗:', error);
    // 不影響主流程，只記錄錯誤
  }
}

// ===== 初始化 =====
async function init() {
  console.log('[Init] 開始初始化...');

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

  // 載入 Pyodide
  try {
    await initPyodide();
    console.log('[Init] Pyodide 載入完成');

    // 顯示主要內容
    DOM.loadingIndicator.classList.add('hidden');
    DOM.mainContent.classList.remove('hidden');

    // 載入初始推薦
    await loadInitialRecommendations();

    // 註冊 Service Worker
    await registerServiceWorker();
  } catch (error) {
    showError(`載入失敗: ${error.message}`);
    console.error('[Init] 錯誤:', error);
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

      // 點擊事件：輸入字母或切換顏色
      cell.addEventListener('click', () => handleCellClick(row, col));

      DOM.grid.appendChild(cell);
      STATE.grid.push(cell);
    }
  }
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

// ===== 提交當前行 =====
async function handleSubmit() {
  console.log('[Submit] 提交所有完整行');

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
        showError(`第 ${row + 1} 行有未標記顏色的字母，請為所有字母標記顏色`);
        return;
      }
    }
  }

  // 如果沒有完整行，提示用戶
  if (completeRows.length === 0) {
    showError('請至少輸入一個完整的 5 字母單字並標記顏色');
    return;
  }

  console.log('[Submit] 找到', completeRows.length, '個完整行');

  // 呼叫 Python 核心處理所有完整行
  try {
    DOM.submitBtn.disabled = true;
    DOM.submitBtn.textContent = '計算中...';

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
    showError(`計算錯誤: ${error.message}`);
    console.error('[Submit] 錯誤:', error);
  } finally {
    DOM.submitBtn.disabled = false;
    DOM.submitBtn.textContent = '提交當前行';
  }
}

// ===== 重置遊戲 =====
async function handleReset() {
  console.log('[Reset] 重置遊戲');

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
function showError(message) {
  DOM.errorMessage.textContent = message;
  DOM.errorMessage.classList.remove('hidden');

  setTimeout(() => {
    DOM.errorMessage.classList.add('hidden');
  }, 5000);
}

// ===== Pyodide 初始化 =====
async function initPyodide() {
  console.log('[Pyodide] 開始載入 Pyodide...');
  PERF.pyodideLoadStart = performance.now();

  // 步驟 1: 載入 Pyodide
  STATE.pyodide = await loadPyodide({
    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/"
  });
  console.log('[Pyodide] Pyodide 載入完成');

  // 步驟 2: 載入字典
  console.log('[Pyodide] 載入字典...');
  const dictResponse = await fetch('assets/five_letter_words.json');
  if (!dictResponse.ok) {
    throw new Error(`無法載入字典: ${dictResponse.status} ${dictResponse.statusText}`);
  }
  const words = await dictResponse.json();
  console.log(`[Pyodide] 字典載入完成: ${words.length} 個單字`);

  // 將字典存到 Python 全域變數
  STATE.pyodide.globals.set('WORD_LIST', words);

  // 步驟 3: 載入 Python 核心模組
  console.log('[Pyodide] 載入 Python 核心模組...');

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
      throw new Error(`無法載入 ${moduleName}: 已嘗試路徑 ${possiblePaths.join(', ')}`);
    }

    // 寫入 Pyodide 虛擬檔案系統
    STATE.pyodide.FS.writeFile(`/home/pyodide/${moduleName}`, code);
    console.log(`[Pyodide] 載入完成: ${moduleName} (從 ${loadedFrom})`);
  }

  // 步驟 4: 初始化 WordleCore
  console.log('[Pyodide] 初始化 WordleCore...');
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
  console.log('[Pyodide] 初始化完成');
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

  // 更新 UI
  updateRecommendations(data.candidates, data.explorations);

  // 記錄歷史
  STATE.history.push({ guess, feedback });
}

// ===== 更新推薦清單 =====
function updateRecommendations(candidates, explorations) {
  console.log('[UI] 更新推薦清單:', candidates.length, '候選,', explorations.length, '探索');

  // 清空兩個欄位
  DOM.candidateList.innerHTML = '';
  DOM.explorationList.innerHTML = '';

  // 檢查是否只有唯一候選
  if (candidates.length === 1) {
    const [word, score] = candidates[0];
    setTimeout(() => {
      alert(`🎉 找到唯一答案！\n\n答案很可能是: ${word.toUpperCase()}\n\n信心分數: ${score.toFixed(1)}`);
    }, 100);
  }

  // 填充候選欄（藍色）
  candidates.forEach(([word, score], index) => {
    const item = document.createElement('div');
    item.className = 'rec-item candidate';
    item.innerHTML = `
      <span class="rec-word">${index + 1}. ${word.toUpperCase()}</span>
      <span class="rec-score">${score.toFixed(1)}</span>
    `;

    item.addEventListener('click', () => {
      fillCurrentRow(word);
    });

    DOM.candidateList.appendChild(item);
  });

  // 填充探索欄（橘色）
  explorations.forEach(([word, score], index) => {
    const item = document.createElement('div');
    item.className = 'rec-item exploration';
    item.innerHTML = `
      <span class="rec-word">${index + 1}. ${word.toUpperCase()}</span>
      <span class="rec-score">${score.toFixed(1)}</span>
    `;

    item.addEventListener('click', () => {
      fillCurrentRow(word);
    });

    DOM.explorationList.appendChild(item);
  });
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
            if (confirm('有新版本可用，是否重新載入？')) {
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
