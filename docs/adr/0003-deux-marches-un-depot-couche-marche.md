# France : un dépôt, une couche marché, deux déploiements

Pour ouvrir un second marché (France) sans diverger en deux produits, trois
options ont été comparées. **Deux dépôts forkés** : rejeté — divergence
irréversible en quelques mois, chaque correctif à refaire deux fois pour un
fondateur seul. **Un seul déploiement partagé** (`Restaurant.market`) :
rejeté — données françaises hors UE ou données tunisiennes en UE, une panne
d'un marché coupe l'autre, et la contrainte « une seule instance backend »
(gestionnaire WebSocket en mémoire) devient un plafond commun aux deux
marchés. **Un dépôt unique, une couche marché** (`core/markets.py` /
`lib/market.ts`) lue une fois au démarrage via la variable `MARKET`, un
déploiement (backend + frontend + base) par marché : retenu.

Source : `MARCHE_FRANCE.md` §4.
