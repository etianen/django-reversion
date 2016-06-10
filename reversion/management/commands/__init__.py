from __future__ import unicode_literals
from django.apps import apps
from django.contrib import admin
from django.core.management.base import BaseCommand, CommandError
from reversion.revisions import RevisionManager


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
            "-m",
            "--manager",
            default="default",
            help="The revision manager to use.",
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

    def get_revision_manager(self, options):
        return RevisionManager.get_manager(options["manager"])

    def get_model_classes(self, options):
        # Load admin classes.
        admin.autodiscover()
        # Get options.
        revision_manager = self.get_revision_manager(options)
        app_labels = options["app_label"]
        # Parse model classes.
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
                    for model_class in app.get_models():
                        if revision_manager.is_registered(model_class):
                            model_classes.add(model_class)
        return model_classes
