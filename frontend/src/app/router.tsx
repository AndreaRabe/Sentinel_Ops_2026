import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/app-shell";
import { LoginPage } from "@/pages/login";
import { ChangePasswordPage } from "@/pages/change-password";
import { DashboardPage } from "@/pages/dashboard";
import { TasksPage } from "@/pages/tasks";
import { PlanningPage } from "@/pages/planning";
import { IncidentsPage } from "@/pages/incidents";
import { ReportsPage } from "@/pages/reports";
import { AuditPage } from "@/pages/audit";
import { AdminPage } from "@/pages/admin";
import { SettingsPage } from "@/pages/settings";
import { ProtectedRoute } from "./protected-route";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/change-password",
    element: (
      <ProtectedRoute allowMustChangePassword>
        <ChangePasswordPage />
      </ProtectedRoute>
    ),
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      {
        path: "taches",
        element: (
          <ProtectedRoute requiredPermission="task:read">
            <TasksPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "planning",
        element: (
          <ProtectedRoute requiredPermission="planning:read">
            <PlanningPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "incidents",
        element: (
          <ProtectedRoute requiredPermission="incident:read">
            <IncidentsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "rapports",
        element: (
          <ProtectedRoute requiredPermission="report:read">
            <ReportsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "audit",
        element: (
          <ProtectedRoute requiredPermission="audit:read">
            <AuditPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "administration",
        element: (
          <ProtectedRoute requiredPermission="user:read">
            <AdminPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "parametres",
        element: (
          <ProtectedRoute requiredPermission="settings:read">
            <SettingsPage />
          </ProtectedRoute>
        ),
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
