self.addEventListener("push", (event) => {
  const d = event.data ? event.data.json() : {};
  event.waitUntil(
    self.registration.showNotification(d.title || "Alien-Trade", {
      body: d.body || "", data: { url: d.url || "/" },
      icon: "/logo.png", badge: "/logo.png",
    })
  );
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data?.url || "/"));
});
