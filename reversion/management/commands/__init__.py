from __future__ import unicode_literals
from django.apps import apps
from django.contrib import admin
from django.core.management.base import BaseCommand, CommandError


class BaseRevisionCommand(BaseCommand):

    def add_arguments(self, parser):
        super(BaseRevisionCommand, self).add_arguments(parser)
        parser.add_argument(
            "app_label",
            metavar="app_label",
            nargs="*",
            help="Optional app_label or app_label.model_name list.",
        )
        parser.add_argument(
            "--db",
            "--database",
            default=None,
            help="The database to query for revision data.",
        )
        parser.add_argument(
            "--model-db",
            default=None,
            help="The database to query for model data.",
        )

    def get_model_classes(self, options):
        # Load admin classes.
        admin.autodiscover()
        # Get options.
        app_labels = options["app_label"]
        # Parse model classes.
        if len(app_labels) == 0:
            return set(apps.get_models())
        else:
            model_classes = set()
            for label in app_labels:
                if "." in label:
                    # This is an app.Model specifier.
                    app_label, model_label = label.split(".")
                    try:
                        app = apps.get_app_config(app_label)
                    except LookupError:
                        raise CommandError("Unknown app: %s" % app_label)
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
                        raise CommandError("Unknown app: %s" % app_label)
                    model_classes.update(app.get_models())
        return model_classes
