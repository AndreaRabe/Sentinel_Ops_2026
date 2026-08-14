/**
 * Compteur de notifications non lues + panneau deroulant.
 *
 * Le compteur est rafraichi periodiquement par React Query : c'est suffisant
 * pour un usage LAN et evite d'introduire un WebSocket (hors perimetre V1).
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  listNotifications,
  markNotificationsRead,
  unreadCount,
  type Notification,
} from "@/features/notifications/api";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/cn";

const POLL_INTERVAL_MS = 60_000;

const RESOURCE_ROUTES: Record<string, string> = {
  task: "/taches",
  incident: "/incidents",
};

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const countQuery = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: unreadCount,
    refetchInterval: POLL_INTERVAL_MS,
  });

  const listQuery = useQuery({
    queryKey: ["notifications", "list"],
    queryFn: () => listNotifications({ page: 1, page_size: 10 }),
    enabled: open,
  });

  const markRead = useMutation({
    mutationFn: markNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const unread = countQuery.data?.unread ?? 0;

  const openNotification = (notification: Notification) => {
    if (!notification.read_at) markRead.mutate([notification.id]);
    const route = notification.resource_type
      ? RESOURCE_ROUTES[notification.resource_type]
      : undefined;
    if (route && notification.resource_id) {
      navigate(`${route}?focus=${notification.resource_id}`);
      setOpen(false);
    }
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label={`Notifications${unread > 0 ? ` (${unread} non lues)` : ""}`}
        className="rounded border border-border px-3 py-1.5 text-sm text-textSecondary
                   hover:bg-surfaceHover hover:text-textPrimary"
      >
        Notifications
        {unread > 0 && (
          <span className="ml-2 rounded bg-primary px-1.5 py-0.5 font-mono text-[11px] text-white">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 border border-border bg-surface shadow-xl">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <span className="font-mono text-[11px] uppercase tracking-widest text-textTertiary">
              Notifications
            </span>
            <button
              type="button"
              className="text-xs text-textSecondary hover:text-textPrimary disabled:opacity-40"
              disabled={unread === 0 || markRead.isPending}
              onClick={() => markRead.mutate(undefined)}
            >
              Tout marquer comme lu
            </button>
          </div>

          <ul className="max-h-80 overflow-y-auto">
            {listQuery.isLoading && (
              <li className="px-3 py-4 text-sm text-textSecondary">Chargement…</li>
            )}
            {listQuery.data?.items.length === 0 && (
              <li className="px-3 py-4 text-sm text-textSecondary">Aucune notification.</li>
            )}
            {listQuery.data?.items.map((notification) => (
              <li key={notification.id} className="border-b border-border last:border-b-0">
                <button
                  type="button"
                  onClick={() => openNotification(notification)}
                  className={cn(
                    "block w-full px-3 py-2 text-left hover:bg-surfaceHover",
                    !notification.read_at && "bg-surfaceElevated"
                  )}
                >
                  <span className="block text-sm text-textPrimary">{notification.title}</span>
                  <span className="mt-0.5 block font-mono text-[11px] text-textTertiary">
                    {formatRelative(notification.created_at)}
                    {!notification.read_at && " · non lue"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
