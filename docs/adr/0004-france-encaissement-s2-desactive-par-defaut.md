---
Status: proposed
---

# France : construire pour l'encaissement conforme (S2), le désactiver en production par défaut

Deux stratégies existaient pour la conformité fiscale française du logiciel
de caisse (art. 286-I-3° bis CGI). **S1** : Tawla n'encaisse aucun règlement,
le patron garde sa caisse. **S2** : Tawla encaisse et devient conforme ISCA
(journal inaltérable, clôtures, archivage, attestation éditeur). Décision de
travail de Wassim (2026-08-26) : construire S2 techniquement en entier, mais
garder l'encaissement réel désactivé par défaut en production — actif
seulement en démo — tant que la confirmation professionnelle (expert-
comptable, revérification ISCA) n'a pas eu lieu. `NullProvider`
(`core/payment_provider.py`) porte ce mode S1 aujourd'hui pour le marché
français, en attendant qu'un fournisseur français existe.

Marquée `proposed` plutôt que `accepted` : la Phase F2 de `MARCHE_FRANCE.md`
(rendez-vous expert-comptable, choix S1/S2 par écrit) reste due avant toute
activation réelle — cette décision peut encore être révisée à ce moment-là.

Source : `MARCHE_FRANCE.md` §3.1 et Annexe C (décision C2).
