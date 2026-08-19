"use client";

import { useCallback, useEffect, useState } from "react";
import EnteteManager from "@/components/EnteteManager";
import { useRouter } from "next/navigation";
import {
  api,
  DashboardStats,
  MenuCsvImportResult,
  MenuItem,
  Restaurant,
  Staff,
  StaffRole,
  SubscriptionTier,
  Table,
} from "@/lib/api";
import { ApiError } from "@/lib/api";
import { requiredTierFromError, toFrenchMessage } from "@/lib/errors";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { clearToken } from "@/lib/auth";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import Skeleton from "@/components/ui/Skeleton";
import { MoonIcon, CoffeeIcon, UtensilsIcon, BellIcon } from "@/components/icons";
import { MENU_CATEGORIES } from "@/lib/menuCategories";
import { reduirePhoto } from "@/lib/photo";
import PhotoDuPlat, { ZonePhoto, ZonePhotoNouveau } from "@/components/PhotoDuPlat";
import RecetteDuJour from "@/components/RecetteDuJour";
import EditeurDePlan from "@/components/plan/EditeurDePlan";
import UpgradeModal from "@/components/UpgradeModal";

// Suggestions, pas un enum figé (voir Table.zone côté backend) : tous les
// établissements n'ont pas les mêmes zones, un café sans terrasse n'en a
// besoin d'aucune — texte libre avec juste un coup de pouce à la saisie.
const ZONE_SUGGESTIONS = ["Intérieur", "Terrasse", "Plage"];

const TIER_LABELS: Record<SubscriptionTier, string> = {
  essentiel: "Essentiel",
  pro: "Pro",
  business: "Business",
};

type TableDraft = { label: string; zone: string };

function tableToDraft(table: Table): TableDraft {
  return { label: table.label, zone: table.zone ?? "" };
}

const EMPTY_TABLE_DRAFT: TableDraft = { label: "", zone: "" };

// Convertit un ISO UTC en valeur pour <input type="datetime-local"> (heure
// locale du navigateur) et inversement — sans lib externe.
function isoToLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function localInputToIso(value: string): string | null {
  if (!value) return null;
  return new Date(value).toISOString();
}

type Draft = {
  name: string;
  category: string;
  price: string;
  description: string;
  spiceLevel: string;
  allergens: string;
  isHalal: boolean;
};

// Les <option> HTML ne peuvent afficher que du texte brut, jamais un
// composant icône — l'iconographie SVG cohérente (FlameIcon) est réservée à
// l'affichage du niveau de piment côté menu client (voir menu/[qrToken]).
const SPICE_LABELS = ["Pas épicé", "Léger", "Moyen", "Fort"];

function itemToDraft(item: MenuItem): Draft {
  return {
    name: item.name,
    category: item.category,
    price: String(item.price),
    description: item.description ?? "",
    spiceLevel: String(item.spice_level),
    allergens: item.allergens ?? "",
    isHalal: item.is_halal,
  };
}

const EMPTY_DRAFT: Draft = {
  name: "",
  category: "Plats",
  price: "",
  description: "",
  spiceLevel: "0",
  allergens: "",
  isHalal: true,
};

type Tab = "menu" | "tables" | "team" | "settings";

const TABS: { key: Tab; label: string }[] = [
  { key: "menu", label: "Menu" },
  { key: "tables", label: "Tables & zones" },
  { key: "team", label: "Équipe" },
  { key: "settings", label: "Réglages" },
];

const ROLE_LABELS: Record<StaffRole, string> = {
  waiter: "Serveur",
  kitchen: "Cuisine",
  manager: "Manager",
};

type StaffDraft = { name: string; role: StaffRole };

function staffToDraft(member: Staff): StaffDraft {
  return { name: member.name, role: member.role };
}

type NewStaffDraft = { name: string; email: string; role: StaffRole };

const EMPTY_STAFF_DRAFT: NewStaffDraft = { name: "", email: "", role: "waiter" };

export default function DashboardPage() {
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["manager"]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [photoEnCours, setPhotoEnCours] = useState<number | null>(null);
  // Photo choisie pour un plat pas encore créé : elle attend d'avoir un
  // identifiant à qui être rattachée.
  const [nouvellePhoto, setNouvellePhoto] = useState<File | null>(null);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [newItem, setNewItem] = useState<Draft>(EMPTY_DRAFT);
  const [error, setError] = useState<string | null>(null);
  const [upgradeTier, setUpgradeTier] = useState<SubscriptionTier | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [dayStats, setDayStats] = useState<DashboardStats | null>(null);
  const [savingPlan, setSavingPlan] = useState(false);
  const [ramadanEnabled, setRamadanEnabled] = useState(false);
  const [iftarInput, setIftarInput] = useState("");
  const [savingRamadan, setSavingRamadan] = useState(false);
  const [cafeModeEnabled, setCafeModeEnabled] = useState(false);
  const [savingCafeMode, setSavingCafeMode] = useState(false);
  const [kitchenSoundEnabled, setKitchenSoundEnabled] = useState(false);
  const [savingKitchenSound, setSavingKitchenSound] = useState(false);
  const [tables, setTables] = useState<Table[]>([]);
  const [tableDrafts, setTableDrafts] = useState<Record<number, TableDraft>>({});
  const [newTable, setNewTable] = useState<TableDraft>(EMPTY_TABLE_DRAFT);
  const [team, setTeam] = useState<Staff[]>([]);
  const [staffDrafts, setStaffDrafts] = useState<Record<number, StaffDraft>>({});
  const [newStaff, setNewStaff] = useState<NewStaffDraft>(EMPTY_STAFF_DRAFT);
  const [savingStaff, setSavingStaff] = useState(false);
  // Identifiants à transmettre de la main à la main : affichés jusqu'à ce que
  // le manager les ferme, jamais effacés par un timer — il doit avoir le temps
  // de les recopier, et ils sont irrécupérables ensuite.
  const [newCredentials, setNewCredentials] = useState<{ email: string; password: string } | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("menu");
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [addingItem, setAddingItem] = useState(false);
  const [importing, setImporting] = useState(false);
  const [csvContent, setCsvContent] = useState("");
  const [csvReplace, setCsvReplace] = useState(false);
  const [csvResult, setCsvResult] = useState<MenuCsvImportResult | null>(null);
  const [savingCsv, setSavingCsv] = useState(false);
  const [suggestions, setSuggestions] = useState<Record<string, number[]>>({});
  const [savingSuggestionsFor, setSavingSuggestionsFor] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");

  const restaurantId = staff?.restaurant_id ?? null;

  const load = useCallback(async () => {
    if (!restaurantId) return;
    try {
      const [menu, rest, tableList, teamList, suggested, dayStats] = await Promise.all([
        api.getMenu(restaurantId),
        api.getRestaurant(restaurantId),
        api.listTables(restaurantId),
        api.listStaff(restaurantId),
        api.getMenuSuggestions(restaurantId),
        // Best-effort : si les chiffres du jour échouent, le manager doit
        // quand même pouvoir gérer sa carte et ses tables.
        api.getDashboardStats(restaurantId).catch(() => null),
      ]);
      setDayStats(dayStats);
      setItems(menu);
      setDrafts(Object.fromEntries(menu.map((m) => [m.id, itemToDraft(m)])));
      setRestaurant(rest);
      setRamadanEnabled(rest.ramadan_mode_enabled);
      setIftarInput(isoToLocalInput(rest.iftar_time));
      setCafeModeEnabled(rest.cafe_mode_enabled);
      setKitchenSoundEnabled(rest.kitchen_sound_enabled);
      setTables(tableList);
      setTableDrafts(Object.fromEntries(tableList.map((t) => [t.id, tableToDraft(t)])));
      setTeam(teamList);
      setStaffDrafts(Object.fromEntries(teamList.map((m) => [m.id, staffToDraft(m)])));
      setSuggestions(suggested);
    } catch (e) {
      handleGatedError(e);
    }
  }, [restaurantId]);

  useEffect(() => {
    if (restaurantId) load();
  }, [restaurantId, load]);

  /**
   * Remplace `setError(toFrenchMessage(e))` dans tous les catch de cette
   * page : un refus `UPGRADE_REQUIRED` ouvre l'écran d'incitation à passer au
   * palier supérieur au lieu du simple bandeau rouge (paiement en ligne du
   * passage à un palier supérieur, 2026-08-19) ; toute autre erreur se
   * comporte exactement comme avant.
   */
  function handleGatedError(e: unknown) {
    const tier = requiredTierFromError(e);
    if (tier) {
      setUpgradeTier(tier);
      return;
    }
    setError(toFrenchMessage(e));
  }

  async function saveRamadanMode(nextEnabled: boolean) {
    if (!restaurantId) return;
    setError(null);
    setSavingRamadan(true);
    try {
      const updated = await api.setRamadanMode(restaurantId, nextEnabled, localInputToIso(iftarInput));
      setRestaurant(updated);
      setRamadanEnabled(updated.ramadan_mode_enabled);
      flash(nextEnabled ? "Mode Ramadan activé." : "Mode Ramadan désactivé.");
    } catch (e) {
      setRamadanEnabled(!nextEnabled);
      handleGatedError(e);
    } finally {
      setSavingRamadan(false);
    }
  }

  async function saveCafeMode(nextEnabled: boolean) {
    if (!restaurantId) return;
    setError(null);
    setSavingCafeMode(true);
    try {
      const updated = await api.setCafeMode(restaurantId, nextEnabled);
      setRestaurant(updated);
      setCafeModeEnabled(updated.cafe_mode_enabled);
      flash(nextEnabled ? "Mode café simplifié activé." : "Mode café simplifié désactivé.");
    } catch (e) {
      handleGatedError(e);
    } finally {
      setSavingCafeMode(false);
    }
  }

  async function saveKitchenSound(nextEnabled: boolean) {
    if (!restaurantId) return;
    setError(null);
    setSavingKitchenSound(true);
    try {
      const updated = await api.setKitchenSound(restaurantId, nextEnabled);
      setRestaurant(updated);
      setKitchenSoundEnabled(updated.kitchen_sound_enabled);
      flash(nextEnabled ? "Retour sonore cuisine activé." : "Retour sonore cuisine désactivé.");
    } catch (e) {
      handleGatedError(e);
    } finally {
      setSavingKitchenSound(false);
    }
  }


  function flash(text: string) {
    setMessage(text);
    setTimeout(() => setMessage(null), 2500);
  }

  async function saveItem(item: MenuItem) {
    setError(null);
    const draft = drafts[item.id];
    const price = Number(draft.price);
    if (!draft.name.trim() || Number.isNaN(price) || price < 0) {
      setError("Nom et prix (positif) sont obligatoires.");
      return;
    }
    try {
      await api.updateMenuItem(item.id, {
        name: draft.name.trim(),
        category: draft.category,
        price,
        description: draft.description.trim() || null,
        // `image_url` volontairement absent : la photo est gérée par ses
        // propres routes. L'envoyer d'ici renverrait la valeur du brouillon,
        // figée à l'ouverture du formulaire — enregistrer un changement de
        // prix après avoir déposé une photo l'aurait effacée.
        spice_level: Number(draft.spiceLevel),
        allergens: draft.allergens.trim() || null,
        is_halal: draft.isHalal,
      });
      flash(`« ${draft.name} » enregistré.`);
      setEditingItemId(null);
      await load();
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function deposerPhoto(item: MenuItem, fichier: File) {
    setError(null);
    setPhotoEnCours(item.id);
    try {
      // Réduite dans le navigateur avant l'envoi : une photo de téléphone
      // brute mettrait la connexion du restaurant à genoux en plein service.
      const reduite = await reduirePhoto(fichier);
      const misAJour = await api.uploadMenuItemPhoto(item.id, reduite);
      setItems((prev) => prev.map((i) => (i.id === item.id ? misAJour : i)));
      flash(`Photo ajoutée à « ${item.name} ».`);
    } catch (e) {
      handleGatedError(e);
    } finally {
      setPhotoEnCours(null);
    }
  }

  async function retirerPhoto(item: MenuItem) {
    setError(null);
    try {
      const misAJour = await api.deleteMenuItemPhoto(item.id);
      setItems((prev) => prev.map((i) => (i.id === item.id ? misAJour : i)));
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function toggleAvailability(item: MenuItem) {
    setError(null);
    try {
      await api.setMenuItemAvailability(item.id, !item.is_available);
      await load();
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function removeItem(item: MenuItem) {
    if (!confirm(`Supprimer « ${item.name} » du menu ?`)) return;
    setError(null);
    try {
      await api.deleteMenuItem(item.id);
      flash(`« ${item.name} » supprimé.`);
      setEditingItemId(null);
      await load();
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function addItem() {
    setError(null);
    if (!restaurantId) return;
    const price = Number(newItem.price);
    if (!newItem.name.trim() || Number.isNaN(price) || price < 0) {
      setError("Nom et prix (positif) sont obligatoires pour ajouter un article.");
      return;
    }
    try {
      const cree = await api.createMenuItem({
        restaurant_id: restaurantId,
        name: newItem.name.trim(),
        category: newItem.category,
        price,
        description: newItem.description.trim() || null,
        spice_level: Number(newItem.spiceLevel),
        allergens: newItem.allergens.trim() || null,
        is_halal: newItem.isHalal,
      });
      // La photo part après coup : elle a besoin de l'identifiant du plat, qui
      // n'existe qu'une fois celui-ci créé. Un échec ici ne doit pas faire
      // croire que le plat n'a pas été ajouté — il l'est.
      if (nouvellePhoto) {
        try {
          await api.uploadMenuItemPhoto(cree.id, await reduirePhoto(nouvellePhoto));
        } catch {
          setError("Le plat est ajouté, mais sa photo n'est pas passée. Glissez-la sur sa vignette.");
        }
      }
      flash(`« ${newItem.name} » ajouté au menu.`);
      setNewItem(EMPTY_DRAFT);
      setNouvellePhoto(null);
      setAddingItem(false);
      await load();
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function saveTable(table: Table) {
    setError(null);
    const draft = tableDrafts[table.id];
    if (!draft.label.trim()) {
      setError("Le nom de la table est obligatoire.");
      return;
    }
    try {
      await api.updateTable(table.id, { label: draft.label.trim(), zone: draft.zone.trim() || null });
      flash(`« ${draft.label} » enregistrée.`);
      await load();
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function addTable() {
    setError(null);
    if (!restaurantId) return;
    if (!newTable.label.trim()) {
      setError("Le nom de la table est obligatoire pour l'ajouter.");
      return;
    }
    try {
      await api.createTable({
        restaurant_id: restaurantId,
        label: newTable.label.trim(),
        zone: newTable.zone.trim() || null,
      });
      flash(`« ${newTable.label} » ajoutée.`);
      setNewTable(EMPTY_TABLE_DRAFT);
      await load();
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function toggleSuggestion(item: MenuItem, suggestedId: number) {
    setError(null);
    const current = suggestions[String(item.id)] ?? [];
    const next = current.includes(suggestedId)
      ? current.filter((id) => id !== suggestedId)
      : [...current, suggestedId];
    if (next.length > 3) {
      setError("Trois suggestions au maximum par plat — au-delà, le client referme la proposition.");
      return;
    }
    setSavingSuggestionsFor(item.id);
    try {
      await api.setMenuSuggestions(item.id, next);
      // L'endpoint public ne renvoie que les articles disponibles ; on garde
      // l'état local tel qu'enregistré pour que le manager voie bien sa
      // sélection même si un plat suggéré est en rupture.
      setSuggestions((prev) => ({ ...prev, [String(item.id)]: next }));
      flash("Suggestions enregistrées.");
    } catch (e) {
      handleGatedError(e);
    } finally {
      setSavingSuggestionsFor(null);
    }
  }

  async function importMenuCsv() {
    setError(null);
    setCsvResult(null);
    setSavingCsv(true);
    try {
      const result = await api.importMenuCsv(csvContent, csvReplace);
      setCsvResult(result);
      flash(`${result.created_count + result.updated_count} article(s) importé(s).`);
      setCsvContent("");
      await load();
    } catch (e) {
      // Fichier totalement illisible : le backend renvoie la liste des raisons
      // dans le détail de l'erreur — les afficher vaut mieux qu'un message
      // générique, le manager doit savoir quoi corriger dans son tableur.
      if (e instanceof ApiError && Array.isArray(e.context.errors)) {
        setCsvResult({
          created_count: 0,
          updated_count: 0,
          disabled_count: 0,
          errors: e.context.errors as string[],
        });
      } else {
        handleGatedError(e);
      }
    } finally {
      setSavingCsv(false);
    }
  }

  async function addStaffMember() {
    setError(null);
    if (!newStaff.name.trim() || !newStaff.email.trim()) {
      setError("Le nom et l'e-mail sont obligatoires pour créer un compte.");
      return;
    }
    setSavingStaff(true);
    try {
      // Pas de mot de passe fourni : le serveur en génère un, affiché une
      // seule fois ci-dessous pour que le manager le transmette.
      const created = await api.createStaff({
        name: newStaff.name.trim(),
        email: newStaff.email.trim(),
        role: newStaff.role,
      });
      setNewCredentials(
        created.temporary_password
          ? { email: created.staff.email, password: created.temporary_password }
          : null
      );
      flash(`Compte de ${created.staff.name} créé.`);
      setNewStaff(EMPTY_STAFF_DRAFT);
      await load();
    } catch (e) {
      handleGatedError(e);
    } finally {
      setSavingStaff(false);
    }
  }

  async function saveStaffMember(member: Staff) {
    setError(null);
    const draft = staffDrafts[member.id];
    if (!draft?.name.trim()) {
      setError("Le nom est obligatoire.");
      return;
    }
    try {
      await api.updateStaff(member.id, { name: draft.name.trim(), role: draft.role });
      flash(`${draft.name} mis à jour.`);
      await load();
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function toggleStaffActive(member: Staff) {
    setError(null);
    try {
      await api.updateStaff(member.id, { is_active: !member.is_active });
      flash(member.is_active ? `Accès de ${member.name} désactivé.` : `Accès de ${member.name} rétabli.`);
      await load();
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function resetStaffPassword(member: Staff) {
    setError(null);
    try {
      const reset = await api.resetStaffPassword(member.id);
      if (reset.temporary_password) {
        setNewCredentials({ email: reset.staff.email, password: reset.temporary_password });
      }
      flash(`Nouveau mot de passe généré pour ${member.name}.`);
    } catch (e) {
      handleGatedError(e);
    }
  }

  if (staffLoading || !staff) {
    return (
      <div className="p-4 max-w-3xl mx-auto space-y-3">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-4 w-96 max-w-full" />
        <Skeleton className="h-24 w-full mt-4" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-32 w-full mt-4" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  const filteredItems = items.filter((item) => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.trim().toLowerCase());
    const matchesCategory = categoryFilter === "all" || item.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="p-4 max-w-3xl mx-auto">
      {upgradeTier && restaurantId && (
        <UpgradeModal
          restaurantId={restaurantId}
          requiredTier={upgradeTier}
          onClose={() => setUpgradeTier(null)}
          onUpgraded={(updated) => setRestaurant(updated)}
        />
      )}
      <EnteteManager
        titre="Carte"
        sousTitre="Modifier un plat, signaler une rupture, en ajouter un — et déposer les photos en les glissant sur leur vignette."
      />

      <RecetteDuJour stats={dayStats} />

      {error && (
        <Card tone="danger" padding="sm" className="mb-4 text-sm text-red-700">
          {error}
        </Card>
      )}
      {message && (
        <Card tone="success" padding="sm" className="mb-4 text-sm text-emerald-700">
          {message}
        </Card>
      )}

      <div className="flex gap-1 border-b border-[var(--line)] mb-4">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab.key
                ? "border-[var(--harissa)] text-[var(--harissa)]"
                : "border-transparent text-neutral-500 hover:text-neutral-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "menu" && (
        <>
          <div className="flex flex-col sm:flex-row gap-2 mb-3">
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Rechercher un plat par nom..."
              className="border rounded px-2 py-1.5 text-sm flex-1"
            />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="border rounded px-2 py-1.5 text-sm"
            >
              <option value="all">Toutes les catégories</option>
              {MENU_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            {filteredItems.map((item) => {
              const draft = drafts[item.id] ?? itemToDraft(item);
              const isEditing = editingItemId === item.id;
              return (
                <Card key={item.id} padding="sm" className={!item.is_available ? "bg-neutral-50" : ""}>
                  <div className="flex items-center gap-3">
                    <PhotoDuPlat
                      item={item}
                      enCours={photoEnCours === item.id}
                      onFichier={(fichier) => deposerPhoto(item, fichier)}
                      onRetirer={() => retirerPhoto(item)}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{item.name}</div>
                      <div className="text-xs text-neutral-500 truncate">
                        {item.category} · {item.price.toFixed(2)} DT
                      </div>
                    </div>
                    <Badge tone={item.is_available ? "success" : "danger"} className="shrink-0 hidden sm:inline-flex">
                      {item.is_available ? "Disponible" : "Rupture"}
                    </Badge>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="shrink-0"
                      onClick={() => setEditingItemId(isEditing ? null : item.id)}
                    >
                      {isEditing ? "Fermer" : "Modifier"}
                    </Button>
                  </div>

                  {isEditing && (
                    <div className="mt-3 pt-3 border-t border-[var(--line)]">
                      <div className="grid grid-cols-1 sm:grid-cols-[2fr_1fr_1fr] gap-2">
                        <input
                          value={draft.name}
                          onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, name: e.target.value } }))}
                          className="border rounded px-2 py-1"
                          placeholder="Nom"
                        />
                        <select
                          value={draft.category}
                          onChange={(e) =>
                            setDrafts((d) => ({ ...d, [item.id]: { ...draft, category: e.target.value } }))
                          }
                          className="border rounded px-2 py-1"
                        >
                          {MENU_CATEGORIES.map((c) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                        </select>
                        <input
                          value={draft.price}
                          onChange={(e) =>
                            setDrafts((d) => ({ ...d, [item.id]: { ...draft, price: e.target.value } }))
                          }
                          className="border rounded px-2 py-1"
                          placeholder="Prix (DT)"
                          inputMode="decimal"
                        />
                      </div>
                      <input
                        value={draft.description}
                        onChange={(e) =>
                          setDrafts((d) => ({ ...d, [item.id]: { ...draft, description: e.target.value } }))
                        }
                        className="border rounded px-2 py-1 w-full mt-2"
                        placeholder="Description (facultatif)"
                      />
                      {/* Une zone de dépôt, et non plus un champ « URL de la
                          photo » : ce champ supposait que le patron héberge
                          ses images ailleurs, ce qu'aucun ne fait. */}
                      <ZonePhoto
                        item={item}
                        enCours={photoEnCours === item.id}
                        onFichier={(fichier) => deposerPhoto(item, fichier)}
                        onRetirer={() => retirerPhoto(item)}
                      />
                      <div className="grid grid-cols-1 sm:grid-cols-[1fr_2fr_auto] gap-2 mt-2 items-center">
                        <select
                          value={draft.spiceLevel}
                          onChange={(e) =>
                            setDrafts((d) => ({ ...d, [item.id]: { ...draft, spiceLevel: e.target.value } }))
                          }
                          className="border rounded px-2 py-1 text-sm"
                        >
                          {SPICE_LABELS.map((label, level) => (
                            <option key={level} value={level}>
                              {label}
                            </option>
                          ))}
                        </select>
                        <input
                          value={draft.allergens}
                          onChange={(e) =>
                            setDrafts((d) => ({ ...d, [item.id]: { ...draft, allergens: e.target.value } }))
                          }
                          className="border rounded px-2 py-1 text-sm"
                          placeholder="Allergènes (facultatif, ex : Gluten, Fruits à coque)"
                        />
                        <label className="flex items-center gap-2 text-sm whitespace-nowrap">
                          <input
                            type="checkbox"
                            checked={draft.isHalal}
                            onChange={(e) =>
                              setDrafts((d) => ({ ...d, [item.id]: { ...draft, isHalal: e.target.checked } }))
                            }
                          />
                          Halal
                        </label>
                      </div>
                      <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={item.is_available}
                            onChange={() => toggleAvailability(item)}
                          />
                          <Badge tone={item.is_available ? "success" : "danger"}>
                            {item.is_available ? "Disponible" : "Rupture de stock"}
                          </Badge>
                        </label>
                        <div className="flex gap-2">
                          <Button onClick={() => saveItem(item)}>Enregistrer</Button>
                          <Button variant="danger" onClick={() => removeItem(item)}>
                            Supprimer
                          </Button>
                        </div>
                      </div>

                      <div className="mt-4 pt-3 border-t border-[var(--line)]">
                        <p className="text-sm font-medium">Proposer avec ce plat</p>
                        <p className="text-xs text-neutral-500 mb-2">
                          Jusqu&apos;à 3 articles proposés au client quand il ajoute « {item.name} » à son
                          panier. C&apos;est ce qui fait monter le panier moyen — et le chiffre se mesure sur
                          la page « Preuve du pilote ».
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {items
                            .filter((candidate) => candidate.id !== item.id)
                            .map((candidate) => {
                              const selected = (suggestions[String(item.id)] ?? []).includes(candidate.id);
                              return (
                                <button
                                  key={candidate.id}
                                  onClick={() => toggleSuggestion(item, candidate.id)}
                                  disabled={savingSuggestionsFor === item.id}
                                  aria-pressed={selected}
                                  className={`text-xs px-2 py-1 rounded-full border transition-colors disabled:opacity-50 ${
                                    selected
                                      ? "bg-[var(--harissa)] text-white border-[var(--harissa)]"
                                      : "border-[var(--line)] text-neutral-600 hover:bg-[var(--semoule)]"
                                  }`}
                                >
                                  {candidate.name}
                                </button>
                              );
                            })}
                        </div>
                      </div>
                    </div>
                  )}
                </Card>
              );
            })}
            {filteredItems.length === 0 && items.length > 0 && (
              <EmptyState message="Aucun plat ne correspond à cette recherche." />
            )}
            {items.length === 0 && <EmptyState message="Aucun article pour l'instant." />}
          </div>

          {addingItem ? (
            <>
              <h2 className="text-base font-semibold mt-6 mb-3">Ajouter un article</h2>
              <Card padding="sm">
                <div className="grid grid-cols-1 sm:grid-cols-[2fr_1fr_1fr] gap-2">
                  <input
                    value={newItem.name}
                    onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                    className="border rounded px-2 py-1"
                    placeholder="Nom"
                  />
                  <select
                    value={newItem.category}
                    onChange={(e) => setNewItem({ ...newItem, category: e.target.value })}
                    className="border rounded px-2 py-1"
                  >
                    {MENU_CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                  <input
                    value={newItem.price}
                    onChange={(e) => setNewItem({ ...newItem, price: e.target.value })}
                    className="border rounded px-2 py-1"
                    placeholder="Prix (DT)"
                    inputMode="decimal"
                  />
                </div>
                <input
                  value={newItem.description}
                  onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
                  className="border rounded px-2 py-1 w-full mt-2"
                  placeholder="Description (facultatif)"
                />
                <ZonePhotoNouveau fichier={nouvellePhoto} onFichier={setNouvellePhoto} />
                <div className="grid grid-cols-1 sm:grid-cols-[1fr_2fr_auto] gap-2 mt-2 items-center">
                  <select
                    value={newItem.spiceLevel}
                    onChange={(e) => setNewItem({ ...newItem, spiceLevel: e.target.value })}
                    className="border rounded px-2 py-1 text-sm"
                  >
                    {SPICE_LABELS.map((label, level) => (
                      <option key={level} value={level}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <input
                    value={newItem.allergens}
                    onChange={(e) => setNewItem({ ...newItem, allergens: e.target.value })}
                    className="border rounded px-2 py-1 text-sm"
                    placeholder="Allergènes (facultatif, ex : Gluten, Fruits à coque)"
                  />
                  <label className="flex items-center gap-2 text-sm whitespace-nowrap">
                    <input
                      type="checkbox"
                      checked={newItem.isHalal}
                      onChange={(e) => setNewItem({ ...newItem, isHalal: e.target.checked })}
                    />
                    Halal
                  </label>
                </div>
                <div className="flex gap-2 mt-3">
                  <Button onClick={addItem}>Ajouter au menu</Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setAddingItem(false);
                      setNewItem(EMPTY_DRAFT);
                    }}
                  >
                    Annuler
                  </Button>
                </div>
              </Card>
            </>
          ) : (
            <Button variant="secondary" className="mt-4" onClick={() => setAddingItem(true)}>
              + Ajouter un article
            </Button>
          )}

          <div className="mt-8 pt-6 border-t border-[var(--line)]">
            {!importing ? (
              <>
                <Button variant="secondary" onClick={() => setImporting(true)}>
                  Importer une carte (CSV)
                </Button>
                <p className="text-xs text-neutral-500 mt-2">
                  Pour saisir une carte entière d&apos;un coup, depuis un export Excel.
                </p>
              </>
            ) : (
              <Card padding="sm">
                <h2 className="text-base font-semibold mb-1">Importer une carte</h2>
                <p className="text-xs text-neutral-500 mb-3">
                  Fichier CSV avec une ligne d&apos;en-tête. Colonnes obligatoires :{" "}
                  <code>nom</code> et <code>prix</code>. Facultatives : <code>categorie</code>,{" "}
                  <code>description</code>, <code>piment</code> (0 à 3), <code>allergenes</code>,{" "}
                  <code>halal</code>. Les prix à virgule et les fichiers à point-virgule d&apos;Excel sont
                  acceptés.
                </p>

                <input
                  type="file"
                  accept=".csv,text/csv"
                  aria-label="Fichier CSV de la carte"
                  className="text-sm"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (file) setCsvContent(await file.text());
                  }}
                />

                <textarea
                  value={csvContent}
                  onChange={(e) => setCsvContent(e.target.value)}
                  rows={6}
                  aria-label="Contenu du CSV"
                  placeholder={"nom;categorie;prix\nCouscous poisson;Plats;24,000"}
                  className="w-full border rounded px-2 py-1 mt-3 font-mono text-xs"
                />

                <label className="flex items-center gap-2 text-sm mt-3">
                  <input
                    type="checkbox"
                    checked={csvReplace}
                    onChange={(e) => setCsvReplace(e.target.checked)}
                  />
                  Ce fichier est ma carte complète
                </label>
                <p className="text-xs text-neutral-500 mt-1">
                  Les articles absents du fichier seront rendus indisponibles — jamais supprimés, les
                  commandes déjà passées y font référence. Sans cette case, l&apos;import ajoute les
                  nouveaux plats et met à jour les prix des plats déjà présents.
                </p>

                {csvResult && (
                  <Card tone={csvResult.errors.length ? "warning" : "success"} padding="sm" className="mt-3">
                    <p className="text-sm font-medium">
                      {csvResult.created_count} article(s) ajouté(s)
                      {csvResult.updated_count > 0 && `, ${csvResult.updated_count} mis à jour`}
                      {csvResult.disabled_count > 0 &&
                        `, ${csvResult.disabled_count} rendu(s) indisponible(s)`}
                      .
                    </p>
                    {csvResult.errors.length > 0 && (
                      <>
                        <p className="text-sm mt-2">Lignes à corriger dans votre fichier :</p>
                        <ul className="list-disc pl-5 text-xs mt-1 space-y-1">
                          {csvResult.errors.map((message) => (
                            <li key={message}>{message}</li>
                          ))}
                        </ul>
                      </>
                    )}
                  </Card>
                )}

                <div className="flex gap-2 mt-3">
                  <Button onClick={importMenuCsv} disabled={savingCsv || !csvContent.trim()}>
                    {savingCsv ? "Import…" : "Importer"}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setImporting(false);
                      setCsvContent("");
                      setCsvResult(null);
                    }}
                  >
                    Fermer
                  </Button>
                </div>
              </Card>
            )}
          </div>
        </>
      )}

      {activeTab === "tables" && (
        <>
          <datalist id="zone-suggestions">
            {ZONE_SUGGESTIONS.map((z) => (
              <option key={z} value={z} />
            ))}
          </datalist>

          <h2 className="text-lg font-semibold mb-1">Le plan de votre salle</h2>
          <p className="text-sm text-neutral-500 mb-3">
            Posez vos tables comme elles sont chez vous. Vos serveurs verront cette salle en
            direct : une table qui attend s&apos;y allume, avec le temps qu&apos;elle attend et
            son rang d&apos;arrivée quand plusieurs commandent en même temps.
          </p>
          <div className="mb-8">
            <EditeurDePlan
              tables={tables}
              enregistrement={savingPlan}
              onEnregistrer={async (placements) => {
                if (!restaurantId) return;
                setSavingPlan(true);
                setError(null);
                try {
                  // Pas de message de succès : l'éditeur enregistre tout seul,
                  // un bandeau vert à chaque table déplacée serait du bruit.
                  setTables(await api.savePlan(restaurantId, placements));
                } catch (e) {
                  handleGatedError(e);
                } finally {
                  setSavingPlan(false);
                }
              }}
            />
          </div>

          <h2 className="text-lg font-semibold mb-1">Vos tables</h2>
          <p className="text-sm text-neutral-500 mb-3">
            Groupez vos tables par zone (intérieur, terrasse, plage...) si votre établissement en a plusieurs —
            laissez vide sinon.
          </p>
          <div className="space-y-2">
            {tables.map((table) => {
              const draft = tableDrafts[table.id] ?? tableToDraft(table);
              return (
                <Card
                  key={table.id}
                  padding="sm"
                  className="grid grid-cols-1 sm:grid-cols-[2fr_2fr_auto] gap-2 items-center"
                >
                  <input
                    value={draft.label}
                    onChange={(e) =>
                      setTableDrafts((d) => ({ ...d, [table.id]: { ...draft, label: e.target.value } }))
                    }
                    className="border rounded px-2 py-1"
                    placeholder="Nom de la table"
                  />
                  <input
                    value={draft.zone}
                    onChange={(e) =>
                      setTableDrafts((d) => ({ ...d, [table.id]: { ...draft, zone: e.target.value } }))
                    }
                    list="zone-suggestions"
                    className="border rounded px-2 py-1"
                    placeholder="Zone (facultatif)"
                  />
                  <Button onClick={() => saveTable(table)}>Enregistrer</Button>
                </Card>
              );
            })}
            {tables.length === 0 && <EmptyState message="Aucune table pour l'instant." />}
          </div>

          <h2 className="text-base font-semibold mt-6 mb-3">Ajouter une table</h2>
          <Card padding="sm" className="grid grid-cols-1 sm:grid-cols-[2fr_2fr_auto] gap-2 items-center">
            <input
              value={newTable.label}
              onChange={(e) => setNewTable({ ...newTable, label: e.target.value })}
              className="border rounded px-2 py-1"
              placeholder="Nom de la table (ex : Table 5)"
            />
            <input
              value={newTable.zone}
              onChange={(e) => setNewTable({ ...newTable, zone: e.target.value })}
              list="zone-suggestions"
              className="border rounded px-2 py-1"
              placeholder="Zone (facultatif)"
            />
            <Button onClick={addTable}>Ajouter la table</Button>
          </Card>
        </>
      )}

      {activeTab === "team" && (
        <>
          <p className="text-sm text-neutral-500 mb-3">
            Créez un compte par serveur et un compte pour la cuisine : sans compte, un serveur ne voit pas les
            commandes à confirmer et l&apos;écran cuisine reste vide. Un compte n&apos;est jamais supprimé mais
            désactivé, pour que les statistiques des commandes qu&apos;il a prises en charge restent intactes.
          </p>

          {newCredentials && (
            <Card tone="success" padding="sm" className="mb-4">
              <p className="font-medium text-emerald-900">Identifiants à transmettre maintenant</p>
              <dl className="mt-2 text-sm grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-emerald-900">
                <dt className="text-emerald-700">E-mail</dt>
                <dd className="font-mono break-all">{newCredentials.email}</dd>
                <dt className="text-emerald-700">Mot de passe</dt>
                <dd className="font-mono break-all">{newCredentials.password}</dd>
              </dl>
              <p className="text-xs text-emerald-700 mt-2">
                Notez-le ou dictez-le tout de suite : il n&apos;est pas conservé en clair et ne pourra plus être
                réaffiché. Vous pourrez en générer un nouveau à tout moment.
              </p>
              <Button variant="secondary" size="sm" className="mt-2" onClick={() => setNewCredentials(null)}>
                J&apos;ai noté, masquer
              </Button>
            </Card>
          )}

          <div className="space-y-2">
            {team.map((member) => {
              const draft = staffDrafts[member.id] ?? staffToDraft(member);
              const isSelf = member.id === staff.id;
              return (
                <Card
                  key={member.id}
                  padding="sm"
                  className={member.is_active ? undefined : "opacity-60"}
                >
                  <div className="grid grid-cols-1 sm:grid-cols-[2fr_1fr_auto] gap-2 items-center">
                    <input
                      value={draft.name}
                      onChange={(e) =>
                        setStaffDrafts((d) => ({ ...d, [member.id]: { ...draft, name: e.target.value } }))
                      }
                      className="border rounded px-2 py-1"
                      placeholder="Nom"
                      aria-label={`Nom de ${member.name}`}
                    />
                    <select
                      value={draft.role}
                      onChange={(e) =>
                        setStaffDrafts((d) => ({
                          ...d,
                          [member.id]: { ...draft, role: e.target.value as StaffRole },
                        }))
                      }
                      className="border rounded px-2 py-1"
                      aria-label={`Rôle de ${member.name}`}
                    >
                      {(Object.keys(ROLE_LABELS) as StaffRole[]).map((role) => (
                        <option key={role} value={role}>
                          {ROLE_LABELS[role]}
                        </option>
                      ))}
                    </select>
                    <Button onClick={() => saveStaffMember(member)}>Enregistrer</Button>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap mt-2 text-sm">
                    <span className="font-mono text-xs text-neutral-500 break-all">{member.email}</span>
                    {!member.is_active && <Badge tone="neutral">Désactivé</Badge>}
                    {isSelf && <Badge tone="info">Vous</Badge>}
                    <span className="grow" />
                    <Button variant="secondary" size="sm" onClick={() => resetStaffPassword(member)}>
                      Nouveau mot de passe
                    </Button>
                    <Button
                      variant={member.is_active ? "danger" : "secondary"}
                      size="sm"
                      onClick={() => toggleStaffActive(member)}
                    >
                      {member.is_active ? "Désactiver l'accès" : "Réactiver"}
                    </Button>
                  </div>
                </Card>
              );
            })}
            {team.length === 0 && <EmptyState message="Aucun compte dans l'équipe pour l'instant." />}
          </div>

          <h2 className="text-base font-semibold mt-6 mb-3">Ajouter un membre de l&apos;équipe</h2>
          <Card padding="sm" className="grid grid-cols-1 sm:grid-cols-[2fr_2fr_1fr_auto] gap-2 items-center">
            <input
              value={newStaff.name}
              onChange={(e) => setNewStaff({ ...newStaff, name: e.target.value })}
              className="border rounded px-2 py-1"
              placeholder="Nom (ex : Sami)"
              aria-label="Nom du nouveau membre"
            />
            <input
              value={newStaff.email}
              onChange={(e) => setNewStaff({ ...newStaff, email: e.target.value })}
              type="email"
              autoComplete="off"
              className="border rounded px-2 py-1"
              placeholder="E-mail de connexion"
              aria-label="E-mail du nouveau membre"
            />
            <select
              value={newStaff.role}
              onChange={(e) => setNewStaff({ ...newStaff, role: e.target.value as StaffRole })}
              className="border rounded px-2 py-1"
              aria-label="Rôle du nouveau membre"
            >
              {(Object.keys(ROLE_LABELS) as StaffRole[]).map((role) => (
                <option key={role} value={role}>
                  {ROLE_LABELS[role]}
                </option>
              ))}
            </select>
            <Button onClick={addStaffMember} disabled={savingStaff}>
              {savingStaff ? "Création…" : "Créer le compte"}
            </Button>
          </Card>
          <p className="text-xs text-neutral-500 mt-2">
            Un mot de passe est généré automatiquement et affiché une seule fois après la création.
          </p>
        </>
      )}

      {activeTab === "settings" && (
        <>
          {restaurant && (
            <Card tone="warning" padding="sm" className="mb-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <label className="flex items-center gap-2 font-medium text-amber-900">
                  <input
                    type="checkbox"
                    checked={ramadanEnabled}
                    onChange={(e) => {
                      setRamadanEnabled(e.target.checked);
                      saveRamadanMode(e.target.checked);
                    }}
                  />
                  <MoonIcon className="w-4 h-4 shrink-0" />
                  Mode Ramadan
                </label>
                {ramadanEnabled && (
                  <div className="flex items-center gap-2 text-sm">
                    <label htmlFor="iftar-time" className="text-amber-800">
                      Heure de l&apos;iftar aujourd&apos;hui
                    </label>
                    <input
                      id="iftar-time"
                      type="datetime-local"
                      value={iftarInput}
                      onChange={(e) => setIftarInput(e.target.value)}
                      onBlur={() => saveRamadanMode(true)}
                      disabled={savingRamadan}
                      className="border rounded px-2 py-1"
                    />
                  </div>
                )}
              </div>
              <p className="text-xs text-amber-700 mt-2">
                Une fois activé, les clients peuvent pré-commander pour l&apos;iftar depuis le menu. Pensez à mettre
                à jour l&apos;heure chaque jour (elle varie). Astuce : classez vos plats de rupture du jeûne dans la
                catégorie « Ftour » pour qu&apos;ils ressortent bien sur le menu client.
              </p>
            </Card>
          )}

          {restaurant && (
            <Card tone="info" padding="sm" className="mb-4">
              <label className="flex items-center gap-2 font-medium text-sky-900">
                <input
                  type="checkbox"
                  checked={cafeModeEnabled}
                  disabled={savingCafeMode}
                  onChange={(e) => {
                    setCafeModeEnabled(e.target.checked);
                    saveCafeMode(e.target.checked);
                  }}
                />
                <CoffeeIcon className="w-4 h-4 shrink-0" />
                Mode café simplifié
              </label>
              <p className="text-xs text-sky-700 mt-2">
                Pour un établissement qui ne sert que des boissons : le menu client s&apos;affiche en liste simple,
                sans regrouper par catégorie (entrées/plats/desserts).
              </p>
            </Card>
          )}

          {restaurant && (
            <Card padding="sm">
              <label className="flex items-center gap-2 font-medium">
                <input
                  type="checkbox"
                  checked={kitchenSoundEnabled}
                  disabled={savingKitchenSound}
                  onChange={(e) => {
                    setKitchenSoundEnabled(e.target.checked);
                    saveKitchenSound(e.target.checked);
                  }}
                />
                <BellIcon className="w-4 h-4 shrink-0" />
                Retour sonore en cuisine
              </label>
              <p className="text-xs text-neutral-500 mt-2">
                Un bip se joue sur l&apos;écran cuisine à chaque nouvelle commande envoyée. Certains navigateurs ne
                joueront le premier son qu&apos;après une interaction sur l&apos;écran cuisine (politique de lecture
                automatique).
              </p>
            </Card>
          )}

          {restaurant && (
            <Card padding="sm" className="mt-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Palier d&apos;abonnement</span>
                <Badge tone="neutral">{TIER_LABELS[restaurant.subscription_tier]}</Badge>
              </div>
              <p className="text-xs text-neutral-500 mt-2">
                Le paiement carte, la fidélité, le plan de salle visuel, les photos, le mode Ramadan, l&apos;import
                CSV et la page de preuve demandent Pro ou plus ; le rapport d&apos;équipe et les notifications
                push demandent Business. Pour changer de palier, contactez Tawla.
              </p>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
