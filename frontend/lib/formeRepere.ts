/**
 * La forme d'un repère du plan de salle — la géométrie, rien que la géométrie.
 *
 * Un repère (le bar, l'entrée) est l'**union** de ses tronçons rectangulaires :
 * un seul dessine un comptoir droit, deux en équerre un L, trois un U. Un
 * rectangle unique ne savait dire aucune de ces deux dernières formes, et
 * poser trois « bars » côte à côte donnait trois étiquettes pour un seul bar.
 *
 * Ici, pas de React : c'est du calcul, donc c'est testable seul — et c'est ce
 * calcul qui décide de ce que le manager voit, pas le CSS.
 */

export type Troncon = {
  /** Coin haut-gauche, en % de la surface du plan (pas le centre). */
  pos_x: number;
  pos_y: number;
  width: number;
  height: number;
};

export type Boite = { left: number; top: number; width: number; height: number };

/** Les coordonnées sont des % avec des décimales : sans arrondi, deux bords
 *  qui se touchent (44 et 43.999999) ne se reconnaissent pas et le contour
 *  se coupe en deux. */
function arrondi(v: number): number {
  return Math.round(v * 1000) / 1000;
}

/** Le plus petit rectangle qui contient tous les tronçons — le cadre dans
 *  lequel le repère est positionné et dessiné. */
export function boiteEnglobante(troncons: Troncon[]): Boite {
  const left = Math.min(...troncons.map((t) => t.pos_x));
  const top = Math.min(...troncons.map((t) => t.pos_y));
  const right = Math.max(...troncons.map((t) => t.pos_x + t.width));
  const bas = Math.max(...troncons.map((t) => t.pos_y + t.height));
  return { left, top, width: right - left, height: bas - top };
}

/** Le tronçon le plus large — celui qui porte l'icône et l'étiquette. Le
 *  centre de la boîte englobante ne convient pas : dans un U, il tombe dans
 *  le creux, donc à côté du bar. */
export function tronconLePlusGrand(troncons: Troncon[]): number {
  let gagnant = 0;
  let record = -1;
  troncons.forEach((t, i) => {
    const aire = t.width * t.height;
    if (aire > record) {
      record = aire;
      gagnant = i;
    }
  });
  return gagnant;
}

/**
 * Le tronçon que les gestes visent — celui du dernier appui, ou le plus large
 * à défaut : un repère fraîchement posé n'a encore été touché nulle part, et
 * un tronçon retiré laisse un index qui ne désigne plus rien.
 *
 * Une seule règle, partagée par la poignée (PieceRepere) et par les boutons
 * qui coudent ou retirent un tronçon (EditeurDePlan) — sinon ils finiraient
 * par viser deux tronçons différents.
 */
export function tronconVise(troncons: Troncon[], vise: number | null): number {
  return vise !== null && vise >= 0 && vise < troncons.length
    ? vise
    : tronconLePlusGrand(troncons);
}

/** Le centre d'un tronçon, en % de la surface. */
export function centre(t: Troncon): { x: number; y: number } {
  return { x: t.pos_x + t.width / 2, y: t.pos_y + t.height / 2 };
}

type Point = [number, number];
type Arete = { de: Point; a: Point };

/**
 * Le contour de l'union des tronçons, en chemin SVG (`d`), dans les mêmes
 * coordonnées que les tronçons eux-mêmes (% de la surface du plan).
 *
 * Un seul chemin, donc une seule bordure : deux tronçons qui se touchent ne
 * laissent pas de couture au milieu du comptoir, et deux qui se chevauchent
 * ne doublent pas la transparence du remplissage.
 *
 * La méthode : découper le plan sur tous les bords des tronçons (une grille
 * irrégulière), marquer les cases couvertes, ne garder que les arêtes entre
 * une case couverte et le vide, puis les enchaîner en boucles fermées. Chaque
 * arête est orientée « intérieur à droite », ce qui donne des boucles
 * cohérentes — un éventuel trou tourne dans l'autre sens et `fill-rule:
 * nonzero` le creuse tout seul.
 */
export function contourUnion(troncons: Troncon[]): string {
  const xs = [...new Set(troncons.flatMap((t) => [arrondi(t.pos_x), arrondi(t.pos_x + t.width)]))].sort(
    (a, b) => a - b
  );
  const ys = [...new Set(troncons.flatMap((t) => [arrondi(t.pos_y), arrondi(t.pos_y + t.height)]))].sort(
    (a, b) => a - b
  );

  const couverte = (i: number, j: number) => {
    if (i < 0 || j < 0 || i >= xs.length - 1 || j >= ys.length - 1) return false;
    const cx = (xs[i] + xs[i + 1]) / 2;
    const cy = (ys[j] + ys[j + 1]) / 2;
    return troncons.some(
      (t) =>
        cx > t.pos_x && cx < t.pos_x + t.width && cy > t.pos_y && cy < t.pos_y + t.height
    );
  };

  const aretes: Arete[] = [];
  for (let i = 0; i < xs.length - 1; i++) {
    for (let j = 0; j < ys.length - 1; j++) {
      if (!couverte(i, j)) continue;
      const [x0, x1, y0, y1] = [xs[i], xs[i + 1], ys[j], ys[j + 1]];
      // Sens de parcours choisi pour que l'intérieur soit toujours à droite
      // (en repère écran, y vers le bas).
      if (!couverte(i, j - 1)) aretes.push({ de: [x0, y0], a: [x1, y0] });
      if (!couverte(i + 1, j)) aretes.push({ de: [x1, y0], a: [x1, y1] });
      if (!couverte(i, j + 1)) aretes.push({ de: [x1, y1], a: [x0, y1] });
      if (!couverte(i - 1, j)) aretes.push({ de: [x0, y1], a: [x0, y0] });
    }
  }

  const cle = (p: Point) => `${p[0]},${p[1]}`;
  const depuis = new Map<string, Arete[]>();
  for (const a of aretes) {
    const liste = depuis.get(cle(a.de)) ?? [];
    liste.push(a);
    depuis.set(cle(a.de), liste);
  }

  const chemins: string[] = [];
  for (;;) {
    // N'importe quelle arête encore libre ouvre la boucle suivante : deux
    // tronçons éloignés l'un de l'autre donnent deux boucles.
    const depart = [...depuis.values()].find((l) => l.length > 0)?.[0];
    if (!depart) break;

    const boucle: Point[] = [];
    let courante: Arete | undefined = depart;
    while (courante) {
      depuis.get(cle(courante.de))?.splice(0, 1);
      boucle.push(courante.de);
      if (cle(courante.a) === cle(depart.de)) break;
      courante = depuis.get(cle(courante.a))?.[0];
    }

    // Les sommets alignés ne servent à rien : chaque jonction entre deux
    // tronçons bout à bout en produirait un au milieu d'un côté droit. Le
    // voisinage est circulaire — la jonction peut tomber sur le premier.
    const utiles = boucle.filter((p, i) => {
      const avant = boucle[(i - 1 + boucle.length) % boucle.length];
      const apres = boucle[(i + 1) % boucle.length];
      const colineaire =
        (avant[0] === p[0] && p[0] === apres[0]) || (avant[1] === p[1] && p[1] === apres[1]);
      return !colineaire;
    });

    chemins.push(`M ${utiles.map((p) => `${p[0]} ${p[1]}`).join(" L ")} Z`);
  }

  return chemins.join(" ");
}

/**
 * Le tronçon que « Prolonger » fait naître au bout du tronçon actif.
 *
 * Il part perpendiculairement, depuis l'extrémité **libre** (celle qui
 * s'éloigne du reste du comptoir), et se replie vers le reste — c'est comme
 * ça qu'un bar tourne dans une salle. Conséquence voulue : un clic donne un
 * L, deux donnent un U, sans que le manager ait à choisir une orientation
 * dans une liste. Il reste libre de le glisser et de l'étirer ensuite.
 *
 * Sans autre tronçon pour s'orienter, le repli se fait vers le centre du
 * plan : un comptoir posé le long d'un mur tourne vers la salle, jamais vers
 * le mur.
 */
export function tronconSuivant(
  troncons: Troncon[],
  index: number,
  { longueur, min, max }: { longueur: number; min: number; max: number }
): Troncon {
  const actif = troncons[index];
  const autres = troncons.filter((_, i) => i !== index);
  const ancre = autres.length
    ? {
        x: autres.reduce((s, t) => s + centre(t).x, 0) / autres.length,
        y: autres.reduce((s, t) => s + centre(t).y, 0) / autres.length,
      }
    : { x: 50, y: 50 };

  const horizontal = actif.width >= actif.height;
  const epaisseur = Math.min(max, Math.max(min, horizontal ? actif.height : actif.width));
  // Le nouveau tronçon englobe le coin (il chevauche l'actif sur son
  // épaisseur) : bout à bout, un arrondi de 0,001 % laisserait un cheveu de
  // vide au pli.
  const longue = Math.min(max, Math.max(min, longueur + epaisseur));

  if (horizontal) {
    const versLeBas = ancre.y >= centre(actif).y;
    const boutGauche =
      Math.abs(actif.pos_x - ancre.x) > Math.abs(actif.pos_x + actif.width - ancre.x);
    return borner({
      pos_x: boutGauche ? actif.pos_x : actif.pos_x + actif.width - epaisseur,
      pos_y: versLeBas ? actif.pos_y : actif.pos_y + actif.height - longue,
      width: epaisseur,
      height: longue,
    });
  }

  const versLaDroite = ancre.x >= centre(actif).x;
  const boutHaut = Math.abs(actif.pos_y - ancre.y) > Math.abs(actif.pos_y + actif.height - ancre.y);
  return borner({
    pos_x: versLaDroite ? actif.pos_x : actif.pos_x + actif.width - longue,
    pos_y: boutHaut ? actif.pos_y : actif.pos_y + actif.height - epaisseur,
    width: longue,
    height: epaisseur,
  });
}

/** Ramène un tronçon dans le plan sans le déformer plus que nécessaire : on
 *  le pousse d'abord, on le raccourcit seulement s'il ne rentre pas. */
function borner(t: Troncon): Troncon {
  const width = Math.min(t.width, 100);
  const height = Math.min(t.height, 100);
  return {
    pos_x: Math.min(100 - width, Math.max(0, t.pos_x)),
    pos_y: Math.min(100 - height, Math.max(0, t.pos_y)),
    width,
    height,
  };
}
