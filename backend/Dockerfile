FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Les migrations tournent avant le serveur : depuis la Phase 12.2 l'app ne crée
# plus le schéma au démarrage, Alembic est la seule voie. Le `&&` fait échouer
# le conteneur si une migration échoue, plutôt que de démarrer un serveur sur
# un schéma incohérent. Sûr en mono-instance, qui est la contrainte assumée du
# projet (gestionnaire WebSocket en mémoire, cf. notifications/manager.py).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
