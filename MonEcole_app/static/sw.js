/**
 * MonEcole Service Worker — PWA offline support.
 * Stratégie : Network-first pour API, Cache-first pour assets statiques.
 */

const CACHE_NAME = 'monecole-v1';
const STATIC_ASSETS = [
  '/static/manifest.json',
  '/static/MonEcole_app/icons/icon-512.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
];

// Install — pre-cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('[SW] Pre-cache partial failure:', err);
      });
    })
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch — network-first for API/pages, cache-first for static
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET
  if (event.request.method !== 'GET') return;

  // API calls → network only (no cache for dynamic data)
  if (url.pathname.startsWith('/api/')) return;

  // Static assets → cache-first
  if (
    url.pathname.startsWith('/static/') ||
    url.hostname.includes('cdn.jsdelivr.net') ||
    url.hostname.includes('cdnjs.cloudflare.com') ||
    url.hostname.includes('fonts.googleapis.com') ||
    url.hostname.includes('fonts.gstatic.com')
  ) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        return cached || fetch(event.request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // Pages → network-first with offline fallback
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

// ═══ PUSH NOTIFICATIONS — System-level (phone notification bar) ═══
self.addEventListener('push', (event) => {
  let data = { title: 'MonEcole', body: 'Nouveau message', icon: '/static/MonEcole_app/icons/icon-512.png' };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch (e) {
    if (event.data) data.body = event.data.text();
  }
  const options = {
    body: data.body || 'Nouveau message reçu',
    icon: data.icon || '/static/MonEcole_app/icons/icon-512.png',
    badge: '/static/MonEcole_app/icons/icon-512.png',
    tag: data.tag || 'monecole-msg-' + Date.now(),
    renotify: true,
    requireInteraction: true, // Stays until user taps — WhatsApp behavior
    vibrate: [200, 100, 200, 100, 200],
    data: { url: data.url || '/parent/', thread_id: data.thread_id || '' },
    actions: [
      { action: 'open', title: 'Ouvrir' },
      { action: 'dismiss', title: 'Ignorer' }
    ]
  };
  event.waitUntil(self.registration.showNotification(data.title || 'MonEcole', options));
});

// Handle notification click — open app at the right page
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  const url = event.notification.data?.url || '/parent/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes('/parent/') && 'focus' in client) {
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});

// Periodic background sync — check for new messages (where supported)
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'check-messages') {
    event.waitUntil(checkNewMessages());
  }
});

async function checkNewMessages() {
  // Lightweight check — browser will call this periodically
  try {
    const r = await fetch('/parent/api/messages/unread-count/');
    const d = await r.json();
    if (d.success && d.count > 0) {
      self.registration.showNotification('MonEcole', {
        body: `${d.count} nouveau${d.count > 1 ? 'x' : ''} message${d.count > 1 ? 's' : ''}`,
        icon: '/static/MonEcole_app/icons/icon-512.png',
        badge: '/static/MonEcole_app/icons/icon-512.png',
        tag: 'monecole-unread',
        requireInteraction: true,
        vibrate: [200, 100, 200],
        data: { url: '/parent/' }
      });
    }
  } catch (e) { /* offline or error — skip */ }
}
