from flask import Blueprint
from flask_restplus import Api

from .annotations import api as ns_annotations
from .categories import api as ns_categories
from .annotator import api as ns_annotator
from .datasets import api as ns_datasets
from .exports import api as ns_exports
from .images import api as ns_images
from .models import api as ns_models
from .users import api as ns_users
from .admin import api as ns_admin
from .tasks import api as ns_tasks
from .undo import api as ns_undo
from .info import api as ns_info

from config import Config

# Create /api/ space
blueprint = Blueprint('api', __name__, url_prefix='/api')

api = Api(
    blueprint,
    title=Config.NAME,
    version=Config.VERSION,
)

# Remove default namespace
api.namespaces.pop(0)

# Setup API namespaces
api.add_namespace(ns_info)
api.add_namespace(ns_users)
api.add_namespace(ns_images)
api.add_namespace(ns_annotations)
api.add_namespace(ns_categories)
api.add_namespace(ns_datasets)
api.add_namespace(ns_exports)
api.add_namespace(ns_tasks)
api.add_namespace(ns_undo)
api.add_namespace(ns_models)
api.add_namespace(ns_admin)
api.add_namespace(ns_annotator)

