"use client";

import { useCallback, useEffect, useState } from "react";
import EnteteManager from "@/components/EnteteManager";
import { useRouter } from "next/navigation";
import {
  api,
  DashboardStats,
  MenuCsvImportResult,
  MenuItem,
  MenuRegime,
  Restaurant,
  Staff,
  StaffRole,
  SubscriptionTier,
  Table,
} from "@/lib/api";
import { ApiError } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";
import { requiredTierFromError, toFrenchMessage } from "@/lib/errors";
import { formatMoney } from "@/lib/currency";
import { currentMarket } from "@/lib/market";
import { TIERS, TIER_ACCENTS, estimateUpgradeProration } from "@/lib/offer";
import { lalezar } from "@/lib/fonts";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { useAccesDemoParLien } from "@/lib/demoLien";
import { sessionDemo } from "@/lib/visite/etat";
import { clearToken } from "@/lib/auth";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import Skeleton from "@/components/ui/Skeleton";
import {
  MoonIcon,
  CoffeeIcon,
  UtensilsIcon,
  BellIcon,
  FacebookIcon,
  InstagramIcon,
  TikTokIcon,
  WhatsAppIcon,
} from "@/components/icons";
import { reduirePhoto } from "@/lib/photo";
import PhotoDuPlat, { ZonePhoto, ZonePhotoNouveau } from "@/components/PhotoDuPlat";
import ChampsVatAllergenes from "@/components/ChampsVatAllergenes";
import RecetteDuJour from "@/components/RecetteDuJour";
import EditeurDePlan from "@/components/plan/EditeurDePlan";
import UpgradeModal from "@/components/UpgradeModal";
import ActivationRequired from "@/components/ActivationRequired";
import SubscriptionReminderModal from "@/components/SubscriptionReminderModal";
import WelcomeTierModal from "@/components/WelcomeTierModal";
import ConfirmDowngradeModal from "@/components/ConfirmDowngradeModal";
import QrCode from "@/components/QrCode";

// Suggestions, pas un enum figé (voir Table.zone côté backend) : tous les
// établissements n'ont pas les mêmes zones, un café sans terrasse n'en a
// besoin d'aucune — texte libre avec juste un coup de pouce à la saisie.
const ZONE_SUGGESTIONS = ["Intérieur", "Terrasse", "Plage"];

const TIER_LABELS: Record<SubscriptionTier, string> = {
  essentiel: "Essentiel",
  pro: "Pro",
  business: "Business",
};

// Passage en libre-service (2026-09-02) : chaque palier peut passer
// directement à n'importe quel palier strictement supérieur — jamais un
// contact manuel avec Tawla. `TIERS` (lib/offer.ts) porte déjà l'ordre et le
// prix, jamais un deuxième classement en dur ici.
const UPGRADE_TIERS_ABOVE: Record<SubscriptionTier, typeof TIERS> = {
  essentiel: TIERS.slice(1),
  pro: TIERS.slice(2),
  business: [],
};

// Rétrogradation en restant abonné (Stripe uniquement — mode Netflix,
// 2026-09-02), distincte d'une annulation complète : Pro peut redescendre à
// Essentiel, Business à Pro ou Essentiel. Jamais depuis Essentiel, déjà le
// plus bas — annuler est alors la seule sortie (voir manageSubscription).
const DOWNGRADE_TIERS_BELOW: Record<SubscriptionTier, typeof TIERS> = {
  essentiel: [],
  pro: TIERS.slice(0, 1),
  business: TIERS.slice(0, 2),
};

// Ce que le manager PERD en redescendant de `current` à `target` (retour
// utilisateur, 2026-09-02 : "ce qu'il perd") — chaque palier liste déjà ses
// propres apports dans `features` (lib/offer.ts), précédés d'une ligne
// récapitulative "Tout <palier précédent>" : on exclut cette ligne-là (déjà
// couverte par `target`) et on prend tout le reste, pour chaque palier
// strictement entre `target` (exclu) et `current` (inclus).
function featuresLostGoingTo(current: SubscriptionTier, target: SubscriptionTier): string[] {
  const currentIndex = TIERS.findIndex((t) => t.id === current);
  const targetIndex = TIERS.findIndex((t) => t.id === target);
  return TIERS.slice(targetIndex + 1, currentIndex + 1).flatMap((tier) =>
    tier.features.filter((f) => !f.startsWith("Tout ")),
  );
}

// `subscription_period_end` reste posé même après expiration (calcul à la
// lecture côté serveur, voir effective_tier()) : ne jamais l'afficher seul,
// toujours avec la garde `subscription_tier !== "essentiel"` — sinon un
// palier déjà retombé à Essentiel afficherait une échéance passée.
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

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
  // "" = pas de catégorie (facture au taux "sur_place" par défaut) — voir
  // VAT_CATEGORY_LABELS plus bas. N'a de sens qu'en France (Market.vatRates).
  vatCategory: string;
  // Sous-ensemble de ALLERGEN_CODES ci-dessous, jamais une saisie libre —
  // le backend rejette (422) tout code hors de cette liste fixe (UE,
  // règlement 1169/2011). Coexiste avec `allergens` (texte libre).
  allergenCodes: string[];
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
    vatCategory: item.vat_category ?? "",
    allergenCodes: item.allergen_codes ? item.allergen_codes.split(",").filter(Boolean) : [],
  };
}

const EMPTY_DRAFT: Draft = {
  name: "",
  category: "Plats",
  price: "",
  description: "",
  spiceLevel: "0",
  allergens: "",
  // Vrai par défaut en Tunisie (norme), faux en France — voir MenuItem.is_halal
  // côté backend (menu/models.py).
  isHalal: currentMarket.code === "tn",
  vatCategory: "",
  allergenCodes: [],
};

// Options et suppléments sur un article (« Cuisson », « Sauce »...) — France,
// MARCHE_FRANCE.md phase F5/A2. Prix en texte (comme Draft.price) pour un
// champ contrôlable pendant la saisie ; converti au moment d'enregistrer.
type OptionDraft = { name: string; priceDelta: string };
type OptionGroupDraft = { name: string; minSelect: string; maxSelect: string; options: OptionDraft[] };

function optionGroupsToDrafts(item: MenuItem): OptionGroupDraft[] {
  return item.option_groups.map((g) => ({
    name: g.name,
    minSelect: String(g.min_select),
    maxSelect: String(g.max_select),
    options: g.options.map((o) => ({ name: o.name, priceDelta: String(o.price_delta) })),
  }));
}

const EMPTY_OPTION_GROUP: OptionGroupDraft = { name: "", minSelect: "0", maxSelect: "1", options: [] };

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
  // Doit être appelé avant useCurrentStaff — voir lib/demoLien.ts.
  useAccesDemoParLien();
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["manager"]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [photoEnCours, setPhotoEnCours] = useState<number | null>(null);
  // Bannière de couverture + logo du restaurant (Phase D1 de
  // ROADMAP_DESIGN.md) — un seul de chaque, pas besoin d'un id comme pour
  // photoEnCours ci-dessus qui distingue quarante plats.
  const [couvertureEnCours, setCouvertureEnCours] = useState(false);
  const [logoEnCours, setLogoEnCours] = useState(false);
  // Icônes réseaux sociaux du menu client (Phase D1, point 3) — un seul
  // formulaire pour les cinq liens, enregistrés ensemble au clic sur
  // "Enregistrer" (pas au blur : un blur par champ envoyait un PATCH par
  // champ rempli, et désactivait les inputs suivants pendant l'aller-retour).
  const [facebookUrl, setFacebookUrl] = useState("");
  const [instagramUrl, setInstagramUrl] = useState("");
  const [tiktokUrl, setTiktokUrl] = useState("");
  const [whatsappUrl, setWhatsappUrl] = useState("");
  const [googleReviewUrl, setGoogleReviewUrl] = useState("");
  const [savingReseaux, setSavingReseaux] = useState(false);
  const [legalAddress, setLegalAddress] = useState("");
  const [taxId, setTaxId] = useState("");
  const [vatNumber, setVatNumber] = useState("");
  const [savingLegalInfo, setSavingLegalInfo] = useState(false);
  // Photo choisie pour un plat pas encore créé : elle attend d'avoir un
  // identifiant à qui être rattachée.
  const [nouvellePhoto, setNouvellePhoto] = useState<File | null>(null);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [newItem, setNewItem] = useState<Draft>(EMPTY_DRAFT);
  const [error, setError] = useState<string | null>(null);
  const [upgradeTier, setUpgradeTier] = useState<SubscriptionTier | null>(null);
  // Palier tout juste activé (paiement réel ou démo) — voir applyTierUpdate,
  // affiche WelcomeTierModal au lieu du simple flash() qui passait inaperçu
  // (retour utilisateur, 2026-09-02).
  const [celebratingTier, setCelebratingTier] = useState<SubscriptionTier | null>(null);
  // Confirmation avant rétrogradation — modale Tawla plutôt que
  // window.confirm() natif (retour utilisateur, 2026-09-02).
  const [confirmingDowngradeTier, setConfirmingDowngradeTier] = useState<SubscriptionTier | null>(null);
  const [downgradeSubmitting, setDowngradeSubmitting] = useState(false);
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);

  // Un seul point d'entrée pour appliquer une fiche restaurant mise à jour
  // après un paiement de palier (réel ou démo) — sur les quatre chemins qui
  // peuvent en produire une (retour Konnect/Stripe, UpgradeModal,
  // SubscriptionReminderModal, ActivationRequired) : ouvre WelcomeTierModal
  // uniquement quand le palier a réellement changé, jamais sur un simple
  // rechargement de la même fiche. Déclaré tôt (avant les effets de retour
  // de paiement plus bas, qui le référencent dans leur tableau de
  // dépendances) : un `const` n'est pas remonté comme une `function`.
  const applyTierUpdate = useCallback(
    (updated: Restaurant) => {
      const previousTier = restaurant?.subscription_tier;
      setRestaurant(updated);
      // `restaurant` encore `null` (fiche pas encore chargée, retour de
      // paiement arrivé avant `load()`) : on ne SAIT pas si le palier a
      // vraiment changé, donc on ne fête rien — mieux vaut silencieux que
      // fêter à tort un palier qui n'a pas bougé (retour utilisateur,
      // 2026-09-02 : modale "Bienvenue" affichée alors que le paiement
      // n'avait pas abouti côté serveur, webhook local injoignable).
      if (previousTier !== undefined && updated.subscription_tier !== previousTier) {
        setCelebratingTier(updated.subscription_tier);
      }
    },
    [restaurant],
  );
  const [message, setMessage] = useState<string | null>(null);
  // Rappel de paiement (offre de lancement, 2026-08-21) : "Plus tard" ne le
  // ferme que pour cette page ouverte — jamais mémorisé, il doit réapparaître
  // à chaque connexion (voir SubscriptionReminderModal).
  const [paymentReminderDismissed, setPaymentReminderDismissed] = useState(false);
  const [dayStats, setDayStats] = useState<DashboardStats | null>(null);
  const [savingPlan, setSavingPlan] = useState(false);
  const [ramadanEnabled, setRamadanEnabled] = useState(false);
  const [iftarInput, setIftarInput] = useState("");
  const [savingRamadan, setSavingRamadan] = useState(false);
  const [cafeModeEnabled, setCafeModeEnabled] = useState(false);
  const [savingCafeMode, setSavingCafeMode] = useState(false);
  const [kitchenSoundEnabled, setKitchenSoundEnabled] = useState(false);
  const [savingKitchenSound, setSavingKitchenSound] = useState(false);
  const [konnectApiKeyInput, setKonnectApiKeyInput] = useState("");
  const [konnectWalletIdInput, setKonnectWalletIdInput] = useState("");
  const [savingKonnect, setSavingKonnect] = useState(false);
  const [startingStripeConnect, setStartingStripeConnect] = useState(false);
  const [tables, setTables] = useState<Table[]>([]);
  const [tableDrafts, setTableDrafts] = useState<Record<number, TableDraft>>({});
  const [newTable, setNewTable] = useState<TableDraft>(EMPTY_TABLE_DRAFT);
  const [copiedTableId, setCopiedTableId] = useState<number | null>(null);
  const [downloadingPosterId, setDownloadingPosterId] = useState<number | null>(null);
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
  // Brouillon des groupes d'options par article — initialisé à l'ouverture de
  // l'édition depuis item.option_groups (voir optionGroupsToDrafts), jamais
  // au chargement de la carte entière (France, MARCHE_FRANCE.md phase F5/A2).
  const [optionDrafts, setOptionDrafts] = useState<Record<number, OptionGroupDraft[]>>({});
  const [savingOptionsFor, setSavingOptionsFor] = useState<number | null>(null);
  // Vocabulaire de régimes du restaurant (« Halal », « Végétarien »...),
  // propre à chaque établissement plutôt qu'une liste figée — demande de
  // Wassim, 2026-08-26. Coexiste avec la case « Halal » existante.
  const [regimeVocabulary, setRegimeVocabulary] = useState<MenuRegime[]>([]);
  const [newRegimeName, setNewRegimeName] = useState("");
  const [savingVocab, setSavingVocab] = useState(false);
  const [savingItemRegimesFor, setSavingItemRegimesFor] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");

  const restaurantId = staff?.restaurant_id ?? null;

  const load = useCallback(async () => {
    if (!restaurantId) return;
    try {
      // La fiche restaurant d'abord, séparément : contrairement au reste
      // (voir require_active_restaurant côté backend), elle reste lisible
      // même si le compte n'est pas encore activé — c'est elle qui permet de
      // savoir s'il faut afficher l'écran de paiement (2026-08-20) plutôt que
      // le dashboard. Inutile de lancer les autres requêtes (menu, tables,
      // équipe, stats) si elles vont toutes échouer en 402.
      const rest = await api.getRestaurant(restaurantId);
      setRestaurant(rest);
      setRamadanEnabled(rest.ramadan_mode_enabled);
      setIftarInput(isoToLocalInput(rest.iftar_time));
      setCafeModeEnabled(rest.cafe_mode_enabled);
      setKitchenSoundEnabled(rest.kitchen_sound_enabled);
      setFacebookUrl(rest.facebook_url ?? "");
      setInstagramUrl(rest.instagram_url ?? "");
      setTiktokUrl(rest.tiktok_url ?? "");
      setWhatsappUrl(rest.whatsapp_url ?? "");
      setGoogleReviewUrl(rest.google_review_url ?? "");
      setLegalAddress(rest.legal_address ?? "");
      setTaxId(rest.tax_id ?? "");
      setVatNumber(rest.vat_number ?? "");
      if (!rest.is_active) return;

      const [menu, tableList, teamList, suggested, regimeList, dayStats] = await Promise.all([
        api.getMenu(restaurantId),
        api.listTables(restaurantId),
        api.listStaff(restaurantId),
        api.getMenuSuggestions(restaurantId),
        api.getMenuRegimes(restaurantId),
        // Best-effort : si les chiffres du jour échouent, le manager doit
        // quand même pouvoir gérer sa carte et ses tables.
        api.getDashboardStats(restaurantId).catch(() => null),
      ]);
      setDayStats(dayStats);
      setItems(menu);
      setDrafts(Object.fromEntries(menu.map((m) => [m.id, itemToDraft(m)])));
      setTables(tableList);
      setTableDrafts(Object.fromEntries(tableList.map((t) => [t.id, tableToDraft(t)])));
      setTeam(teamList);
      setStaffDrafts(Object.fromEntries(teamList.map((m) => [m.id, staffToDraft(m)])));
      setSuggestions(suggested);
      setRegimeVocabulary(regimeList);
    } catch (e) {
      handleGatedError(e);
    }
  }, [restaurantId]);

  useEffect(() => {
    if (restaurantId) load();
  }, [restaurantId, load]);

  // Le badge de palier de l'en-tête (EnteteManager, cliquable depuis les
  // quatre écrans de direction) pointe vers `?tab=settings` : ouvrir
  // directement l'onglet Réglages plutôt que de laisser le manager
  // rechercher la carte "Palier d'abonnement" (retour utilisateur,
  // 2026-09-02 : "doit être cliquable"). `#abonnement` sur la carte fait le
  // reste du travail de défilement, géré par le navigateur.
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("tab") === "settings") setActiveTab("settings");
  }, []);

  // Page de retour du paiement en ligne d'un palier (`?konnect=success` /
  // `?konnect=fail`, voir tenants/router.py::start_subscription_checkout) :
  // en dev local le webhook Konnect ne peut jamais joindre localhost, ce
  // filet de sécurité est donc le SEUL moyen de refléter le paiement. Restait
  // non branché côté frontend malgré l'endpoint déjà prêt (`api.
  // checkSubscriptionPayment`) — sans lui un manager qui revient de Konnect
  // voit son ancien palier tant qu'il ne recharge pas après le webhook.
  useEffect(() => {
    if (!restaurantId) return;
    const params = new URLSearchParams(window.location.search);
    const konnectResult = params.get("konnect");
    if (!konnectResult) return;
    window.history.replaceState(null, "", window.location.pathname);
    if (konnectResult === "success") {
      api
        .checkSubscriptionPayment(restaurantId)
        .then(applyTierUpdate)
        .catch((e) => setError(toFrenchMessage(e)));
    } else if (konnectResult === "fail") {
      // purchase_completed est émis côté serveur (settle_subscription_payment,
      // seule source de vérité côté paiement) — mais aucun signal serveur
      // n'existe pour un échec/abandon Konnect, uniquement ce retour client.
      trackEvent("purchase_cancelled");
      setError("Le paiement n'a pas abouti. Vous pouvez réessayer depuis Réglages.");
    }
  }, [restaurantId, applyTierUpdate]);

  // Même filet de sécurité que ci-dessus, côté Stripe (France) — paramètre
  // distinct (`stripe_subscription=`) pour ne jamais se confondre avec le
  // retour de l'onboarding Connect (`?stripe=return`/`?stripe=refresh`, voir
  // startStripeConnect), un usage totalement différent de la même query key.
  useEffect(() => {
    if (!restaurantId) return;
    const params = new URLSearchParams(window.location.search);
    const stripeResult = params.get("stripe_subscription");
    if (!stripeResult) return;
    window.history.replaceState(null, "", window.location.pathname);
    if (stripeResult === "success") {
      api
        .checkSubscriptionPayment(restaurantId)
        .then(applyTierUpdate)
        .catch((e) => setError(toFrenchMessage(e)));
    } else if (stripeResult === "fail") {
      trackEvent("purchase_cancelled");
      setError("Le paiement n'a pas abouti. Vous pouvez réessayer depuis Réglages.");
    }
  }, [restaurantId, applyTierUpdate]);

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
      trackEvent("paywall_hit", { required_tier: tier, is_demo: Boolean(sessionDemo()) });
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

  async function saveKonnectCredentials() {
    if (!restaurantId || !konnectApiKeyInput.trim() || !konnectWalletIdInput.trim()) return;
    setError(null);
    setSavingKonnect(true);
    try {
      const updated = await api.setKonnectCredentials(
        restaurantId, konnectApiKeyInput.trim(), konnectWalletIdInput.trim()
      );
      setRestaurant(updated);
      setKonnectApiKeyInput("");
      flash("Konnect connecté — le paiement carte de vos clients passe désormais par votre compte.");
    } catch (e) {
      handleGatedError(e);
    } finally {
      setSavingKonnect(false);
    }
  }

  async function confirmDowngrade() {
    if (!restaurantId || !confirmingDowngradeTier) return;
    const tier = confirmingDowngradeTier;
    const isDemo = Boolean(restaurant?.is_demo);
    setError(null);
    setDowngradeSubmitting(true);
    try {
      const updated = await api.scheduleDowngrade(restaurantId, tier);
      setRestaurant(updated);
      setConfirmingDowngradeTier(null);
      flash(
        isDemo
          ? `Simulation — palier ${TIER_LABELS[tier]} appliqué.`
          : `Passage à ${TIER_LABELS[tier]} programmé pour la prochaine échéance.`
      );
    } catch (e) {
      handleGatedError(e);
    } finally {
      setDowngradeSubmitting(false);
    }
  }

  async function manageSubscription() {
    if (!restaurantId) return;
    setError(null);
    try {
      const { portal_url } = await api.openBillingPortal(restaurantId);
      // Nouvel onglet, pas une redirection sur place (retour utilisateur,
      // 2026-09-02) : contrairement au paiement (success_url/fail_url
      // ramènent automatiquement sur Tawla), le portail Stripe n'a pas de
      // retour prévu — perdre l'onglet du dashboard manager n'aurait aucun
      // intérêt.
      window.open(portal_url, "_blank", "noopener,noreferrer");
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function simulateCancel() {
    // Établissement de démo uniquement (voir tenants/router.py::
    // simulate_subscription_cancellation) — jamais de vrai portail à ouvrir
    // pour un compte sans vrai abonnement Stripe (retour utilisateur,
    // 2026-09-02 bis : "active tout même pour la démo").
    if (!restaurantId) return;
    setError(null);
    try {
      const updated = await api.simulateSubscriptionCancel(restaurantId);
      setRestaurant(updated);
      flash("Simulation — abonnement résilié, plus aucun accès jusqu'à un nouveau palier.");
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function startStripeConnect() {
    if (!restaurantId) return;
    setError(null);
    setStartingStripeConnect(true);
    try {
      const { onboarding_url } = await api.startStripeConnect(restaurantId);
      window.location.href = onboarding_url;
    } catch (e) {
      handleGatedError(e);
      setStartingStripeConnect(false);
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
        allergen_codes: draft.allergenCodes.length ? draft.allergenCodes.join(",") : null,
        is_halal: draft.isHalal,
        vat_category: draft.vatCategory || null,
      });
      flash(`« ${draft.name} » enregistré.`);
      trackEvent("menu_edited", { feature: "edit_item", is_demo: Boolean(sessionDemo()) });
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
      trackEvent("menu_edited", { feature: "upload_photo", is_demo: Boolean(sessionDemo()) });
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
      trackEvent("menu_edited", { feature: "remove_photo", is_demo: Boolean(sessionDemo()) });
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function deposerCouverture(fichier: File) {
    if (!restaurantId) return;
    setError(null);
    setCouvertureEnCours(true);
    try {
      const reduite = await reduirePhoto(fichier);
      const misAJour = await api.uploadRestaurantCoverPhoto(restaurantId, reduite);
      setRestaurant(misAJour);
      flash("Photo de couverture ajoutée.");
    } catch (e) {
      handleGatedError(e);
    } finally {
      setCouvertureEnCours(false);
    }
  }

  async function retirerCouverture() {
    if (!restaurantId) return;
    setError(null);
    try {
      const misAJour = await api.deleteRestaurantCoverPhoto(restaurantId);
      setRestaurant(misAJour);
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function deposerLogo(fichier: File) {
    if (!restaurantId) return;
    setError(null);
    setLogoEnCours(true);
    try {
      const reduite = await reduirePhoto(fichier);
      const misAJour = await api.uploadRestaurantLogo(restaurantId, reduite);
      setRestaurant(misAJour);
      flash("Logo ajouté.");
    } catch (e) {
      handleGatedError(e);
    } finally {
      setLogoEnCours(false);
    }
  }

  async function retirerLogo() {
    if (!restaurantId) return;
    setError(null);
    try {
      const misAJour = await api.deleteRestaurantLogo(restaurantId);
      setRestaurant(misAJour);
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function saveReseaux() {
    if (!restaurantId) return;
    setError(null);
    setSavingReseaux(true);
    try {
      const misAJour = await api.setSocialLinks(restaurantId, {
        facebook_url: facebookUrl.trim() || null,
        instagram_url: instagramUrl.trim() || null,
        tiktok_url: tiktokUrl.trim() || null,
        whatsapp_url: whatsappUrl.trim() || null,
        google_review_url: googleReviewUrl.trim() || null,
      });
      setRestaurant(misAJour);
      flash("Liens enregistrés.");
    } catch (e) {
      handleGatedError(e);
    } finally {
      setSavingReseaux(false);
    }
  }

  async function saveLegalInfo() {
    if (!restaurantId) return;
    setError(null);
    setSavingLegalInfo(true);
    try {
      const misAJour = await api.setLegalInfo(restaurantId, {
        legal_address: legalAddress.trim() || null,
        tax_id: taxId.trim() || null,
        vat_number: vatNumber.trim() || null,
      });
      setRestaurant(misAJour);
      flash("Mentions légales enregistrées.");
    } catch (e) {
      handleGatedError(e);
    } finally {
      setSavingLegalInfo(false);
    }
  }

  async function toggleAvailability(item: MenuItem) {
    setError(null);
    try {
      await api.setMenuItemAvailability(item.id, !item.is_available);
      trackEvent("menu_edited", { feature: "toggle_availability", is_demo: Boolean(sessionDemo()) });
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
      trackEvent("menu_edited", { feature: "remove_item", is_demo: Boolean(sessionDemo()) });
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
        allergen_codes: newItem.allergenCodes.length ? newItem.allergenCodes.join(",") : null,
        is_halal: newItem.isHalal,
        vat_category: newItem.vatCategory || null,
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
      trackEvent("menu_edited", { feature: "add_item", is_demo: Boolean(sessionDemo()) });
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
      trackEvent("table_managed", { feature: "edit_table", is_demo: Boolean(sessionDemo()) });
      await load();
    } catch (e) {
      handleGatedError(e);
    }
  }

  async function downloadTablePoster(table: Table) {
    setError(null);
    setDownloadingPosterId(table.id);
    try {
      const blob = await api.downloadTablePoster(table.id);
      const slug = table.label.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `tawla-affiche-${slug || table.id}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
      trackEvent("table_managed", { feature: "download_poster", is_demo: Boolean(sessionDemo()) });
    } catch (e) {
      handleGatedError(e);
    } finally {
      setDownloadingPosterId(null);
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
      trackEvent("table_managed", { feature: "add_table", is_demo: Boolean(sessionDemo()) });
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
      trackEvent("menu_edited", { feature: "toggle_suggestion", is_demo: Boolean(sessionDemo()) });
    } catch (e) {
      handleGatedError(e);
    } finally {
      setSavingSuggestionsFor(null);
    }
  }

  // --- Options et suppléments (France, MARCHE_FRANCE.md phase F5/A2) -------

  function optionGroupsFor(item: MenuItem): OptionGroupDraft[] {
    return optionDrafts[item.id] ?? optionGroupsToDrafts(item);
  }

  function updateOptionGroups(itemId: number, next: OptionGroupDraft[]) {
    setOptionDrafts((prev) => ({ ...prev, [itemId]: next }));
  }

  function addOptionGroup(item: MenuItem) {
    updateOptionGroups(item.id, [...optionGroupsFor(item), { ...EMPTY_OPTION_GROUP }]);
  }

  function removeOptionGroup(item: MenuItem, groupIndex: number) {
    updateOptionGroups(item.id, optionGroupsFor(item).filter((_, i) => i !== groupIndex));
  }

  function updateOptionGroupField(
    item: MenuItem, groupIndex: number, field: "name" | "minSelect" | "maxSelect", value: string
  ) {
    const groups = optionGroupsFor(item).map((g, i) => (i === groupIndex ? { ...g, [field]: value } : g));
    updateOptionGroups(item.id, groups);
  }

  function addOption(item: MenuItem, groupIndex: number) {
    const groups = optionGroupsFor(item).map((g, i) =>
      i === groupIndex ? { ...g, options: [...g.options, { name: "", priceDelta: "0" }] } : g
    );
    updateOptionGroups(item.id, groups);
  }

  function removeOption(item: MenuItem, groupIndex: number, optionIndex: number) {
    const groups = optionGroupsFor(item).map((g, i) =>
      i === groupIndex ? { ...g, options: g.options.filter((_, oi) => oi !== optionIndex) } : g
    );
    updateOptionGroups(item.id, groups);
  }

  function updateOptionField(
    item: MenuItem, groupIndex: number, optionIndex: number, field: "name" | "priceDelta", value: string
  ) {
    const groups = optionGroupsFor(item).map((g, i) =>
      i === groupIndex
        ? { ...g, options: g.options.map((o, oi) => (oi === optionIndex ? { ...o, [field]: value } : o)) }
        : g
    );
    updateOptionGroups(item.id, groups);
  }

  async function saveOptionGroups(item: MenuItem) {
    setError(null);
    const drafts = optionGroupsFor(item);
    for (const g of drafts) {
      const min = Number(g.minSelect);
      const max = Number(g.maxSelect);
      if (!g.name.trim()) {
        setError("Chaque groupe d'options doit avoir un nom (ex : « Cuisson »).");
        return;
      }
      if (g.options.length === 0) {
        setError(`Le groupe « ${g.name} » doit contenir au moins un choix.`);
        return;
      }
      if (g.options.some((o) => !o.name.trim())) {
        setError(`Un choix du groupe « ${g.name} » n'a pas de nom.`);
        return;
      }
      if (Number.isNaN(min) || Number.isNaN(max) || min < 0 || max < 1 || min > max) {
        setError(`« ${g.name} » : le minimum et le maximum de choix ne sont pas valides.`);
        return;
      }
    }
    setSavingOptionsFor(item.id);
    try {
      await api.setMenuItemOptionGroups(
        item.id,
        drafts.map((g) => ({
          name: g.name.trim(),
          min_select: Number(g.minSelect),
          max_select: Number(g.maxSelect),
          options: g.options.map((o) => ({ name: o.name.trim(), price_delta: Number(o.priceDelta) || 0 })),
        }))
      );
      flash("Options enregistrées.");
      trackEvent("menu_edited", { feature: "save_options", is_demo: Boolean(sessionDemo()) });
      await load();
    } catch (e) {
      handleGatedError(e);
    } finally {
      setSavingOptionsFor(null);
    }
  }

  // --- Régimes alimentaires (France, demande de Wassim 2026-08-26) ---------
  // Vocabulaire propre au restaurant (pas une liste figée), coexiste avec la
  // case "Halal" existante plutôt que de la remplacer.

  async function saveRegimeVocabulary(names: string[]) {
    setError(null);
    setSavingVocab(true);
    try {
      const next = await api.setMenuRegimes(restaurantId!, names);
      setRegimeVocabulary(next);
    } catch (e) {
      handleGatedError(e);
    } finally {
      setSavingVocab(false);
    }
  }

  async function addRegimeToVocab() {
    const name = newRegimeName.trim();
    if (!name) return;
    if (regimeVocabulary.some((r) => r.name === name)) {
      setNewRegimeName("");
      return;
    }
    await saveRegimeVocabulary([...regimeVocabulary.map((r) => r.name), name]);
    setNewRegimeName("");
  }

  async function removeRegimeFromVocab(name: string) {
    await saveRegimeVocabulary(regimeVocabulary.filter((r) => r.name !== name).map((r) => r.name));
  }

  async function toggleItemRegime(item: MenuItem, regimeId: number) {
    setError(null);
    const current = item.regimes.map((r) => r.id);
    const next = current.includes(regimeId) ? current.filter((id) => id !== regimeId) : [...current, regimeId];
    setSavingItemRegimesFor(item.id);
    try {
      const updated = await api.setMenuItemRegimes(item.id, next);
      setItems((prev) => prev.map((i) => (i.id === item.id ? updated : i)));
    } catch (e) {
      handleGatedError(e);
    } finally {
      setSavingItemRegimesFor(null);
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
      trackEvent("csv_imported", {
        created_count: result.created_count,
        updated_count: result.updated_count,
        is_demo: Boolean(sessionDemo()),
      });
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
      trackEvent("staff_managed", { feature: "add_staff", is_demo: Boolean(sessionDemo()) });
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
      trackEvent("staff_managed", { feature: "edit_staff", is_demo: Boolean(sessionDemo()) });
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
      trackEvent("staff_managed", { feature: "toggle_active", is_demo: Boolean(sessionDemo()) });
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
      trackEvent("staff_managed", { feature: "reset_password", is_demo: Boolean(sessionDemo()) });
    } catch (e) {
      handleGatedError(e);
    }
  }

  if (staffLoading || !staff) {
    return (
      <div className="p-4 md:p-6 space-y-3">
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

  // Écran bloquant, jamais une modale dismissible (contrairement à
  // UpgradeModal) : Essentiel n'est jamais gratuit, y compris pour un compte
  // inscrit en self-service (2026-08-20, voir CLAUDE.md). Gardé par
  // `restaurant &&` : ne rien afficher tant que la fiche restaurant n'a pas
  // fini de charger (voir load()), pour ne jamais flasher cet écran avant le
  // dashboard normal chez un compte déjà actif.
  if (restaurant && !restaurant.is_active) {
    return (
      <>
        <ActivationRequired restaurant={restaurant} onActivated={applyTierUpdate} />
        {celebratingTier && <WelcomeTierModal tier={celebratingTier} onClose={() => setCelebratingTier(null)} />}
      </>
    );
  }

  const filteredItems = items.filter((item) => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.trim().toLowerCase());
    const matchesCategory = categoryFilter === "all" || item.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="p-4 md:p-6">
      {upgradeTier && restaurantId && (
        <UpgradeModal
          restaurantId={restaurantId}
          requiredTier={upgradeTier}
          restaurant={restaurant ?? undefined}
          onClose={() => setUpgradeTier(null)}
          onUpgraded={applyTierUpdate}
        />
      )}
      {restaurant && !restaurant.is_demo && !restaurant.has_paid_for_subscription && !paymentReminderDismissed && (
        <SubscriptionReminderModal
          restaurant={restaurant}
          onPaid={(updated) => {
            applyTierUpdate(updated);
            setPaymentReminderDismissed(true);
          }}
          onDismiss={() => setPaymentReminderDismissed(true)}
        />
      )}
      {celebratingTier && <WelcomeTierModal tier={celebratingTier} onClose={() => setCelebratingTier(null)} />}
      {confirmingDowngradeTier && restaurant?.subscription_period_end && (
        <ConfirmDowngradeModal
          tier={confirmingDowngradeTier}
          periodEndLabel={formatDate(restaurant.subscription_period_end)}
          isDemo={Boolean(restaurant.is_demo)}
          submitting={downgradeSubmitting}
          onConfirm={confirmDowngrade}
          onCancel={() => setConfirmingDowngradeTier(null)}
        />
      )}
      <EnteteManager
        titre="Carte"
        sousTitre="Modifier un plat, signaler une rupture, en ajouter un — et déposer les photos en les glissant sur leur vignette."
        palier={restaurant?.subscription_tier}
      />

      <div data-visite="dashboard-recette">
        <RecetteDuJour stats={dayStats} />
      </div>

      {error && (
        <Card tone="danger" padding="sm" className="mb-4 text-sm text-[var(--harissa)]">
          {error}
        </Card>
      )}
      {message && (
        <Card tone="success" padding="sm" className="mb-4 text-sm text-[var(--menthe)]">
          {message}
        </Card>
      )}

      <div className="flex flex-col md:flex-row gap-4 md:gap-6 md:items-start">
        <Card
          dark
          padding="sm"
          className="flex md:block gap-1 md:space-y-1 overflow-x-auto md:w-48 md:shrink-0 md:sticky md:top-4"
          data-visite="dashboard-onglets"
        >
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`shrink-0 whitespace-nowrap text-left px-3 py-2 rounded-lg text-sm font-semibold transition-colors md:w-full ${
                activeTab === tab.key
                  ? "bg-[var(--harissa-on-espresso-bg)] text-[var(--harissa-on-espresso-text)]"
                  : "text-[var(--ink-on-espresso)] hover:text-[var(--ink-on-espresso-strong)]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </Card>

        <div className="flex-1 min-w-0">
      {activeTab === "menu" && (
        <>
          <Card padding="sm" className="mb-3">
            <p className="text-sm font-medium">Régimes proposés</p>
            <p className="text-xs text-neutral-500 mb-2">
              Halal, végétarien, vegan, ou tout régime de votre choix — visibles des clients, à cocher
              plat par plat plus bas.
            </p>
            <div className="flex flex-wrap gap-1.5 items-center">
              {regimeVocabulary.map((r) => (
                <span
                  key={r.id}
                  className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full border border-[var(--line)] bg-white"
                >
                  {r.name}
                  <button
                    onClick={() => removeRegimeFromVocab(r.name)}
                    disabled={savingVocab}
                    aria-label={`Retirer ${r.name} du vocabulaire`}
                    className="text-neutral-400 hover:text-[var(--harissa)] disabled:opacity-50"
                  >
                    ✕
                  </button>
                </span>
              ))}
              <input
                value={newRegimeName}
                onChange={(e) => setNewRegimeName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addRegimeToVocab();
                  }
                }}
                placeholder="Nouveau régime (ex : Sans porc)"
                className="border rounded px-2 py-1 text-xs w-48"
              />
              <Button size="sm" variant="secondary" onClick={addRegimeToVocab} disabled={savingVocab}>
                + Ajouter
              </Button>
            </div>
          </Card>

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
              {currentMarket.menuCategories.map((c) => (
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
                        {item.category} · {formatMoney(item.price)}
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
                          {currentMarket.menuCategories.map((c) => (
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
                          placeholder={`Prix (${currentMarket.currency.symbol})`}
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
                        photoUrl={item.image_url}
                        alt={item.name}
                        label="Photo du plat"
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
                      <ChampsVatAllergenes
                        vatCategory={draft.vatCategory}
                        allergenCodes={draft.allergenCodes}
                        onVatCategoryChange={(value) =>
                          setDrafts((d) => ({ ...d, [item.id]: { ...draft, vatCategory: value } }))
                        }
                        onAllergenCodesChange={(codes) =>
                          setDrafts((d) => ({ ...d, [item.id]: { ...draft, allergenCodes: codes } }))
                        }
                      />
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

                      <div className="mt-4 pt-3 border-t border-[var(--line)]">
                        <p className="text-sm font-medium">Options et suppléments</p>
                        <p className="text-xs text-neutral-500 mb-2">
                          Cuisson, sauce, accompagnement, taille... Un groupe obligatoire à choix
                          unique (min 1, max 1) bloque la commande tant que le client n&apos;a rien
                          choisi — utile pour une cuisson qui doit toujours être précisée.
                        </p>
                        <div className="space-y-3">
                          {optionGroupsFor(item).map((group, groupIndex) => (
                            <div key={groupIndex} className="rounded-lg border border-[var(--line)] p-2.5">
                              <div className="grid grid-cols-1 sm:grid-cols-[2fr_1fr_1fr_auto] gap-2 items-center">
                                <input
                                  value={group.name}
                                  onChange={(e) => updateOptionGroupField(item, groupIndex, "name", e.target.value)}
                                  className="border rounded px-2 py-1 text-sm"
                                  placeholder="Nom du groupe (ex : Cuisson)"
                                />
                                <label className="flex items-center gap-1.5 text-xs text-neutral-500">
                                  Min
                                  <input
                                    type="number"
                                    min={0}
                                    value={group.minSelect}
                                    onChange={(e) => updateOptionGroupField(item, groupIndex, "minSelect", e.target.value)}
                                    className="border rounded px-2 py-1 text-sm w-16"
                                  />
                                </label>
                                <label className="flex items-center gap-1.5 text-xs text-neutral-500">
                                  Max
                                  <input
                                    type="number"
                                    min={1}
                                    value={group.maxSelect}
                                    onChange={(e) => updateOptionGroupField(item, groupIndex, "maxSelect", e.target.value)}
                                    className="border rounded px-2 py-1 text-sm w-16"
                                  />
                                </label>
                                <Button size="sm" variant="danger" onClick={() => removeOptionGroup(item, groupIndex)}>
                                  Retirer
                                </Button>
                              </div>
                              <div className="mt-2 space-y-1.5">
                                {group.options.map((option, optionIndex) => (
                                  <div key={optionIndex} className="grid grid-cols-[2fr_1fr_auto] gap-2 items-center">
                                    <input
                                      value={option.name}
                                      onChange={(e) => updateOptionField(item, groupIndex, optionIndex, "name", e.target.value)}
                                      className="border rounded px-2 py-1 text-sm"
                                      placeholder="Choix (ex : À point)"
                                    />
                                    <input
                                      value={option.priceDelta}
                                      onChange={(e) => updateOptionField(item, groupIndex, optionIndex, "priceDelta", e.target.value)}
                                      className="border rounded px-2 py-1 text-sm"
                                      placeholder={`Supplément (${currentMarket.currency.symbol})`}
                                      inputMode="decimal"
                                    />
                                    <button
                                      onClick={() => removeOption(item, groupIndex, optionIndex)}
                                      aria-label={`Retirer ${option.name || "ce choix"}`}
                                      className="text-neutral-400 hover:text-[var(--harissa)] text-sm px-1"
                                    >
                                      ✕
                                    </button>
                                  </div>
                                ))}
                              </div>
                              <Button
                                size="sm" variant="secondary" className="mt-2"
                                onClick={() => addOption(item, groupIndex)}
                              >
                                + Ajouter un choix
                              </Button>
                            </div>
                          ))}
                        </div>
                        <div className="flex items-center justify-between mt-2.5 flex-wrap gap-2">
                          <Button size="sm" variant="secondary" onClick={() => addOptionGroup(item)}>
                            + Ajouter un groupe d&apos;options
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => saveOptionGroups(item)}
                            disabled={savingOptionsFor === item.id}
                          >
                            {savingOptionsFor === item.id ? "Enregistrement..." : "Enregistrer les options"}
                          </Button>
                        </div>
                      </div>

                      {regimeVocabulary.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-[var(--line)]">
                          <p className="text-sm font-medium">Régimes de ce plat</p>
                          <div className="flex flex-wrap gap-1.5 mt-1">
                            {regimeVocabulary.map((r) => {
                              const selected = item.regimes.some((ir) => ir.id === r.id);
                              return (
                                <button
                                  key={r.id}
                                  onClick={() => toggleItemRegime(item, r.id)}
                                  disabled={savingItemRegimesFor === item.id}
                                  aria-pressed={selected}
                                  className={`text-xs px-2 py-1 rounded-full border transition-colors disabled:opacity-50 ${
                                    selected
                                      ? "bg-[var(--harissa)] text-white border-[var(--harissa)]"
                                      : "border-[var(--line)] text-neutral-600 hover:bg-[var(--semoule)]"
                                  }`}
                                >
                                  {r.name}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
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
                    {currentMarket.menuCategories.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                  <input
                    value={newItem.price}
                    onChange={(e) => setNewItem({ ...newItem, price: e.target.value })}
                    className="border rounded px-2 py-1"
                    placeholder={`Prix (${currentMarket.currency.symbol})`}
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
                <ChampsVatAllergenes
                  vatCategory={newItem.vatCategory}
                  allergenCodes={newItem.allergenCodes}
                  onVatCategoryChange={(value) => setNewItem({ ...newItem, vatCategory: value })}
                  onAllergenCodesChange={(codes) => setNewItem({ ...newItem, allergenCodes: codes })}
                />
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
                  // Renvoyé à EditeurDePlan : sans ce throw, son brouillon local
                  // croit l'enregistrement réussi et garde la table affichée posée
                  // sur le plan alors que le serveur l'a refusée (palier Essentiel).
                  throw e;
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
              const clientLink =
                typeof window !== "undefined" ? `${window.location.origin}/menu/${table.qr_token}` : null;
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
                  {/* Sans ce lien, seul un accès direct à l'API donnait le
                      qr_token : le manager dépendait de nous pour tester ou
                      remplacer un QR perdu, alors que la donnée est déjà là
                      côté client (audit pilote, 2026-08-19). */}
                  <div className="sm:col-span-3 flex items-center gap-2 text-xs text-neutral-500">
                    <span className="truncate">
                      Lien client : {typeof window !== "undefined" ? window.location.origin : ""}/menu/
                      {table.qr_token}
                    </span>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        const link = `${window.location.origin}/menu/${table.qr_token}`;
                        navigator.clipboard.writeText(link);
                        setCopiedTableId(table.id);
                        setTimeout(() => setCopiedTableId((id) => (id === table.id ? null : id)), 2000);
                      }}
                    >
                      {copiedTableId === table.id ? "Copié !" : "Copier le lien"}
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      disabled={downloadingPosterId === table.id}
                      onClick={() => downloadTablePoster(table)}
                    >
                      {downloadingPosterId === table.id ? "Téléchargement..." : "Télécharger l'affiche (PDF)"}
                    </Button>
                  </div>
                  {clientLink && (
                    <div className="sm:col-span-3">
                      <QrCode url={clientLink} alt={`QR code — ${table.label}`} caption={table.label} />
                    </div>
                  )}
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
              <p className="font-medium text-[var(--menthe)]">Identifiants à transmettre maintenant</p>
              <dl className="mt-2 text-sm grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[var(--menthe)]">
                <dt className="text-[var(--menthe)]/80">E-mail</dt>
                <dd className="font-mono break-all">{newCredentials.email}</dd>
                <dt className="text-[var(--menthe)]/80">Mot de passe</dt>
                <dd className="font-mono break-all">{newCredentials.password}</dd>
              </dl>
              <p className="text-xs text-[var(--menthe)]/80 mt-2">
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
          {restaurant && currentMarket.ramadanModeAvailable && (
            <Card tone="warning" padding="sm" className="mb-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <label className="flex items-center gap-2 font-medium text-[#8a6420]">
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
                    <label htmlFor="iftar-time" className="text-[#8a6420]">
                      Heure de l&apos;iftar aujourd&apos;hui
                    </label>
                    <input
                      id="iftar-time"
                      type="datetime-local"
                      value={iftarInput}
                      onChange={(e) => setIftarInput(e.target.value)}
                      onBlur={() => saveRamadanMode(true)}
                      disabled={savingRamadan}
                      className="bg-white border border-[var(--line)] rounded px-2 py-1"
                    />
                  </div>
                )}
              </div>
              <p className="text-xs text-[#8a6420] mt-2">
                Une fois activé, les clients peuvent pré-commander pour l&apos;iftar depuis le menu. Pensez à mettre
                à jour l&apos;heure chaque jour (elle varie). Astuce : classez vos plats de rupture du jeûne dans la
                catégorie « Ftour » pour qu&apos;ils ressortent bien sur le menu client.
              </p>
            </Card>
          )}

          {restaurant && (
            <Card tone="info" padding="sm" className="mb-4">
              <label className="flex items-center gap-2 font-medium text-[#8a6420]">
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
              <p className="text-xs text-[#8a6420] mt-2">
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
              <span className="font-medium">Photo de couverture et logo</span>
              <p className="text-xs text-neutral-500 mt-1">
                Affichés en tête du menu client, à la place de l&apos;aplat de couleur uni. Facultatifs — sans eux, le
                menu garde son en-tête actuel.
              </p>
              <div className="mt-2">
                <ZonePhoto
                  photoUrl={restaurant.cover_photo_url}
                  alt={`Photo de couverture — ${restaurant.name}`}
                  label="Photo de couverture"
                  enCours={couvertureEnCours}
                  onFichier={deposerCouverture}
                  onRetirer={retirerCouverture}
                />
              </div>
              <div className="mt-3">
                <ZonePhoto
                  photoUrl={restaurant.logo_url}
                  alt={`Logo — ${restaurant.name}`}
                  label="Logo"
                  enCours={logoEnCours}
                  onFichier={deposerLogo}
                  onRetirer={retirerLogo}
                />
              </div>
            </Card>
          )}

          {restaurant && (
            <Card padding="sm" className="mt-4">
              <span className="font-medium">Réseaux sociaux et avis Google</span>
              <p className="text-xs text-neutral-500 mt-1">
                Affichés en petites icônes dans l&apos;en-tête du menu client. Facultatifs, indépendants les uns des
                autres — laisser un champ vide retire son icône sans toucher aux autres. Un seul bouton
                Enregistrer pour les cinq liens ci-dessous.
              </p>
              <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
                <label className="text-sm">
                  <span className="flex items-center gap-1.5 text-xs text-neutral-500 mb-0.5">
                    <FacebookIcon className="w-3.5 h-3.5" /> Facebook
                  </span>
                  <input
                    type="url"
                    value={facebookUrl}
                    disabled={savingReseaux}
                    onChange={(e) => setFacebookUrl(e.target.value)}
                    placeholder="https://facebook.com/…"
                    className="bg-white border border-[var(--line)] rounded px-2 py-1 w-full"
                  />
                </label>
                <label className="text-sm">
                  <span className="flex items-center gap-1.5 text-xs text-neutral-500 mb-0.5">
                    <InstagramIcon className="w-3.5 h-3.5" /> Instagram
                  </span>
                  <input
                    type="url"
                    value={instagramUrl}
                    disabled={savingReseaux}
                    onChange={(e) => setInstagramUrl(e.target.value)}
                    placeholder="https://instagram.com/…"
                    className="bg-white border border-[var(--line)] rounded px-2 py-1 w-full"
                  />
                </label>
                <label className="text-sm">
                  <span className="flex items-center gap-1.5 text-xs text-neutral-500 mb-0.5">
                    <TikTokIcon className="w-3.5 h-3.5" /> TikTok
                  </span>
                  <input
                    type="url"
                    value={tiktokUrl}
                    disabled={savingReseaux}
                    onChange={(e) => setTiktokUrl(e.target.value)}
                    placeholder="https://tiktok.com/@…"
                    className="bg-white border border-[var(--line)] rounded px-2 py-1 w-full"
                  />
                </label>
                <label className="text-sm">
                  <span className="flex items-center gap-1.5 text-xs text-neutral-500 mb-0.5">
                    <WhatsAppIcon className="w-3.5 h-3.5" /> WhatsApp
                  </span>
                  <input
                    type="url"
                    value={whatsappUrl}
                    disabled={savingReseaux}
                    onChange={(e) => setWhatsappUrl(e.target.value)}
                    placeholder="https://wa.me/216…"
                    className="bg-white border border-[var(--line)] rounded px-2 py-1 w-full"
                  />
                </label>
              </div>

              <div className="mt-4 pt-3 border-t border-[var(--line)]">
                <span className="text-xs text-neutral-500 font-medium">Avis Google</span>
                <p className="text-xs text-neutral-500 mt-1">
                  Une fois l&apos;addition réglée, le client voit une invitation à laisser un avis Google avec ce
                  lien. Facultatif — sans lui, rien ne s&apos;affiche après le paiement.
                </p>
                <label className="text-sm mt-2 block">
                  <span className="text-xs text-neutral-500 mb-0.5 block">Lien vers la fiche d&apos;avis</span>
                  <input
                    type="url"
                    value={googleReviewUrl}
                    disabled={savingReseaux}
                    onChange={(e) => setGoogleReviewUrl(e.target.value)}
                    placeholder="https://g.page/r/…/review"
                    className="bg-white border border-[var(--line)] rounded px-2 py-1 w-full"
                  />
                </label>
              </div>

              <div className="mt-3">
                <Button size="sm" onClick={saveReseaux} disabled={savingReseaux}>
                  {savingReseaux ? "Enregistrement..." : "Enregistrer"}
                </Button>
              </div>
            </Card>
          )}

          {restaurant && (
            <Card padding="sm" className="mt-4">
              <span className="font-medium">Mentions légales de la facture</span>
              <p className="text-xs text-neutral-500 mt-1">
                Affichées sur la facture PDF envoyée à vos clients (adresse, SIRET ou matricule fiscal, TVA
                intracommunautaire). Facultatives, indépendantes les unes des autres — laisser un champ vide le
                retire sans toucher aux autres.
              </p>
              <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
                <label className="text-sm sm:col-span-2">
                  <span className="text-xs text-neutral-500 mb-0.5 block">Adresse</span>
                  <input
                    type="text"
                    value={legalAddress}
                    disabled={savingLegalInfo}
                    onChange={(e) => setLegalAddress(e.target.value)}
                    placeholder="12 rue de la République, 75011 Paris"
                    className="bg-white border border-[var(--line)] rounded px-2 py-1 w-full"
                  />
                </label>
                <label className="text-sm">
                  <span className="text-xs text-neutral-500 mb-0.5 block">SIRET / matricule fiscal</span>
                  <input
                    type="text"
                    value={taxId}
                    disabled={savingLegalInfo}
                    onChange={(e) => setTaxId(e.target.value)}
                    placeholder="812 345 678 00019"
                    className="bg-white border border-[var(--line)] rounded px-2 py-1 w-full"
                  />
                </label>
                <label className="text-sm">
                  <span className="text-xs text-neutral-500 mb-0.5 block">TVA intracommunautaire</span>
                  <input
                    type="text"
                    value={vatNumber}
                    disabled={savingLegalInfo}
                    onChange={(e) => setVatNumber(e.target.value)}
                    placeholder="FR32812345678"
                    className="bg-white border border-[var(--line)] rounded px-2 py-1 w-full"
                  />
                </label>
              </div>

              <div className="mt-3">
                <Button size="sm" onClick={saveLegalInfo} disabled={savingLegalInfo}>
                  {savingLegalInfo ? "Enregistrement..." : "Enregistrer"}
                </Button>
              </div>
            </Card>
          )}

          {restaurant && (
            <Card id="abonnement" padding="sm" className="mt-4 scroll-mt-4">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium">Votre palier :</span>
                <span
                  className="text-sm font-semibold px-2.5 py-1 rounded-full border-2"
                  style={{
                    backgroundColor: TIER_ACCENTS[restaurant.subscription_tier].fond,
                    borderColor: TIER_ACCENTS[restaurant.subscription_tier].bord,
                    color: TIER_ACCENTS[restaurant.subscription_tier].texte,
                  }}
                >
                  {TIER_LABELS[restaurant.subscription_tier]}
                </span>
              </div>
              {/* Essentiel est un abonnement payant comme Pro/Business,
                  jamais une exception (retour utilisateur, 2026-09-02 :
                  "Essentiel c'est payant") — la garde qui l'excluait ici
                  cachait le bouton "Gérer mon abonnement" à un manager
                  Essentiel pourtant bel et bien abonné. */}
              {restaurant.subscription_period_end &&
                (restaurant.stripe_subscription_active ? (
                  // Abonnement récurrent (mode Netflix, 2026-09-02) : se
                  // renouvelle tout seul, contrairement à Konnect ci-dessous
                  // — jamais le même texte "sans renouvellement d'ici là",
                  // qui serait faux ici et inquiéterait pour rien.
                  <>
                    <p className="text-xs text-neutral-500 mt-2">
                      {restaurant.subscription_cancel_at_period_end ? (
                        restaurant.subscription_tier === "essentiel" ? (
                          // Essentiel est déjà le palier le plus bas — "repasse
                          // à Essentiel" n'aurait aucun sens ici (retour
                          // utilisateur, 2026-09-02). Dire ce qui se passe
                          // vraiment : accès gratuit conservé, plus jamais
                          // prélevé, jusqu'à un réabonnement volontaire.
                          <>
                            Abonnement annulé — accès Essentiel conservé au-delà du{" "}
                            {formatDate(restaurant.subscription_period_end)}, sans nouveau prélèvement.
                          </>
                        ) : (
                          <>
                            Abonnement annulé — accès conservé jusqu&apos;au{" "}
                            {formatDate(restaurant.subscription_period_end)}, puis repasse à Essentiel.
                          </>
                        )
                      ) : (
                        <>
                          Prochain prélèvement le {formatDate(restaurant.subscription_period_end)}. Renouvellement
                          automatique chaque mois.
                        </>
                      )}
                    </p>
                    <Button variant="secondary" onClick={manageSubscription} className="mt-2">
                      Gérer mon abonnement
                    </Button>
                  </>
                ) : (
                  <>
                    <p className="text-xs text-neutral-500 mt-2">
                      Valable jusqu&apos;au {formatDate(restaurant.subscription_period_end)}. Repasse automatiquement
                      à Essentiel sans renouvellement d&apos;ici là.
                    </p>
                    {currentMarket.paymentProvider === "stripe" && restaurant.is_demo && (
                      // Établissement de démo : jamais de vrai abonnement à
                      // résilier (voir stripe_subscription_active), donc pas
                      // de vrai portail — un clic simule directement l'effet
                      // d'une résiliation réelle (retour utilisateur,
                      // 2026-09-02 : "un bouton de simulation pour... paiement
                      // pour tawla", et 2026-09-02 bis : "active tout même
                      // pour la démo").
                      <Button variant="secondary" onClick={simulateCancel} className="mt-2">
                        Simuler la résiliation
                      </Button>
                    )}
                  </>
                ))}

              {UPGRADE_TIERS_ABOVE[restaurant.subscription_tier].length > 0 && (
                <div className="mt-4">
                  <p className={`${lalezar.className} text-xl text-[var(--encre)]`}>Passez au palier suivant</p>
                  <div className="grid sm:grid-cols-2 gap-3 mt-2">
                    {UPGRADE_TIERS_ABOVE[restaurant.subscription_tier].map((tier) => {
                      const accent = TIER_ACCENTS[tier.id];
                      const currentPriceDT = TIERS.find((t) => t.id === restaurant.subscription_tier)?.priceDT ?? 0;
                      const proration =
                        restaurant.stripe_subscription_active && restaurant.subscription_period_end
                          ? estimateUpgradeProration(currentPriceDT, tier.priceDT, restaurant.subscription_period_end)
                          : null;
                      return (
                        <div
                          key={tier.id}
                          className="rounded-xl border-2 p-4 flex flex-col"
                          style={{ backgroundColor: accent.fond, borderColor: accent.bord }}
                        >
                          {tier.recommended && (
                            <span
                              className="self-start text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full mb-2"
                              style={{ backgroundColor: accent.texte, color: "var(--semoule)" }}
                            >
                              Recommandé
                            </span>
                          )}
                          <p className={`${lalezar.className} text-2xl`} style={{ color: accent.texte }}>
                            {tier.name}
                          </p>
                          <p className="text-xs text-[var(--ink-soft)] mt-0.5">{tier.tagline}</p>
                          <p className="mt-2">
                            <span className="text-2xl font-semibold text-[var(--encre)] tabular-nums">
                              {tier.priceDT} {currentMarket.currency.symbol}
                            </span>
                            <span className="text-sm text-[var(--ink-soft)]"> / mois</span>
                          </p>
                          {proration !== null ? (
                            // Argument de vente (retour utilisateur,
                            // 2026-09-02) : montrer que l'upgrade ne coûte
                            // presque rien en fin de mois, pas juste "89€/mois"
                            // qui peut faire hésiter.
                            <p className="text-[11px] font-medium mt-0.5" style={{ color: "var(--menthe)" }}>
                              ~{proration} {currentMarket.currency.symbol} aujourd&apos;hui (prorata), puis plein
                              tarif au prochain prélèvement.
                            </p>
                          ) : restaurant.is_demo ? (
                            // Établissement de démo (jetable, purgé sous 2h) :
                            // jamais le texte de prélèvement réel ci-dessous —
                            // le backend force le mode simulé quel que soit
                            // PAYMENT_MODE (retour utilisateur, 2026-09-02),
                            // ce texte doit le dire clairement plutôt que de
                            // laisser croire à un vrai abonnement.
                            <p className="text-[11px] text-[var(--ink-soft)] mt-0.5">
                              Simulation — aucun prélèvement réel en démo.
                            </p>
                          ) : (
                            currentMarket.paymentProvider === "stripe" && (
                              // Abonnement RÉCURRENT (mode Netflix, 2026-09-02)
                              // — jamais laisser croire à un paiement unique,
                              // voir la même note dans UpgradeModal.tsx (retour
                              // utilisateur : "ça peut coûter de l'argent").
                              <p className="text-[11px] text-[var(--ink-soft)] mt-0.5">
                                Prélevé chaque mois, résiliable à tout moment.
                              </p>
                            )
                          )}
                          <ul className="mt-2 space-y-1 text-sm text-[var(--encre)] flex-1">
                            {tier.features.slice(0, 4).map((feature) => (
                              <li key={feature}>• {feature}</li>
                            ))}
                          </ul>
                          <Button
                            variant={tier.recommended ? "primary" : "laiton"}
                            onClick={() => setUpgradeTier(tier.id)}
                            className="mt-3 w-full"
                          >
                            {restaurant.is_demo
                              ? "Simuler"
                              : currentMarket.paymentProvider === "stripe"
                                ? "S'abonner à"
                                : "Passer à"}{" "}
                            {tier.name}
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {currentMarket.paymentProvider === "stripe" && restaurant.subscription_downgrade_pending_tier && (
                // Indicateur PERSISTANT — sans lui, rien ne distingue un clic
                // réussi d'un clic resté sans effet une fois le flash() de
                // 2,5 secondes disparu (retour utilisateur, 2026-09-02 :
                // "je reste à Business sans aucune indication").
                <p
                  className="mt-3 text-sm rounded px-3 py-2"
                  style={{ backgroundColor: "rgba(184,134,46,.12)", color: "var(--laiton)" }}
                >
                  Rétrogradation vers <strong>{TIER_LABELS[restaurant.subscription_downgrade_pending_tier]}</strong>{" "}
                  programmée pour le {formatDate(restaurant.subscription_period_end ?? "")}.
                </p>
              )}

              {currentMarket.paymentProvider === "stripe" &&
                (restaurant.stripe_subscription_active || restaurant.is_demo) &&
                DOWNGRADE_TIERS_BELOW[restaurant.subscription_tier].length > 0 && (
                  // Rétrogradation en restant abonné, distincte d'annuler
                  // (retour utilisateur, 2026-09-02) — jamais pour Konnect,
                  // qui n'a pas de notion d'abonnement actif à modifier.
                  // Aussi pour un établissement de démo (2026-09-02 bis :
                  // "active tout même pour la démo") — sans vrai abonnement à
                  // programmer, appliqué immédiatement plutôt qu'à une
                  // échéance que personne ne reverra dans la session de 2h.
                  <div className="mt-4">
                    <p className={`${lalezar.className} text-xl text-[var(--encre)]`}>
                      Ou redescendre à un palier moins cher
                    </p>
                    <p className="text-xs text-neutral-500 mt-1">
                      {restaurant.is_demo
                        ? "Simulation — appliqué immédiatement."
                        : `Effectif à la prochaine échéance (${formatDate(restaurant.subscription_period_end ?? "")}), jamais immédiat — vous gardez ${TIER_LABELS[restaurant.subscription_tier]} jusque-là.`}
                    </p>
                    <div className="grid sm:grid-cols-2 gap-3 mt-2">
                      {DOWNGRADE_TIERS_BELOW[restaurant.subscription_tier].map((tier) => {
                        const lost = featuresLostGoingTo(restaurant.subscription_tier, tier.id);
                        return (
                          <div key={tier.id} className="rounded-xl border border-[var(--line)] p-3">
                            <p className="text-sm font-medium text-[var(--encre)]">
                              {tier.name} — {tier.priceDT} {currentMarket.currency.symbol}/mois
                            </p>
                            {lost.length > 0 && (
                              <>
                                <p className="text-xs text-[var(--harissa)] mt-1.5">Vous perdrez :</p>
                                <ul className="mt-0.5 space-y-0.5 text-xs text-neutral-500">
                                  {lost.map((feature) => (
                                    <li key={feature}>• {feature}</li>
                                  ))}
                                </ul>
                              </>
                            )}
                            <Button
                              variant="secondary"
                              onClick={() => setConfirmingDowngradeTier(tier.id)}
                              disabled={restaurant.subscription_downgrade_pending_tier === tier.id}
                              className="mt-2 w-full"
                            >
                              {restaurant.is_demo
                                ? `Simuler ${tier.name}`
                                : restaurant.subscription_downgrade_pending_tier === tier.id
                                  ? "Déjà programmé ✓"
                                  : `Passer à ${tier.name}`}
                            </Button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
            </Card>
          )}

          {restaurant && currentMarket.paymentProvider === "konnect" && (
            <Card padding="sm" className="mt-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Paiement carte de vos clients</span>
                <Badge tone={restaurant.is_demo || restaurant.konnect_configured ? "success" : "neutral"}>
                  {restaurant.is_demo ? "Simulé" : restaurant.konnect_configured ? "Connecté" : "Non connecté"}
                </Badge>
              </div>
              {restaurant.is_demo ? (
                // Connecter un vrai wallet est bloqué côté backend pour un
                // établissement de démo (jetable, purgé sous 2h) — inutile
                // d'afficher un formulaire qui échouerait au clic, le
                // paiement carte y est déjà simulé automatiquement (retour
                // utilisateur, 2026-09-02 : "un bouton de simulation pour...
                // paiement de son client").
                <p className="text-xs text-neutral-500 mt-2">
                  Simulation — paiement carte confirmé immédiatement, sans vrai débit. La connexion d&apos;un
                  vrai wallet Konnect n&apos;est pas proposée sur un établissement de démonstration.
                </p>
              ) : restaurant.subscription_tier === "essentiel" ? (
                <>
                  <p className="text-xs text-neutral-500 mt-2 mb-3">
                    Le paiement carte est réservé aux paliers Pro et Business. En Essentiel, vos clients
                    règlent uniquement en espèces.
                  </p>
                  <Button variant="secondary" disabled>
                    Connecter
                  </Button>
                  <button
                    type="button"
                    onClick={() => setUpgradeTier("pro")}
                    className="block text-xs text-[var(--harissa)] underline mt-2"
                  >
                    Passer à Pro pour l&apos;activer
                  </button>
                </>
              ) : (
                <>
                  <p className="text-xs text-neutral-500 mt-2 mb-3">
                    Sans compte Konnect connecté, le paiement carte reste en mode démonstration (confirmé
                    immédiatement, sans vrai débit). Une fois connecté, vos clients règlent directement votre propre
                    compte — jamais celui de Tawla.
                    {restaurant.konnect_configured && restaurant.konnect_wallet_id && (
                      <> Wallet connecté : <code className="text-neutral-700">{restaurant.konnect_wallet_id}</code>.</>
                    )}
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-[2fr_2fr_auto] gap-2">
                    <input
                      type="password"
                      value={konnectApiKeyInput}
                      onChange={(e) => setKonnectApiKeyInput(e.target.value)}
                      placeholder="Clé API Konnect"
                      className="border rounded px-2 py-1"
                    />
                    <input
                      value={konnectWalletIdInput}
                      onChange={(e) => setKonnectWalletIdInput(e.target.value)}
                      placeholder="ID du portefeuille"
                      className="border rounded px-2 py-1"
                    />
                    <Button
                      onClick={saveKonnectCredentials}
                      disabled={savingKonnect || !konnectApiKeyInput.trim() || !konnectWalletIdInput.trim()}
                    >
                      {restaurant.konnect_configured ? "Remplacer" : "Connecter"}
                    </Button>
                  </div>
                  <p className="text-xs text-neutral-500 mt-2">
                    Jamais réaffichée après coup, comme un mot de passe temporaire — vous pourrez toujours la
                    remplacer par une nouvelle.
                  </p>
                </>
              )}
            </Card>
          )}

          {restaurant && currentMarket.paymentProvider === "stripe" && (
            <Card padding="sm" className="mt-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Paiement carte de vos clients</span>
                <Badge tone={restaurant.is_demo || restaurant.stripe_configured ? "success" : "neutral"}>
                  {restaurant.is_demo ? "Simulé" : restaurant.stripe_configured ? "Connecté" : "Non connecté"}
                </Badge>
              </div>
              {restaurant.is_demo ? (
                <p className="text-xs text-neutral-500 mt-2">
                  Simulation — paiement carte confirmé immédiatement, sans vrai débit. La connexion d&apos;un
                  vrai compte Stripe n&apos;est pas proposée sur un établissement de démonstration.
                </p>
              ) : restaurant.subscription_tier === "essentiel" ? (
                <>
                  <p className="text-xs text-neutral-500 mt-2 mb-3">
                    Le paiement carte est réservé aux paliers Pro et Business. En Essentiel, vos clients
                    règlent uniquement en espèces.
                  </p>
                  <Button variant="secondary" disabled>
                    Connecter Stripe
                  </Button>
                  <button
                    type="button"
                    onClick={() => setUpgradeTier("pro")}
                    className="block text-xs text-[var(--harissa)] underline mt-2"
                  >
                    Passer à Pro pour l&apos;activer
                  </button>
                </>
              ) : (
                <>
                  <p className="text-xs text-neutral-500 mt-2 mb-3">
                    Sans compte Stripe connecté, le paiement carte reste en mode démonstration (confirmé
                    immédiatement, sans vrai débit). Une fois connecté, vos clients règlent directement votre propre
                    compte Stripe — jamais celui de Tawla.
                  </p>
                  <Button onClick={startStripeConnect} disabled={startingStripeConnect}>
                    {restaurant.stripe_configured ? "Gérer mon compte Stripe" : "Connecter Stripe"}
                  </Button>
                  <p className="text-xs text-neutral-500 mt-2">
                    Vous serez redirigé vers Stripe pour renseigner vos informations — Tawla ne les reçoit jamais.
                  </p>
                </>
              )}
            </Card>
          )}
        </>
      )}
        </div>
      </div>
    </div>
  );
}
