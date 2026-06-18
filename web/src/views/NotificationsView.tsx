import { NotificationPanel } from "../components/NotificationPanel";

export function NotificationsView() {
  return (
    <div className="p-3 sm:p-4">
      <NotificationPanel limit={100} />
    </div>
  );
}
