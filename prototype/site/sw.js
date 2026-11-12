// Прво мрежа, па зачуваното: страницата е свежа кога има интернет, а се отвора и во маркет без сигнал.
const CACHE = "my-shopping-1";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", event => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET" || new URL(request.url).origin !== location.origin) return;
  event.respondWith(
    fetch(request).then(response => {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put(request, copy));
      return response;
    }).catch(() => caches.match(request, { ignoreSearch: true }))
  );
});
