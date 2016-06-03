from __future__ import unicode_literals
from django.apps import apps
from django.core.management.base import CommandError


def parse_app_labels(revision_manager, app_labels):
    model_classes = set()
    if len(app_labels) == 0:
        for model_class in apps.get_models():
            if revision_manager.is_registered(model_class):
                model_classes.add(model_class)
    else:
        for label in app_labels:
            if "." in label:
                # This is an app.Model specifier.
                app_label, model_label = label.split(".")
                try:
                    app = apps.get_app_config(app_label)
                except LookupError:
                    raise CommandError("Unknown application: %s" % app_label)
                try:
                    model_class = app.get_model(model_label)
                except LookupError:
                    raise CommandError("Unknown model: %s.%s" % (app_label, model_label))
                model_classes.add(model_class)
            else:
                # This is just an app - no model qualifier.
                app_label = label
                try:
                    app = apps.get_app_config(app_label)
                except LookupError:
                    raise CommandError("Unknown application: %s" % app_label)
                for model_class in app.get_models():
                    if revision_manager.is_registered(model_class):
                        model_classes.add(model_class)
    return model_classes
