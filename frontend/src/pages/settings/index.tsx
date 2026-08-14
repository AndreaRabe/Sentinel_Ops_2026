/**
 * Parametres systeme (Super Admin).
 *
 * Aucun secret n'est editable ici : cles, mots de passe et URL restent dans
 * `.env`, hors application (cahier des charges section 7).
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Can } from "@/components/can";
import { Button } from "@/components/ui/button";
import { Field, Input, Textarea } from "@/components/ui/field";
import {
  DataTable,
  EmptyState,
  ErrorState,
  PageHeader,
  SectionTitle,
} from "@/components/ui/data-display";
import { ScanLoader } from "@/components/ui/loaders";
import { listSettings, upsertSetting } from "@/features/admin/api";
import { apiErrorMessage } from "@/lib/api-types";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const [key, setKey] = useState("");
  const [valueText, setValueText] = useState("{}");
  const [jsonError, setJsonError] = useState<string | undefined>();

  const settings = useQuery({ queryKey: ["settings"], queryFn: listSettings });

  const mutation = useMutation({
    mutationFn: () => upsertSetting(key, JSON.parse(valueText)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      toast.success("Parametre enregistre.");
      setKey("");
      setValueText("{}");
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Enregistrement impossible.")),
  });

  const submit = () => {
    try {
      JSON.parse(valueText);
      setJsonError(undefined);
      mutation.mutate();
    } catch {
      setJsonError("La valeur doit etre un objet JSON valide.");
    }
  };

  return (
    <>
      <PageHeader
        title="Parametres"
        subtitle="Reglages fonctionnels stockes en base. Les secrets restent dans le fichier .env."
      />

      <SectionTitle>Parametres existants</SectionTitle>
      {settings.isLoading && <ScanLoader label="Chargement des parametres" rows={3} />}
      {settings.isError && <ErrorState />}
      {settings.data?.length === 0 && <EmptyState title="Aucun parametre defini." />}

      {settings.data && settings.data.length > 0 && (
        <DataTable caption="Parametres systeme" headers={["Cle", "Valeur", "Description"]}>
          {settings.data.map((setting) => (
            <tr key={setting.key} className="border-b border-border align-top">
              <td className="px-3 py-2 font-mono text-xs text-textPrimary">{setting.key}</td>
              <td className="px-3 py-2 font-mono text-[11px] text-textSecondary">
                {JSON.stringify(setting.value)}
              </td>
              <td className="px-3 py-2 text-sm text-textSecondary">
                {setting.description ?? "—"}
              </td>
            </tr>
          ))}
        </DataTable>
      )}

      <Can permission="settings:update">
        <section className="mt-10 max-w-lg">
          <SectionTitle>Creer ou modifier</SectionTitle>
          <div className="space-y-4">
            <Field label="Cle" htmlFor="setting-key">
              <Input
                id="setting-key"
                value={key}
                onChange={(event) => setKey(event.target.value)}
              />
            </Field>
            <Field label="Valeur (JSON)" htmlFor="setting-value" error={jsonError}>
              <Textarea
                id="setting-value"
                rows={4}
                className="font-mono text-xs"
                value={valueText}
                onChange={(event) => setValueText(event.target.value)}
              />
            </Field>
            <Button disabled={!key.trim()} loading={mutation.isPending} onClick={submit}>
              Enregistrer
            </Button>
          </div>
        </section>
      </Can>
    </>
  );
}
