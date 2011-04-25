import datetime, operator, sys
from optparse import make_option

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db.models import Q, Count
from django.contrib.contenttypes.models import ContentType

from reversion.models import Revision, Version


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--date", "-t",
            dest="date",
            help="Delete only revisions older then the specify date. The date should be a valid date given in the ISO format (YYYY-MM-DD)"),
        make_option("--days", "-d",
            dest="days",
            default=0,
            type="int",
            help="Delete only revisions older then the specify number of days."),
        make_option("--keep-revision", "-k",
            dest="keep",
            default=0,
            type="int",
            help="Keep the specified number of revisions (most recent) for each object."),
        make_option("--force", "-f",
            action="store_true",
            dest="force",
            default=False,
            help="Force the deletion of revisions even if an other app/model is involved"),
        make_option("--no-confirmation", "-c",
            action="store_false",
            dest="confirmation",
            default=True,
            help="Disable the confirmation before deleting revisions"),
        )
    args = "[appname, appname.ModelName, ...] [--date=YYYY-MM-DD | days=0] [--keep=0] [--force] [--no-confirmation]"
    help = """Deletes revisions for a given app [and model] and/or before a specified delay or date.
    
If an app or a model is specified, revisions that have an other app/model involved will not be deleted. Use --force to avoid that.

You can specify only apps/models or only delay or date or only a nuber of revision to keep or use all possible combinations of these options.

Examples:

        deleterevisions myapp
    
    That will delete every revisions of myapp (except if there's an other app involved in the revision)
    
        deleterevisions --date=2010-11-01
    
    That will delete every revision created before November 1, 2010 for all apps.
    
        deleterevisions myapp.mymodel --days=365 --force
        
    That will delete every revision of myapp.model that are older then 365 days, even if there's revisions involving other apps and/or models.
    
        deleterevisions myapp.mymodel --keep=10
        
    That will delete only revisions of myapp.model if there's more then 10 revisions for an object, keeping the 10 most recent revisons.
"""

    def handle(self, *app_labels, **options):
        days = options["days"]
        keep = options["keep"]
        force = options["force"]
        confirmation = options["confirmation"]
        # I don't know why verbosity is not already an int in Django?
        try:
            verbosity = int(options["verbosity"])
        except ValueError:
            raise CommandError("option -v: invalid choice: '%s' (choose from '0', '1', '2')" % options["verbosity"])

        date = None

        # Validating arguments
        if options["date"]:
            if days:
                raise CommandError("You cannot use --date and --days at the same time. They are exclusive.")

            try:
                date = datetime.datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                raise CommandError("The date you give (%s) is not a valid date. The date should be in the ISO format (YYYY-MM-DD)." % options["date"])

        # Find the date from the days arguments.        
        elif days:
            date = datetime.datetime.now() - datetime.timedelta(days)

        # Build the queries
        revision_query = Revision.objects.all()

        if date:
            revision_query = revision_query.filter(date_created__lt=date)

        if app_labels:
            app_list = set()
            mod_list = set()
            for label in app_labels:
                try:
                    app_label, model_label = label.split(".")
                    mod_list.add((app_label, model_label))
                except ValueError:
                    # This is just an app, no model qualifier.
                    app_list.add(label)

            # Remove models that their app is already in app_list            
            for app, model in mod_list.copy():
                if app in app_list:
                    mod_list.remove((app, model))

            # Build apps/models subqueries
            subqueries = []
            if app_list:
                subqueries.append(Q(app_label__in=app_list))
            if mod_list:
                subqueries.extend([Q(app_label=app, model=model) for app, model in mod_list])
            subqueries = reduce(operator.or_, subqueries)

            if force:
                models = ContentType.objects.filter(subqueries)
                revision_query = revision_query.filter(version__content_type__in=models)
            else:
                models = ContentType.objects.exclude(subqueries)
                revision_query = revision_query.exclude(version__content_type__in=models)

        if keep:
            objs = Version.objects.all()

            # If app is specified, to speed up the loop on theses objects,
            # get only the specified subset.
            if app_labels:
                if force:
                    objs = objs.filter(content_type__in=models)
                else:
                    objs = objs.exclude(content_type__in=models)

            # Get all the objects that have more then the maximum revisions
            objs = objs.values("object_id", "content_type_id").annotate(total_ver=Count("object_id")).filter(total_ver__gt=keep)

            revisions_not_keeped = set()

            # Get all ids of the oldest revisions minus the max allowed
            # revisions for all objects.
            # Was not able to avoid this loop...
            for obj in objs:
                revisions_not_keeped.update(list(Version.objects.filter(content_type__id=obj["content_type_id"], object_id=obj["object_id"]).order_by("-revision__date_created").values_list("revision_id", flat=True)[keep:]))

            revision_query = revision_query.filter(pk__in=revisions_not_keeped)


        # Prepare message if verbose
        if verbosity > 0:
            if not date and not app_labels and not keep:
                print "All revisions will be deleted for all models."
            else:
                date_msg = ""
                if date:
                    date_msg = " older than %s" % date.isoformat()
                models_msg = " "
                if app_labels:
                    force_msg = ""
                    if not force:
                        force_msg = " only"
                    models_msg = " having%s theses apps and models:\n- %s\n" % (force_msg, "\n- ".join(sorted(app_list.union(["%s.%s" % (app, model) for app, model in mod_list])),))
                    if date:
                        models_msg = " and" + models_msg
                keep_msg = ""
                if keep:
                    keep_msg = " keeping the %s most recent revisions of each object" % keep

                revision_count = revision_query.count()
                if revision_count:
                    version_query = Version.objects.all()
                    if date or app_labels or keep:
                        version_query = version_query.filter(revision__in=revision_query)
                    print "%s revision(s)%s%swill be deleted%s.\n%s model version(s) will be deleted." % (revision_count, date_msg, models_msg, keep_msg, version_query.count())
                else:
                    print "No revision%s%sto delete%s.\nDone" % (date_msg, models_msg, keep_msg)
                    sys.exit()


        # Ask confirmation
        if confirmation:
            choice = raw_input("Are you sure you want to delete theses revisions? [y|N] ")
            if choice.lower() != "y":
                print "Aborting revision deletion."
                sys.exit()


        # Delete versions and revisions
        print "Deleting revisions..."
        revision_query.delete()
        print "Done"