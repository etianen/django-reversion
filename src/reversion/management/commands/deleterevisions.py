from optparse import make_option
import datetime
import operator

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db.models import Q

from reversion import revision
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
        )    
    args = '[appname, appname.ModelName, ...] [--date=YYYY-MM-DD | --years=0 | --months=0 | days=0] [--force]'
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
        
        date = None
        
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


        if date and date.year < 2000:
            raise CommandError("The year you give (%s) is too old. Django was not exisiting at this time!" % date.year)
                 
        if app_labels:
            self.delete_apps(app_labels, date, options["force"])
        elif date:
            self.delete_all_apps(date)
        else:
            # 3 possibilities:
            #   1. delete all revisions
            #   2 .delete all revisions but ask a confirmation
            #   3. raise an error
            # Which should we choose?

            # 1.
#             self.delete_all_revisions()
            
            # 2.
            choice = raw_input("Are you sure you want to delete all the revisions? [y|N]")
            if choice.lower() == "y":
                self.delete_all_revisions()
            else:
                print "Aborting deletion of all revisions."

            # 3.
#             raise CommandError("Nothing specified. You need to specify at least a date or a delay or an app or a model.")
            
        
    def delete_all_apps(self, date):
        print "Deleting all revisions older than %s..." % date.isoformat()
        Version.objects.filter(revision__date_created__lt=date).delete()
        Revision.objects.filter(date_created__lt=date).delete()
        print "Done"
        
        
    def delete_all_revisions(self):
        print "Deleting all revisions..."
        Version.objects.all().delete()
        Revision.objects.all().delete()
        print "Done"
        
    
    def delete_apps(self, app_labels, date=None, force=False):
        app_list = set()
        mod_list = set()
        for label in app_labels:
            try:
                app_label, model_label = label.split(".")
                mod_list.add((app_label, model_label))
            except ValueError:
                # This is just an app - no model qualifier.
                app_list.add(label)
                    
        # Remove models that their app is already in app_list            
        for app, model in mod_list.copy():
            if app in app_list:
                mod_list.remove((app, model))

        # Delete revisions for apps and models
        subqueries = []
        if app_list:
            subqueries.append(Q(content_type__app_label__in=app_list))
        if mod_list:
            subqueries.extend([Q(content_type__app_label=app, content_type__model=model) for app, model in mod_list])
        subqueries = reduce(operator.or_, subqueries)
        if date:
            query = Version.objects.filter(revision__date_created__lt=date).filter(subqueries)
            date_msg = " older than %s" % date.isoformat()
        else:
            query = Version.objects.filter(subqueries)
            date_msg = ""

        revisions = query.values_list('revision_id', flat=True)
        
        if force:
            print "Deleting revisions having theses apps and models (%s)%s..." % (", ".join(app_list.union(["%s.%s" % (app, model) for app, model in mod_list])), date_msg)
            Version.objects.filter(revision__id__in=revisions).delete()
            Revision.objects.filter(pk__in=revisions).delete()
            print "Done"

        else:
            print "Deleting revisions having only theses apps and models (%s)%s..." % (", ".join(app_list.union(["%s.%s" % (app, model) for app, model in mod_list])), date_msg)
            revisions_to_delete = []
            for revision_id in revisions:
                revision = Revision.objects.get(pk=revision_id)
                if not revision.version_set.exclude(subqueries).count():
                    Version.objects.filter(revision=revision).delete()
                    revisions_to_delete.append(revision_id)
                else:
                    print 'Not deleting: %s' % revision
            Revision.objects.filter(pk__in=revisions_to_delete).delete()
            print "Done"
    
