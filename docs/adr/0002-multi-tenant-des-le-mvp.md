# Multi-tenant dès le MVP (`restaurant_id` partout)

Chaque modèle porte `restaurant_id` depuis le premier jour, alors que le MVP
ne sert en pratique qu'un seul restaurant. Le coût d'ajouter la colonne
partout maintenant est faible ; la retrofitter plus tard sur un schéma déjà
peuplé — avec l'historique de commandes et de personnel d'un premier client
réel — serait une migration lourde. L'isolation entre restaurants est
testée (`tests/test_isolation.py`).

Source : `tenants/models.py` (docstring de `Restaurant`), `CLAUDE.md` (Tawla)
§Conventions.
