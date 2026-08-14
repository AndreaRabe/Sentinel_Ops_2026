/**
 * Coquille applicative : navigation laterale + barre haute.
 *
 * Les entrees de navigation sont filtrees par permission : un agent ne voit
 * ni Administration ni Audit. Le filtrage est cosmetique (voir Can) - les
 * routes elles-memes sont protegees par ProtectedRoute et le backend.
 */
import { NavLink, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/auth-store";
import { cn } from "@/lib/cn";
import { NotificationBell } from "./notification-bell";
import { UserMenu } from "./user-menu";

interface NavItem {
  to: string;
  label: string;
  permission?: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard" },
  { to: "/taches", label: "Taches", permission: "task:read" },
  { to: "/planning", label: "Planning", permission: "planning:read" },
  { to: "/incidents", label: "Incidents", permission: "incident:read" },
  { to: "/rapports", label: "Rapports", permission: "report:read" },
  { to: "/audit", label: "Audit", permission: "audit:read" },
  { to: "/administration", label: "Administration", permission: "user:read" },
  { to: "/parametres", label: "Parametres", permission: "settings:read" },
];

export function AppShell() {
  const permissions = useAuthStore((s) => s.permissions);
  const canSee = (permission?: string) =>
    !permission || permissions.includes("*") || permissions.includes(permission);

  return (
    <div className="flex min-h-screen bg-bg text-textPrimary">
      <aside className="hidden w-56 shrink-0 border-r border-border md:block">
        <div className="border-b border-border px-5 py-4">
          <span className="font-mono text-[11px] uppercase tracking-widest text-textTertiary">
            Sentinel Ops
          </span>
        </div>
        <nav aria-label="Navigation principale" className="py-3">
          {NAV_ITEMS.filter((item) => canSee(item.permission)).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "block border-l-2 px-5 py-2 text-sm transition-colors",
                  isActive
                    ? "border-primary bg-surface text-textPrimary"
                    : "border-transparent text-textSecondary hover:bg-surfaceHover hover:text-textPrimary"
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border px-5 py-3">
          <nav aria-label="Navigation principale (mobile)" className="flex gap-3 md:hidden">
            {NAV_ITEMS.filter((item) => canSee(item.permission))
              .slice(0, 4)
              .map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    cn("text-sm", isActive ? "text-textPrimary" : "text-textSecondary")
                  }
                >
                  {item.label}
                </NavLink>
              ))}
          </nav>
          <div className="hidden md:block" />
          <div className="flex items-center gap-3">
            <NotificationBell />
            <UserMenu />
          </div>
        </header>

        <main className="flex-1 px-5 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
