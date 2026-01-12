/**
 * Service Worker for Wordle Solver PWA
 * 提供離線快取與快速二次載入
 */

const CACHE_NAME = 'wordle-solver-v1.0.1';
const PYODIDE_CACHE = 'pyodide-cache-v1';

// 需要快取的靜態資源（使用相對路徑，適配 GitHub Pages 子路徑部署）
const STATIC_ASSETS = [
  './',
  './index.html',
  './styles.css',
  './app.js',
  './manifest.json',
  './assets/five_letter_words.json',
  // Python 核心模組
  './src/constraints.py',
  './src/dictionary.py',
  './src/solver.py',
  './src/recommender.py',
  './src/stats.py'
];

// Pyodide 相關資源（較大，分開快取）
const PYODIDE_ASSETS = [
  'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js',
  'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.asm.js',
  'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.asm.wasm',
  'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/python_stdlib.zip'
];

// ===== 安裝階段 =====
self.addEventListener('install', event => {
  console.log('[SW] 安裝中...');

  event.waitUntil(
    Promise.all([
      // 快取靜態資源
      caches.open(CACHE_NAME).then(cache => {
        console.log('[SW] 快取靜態資源:', STATIC_ASSETS.length, '個');
        return cache.addAll(STATIC_ASSETS);
      }),

      // 快取 Pyodide（允許失敗）
      caches.open(PYODIDE_CACHE).then(cache => {
        console.log('[SW] 快取 Pyodide 資源（背景）');
        // 不阻塞安裝，背景下載
        return Promise.allSettled(
          PYODIDE_ASSETS.map(url =>
            cache.add(url).catch(err => {
              console.warn('[SW] 快取失敗:', url, err);
            })
          )
        );
      })
    ]).then(() => {
      console.log('[SW] 安裝完成');
      self.skipWaiting();  // 立即啟用
    })
  );
});

// ===== 啟用階段 =====
self.addEventListener('activate', event => {
  console.log('[SW] 啟用中...');

  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          // 刪除舊版快取
          if (cacheName !== CACHE_NAME && cacheName !== PYODIDE_CACHE) {
            console.log('[SW] 刪除舊快取:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] 啟用完成');
      self.clients.claim();  // 立即控制所有頁面
    })
  );
});

// ===== 請求攔截 =====
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // 只處理 GET 請求
  if (request.method !== 'GET') {
    return;
  }

  // 策略：Cache First（快取優先）
  event.respondWith(
    caches.match(request).then(cachedResponse => {
      if (cachedResponse) {
        console.log('[SW] 快取命中:', url.pathname);
        return cachedResponse;
      }

      // 快取未命中，從網路取得
      console.log('[SW] 網路請求:', url.pathname);
      return fetch(request).then(response => {
        // 只快取成功的回應
        if (!response || response.status !== 200 || response.type === 'error') {
          return response;
        }

        // 複製回應（因為 response 是 stream，只能讀一次）
        const responseToCache = response.clone();

        // 決定快取位置
        const cacheName = url.hostname.includes('pyodide')
          ? PYODIDE_CACHE
          : CACHE_NAME;

        caches.open(cacheName).then(cache => {
          cache.put(request, responseToCache);
        });

        return response;
      });
    }).catch(error => {
      console.error('[SW] 請求失敗:', url.pathname, error);

      // 如果是 HTML，返回離線頁面（選用）
      if (request.headers.get('accept').includes('text/html')) {
        return caches.match('/index.html');
      }
    })
  );
});

// ===== 訊息處理（允許頁面手動觸發快取更新）=====
self.addEventListener('message', event => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  } else if (event.data === 'clearCache') {
    event.waitUntil(
      caches.keys().then(names =>
        Promise.all(names.map(name => caches.delete(name)))
      ).then(() => {
        event.ports[0].postMessage({ success: true });
      })
    );
  }
});
