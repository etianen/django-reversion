from __future__ import unicode_literals
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.core.management.base import BaseCommand
from django.db import reset_queries, transaction
from django.utils import translation
from django.utils.encoding import force_text
from reversion.revisions import RevisionManager
from reversion.models import Version
from reversion.management.commands import parse_app_labels


def get_app(app_label):
    return apps.get_app_config(app_label).models_module


class Command(BaseCommand):

    help = "Creates initial revisions for a given app [and model]."

    def add_arguments(self, parser):
        parser.add_argument(
            "args",
            metavar="app_label",
            nargs="*",
            help="Optional apps or app.Model list.",
        )
        parser.add_argument(
            "--comment",
            action="store",
            default="Initial version.",
            help="Specify the comment to add to the revisions. Defaults to 'Initial version'.")
        parser.add_argument(
            "--batch-size",
            action="store",
            type=int,
            default=500,
            help="For large sets of data, revisions will be populated in batches. Defaults to 500.",
        )
        parser.add_argument(
            "-m",
            "--manager",
            default="default",
            help="Create revisions for the given revision manager. Defaults to the default revision manager.",
        )
        parser.add_argument(
            "--database",
            default=None,
            help="Nominates a database to create revisions in.",
        )

    def handle(self, *app_labels, **options):
        # Activate project's default language
        translation.activate(settings.LANGUAGE_CODE)
        # Load admin classes.
        admin.autodiscover()
        # Parse options.
        comment = options["comment"]
        batch_size = options["batch_size"]
        revision_manager = RevisionManager.get_manager(options["manager"])
        database = options["database"]
        verbosity = int(options.get("verbosity", 1))
        model_classes = parse_app_labels(revision_manager, app_labels)
        # Create revisions.
        with transaction.atomic(using=database):
            for model_class in model_classes:
                self.create_initial_revisions(model_class, comment, batch_size, verbosity, revision_manager, database)
        # Go back to default language
        translation.deactivate()

    def create_initial_revisions(self, model_class, comment, batch_size, verbosity, revision_manager, database):
        # Check all models for empty revisions.
        if verbosity >= 2:
            self.stdout.write("Creating initial revision(s) for model %s ..." % (
                force_text(model_class._meta.verbose_name)
            ))
        created_count = 0
        content_type = revision_manager._get_content_type(model_class, db=database)
        live_objs = model_class._default_manager.using(database).exclude(
            pk__reversion_in=(Version.objects.using(database).filter(
                content_type=content_type,
            ), "object_id")
        )
        # Save all the versions.
        ids = list(live_objs.values_list("pk", flat=True).order_by())
        total = len(ids)
        for i in range(0, total, batch_size):
            chunked_ids = ids[i:i+batch_size]
            objects = live_objs.in_bulk(chunked_ids)
            for id, obj in objects.items():
                try:
                    revision_manager.save_revision(
                        objects=(obj,),
                        comment=comment,
                        db=database,
                    )
                except:
                    self.stdout.write("ERROR: Could not save initial version for %s %s." % (
                        model_class.__name__,
                        obj.pk,
                    ))
                    raise
                created_count += 1
            reset_queries()
            if verbosity >= 2:
                self.stdout.write("Created %s of %s." % (created_count, total))
        # Print out a message, if feeling verbose.
        if verbosity >= 2:
            self.stdout.write("Created %s initial revision(s) for model %s." % (
                created_count,
                force_text(model_class._meta.verbose_name),
            ))
