"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, MenuItem, Restaurant, Table } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { clearToken } from "@/lib/auth";

const CATEGORIES = ["Entrées", "Plats", "Desserts", "Boissons", "Ftour", "Autre"];

// Suggestions, pas un enum figé (voir Table.zone côté backend) : tous les
// établissements n'ont pas les mêmes zones, un café sans terrasse n'en a
// besoin d'aucune — texte libre avec juste un coup de pouce à la saisie.
const ZONE_SUGGESTIONS = ["Intérieur", "Terrasse", "Plage"];

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
  image_url: string;
  spiceLevel: string;
  allergens: string;
  isHalal: boolean;
};

const SPICE_LABELS = ["Pas épicé", "🌶️ Léger", "🌶️🌶️ Moyen", "🌶️🌶️🌶️ Fort"];

function itemToDraft(item: MenuItem): Draft {
  return {
    name: item.name,
    category: item.category,
    price: String(item.price),
    description: item.description ?? "",
    image_url: item.image_url ?? "",
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
  image_url: "",
  spiceLevel: "0",
  allergens: "",
  isHalal: true,
};

export default function DashboardPage() {
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["manager"]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [newItem, setNewItem] = useState<Draft>(EMPTY_DRAFT);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [ramadanEnabled, setRamadanEnabled] = useState(false);
  const [iftarInput, setIftarInput] = useState("");
  const [savingRamadan, setSavingRamadan] = useState(false);
  const [cafeModeEnabled, setCafeModeEnabled] = useState(false);
  const [savingCafeMode, setSavingCafeMode] = useState(false);
  const [tables, setTables] = useState<Table[]>([]);
  const [tableDrafts, setTableDrafts] = useState<Record<number, TableDraft>>({});
  const [newTable, setNewTable] = useState<TableDraft>(EMPTY_TABLE_DRAFT);

  const restaurantId = staff?.restaurant_id ?? null;

  const load = useCallback(async () => {
    if (!restaurantId) return;
    try {
      const [menu, rest, tableList] = await Promise.all([
        api.getMenu(restaurantId),
        api.getRestaurant(restaurantId),
        api.listTables(restaurantId),
      ]);
      setItems(menu);
      setDrafts(Object.fromEntries(menu.map((m) => [m.id, itemToDraft(m)])));
      setRestaurant(rest);
      setRamadanEnabled(rest.ramadan_mode_enabled);
      setIftarInput(isoToLocalInput(rest.iftar_time));
      setCafeModeEnabled(rest.cafe_mode_enabled);
      setTables(tableList);
      setTableDrafts(Object.fromEntries(tableList.map((t) => [t.id, tableToDraft(t)])));
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId]);

  useEffect(() => {
    if (restaurantId) load();
  }, [restaurantId, load]);

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
      setError(toFrenchMessage(e));
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
      setError(toFrenchMessage(e));
    } finally {
      setSavingCafeMode(false);
    }
  }

  function logout() {
    clearToken();
    router.push("/login");
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
        image_url: draft.image_url.trim() || null,
        spice_level: Number(draft.spiceLevel),
        allergens: draft.allergens.trim() || null,
        is_halal: draft.isHalal,
      });
      flash(`« ${draft.name} » enregistré.`);
      await load();
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function toggleAvailability(item: MenuItem) {
    setError(null);
    try {
      await api.setMenuItemAvailability(item.id, !item.is_available);
      await load();
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function removeItem(item: MenuItem) {
    if (!confirm(`Supprimer « ${item.name} » du menu ?`)) return;
    setError(null);
    try {
      await api.deleteMenuItem(item.id);
      flash(`« ${item.name} » supprimé.`);
      await load();
    } catch (e) {
      setError(toFrenchMessage(e));
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
      await api.createMenuItem({
        restaurant_id: restaurantId,
        name: newItem.name.trim(),
        category: newItem.category,
        price,
        description: newItem.description.trim() || null,
        image_url: newItem.image_url.trim() || null,
        spice_level: Number(newItem.spiceLevel),
        allergens: newItem.allergens.trim() || null,
        is_halal: newItem.isHalal,
      });
      flash(`« ${newItem.name} » ajouté au menu.`);
      setNewItem(EMPTY_DRAFT);
      await load();
    } catch (e) {
      setError(toFrenchMessage(e));
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
      setError(toFrenchMessage(e));
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
      setError(toFrenchMessage(e));
    }
  }

  if (staffLoading || !staff) return null;

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <h1 className="text-lg font-semibold">Dashboard resto — gérer le menu</h1>
        <div className="flex items-center gap-4 text-sm">
          <Link href="/dashboard/stats" className="underline">
            Suivi de l&apos;activité
          </Link>
          <button onClick={logout} className="text-neutral-500 underline">
            Se déconnecter
          </button>
        </div>
      </div>
      <p className="text-sm text-neutral-500 mb-4">
        Modifier un article, basculer une rupture de stock, ou en ajouter un nouveau — sans passer par Swagger.
      </p>

      {restaurant && (
        <div className="border rounded-lg p-3 mb-4 bg-amber-50 border-amber-200">
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
              🌙 Mode Ramadan
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
            Une fois activé, les clients peuvent pré-commander pour l&apos;iftar depuis le menu. Pensez à mettre à
            jour l&apos;heure chaque jour (elle varie). Astuce : classez vos plats de rupture du jeûne dans la
            catégorie « Ftour » pour qu&apos;ils ressortent bien sur le menu client.
          </p>
        </div>
      )}

      {restaurant && (
        <div className="border rounded-lg p-3 mb-4 bg-sky-50 border-sky-200">
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
            ☕ Mode café simplifié
          </label>
          <p className="text-xs text-sky-700 mt-2">
            Pour un établissement qui ne sert que des boissons : le menu client s&apos;affiche en liste simple, sans
            regrouper par catégorie (entrées/plats/desserts).
          </p>
        </div>
      )}

      {error && (
        <div className="mb-4 text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">{error}</div>
      )}
      {message && (
        <div className="mb-4 text-sm bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg p-3">
          {message}
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => {
          const draft = drafts[item.id] ?? itemToDraft(item);
          return (
            <div key={item.id} className={`border rounded-lg p-3 ${!item.is_available ? "bg-neutral-50" : ""}`}>
              <div className="grid grid-cols-1 sm:grid-cols-[2fr_1fr_1fr] gap-2">
                <input
                  value={draft.name}
                  onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, name: e.target.value } }))}
                  className="border rounded px-2 py-1"
                  placeholder="Nom"
                />
                <select
                  value={draft.category}
                  onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, category: e.target.value } }))}
                  className="border rounded px-2 py-1"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
                <input
                  value={draft.price}
                  onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, price: e.target.value } }))}
                  className="border rounded px-2 py-1"
                  placeholder="Prix (DT)"
                  inputMode="decimal"
                />
              </div>
              <input
                value={draft.description}
                onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, description: e.target.value } }))}
                className="border rounded px-2 py-1 w-full mt-2"
                placeholder="Description (facultatif)"
              />
              <input
                value={draft.image_url}
                onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, image_url: e.target.value } }))}
                className="border rounded px-2 py-1 w-full mt-2"
                placeholder="URL de la photo (facultatif)"
              />
              <div className="grid grid-cols-1 sm:grid-cols-[1fr_2fr_auto] gap-2 mt-2 items-center">
                <select
                  value={draft.spiceLevel}
                  onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, spiceLevel: e.target.value } }))}
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
                  onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, allergens: e.target.value } }))}
                  className="border rounded px-2 py-1 text-sm"
                  placeholder="Allergènes (facultatif, ex : Gluten, Fruits à coque)"
                />
                <label className="flex items-center gap-2 text-sm whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={draft.isHalal}
                    onChange={(e) => setDrafts((d) => ({ ...d, [item.id]: { ...draft, isHalal: e.target.checked } }))}
                  />
                  Halal
                </label>
              </div>
              <div className="flex items-center justify-between mt-3">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={item.is_available} onChange={() => toggleAvailability(item)} />
                  {item.is_available ? "Disponible" : "Rupture de stock"}
                </label>
                <div className="flex gap-2">
                  <button onClick={() => saveItem(item)} className="bg-neutral-900 text-white text-sm px-3 py-1.5 rounded-lg">
                    Enregistrer
                  </button>
                  <button
                    onClick={() => removeItem(item)}
                    className="text-red-600 border border-red-200 text-sm px-3 py-1.5 rounded-lg"
                  >
                    Supprimer
                  </button>
                </div>
              </div>
            </div>
          );
        })}
        {items.length === 0 && <p className="text-neutral-500">Aucun article pour l&apos;instant.</p>}
      </div>

      <h2 className="text-base font-semibold mt-8 mb-3">Ajouter un article</h2>
      <div className="border rounded-lg p-3">
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
            {CATEGORIES.map((c) => (
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
        <input
          value={newItem.image_url}
          onChange={(e) => setNewItem({ ...newItem, image_url: e.target.value })}
          className="border rounded px-2 py-1 w-full mt-2"
          placeholder="URL de la photo (facultatif)"
        />
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
        <button onClick={addItem} className="mt-3 bg-amber-700 text-white text-sm px-4 py-2 rounded-lg">
          Ajouter au menu
        </button>
      </div>

      <datalist id="zone-suggestions">
        {ZONE_SUGGESTIONS.map((z) => (
          <option key={z} value={z} />
        ))}
      </datalist>

      <h2 className="text-base font-semibold mt-8 mb-1">Tables &amp; zones de salle</h2>
      <p className="text-sm text-neutral-500 mb-3">
        Groupez vos tables par zone (intérieur, terrasse, plage...) si votre établissement en a plusieurs — laissez
        vide sinon.
      </p>
      <div className="space-y-2">
        {tables.map((table) => {
          const draft = tableDrafts[table.id] ?? tableToDraft(table);
          return (
            <div key={table.id} className="border rounded-lg p-3 grid grid-cols-1 sm:grid-cols-[2fr_2fr_auto] gap-2 items-center">
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
                onChange={(e) => setTableDrafts((d) => ({ ...d, [table.id]: { ...draft, zone: e.target.value } }))}
                list="zone-suggestions"
                className="border rounded px-2 py-1"
                placeholder="Zone (facultatif)"
              />
              <button
                onClick={() => saveTable(table)}
                className="bg-neutral-900 text-white text-sm px-3 py-1.5 rounded-lg whitespace-nowrap"
              >
                Enregistrer
              </button>
            </div>
          );
        })}
        {tables.length === 0 && <p className="text-neutral-500">Aucune table pour l&apos;instant.</p>}
      </div>

      <h2 className="text-base font-semibold mt-6 mb-3">Ajouter une table</h2>
      <div className="border rounded-lg p-3 grid grid-cols-1 sm:grid-cols-[2fr_2fr_auto] gap-2 items-center">
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
        <button onClick={addTable} className="bg-amber-700 text-white text-sm px-4 py-2 rounded-lg whitespace-nowrap">
          Ajouter la table
        </button>
      </div>
    </div>
  );
}
