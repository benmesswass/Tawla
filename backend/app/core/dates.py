from datetime import datetime, timezone


def as_utc(value: datetime) -> datetime:
    """
    SQLite rend les datetime sans fuseau (Postgres les rend avec) : sans cette
    normalisation, toute comparaison à un seuil calculé en UTC lève un
    TypeError sur la base de test et passerait inaperçue jusqu'en production.
    """
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
