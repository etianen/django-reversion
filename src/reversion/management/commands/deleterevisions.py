from optparse import make_option
import datetime
import operator
import sys

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from reversion.models import Revision, Version


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--date", "-t",
            dest="date",
            help='Delete only revisions older then the specify date. The date should be a valid date given in the ISO format (YYYY-MM-DD)'),
        make_option("--years", "-y",
            dest="years",
            default=0,
            type="int",
            help='Delete only revisions older then the specify number of years (combined to months and days if specified).'),
        make_option("--months", "-m",
            dest="months",
            default=0,
            type="int",
            help='Delete only revisions older then the specify number of months (combined to years and days if specified).'),
        make_option("--days", "-d",
            dest="days",
            default=0,
            type="int",
            help='Delete only revisions older then the specify number of days (combined to years and months if specified).'),
        make_option("--force", "-f",
            action="store_true",
            dest="force",
            default=False,
            help='Force the deletion of revisions even if an other app/model is involved'),
        make_option("--no-confirmation", "-c",
            action="store_false",
            dest="confirmation",
            default=True,
            help='Disable the confirmation before deleting revisions'),
        )
    args = '[appname, appname.ModelName, ...] [--date=YYYY-MM-DD | --years=0 | --months=0 | days=0] [--force] [--no-confirmation]'
    help = """Deletes revisions for a given app [and model] and/or before a specified delay or date.
    
If an app or a model is specified, revisions that have an other app/model involved will not be deleted. Use --force to avoid that.

You can specify only apps/models or only delay or date or use a combination of both.

Examples:

        deleterevisions myapp
    
    That will delete every revisions of myapp (except if there's an other app involved in the revision)
    
        deleterevisions --date=2010-11-01
    
    That will delete every revisions created before November 1, 2010 for all apps.
    
        deleterevisions myapp.mymodel --year=1 --month=2 --force
        
    That will delete every revisions of myapp.model that are older then 1 year and 2 months (14 months) even if there's revisions involving other apps and/or models.
"""

    def handle(self, *app_labels, **options):
        days = options["days"]
        months = options["months"]
        years = options["years"]
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
            if days or months or years:
                raise CommandError("You cannot use --date and --years|months|days at the same time. They are exclusive.")

            try:
                date = datetime.datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                raise CommandError("The date you give (%s) is not a valid date. The date should be in the ISO format (YYYY-MM-DD)." % options["date"])

        # Find the date from the years, months and days arguments.        
        elif days or months or years:
            today = datetime.datetime.today().date()
            # Remove years from current year
            # If months are more then 12 substract them also to current year
            year = today.year - years - (months / 12)
            # Get only remaining months (12 or less) and substract them to current month
            month = today.month - (months % 12)
            # If month is negative, add 12 months and remove a year
            if month < 1:
                month += 12
                year -= 1
            # Find the first existing date with the calculated year and month
            # (for case like when month is February and day is > 28 or 29.
            for days_removed in (0, 1, 2, 3):
                try:
                    date = datetime.date(year, month, today.day - days_removed)
                except ValueError:
                    continue
                else:
                    break

            if not date:
                raise CommandError("Error. It's not possible to calcualte a proper date for the years, months and days you give.")

            date = date - datetime.timedelta(days)


            # An other solution is to convert years and months to days using
            # the average number of days in a month and in a year.
#             days += int(round(((months / 12.0) + years) * 365.25))
#             date = datetime.datetime.today().date() - datetime.timedelta(days)


        # Check if date is too old to prevent some limit bug (and help people
        # putting useful dates)
        if date and date.year < 2005:
            raise CommandError("The year you give (%s) is too old. Django was not exisiting at this time!" % date.year)


        # Build the queries
        version_query = Version.objects.all()
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

        if date or app_labels:
            version_query = version_query.filter(revision__in=revision_query)


        # Prepare message if verbose
        if verbosity > 0:
            if not date and not app_labels:
                print "All revisions will be deleted and all model's versions."
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

                revision_count = revision_query.count()
                if revision_count:
                    print "%s revision(s)%s%swill be deleted.\n%s model's version(s) will be deleted." % (revision_count, date_msg, models_msg, version_query.count())
                else:
                    print "No revision%s%sto delete.\nDone" % (date_msg, models_msg)
                    sys.exit()


        # Ask confirmation
        if confirmation:
            choice = raw_input("Are you sure you want to delete theses revisions? [y|N] ")
            if choice.lower() != "y":
                print "Aborting revisions deletion."
                sys.exit()


        # Delete versions and revisions
        print "Deleting revisions..."
        version_query.delete()
        revision_query.delete()
        print "Done"
