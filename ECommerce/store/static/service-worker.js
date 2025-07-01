const CACHE_NAME = 'eshop-cache-v2';
const urlsToCache = [
  '/',
  '/cart',
  '/static/manifest.json',
  '/static/logo.png',
  '/static/offline.html',
  '/static/css/style.css',
  '/static/js/main.js',
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        return response || fetch(event.request).catch(() => caches.match('/static/offline.html'));
      })
  );
}); 