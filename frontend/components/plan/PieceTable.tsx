"use client";

import { EtatTable, LIBELLE_URGENCE, PlanTable, demandeUnServeur, libelleAttente, secondesDepuis } from "./types";

/**
 * Une table dessinée sur le plan.
 *
 * Le contraste est volontairement inversé par rapport au reste de l'application :
 * le sol du plan est sombre, les plateaux sont clairs. C'est ce qui fait qu'une
 * table qui attend — la seule chose colorée de l'écran — se repère sans effort,
 * y compris dans une salle peu éclairée.
 *
 * Trois choses à lire, dans cet ordre pour un serveur qui traverse la salle :
 *
 * 1. **La couleur dit s'il faut y aller.** Clair = rien à faire ; terne avec un
 *    liseré froid = en cuisine, pas pour lui ; harissa = on l'attend.
 * 2. **Le chiffre dit dans quel ordre.** Quand plusieurs tables commandent en
 *    même temps — le cas normal d'un service — chacune porte son rang d'arrivée,
 *    et le temps affiché monte sans jamais s'arrêter. Le serveur n'a pas à
 *    arbitrer entre six tables rouges qui se valent : la 1 attend depuis le plus
 *    longtemps, c'est elle d'abord.
 * 3. **Les chaises disent le nombre de couverts** — et c'est ce qui fait lire un
 *    meuble plutôt qu'une pastille.
 *
 * Pas de clignotement : dans une salle, ce qui clignote est ignoré au bout de
 * dix minutes, ou insupportable. Seule la table la plus urgente respire, et
 * cette respiration s'arrête sous `prefers-reduced-motion`.
 */

const TAILLE: Record<PlanTable["shape"], { w: number; h: number; r: number }> = {
  round: { w: 82, h: 82, r: 41 },
  square: { w: 78, h: 78, r: 14 },
  rect: { w: 116, h: 72, r: 14 },
};

const CHAISE = { l: 20, e: 9, ecart: 11 };

/** Position des chaises autour du plateau, dans le repère de la table. */
function chaises(shape: PlanTable["shape"], seats: number, w: number, h: number) {
  const places: { x: number; y: number; rot: number }[] = [];
  const n = Math.max(1, Math.min(12, seats));

  if (shape === "round") {
    const rayon = w / 2 + CHAISE.ecart;
    for (let i = 0; i < n; i += 1) {
      const a = (i / n) * 2 * Math.PI - Math.PI / 2;
      places.push({
        x: Math.cos(a) * rayon,
        y: Math.sin(a) * rayon,
        rot: (a * 180) / Math.PI + 90,
      });
    }
    return places;
  }

  // Table droite : on répartit d'abord sur les deux longueurs, puis sur les
  // bouts quand il reste des couverts — comme on dresse une vraie table.
  const parLong = Math.min(Math.ceil(n / 2), 4);
  const dessus = Math.ceil(n / 2) > parLong ? parLong : Math.ceil(n / 2);
  const dessous = Math.min(n - dessus, parLong);
  const bouts = n - dessus - dessous;

  for (let i = 0; i < dessus; i += 1)
    places.push({ x: -w / 2 + ((i + 0.5) * w) / dessus, y: -h / 2 - CHAISE.ecart, rot: 0 });
  for (let i = 0; i < dessous; i += 1)
    places.push({ x: -w / 2 + ((i + 0.5) * w) / dessous, y: h / 2 + CHAISE.ecart, rot: 0 });
  if (bouts >= 1) places.push({ x: -w / 2 - CHAISE.ecart, y: 0, rot: 90 });
  if (bouts >= 2) places.push({ x: w / 2 + CHAISE.ecart, y: 0, rot: 90 });

  return places;
}

export default function PieceTable({
  table,
  etat,
  maintenant,
  rang = null,
  laPlusUrgente = false,
  selectionnee = false,
  onActiver,
  enDeplacement = false,
}: {
  table: PlanTable;
  etat: EtatTable;
  maintenant: number;
  /** Rang d'arrivée parmi les tables qui attendent d'être prises en charge. */
  rang?: number | null;
  laPlusUrgente?: boolean;
  selectionnee?: boolean;
  onActiver?: () => void;
  enDeplacement?: boolean;
}) {
  const { w, h } = TAILLE[table.shape];
  const appelle = demandeUnServeur(etat.urgence);
  const attente = libelleAttente(secondesDepuis(etat.depuis, maintenant));

  // Marge autour du plateau : les chaises et la pastille de rang vivent là.
  const m = CHAISE.ecart + CHAISE.e + 4;
  const W = w + m * 2;
  const H = h + m * 2;

  const tone = appelle ? "appelle" : etat.urgence === "en_cuisine" ? "cuisine" : "libre";

  return (
    <button
      type="button"
      onClick={onActiver}
      data-tone={tone}
      data-forme={table.shape}
      data-urgente={laPlusUrgente ? "" : undefined}
      data-selectionnee={selectionnee ? "" : undefined}
      data-deplacement={enDeplacement ? "" : undefined}
      className="piece"
      style={{ width: W, height: H }}
      aria-label={
        appelle
          ? `${table.label}, ${table.seats} couverts — ${LIBELLE_URGENCE[etat.urgence]} ${attente}` +
            (rang ? `, ${rang}${rang === 1 ? "re" : "e"} à avoir commandé` : "")
          : `${table.label}, ${table.seats} couverts — ${LIBELLE_URGENCE[etat.urgence] || "rien à faire"}`
      }
    >
      <svg className="dessin" viewBox={`${-W / 2} ${-H / 2} ${W} ${H}`} aria-hidden="true">
        {chaises(table.shape, table.seats, w, h).map((c, i) => (
          <rect
            key={i}
            className="chaise"
            x={c.x - CHAISE.l / 2}
            y={c.y - CHAISE.e / 2}
            width={CHAISE.l}
            height={CHAISE.e}
            rx={4}
            transform={`rotate(${c.rot} ${c.x} ${c.y})`}
          />
        ))}

        <rect className="plateau" x={-w / 2} y={-h / 2} width={w} height={h} rx={TAILLE[table.shape].r} />
      </svg>

      <span className="contenu">
        <span className="etiquette">{table.label}</span>
        {appelle && <span className="minutes">{attente}</span>}
        {!appelle && etat.urgence === "en_cuisine" && <span className="minutes">en cuisine</span>}
      </span>

      {/* Le rang d'arrivée, posé sur le coin de la table : 1 a commandé en
          premier. C'est le seul chiffre qui décide de quelque chose. */}
      {rang !== null && (
        <span className="rang" data-premier={rang === 1 ? "" : undefined} aria-hidden="true">
          {rang}
        </span>
      )}
      {etat.aMoi && <span className="mienne" aria-hidden="true" />}
    </button>
  );
}
