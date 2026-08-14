/**
 * Administration : comptes utilisateurs et sites.
 *
 * Point sensible : le mot de passe temporaire (creation ou reinitialisation)
 * n'est affiche qu'UNE fois, dans une boite dediee. Il n'est stocke nulle part
 * en clair et ne peut pas etre reconsulte.
 */
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Can } from "@/components/can";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Drawer } from "@/components/ui/drawer";
import { Field, Input, Select } from "@/components/ui/field";
import {
  DataTable,
  EmptyState,
  ErrorState,
  PageHeader,
  Pagination,
  SectionTitle,
} from "@/components/ui/data-display";
import { ScanLoader } from "@/components/ui/loaders";
import { ROLE_LABELS } from "@/components/ui/badge";
import {
  createSite,
  createUser,
  deleteSite,
  listSites,
  listUsers,
  resetUserPassword,
  setUserActivation,
  updateSite,
  updateUser,
  type Site,
  type User,
} from "@/features/admin/api";
import { apiErrorMessage } from "@/lib/api-types";
import { formatDateTime } from "@/lib/format";

const userSchema = z.object({
  first_name: z.string().min(1, "Prenom requis."),
  last_name: z.string().min(1, "Nom requis."),
  email: z.string().email("Adresse email invalide."),
  role: z.string().min(1, "Selectionnez un role."),
  site_ids: z.array(z.string().uuid()),
});

type UserFormValues = z.infer<typeof userSchema>;

/** Roles a portee globale : ils ne prennent aucune affectation de site. */
const GLOBAL_SCOPE_ROLES = ["super_admin", "responsable"];

export function AdminPage() {
  const [tab, setTab] = useState<"users" | "sites">("users");

  return (
    <>
      <PageHeader
        title="Administration"
        subtitle="Comptes utilisateurs, roles et sites."
      />

      <div className="mb-5 flex rounded border border-border">
        {(
          [
            ["users", "Utilisateurs"],
            ["sites", "Sites"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => setTab(value)}
            className={
              "px-4 py-1.5 font-mono text-[11px] uppercase tracking-widest " +
              (tab === value ? "bg-surface text-textPrimary" : "text-textTertiary")
            }
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "users" ? <UsersTab /> : <SitesTab />}
    </>
  );
}

function TemporaryPasswordDialog({
  password,
  onClose,
}: {
  password: string | null;
  onClose: () => void;
}) {
  if (!password) return null;
  return (
    <ConfirmDialog
      open
      title="Mot de passe temporaire"
      message={`Transmettez ce mot de passe a l'utilisateur hors application. Il ne sera plus affiche : ${password}`}
      confirmLabel="J'ai note"
      onConfirm={onClose}
      onCancel={onClose}
    />
  );
}

function UsersTab() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  /** Non nul = le drawer est en mode edition sur cet utilisateur. */
  const [editTarget, setEditTarget] = useState<User | null>(null);
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(null);
  const [resetTarget, setResetTarget] = useState<User | null>(null);

  const sites = useQuery({ queryKey: ["sites"], queryFn: () => listSites(true) });
  const usersQuery = useQuery({
    queryKey: ["users", { page, search }],
    queryFn: () => listUsers({ page, page_size: 25, q: search || undefined }),
  });

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<UserFormValues>({
    resolver: zodResolver(userSchema),
    defaultValues: { first_name: "", last_name: "", email: "", role: "agent", site_ids: [] },
  });

  const selectedRole = watch("role");
  const needsSites = !GLOBAL_SCOPE_ROLES.includes(selectedRole);

  const closeForm = () => {
    setCreateOpen(false);
    setEditTarget(null);
    reset({ first_name: "", last_name: "", email: "", role: "agent", site_ids: [] });
  };

  const openEdit = (user: User) => {
    reset({
      first_name: user.first_name,
      last_name: user.last_name,
      email: user.email,
      role: user.role,
      site_ids: user.sites.map((site) => site.id),
    });
    setEditTarget(user);
  };

  // La creation renvoie un mot de passe temporaire, l'edition renvoie
  // l'utilisateur : le type de retour est donc une union explicite.
  const saveMutation = useMutation<{ temporary_password: string } | User, unknown, UserFormValues>({
    mutationFn: (values: UserFormValues) => {
      const payload = { ...values, site_ids: needsSites ? values.site_ids : [] };
      return editTarget ? updateUser(editTarget.id, payload) : createUser(payload);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      // Seule la creation renvoie un mot de passe temporaire.
      if (data && "temporary_password" in data) {
        setTemporaryPassword(data.temporary_password);
      } else {
        toast.success("Utilisateur mis a jour.");
      }
      closeForm();
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Enregistrement impossible.")),
  });

  const activationMutation = useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      setUserActivation(userId, isActive),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
    onError: (error) => toast.error(apiErrorMessage(error, "Operation refusee.")),
  });

  const resetMutation = useMutation({
    mutationFn: (userId: string) => resetUserPassword(userId),
    onSuccess: (data) => {
      setResetTarget(null);
      setTemporaryPassword(data.temporary_password);
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Reinitialisation impossible.")),
  });

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Input
          className="w-64"
          placeholder="Rechercher un utilisateur…"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
        />
        <Can permission="user:create">
          <Button onClick={() => setCreateOpen(true)}>Ajouter un utilisateur</Button>
        </Can>
      </div>

      {usersQuery.isLoading && <ScanLoader label="Chargement des utilisateurs" />}
      {usersQuery.isError && <ErrorState />}
      {usersQuery.data?.items.length === 0 && <EmptyState title="Aucun utilisateur." />}

      {usersQuery.data && usersQuery.data.items.length > 0 && (
        <>
          <DataTable
            caption="Utilisateurs"
            headers={["Nom", "Email", "Role", "Sites", "Derniere connexion", "Etat", ""]}
          >
            {usersQuery.data.items.map((user) => (
              <tr key={user.id} className="border-b border-border">
                <td className="px-3 py-2 text-textPrimary">
                  {user.first_name} {user.last_name}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-textSecondary">{user.email}</td>
                <td className="px-3 py-2 text-textSecondary">
                  {ROLE_LABELS[user.role] ?? user.role}
                </td>
                <td className="px-3 py-2 text-textSecondary">
                  {user.sites.length ? user.sites.map((site) => site.name).join(", ") : "Tous"}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-textSecondary">
                  {formatDateTime(user.last_login_at)}
                </td>
                <td className="px-3 py-2 text-textSecondary">
                  {user.is_active ? "Actif" : "Desactive"}
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    <Can permission="user:update">
                      <button
                        type="button"
                        className="font-mono text-[11px] uppercase text-textTertiary hover:text-textPrimary"
                        onClick={() => openEdit(user)}
                      >
                        Modifier
                      </button>
                    </Can>
                    <Can permission="user:reset_password">
                      <button
                        type="button"
                        className="font-mono text-[11px] uppercase text-textTertiary hover:text-textPrimary"
                        onClick={() => setResetTarget(user)}
                      >
                        Reinitialiser
                      </button>
                    </Can>
                    <Can permission="user:deactivate">
                      <button
                        type="button"
                        className="font-mono text-[11px] uppercase text-textTertiary hover:text-textPrimary"
                        onClick={() =>
                          activationMutation.mutate({
                            userId: user.id,
                            isActive: !user.is_active,
                          })
                        }
                      >
                        {user.is_active ? "Desactiver" : "Reactiver"}
                      </button>
                    </Can>
                  </div>
                </td>
              </tr>
            ))}
          </DataTable>
          <Pagination
            page={usersQuery.data.page}
            pages={usersQuery.data.pages}
            total={usersQuery.data.total}
            onChange={setPage}
          />
        </>
      )}

      <Drawer
        open={createOpen || Boolean(editTarget)}
        onClose={closeForm}
        title={editTarget ? "Modifier l'utilisateur" : "Nouvel utilisateur"}
        description={
          editTarget
            ? "Le mot de passe n'est pas modifiable ici : utilisez la reinitialisation."
            : "Un mot de passe temporaire sera genere et affiche une seule fois."
        }
        footer={
          <>
            <Button variant="secondary" onClick={closeForm}>
              Annuler
            </Button>
            <Button
              loading={saveMutation.isPending}
              onClick={handleSubmit((values) => saveMutation.mutate(values))}
            >
              {editTarget ? "Enregistrer" : "Creer le compte"}
            </Button>
          </>
        }
      >
        <form className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Prenom" htmlFor="first_name" error={errors.first_name?.message} required>
              <Input id="first_name" {...register("first_name")} />
            </Field>
            <Field label="Nom" htmlFor="last_name" error={errors.last_name?.message} required>
              <Input id="last_name" {...register("last_name")} />
            </Field>
          </div>
          <Field label="Email" htmlFor="email" error={errors.email?.message} required>
            <Input id="email" type="email" {...register("email")} />
          </Field>
          <Field label="Role" htmlFor="role" error={errors.role?.message} required>
            <Select id="role" {...register("role")}>
              <option value="agent">Agent</option>
              <option value="chef_equipe">Chef d'equipe</option>
              <option value="responsable">Responsable</option>
              {/* Propose uniquement en edition d'un compte qui l'est deja : le
                  backend refuse d'attribuer ce role a quiconque n'est pas
                  lui-meme Super Admin. */}
              {editTarget?.role === "super_admin" && (
                <option value="super_admin">Super Admin</option>
              )}
            </Select>
          </Field>
          <Field
            label="Sites"
            hint={
              needsSites
                ? "Au moins un site est obligatoire pour ce role."
                : "Ce role couvre tous les sites : aucune affectation a faire."
            }
          >
            <Select multiple size={5} disabled={!needsSites} {...register("site_ids")}>
              {sites.data?.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.name}
                </option>
              ))}
            </Select>
          </Field>
        </form>
      </Drawer>

      <ConfirmDialog
        open={Boolean(resetTarget)}
        title="Reinitialiser le mot de passe"
        message={
          resetTarget
            ? `Un mot de passe temporaire sera genere pour ${resetTarget.first_name} ${resetTarget.last_name}, et toutes ses sessions seront fermees.`
            : ""
        }
        confirmLabel="Reinitialiser"
        loading={resetMutation.isPending}
        onConfirm={() => resetTarget && resetMutation.mutate(resetTarget.id)}
        onCancel={() => setResetTarget(null)}
      />

      <TemporaryPasswordDialog
        password={temporaryPassword}
        onClose={() => setTemporaryPassword(null)}
      />
    </>
  );
}

function SitesTab() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Site | null>(null);
  const [renameTarget, setRenameTarget] = useState<Site | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const sitesQuery = useQuery({ queryKey: ["sites", "all"], queryFn: () => listSites(true) });

  const createMutation = useMutation({
    mutationFn: () => createSite(name),
    onSuccess: () => {
      setName("");
      queryClient.invalidateQueries({ queryKey: ["sites"] });
      toast.success("Site cree.");
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Creation impossible.")),
  });

  const deleteMutation = useMutation({
    mutationFn: (siteId: string) => deleteSite(siteId),
    onSuccess: () => {
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ["sites"] });
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Suppression impossible.")),
  });

  const updateMutation = useMutation({
    mutationFn: ({ siteId, payload }: { siteId: string; payload: { name?: string; is_active?: boolean } }) =>
      updateSite(siteId, payload),
    onSuccess: () => {
      setRenameTarget(null);
      queryClient.invalidateQueries({ queryKey: ["sites"] });
      toast.success("Site mis a jour.");
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Modification impossible.")),
  });

  return (
    <>
      <Can permission="site:create">
        <div className="mb-6 flex max-w-md items-end gap-2">
          <div className="flex-1">
            <Field label="Nouveau site" htmlFor="site-name">
              <Input
                id="site-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </Field>
          </div>
          <Button
            disabled={name.trim().length < 2}
            loading={createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            Ajouter
          </Button>
        </div>
      </Can>

      <SectionTitle>Sites existants</SectionTitle>
      {sitesQuery.isLoading && <ScanLoader label="Chargement des sites" rows={3} />}
      {sitesQuery.isError && <ErrorState />}
      {sitesQuery.data?.length === 0 && <EmptyState title="Aucun site." />}

      {sitesQuery.data && sitesQuery.data.length > 0 && (
        <DataTable caption="Sites" headers={["Nom", "Utilisateurs", "Etat", ""]}>
          {sitesQuery.data.map((site) => (
            <tr key={site.id} className="border-b border-border">
              <td className="px-3 py-2 text-textPrimary">{site.name}</td>
              <td className="px-3 py-2 font-mono text-xs text-textSecondary">
                {site.user_count}
              </td>
              <td className="px-3 py-2 text-textSecondary">
                {site.is_active ? "Actif" : "Inactif"}
              </td>
              <td className="px-3 py-2 text-right">
                <div className="flex justify-end gap-3">
                  <Can permission="site:update">
                    <>
                      <button
                        type="button"
                        className="font-mono text-[11px] uppercase text-textTertiary hover:text-textPrimary"
                        onClick={() => {
                          setRenameTarget(site);
                          setRenameValue(site.name);
                        }}
                      >
                        Renommer
                      </button>
                      <button
                        type="button"
                        className="font-mono text-[11px] uppercase text-textTertiary hover:text-textPrimary"
                        onClick={() =>
                          updateMutation.mutate({
                            siteId: site.id,
                            payload: { is_active: !site.is_active },
                          })
                        }
                      >
                        {site.is_active ? "Desactiver" : "Reactiver"}
                      </button>
                    </>
                  </Can>
                  <Can permission="site:delete">
                    <button
                      type="button"
                      className="font-mono text-[11px] uppercase text-textTertiary hover:text-danger"
                      onClick={() => setDeleteTarget(site)}
                    >
                      Supprimer
                    </button>
                  </Can>
                </div>
              </td>
            </tr>
          ))}
        </DataTable>
      )}

      <Drawer
        open={Boolean(renameTarget)}
        onClose={() => setRenameTarget(null)}
        title="Renommer le site"
        footer={
          <>
            <Button variant="secondary" onClick={() => setRenameTarget(null)}>
              Annuler
            </Button>
            <Button
              disabled={renameValue.trim().length < 2}
              loading={updateMutation.isPending}
              onClick={() =>
                renameTarget &&
                updateMutation.mutate({
                  siteId: renameTarget.id,
                  payload: { name: renameValue.trim() },
                })
              }
            >
              Enregistrer
            </Button>
          </>
        }
      >
        <Field label="Nom du site" htmlFor="rename-site">
          <Input
            id="rename-site"
            value={renameValue}
            onChange={(event) => setRenameValue(event.target.value)}
          />
        </Field>
      </Drawer>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Supprimer le site"
        message={
          deleteTarget
            ? `Le site « ${deleteTarget.name} » sera archive. La suppression est refusee s'il reste des utilisateurs affectes.`
            : ""
        }
        confirmLabel="Supprimer"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}
