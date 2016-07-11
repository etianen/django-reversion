import django

if django.get_version() >= '1.8':
    from django.apps import apps

    get_app = lambda app_label: apps.get_app_config(app_label).models_module
    get_apps = lambda: [config.models_module for config in apps.get_app_configs()
                        if config.models_module is not None]
    get_model = apps.get_model
    get_models = apps.get_models
elif django.get_version() >= '1.7':
    from django.apps import apps

    get_app = apps.get_app
    get_apps = apps.get_apps
    get_model = apps.get_model
    get_models = apps.get_models
else:
    from django.db.models import get_app, get_apps, get_model, get_models

