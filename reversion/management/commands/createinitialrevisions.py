from __future__ import unicode_literals
from django.db import reset_queries, transaction
from django.utils.encoding import force_text
from reversion.revisions import RevisionManager
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
        # Parse options.
        comment = options["comment"]
        batch_size = options["batch_size"]
        db = options["db"]
        model_db = options["model_db"]
        verbosity = int(options.get("verbosity", 1))
        model_classes = self.get_model_classes(options)
        # Create revisions.
        with transaction.atomic(using=db):
            for model_class in model_classes:
                for revision_manager in RevisionManager.get_created_managers():
                    if not revision_manager.is_registered(model_class):
                        continue
                    # Check all models for empty revisions.
                    if verbosity >= 1:
                        self.stdout.write("Creating initial revision(s) for model {name} in {manager}...".format(
                            name=model_class._meta.verbose_name,
                            manager=revision_manager._manager_slug
                        ))
                    created_count = 0
                    live_objs = model_class._default_manager.using(model_db).exclude(
                        pk__reversion_in=(revision_manager.get_for_model(
                            model_class,
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
                            try:
                                with revision_manager._revision_context_manager.create_revision(db=db):
                                    revision_manager._revision_context_manager.set_comment(comment)
                                    revision_manager.add_to_revision(obj, model_db=model_db)
                            except:
                                if verbosity >= 1:
                                    self.stderr.write("ERROR: Could not save initial version for %s %s" % (
                                        model_class.__name__,
                                        obj.pk,
                                    ))
                                raise
                            created_count += 1
                        reset_queries()
                        if verbosity >= 2:
                            self.stdout.write("Created %s of %s" % (created_count, total))
                    # Print out a message, if feeling verbose.
                    if verbosity >= 1:
                        self.stdout.write("Created %s initial revision(s) for model %s" % (
                            created_count,
                            force_text(model_class._meta.verbose_name),
                        ))
