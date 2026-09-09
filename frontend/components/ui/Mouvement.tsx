"use client";

import { LazyMotion, MotionConfig } from "motion/react";
import type { ReactNode } from "react";

/**
 * Le socle Motion de l'application.
 *
 * Deux décisions portées ici, et elles comptent parce que le menu client se
 * charge sur le réseau d'un restaurant, avec le téléphone que le client a dans
 * la poche :
 *
 * 1. `features` est une fonction : le moteur d'animation n'est téléchargé
 *    qu'après le premier rendu, dans un morceau séparé. Le HTML de la carte
 *    arrive donc sans lui.
 * 2. `strict` fait échouer bruyamment tout composant qui importe `motion.*`
 *    au lieu de `m.*` (`motion/react-m`). C'est ce qui empêche le paquet
 *    complet de rentrer par la porte de derrière : sans ce garde-fou, un seul
 *    `motion.div` oublié dans une page annule le découpage ci-dessus.
 *
 * `domAnimation` et non `domMax` : il couvre l'animation, les gestes
 * survol/pression et `AnimatePresence`. `domMax` n'ajoute que le glisser et
 * les animations de layout — à charger localement, là où ils servent
 * réellement (plan de salle, carrousel), plutôt que pour tout le monde.
 *
 * `reducedMotion="user"` respecte `prefers-reduced-motion` sans qu'aucun
 * composant n'ait à s'en occuper : Motion neutralise alors les transformations
 * et laisse les opacités, c'est-à-dire l'état final immédiatement — jamais
 * l'absence d'état final.
 */
const chargerAnimation = () => import("motion/react").then((mod) => mod.domAnimation);

export default function Mouvement({ children }: { children: ReactNode }) {
  return (
    <LazyMotion features={chargerAnimation} strict>
      <MotionConfig reducedMotion="user">{children}</MotionConfig>
    </LazyMotion>
  );
}
