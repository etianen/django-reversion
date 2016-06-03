from __future__ import unicode_literals
import datetime
import warnings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import Count
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.utils.six.moves import input
from reversion.models import Revision, Version
from reversion.management.commands import parse_app_labels
from reversion.revisions import RevisionManager


class Command(BaseCommand):

    help = "Deletes revisions for a given app [and model]."

    def add_arguments(self, parser):
        parser.add_argument(
            "args",
            metavar="app_label",
            nargs="*",
            help="Optional apps or app.Model list.",
        )
        parser.add_argument(
            "-t",
            "--date",
            help=(
                "Delete only revisions older than the specied date. "
                "The date should be a valid date given in the ISO format (YYYY-MM-DD)"
            ),
        )
        parser.add_argument(
            "-d",
            "--days",
            default=0,
            type=int,
            help="Delete only revisions older than the specified number of days.",
        )
        parser.add_argument(
            "-k",
            "--keep-revision",
            dest="keep",
            default=0,
            type=int,
            help="Keep the specified number of revisions (most recent) for each object.",
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            default=False,
            help="Force the deletion of revisions even if an other app/model is involved.",
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            default=True,
            help="Do NOT prompt the user for input of any kind before deleting revisions.",
        )
        parser.add_argument(
            "-c",
            "--no-confirmation",
            action="store_false",
            dest="confirmation",
            default=True,
            help="Disable the confirmation before deleting revisions (DEPRECATED).",
        )
        parser.add_argument(
            "-m",
            "--manager",
            default="default",
            help="Delete revisions from specified revision manager. Defaults to the default revision manager.",
        )
        parser.add_argument(
            "--database",
            default=None,
            help="Nominates a database to delete revisions from.",
        )

    def handle(self, *app_labels, **options):
        days = options["days"]
        keep = options["keep"]
        force = options["force"]
        interactive = options["interactive"]
        # Load admin classes.
        admin.autodiscover()
        # Check for deprecated confirmation option.
        if not options["confirmation"]:
            interactive = False
            warnings.warn(
                (
                    "--no-confirmation is deprecated, please use --no-input instead. "
                    "--no-confirmation will be removed in django-reversion 1.12.0"
                ),
                DeprecationWarning
            )
        revision_manager = RevisionManager.get_manager(options["manager"])
        database = options.get("database")
        verbosity = int(options.get("verbosity", 1))
        # Parse date.
        date = None
        if options["date"]:
            if days:
                raise CommandError("You cannot use --date and --days at the same time. They are exclusive.")
            try:
                date = datetime.datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                raise CommandError((
                    "The date you gave (%s) is not a valid date. ",
                    "The date should be in the ISO format (YYYY-MM-DD)."
                ) % options["date"])
        # Find the date from the days arguments.
        elif days:
            date = datetime.date.today() - datetime.timedelta(days)
        # Build the queries
        revision_query = Revision.objects.using(database).filter(
            manager_slug=revision_manager._manager_slug,
        )
        if date:
            revision_query = revision_query.filter(date_created__lt=date)
        if app_labels:
            model_classes = parse_app_labels(revision_manager, app_labels)
            content_types = [
                revision_manager._get_content_type(model_class, db=database)
                for model_class
                in model_classes
            ]
            revision_query = revision_query.filter(version__content_type__in=content_types)
            if not force:
                excluded_content_types = ContentType.objects.db_manager(database).exclude(pk__in=[
                    content_type.pk
                    for content_type
                    in content_types
                ])
                revision_query = revision_query.exclude(version__content_type__in=excluded_content_types)
        # Handle keeping n versions.
        if keep:
            objs = Version.objects.using(database).filter(
                revision__manager_slug=revision_manager._manager_slug,
                revision__in=revision_query,
            )
            # Get all the objects that have more than the maximum revisions.
            objs = objs.values("object_id", "content_type_id", "db").annotate(
                total_ver=Count("object_id"),
            ).filter(total_ver__gt=keep)
            # Get all ids of the oldest revisions minus the max allowed revisions for all objects.
            revisions_not_kept = set()
            for obj in objs:
                revisions_not_kept.update(list(Version.objects.using(database).filter(
                    content_type__id=obj["content_type_id"],
                    object_id=obj["object_id"],
                    db=obj["db"],
                ).order_by("-pk").values_list("revision_id", flat=True)[keep:]))
            revision_query = revision_query.filter(pk__in=revisions_not_kept)
        revision_count = revision_query.count()
        # Ask confirmation
        if interactive:
            choice = input("Are you sure you want to delete %s revisions? [y|N] " % revision_count)
            if choice.lower() != "y":
                self.stdout.write("Aborting revision deletion.")
                return
        # Delete versions and revisions
        if verbosity >= 2:
            self.stdout.write("Deleting %s revisions..." % revision_count)
        # Delete the revisions.
        with transaction.atomic(using=database):
            revision_query.delete()
        # Final logging.
        if verbosity >= 2:
            self.stdout.write("Deleted %s revisions." % revision_count)
