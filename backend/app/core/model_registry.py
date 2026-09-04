"""
Importe tous les modèles de tous les modules pour que SQLAlchemy connaisse
l'intégralité du schéma avant un create_all().

Sans ce fichier, un module dont le modèle n'est jamais importé ailleurs
(ex: `staff`, qui n'a pas encore de router) est invisible pour SQLAlchemy,
et toute ForeignKey qui pointe vers lui casse au démarrage — c'est arrivé
une fois, d'où ce fichier explicite plutôt qu'un import implicite fragile.
"""
from app.modules.loyalty import models as _loyalty_models  # noqa: F401
from app.modules.menu import models as _menu_models  # noqa: F401
from app.modules.orders import models as _orders_models  # noqa: F401  (Order, OrderItem, OrderItemOption, InvoiceCounter)
from app.modules.platform_admin import models as _platform_admin_models  # noqa: F401
from app.modules.staff import models as _staff_models  # noqa: F401
from app.modules.stats import models as _stats_models  # noqa: F401
from app.modules.tables import models as _tables_models  # noqa: F401
from app.modules.tenants import models as _tenants_models  # noqa: F401
from app.modules.waiter_calls import models as _waiter_calls_models  # noqa: F401
