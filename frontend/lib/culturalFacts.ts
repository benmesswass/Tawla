import { currentMarket } from "@/lib/market";

// Anecdotes culturelles affichées pendant l'attente cuisine (voir
// menu/[qrToken]/page.tsx) — un petit plus pendant les 10-20 minutes
// d'attente, plutôt qu'un écran silencieux. Faits vérifiés (UNESCO,
// géographie, traditions), pas de contenu spécifique à un plat précis du
// menu (celui-ci variant d'un restaurant à l'autre).
//
// Contenu propre à CHAQUE marché — jamais une traduction d'un marché vers
// l'autre (le couscous n'a rien à faire devant un client parisien, et
// inversement). Sur le marché France, le contenu est en plus scindé par
// type d'établissement (`Restaurant.cafe_mode_enabled`, déjà existant côté
// produit) : les habitués d'un café n'ont pas les mêmes réflexes qu'une
// table de restaurant.

const TUNISIA_FACTS: Record<"fr" | "ar", string[]> = {
  fr: [
    "Le couscous est inscrit au patrimoine culturel immatériel de l'UNESCO depuis 2020, une tradition partagée par l'Algérie, le Maroc, la Mauritanie et la Tunisie.",
    "La harissa tunisienne est elle-même reconnue par l'UNESCO depuis 2022 comme patrimoine culturel immatériel de l'humanité.",
    "Servir le thé à la menthe est un rituel d'hospitalité en Tunisie — le refuser peut être perçu comme un manque de politesse envers son hôte.",
    "Le brik, cette fine feuille croustillante à l'œuf, est un classique incontournable des tables tunisiennes pendant le Ramadan.",
    "Le tajine tunisien n'a rien à voir avec le plat mijoté marocain du même nom : c'est une sorte de quiche épaisse à base d'œufs, souvent servie froide.",
    "L'huile d'olive tunisienne compte parmi les plus anciennes traditions agricoles du pays, avec des oliviers cultivés depuis l'Antiquité.",
    "Le lablabi, une soupe de pois chiches épicée servie avec du pain rassis, est un plat populaire souvent pris au petit-déjeuner.",
    "La Tunisie est l'un des plus grands producteurs de dattes au monde, notamment la variété Deglet Nour, surnommée « doigt de lumière ».",
  ],
  ar: [
    "الكسكسي مسجل فالتراث الثقافي اللامادي لليونسكو من 2020 — تقليد نتقاسموه مع الجزائر والمغرب وموريتانيا.",
    "الهريسة التونسية زادة مسجلة عند اليونسكو من 2022 كتراث ثقافي لامادي للإنسانية.",
    "تقديم أتاي بالنعناع عادة تونسية أصيلة فالضيافة — رفضه يتحسب قلة أدب مع إلي عزمك.",
    "البريك، الورقة القرمشة بالعظمة، أكلة ما تنقصش من مائدة رمضان فتونس.",
    "التاجين التونسي ما عندوش علاقة بالطاجين المغربي — عندنا هو أكلة بالعظمة تشبه الكيش، وتتاكل بارة.",
    "زيت الزيتون التونسي من أقدم التقاليد الفلاحية فالبلاد، بزيتون مغروس من العصور القديمة.",
    "اللبلابي، شربة الحمص الحارة بالخبز اليابس، أكلة شعبية تتاكل حتى فطور الصباح.",
    "تونس من أكبر منتجي التمر فالعالم، خصوصا صنف « دقلة النور » إلي معناها « صباع النور ».",
  ],
};

// France, table de restaurant — gastronomie, vin, tradition de salle.
const FRANCE_RESTAURANT_FACTS: Record<"fr" | "en", string[]> = {
  fr: [
    "Le repas gastronomique des Français est inscrit au patrimoine culturel immatériel de l'UNESCO depuis 2010 — ce n'est pas un plat qui est reconnu, mais l'art de bien manger et bien boire ensemble.",
    "La baguette de tradition française, encadrée par un décret depuis 1993 (rien d'autre que farine, eau, sel et levure), a été reconnue à son tour par l'UNESCO en 2022 comme patrimoine immatériel.",
    "Le système des Appellations d'Origine Contrôlée, qui protège les vins et fromages français par leur origine géographique, existe depuis 1935 — l'un des plus anciens systèmes de ce genre au monde.",
    "Le service « à la russe » (les plats apportés les uns après les autres) a remplacé au XIXe siècle le service « à la française » (tout posé sur la table en même temps) — c'est l'origine de l'ordre entrée, plat, dessert que l'on connaît aujourd'hui.",
    "Le trou normand — un petit verre de calvados entre deux plats, censé « faire de la place » — reste une tradition de certaines tables normandes et bourguignonnes.",
    "La France compte plusieurs centaines de fromages différents ; le général de Gaulle aurait demandé, dans une citation restée célèbre, comment gouverner un pays qui en compte autant.",
    "Le mot « restaurant » vient à l'origine d'un bouillon censé « restaurer » les forces, vendu à Paris au XVIIIe siècle, avant de désigner l'établissement lui-même.",
  ],
  en: [
    "The gastronomic meal of the French has been on UNESCO's intangible cultural heritage list since 2010 — it's not a dish that's recognised, but the art of eating and drinking well together.",
    "The traditional French baguette, regulated by a decree since 1993 (nothing but flour, water, salt and yeast), was in turn recognised by UNESCO in 2022 as intangible heritage.",
    "The Appellation d'Origine Contrôlée system, which protects French wines and cheeses by their geographic origin, has existed since 1935 — one of the oldest such systems in the world.",
    "\"Service à la russe\" (dishes brought out one after another) replaced \"service à la française\" (everything laid on the table at once) during the 19th century — the origin of the starter, main, dessert order still used today.",
    "The \"trou normand\" — a small glass of calvados between courses, meant to \"make room\" — remains a tradition at some tables in Normandy and Burgundy.",
    "France has several hundred different cheeses; General de Gaulle is famously said to have asked how anyone could govern a country with that many.",
    "The word \"restaurant\" originally referred to a broth meant to \"restore\" one's strength, sold in 18th-century Paris, before it came to mean the establishment itself.",
  ],
};

// France, café/bar (`Restaurant.cafe_mode_enabled`) — rituels de comptoir et
// de terrasse, distincts d'une salle de restaurant.
const FRANCE_CAFE_FACTS: Record<"fr" | "en", string[]> = {
  fr: [
    "Dans un café français, un espresso pris au comptoir coûte traditionnellement moins cher qu'assis en salle ou en terrasse — un usage toujours répandu, parfois même affiché sur la carte.",
    "Le zinc, ce comptoir de bar traditionnellement recouvert de ce métal, a donné son nom familier au comptoir lui-même : « prendre un verre au zinc ».",
    "Des cafés parisiens comme le Café de Flore ou Les Deux Magots ont accueilli au XXe siècle des habitués devenus célèbres, écrivains et philosophes qui s'y retrouvaient pour écrire et débattre pendant des heures.",
    "L'apéritif, ce moment convivial pris avant le repas, est une véritable institution sociale en France — davantage un rituel qu'un simple verre.",
    "Le pastis, anisé et servi allongé d'eau, est associé à la culture des terrasses du sud de la France, en particulier autour de Marseille.",
    "S'attarder en terrasse devant un café, hiver comme été, n'est jamais mal vu en France — la terrasse reste un lieu de vie à part entière.",
  ],
  en: [
    "In a French café, an espresso taken standing at the counter is traditionally cheaper than the same coffee seated inside or on the terrace — a custom still widespread, sometimes even printed on the menu.",
    "\"Le zinc\", the bar counter traditionally covered in that metal, lent its name to the counter itself — \"having a drink at the zinc\" is still a common expression.",
    "Parisian cafés such as Café de Flore or Les Deux Magots hosted famous regulars during the 20th century — writers and philosophers who met there to write and debate for hours.",
    "The apéritif, a convivial moment before the meal, is a genuine social institution in France — more a ritual than just a drink.",
    "Pastis, an aniseed spirit served lengthened with water, is tied to terrace culture in the south of France, particularly around Marseille.",
    "Lingering on a café terrace over a coffee, winter or summer, is never frowned upon in France — the terrace remains a place to live in, not just to pass through.",
  ],
};

/**
 * Anecdotes pour CE marché, dans la langue en cours, adaptées au type
 * d'établissement quand le marché le distingue (France : restaurant vs
 * café/bar). `isCafeMode` : `Restaurant.cafe_mode_enabled`, déjà existant
 * côté produit — jamais un nouveau champ pour cette seule fonctionnalité.
 *
 * `marketCode` : paramètre explicite (comme `_pdf_money`/`nextLocaleOf`
 * ailleurs dans ce dépôt), pas seulement `currentMarket.code` en dur — sans
 * ça, un seul des deux marchés serait testable par process de test (celui
 * que `NEXT_PUBLIC_MARKET` fixe au chargement du module).
 */
export function culturalFactsFor(
  locale: string,
  isCafeMode: boolean,
  marketCode: string = currentMarket.code
): string[] {
  if (marketCode === "fr") {
    const set = isCafeMode ? FRANCE_CAFE_FACTS : FRANCE_RESTAURANT_FACTS;
    return set[locale === "en" ? "en" : "fr"];
  }
  return TUNISIA_FACTS[locale === "ar" ? "ar" : "fr"];
}
