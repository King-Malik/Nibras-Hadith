const CACHE_NAME = 'hadith-pwa-v3';
const CACHE_PAGES = 'hadith-pages-v3';

// 1. إضافة الروابط الأساسية لضمان عمل التطبيق Offline
const STATIC_ASSETS = [
  '/', 
  '/index.html',
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-180x180.png',
  '/static/icons/icon-512x512.png',
  '/static/icons/icon-152x152.png',
  '/static/icons/icon-72x72.png',
  '/static/icons/icon-384x384.png',
];

// ── Install: تخزين الملفات الأساسية ─────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('SW: Caching Static Assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
      .catch(err => console.error('SW: Install Error', err))
  );
});

// ── Activate: تنظيف الكاش القديم ───────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_NAME && k !== CACHE_PAGES)
          .map(k => caches.delete(k))
      )
    ).then(() => {
      console.log('SW: Activated and Old Caches Cleared');
      return self.clients.claim();
    })
  );
});

// ── Fetch: استراتيجيات جلب البيانات ────────────────────────────
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);

  // تجاهل الطلبات غير GET
  if (req.method !== 'GET') return;

  // تجاهل أدوات التطوير والـ Extensions
  if (url.protocol === 'chrome-extension:' || (url.hostname === 'localhost' && url.port === '3000')) return;

  // ── أ: خطوط جوجل (Stale-While-Revalidate)
  if (url.hostname.includes('fonts.googleapis.com') || url.hostname.includes('fonts.gstatic.com')) {
    event.respondWith(
      caches.open(CACHE_NAME).then(cache => {
        return cache.match(req).then(cached => {
          const fetchPromise = fetch(req).then(networkRes => {
            if (networkRes.ok) cache.put(req, networkRes.clone());
            return networkRes;
          }).catch(() => null);
          return cached || fetchPromise;
        });
      })
    );
    return;
  }

  // ── ب: صفحات HTML (Network First مع Fallback)
  if (req.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(req)
        .then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_PAGES).then(cache => cache.put(req, clone));
          }
          return res;
        })
        .catch(() => {
          // إذا فشل الشبكة، ابحث في كاش الصفحات، وإذا لم تجد، ابحث عن الـ Root
          return caches.match(req).then(cached => cached || caches.match('/'));
        })
    );
    return;
  }

  // ── ج: الملفات الثابتة /static/ (Cache First)
  if (url.pathname.includes('/static/')) {
    event.respondWith(
      caches.match(req).then(cached => {
        return cached || fetch(req).then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(req, clone));
          }
          return res;
        });
      })
    );
    return;
  }

  // ── د: باقي الطلبات (الافتراضي)
  event.respondWith(
    caches.match(req).then(cached => {
      return cached || fetch(req).catch(() => {
        // إذا كان الطلب صورة، يمكنك إرجاع صورة "Offline" هنا
        return new Response('Offline content unavailable');
      });
    })
  );
});
