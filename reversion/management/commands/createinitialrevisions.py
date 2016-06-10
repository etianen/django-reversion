from __future__ import unicode_literals
from django.db import reset_queries, transaction, router
from reversion.models import Revision
from reversion.management.commands import BaseRevisionCommand


class Command(BaseRevisionCommand):

    help = "Creates initial revisions for a given app [and model]."

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
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

    def handle(self, *app_labels, **options):
        verbosity = options["verbosity"]
        db = options["db"]
        model_db = options["model_db"]
        comment = options["comment"]
        batch_size = options["batch_size"]
        # Create revisions.
        db = router.db_for_write(Revision) if db is None else db
        with transaction.atomic(using=db):
            for revision_manager, model in self.get_managers_and_models(options):
                # Check all models for empty revisions.
                if verbosity >= 1:
                    self.stdout.write("Creating revisions for {name} using {manager} manager".format(
                        name=model._meta.verbose_name,
                        manager=revision_manager._manager_slug
                    ))
                created_count = 0
                live_objs = model._default_manager.using(model_db).exclude(
                    pk__reversion_in=(revision_manager.get_for_model(
                        model,
                        db=db,
                        model_db=model_db,
                    ), "object_id"),
                )
                # Save all the versions.
                ids = list(live_objs.values_list("pk", flat=True).order_by())
                total = len(ids)
                for i in range(0, total, batch_size):
                    chunked_ids = ids[i:i+batch_size]
                    objects = live_objs.in_bulk(chunked_ids)
                    for obj in objects.values():
                        with revision_manager._revision_context_manager.create_revision(db=db):
                            revision_manager._revision_context_manager.set_comment(comment)
                            revision_manager.add_to_revision(obj, model_db=model_db)
                        created_count += 1
                    reset_queries()
                    if verbosity >= 2:
                        self.stdout.write("- Created {created_count} / {total}".format(
                            created_count=created_count,
                            total=total,
                        ))
                # Print out a message, if feeling verbose.
                if verbosity >= 1:
                    self.stdout.write("- Created {total} / {total}".format(
                        total=total,
                    ))
