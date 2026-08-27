# Monolithe modulaire, pas de microservices

Tawla est un monolithe modulaire (un module = un domaine métier, isolé sous
`backend/app/modules/<nom>/`), pas des microservices. Décision assumée tant
qu'il n'existe pas de preuve réelle de besoin — plusieurs équipes séparées, ou
une charge mesurée qui justifie de scinder le service. Pour un produit porté
par un seul développeur, le risque de sur-découper trop tôt coûte plus cher
que le risque qu'un monolithe est censé éviter à ce stade.

Source : `CLAUDE.md` (Tawla) §Architecture.
