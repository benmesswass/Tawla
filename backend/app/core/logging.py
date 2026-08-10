import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Logs structurés en JSON. Objectif : pouvoir debugger un bug en
    prod sans reproduction locale (filtrer par restaurant_id/order_id
    dans les logs directement).
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        # Contexte métier passé via logger.info(..., extra={"context": {...}})
        context = getattr(record, "context", None)
        if context:
            payload["context"] = context
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_event(logger: logging.Logger, message: str, **context) -> None:
    """
    Usage: log_event(logger, "order.confirmed", restaurant_id=1, order_id=42, table_id=5)
    -> toujours inclure les IDs métier pertinents (règle observabilité).
    """
    logger.info(message, extra={"context": context})
