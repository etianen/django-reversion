from optparse import make_option

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.importlib import import_module
from django.utils.datastructures import SortedDict
from django.utils.encoding import smart_unicode

from reversion import default_revision_manager
from reversion.models import Version, has_int_pk


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--comment",
            action="store",
            dest="comment",
            default=u"Initial version.",
            help='Specify the comment to add to the revisions. Defaults to "Initial version.".'),
        )
    args = '[appname, appname.ModelName, ...] [--comment="Initial version."]'
    help = "Creates initial revisions for a given app [and model]."

    def handle(self, *app_labels, **options):
        comment = options["comment"]
        verbosity = int(options.get("verbosity", 1))
        app_list = SortedDict()
        # if no apps given, use all installed.
        if len(app_labels) == 0:
            for app in models.get_apps ():
                if not app in app_list.keys():
                    app_list[app] = []
                for model_class in models.get_models(app):
                    if not model_class in app_list[app]:
                        app_list[app].append(model_class)
        else:
            for label in app_labels:
                try:
                    app_label, model_label = label.split(".")
                    try:
                        app = models.get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)

                    model_class = models.get_model(app_label, model_label)
                    if model_class is None:
                        raise CommandError("Unknown model: %s.%s" % (app_label, model_label))
                    if app in app_list.keys():
                        if app_list[app] and model_class not in app_list[app]:
                            app_list[app].append(model_class)
                    else:
                        app_list[app] = [model_class]
                except ValueError:
                    # This is just an app - no model qualifier.
                    app_label = label
                    try:
                        app = models.get_app(app_label)
                        if not app in app_list.keys():
                            app_list[app] = []
                        for model_class in models.get_models(app):
                            if not model_class in app_list[app]:
                                app_list[app].append(model_class)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)
        # Create revisions.
        for app, model_classes in app_list.items():
            for model_class in model_classes:
                self.create_initial_revisions(app, model_class, comment, verbosity)

    def create_initial_revisions(self, app, model_class, comment, verbosity=2, **kwargs):
        """Creates the set of initial revisions for the given model."""
        # Import the relevant admin module.
        try:
            import_module("%s.admin" % app.__name__.rsplit(".", 1)[0])
        except ImportError:
            pass
        # Check all models for empty revisions.
        if default_revision_manager.is_registered(model_class):
            created_count = 0
            content_type = ContentType.objects.get_for_model(model_class)
            versioned_pk_queryset = Version.objects.filter(content_type=content_type).all()
            live_objs = model_class._default_manager.all()
            if has_int_pk(model_class):
                # We can do this as a fast database join!
                live_objs = live_objs.exclude(
                    pk__in = versioned_pk_queryset.values_list("object_id_int", flat=True)
                )
            else:
                # This join has to be done as two separate queries.
                live_objs = live_objs.exclude(
                    pk__in = list(versioned_pk_queryset.values_list("object_id", flat=True).iterator())
                )
            # Save all the versions.
            for obj in live_objs:
                try:
                    default_revision_manager.save_revision((obj,), comment=comment)
                except:
                    print "ERROR: Could not save initial version for %s %s." % (model_class.__name__, obj.pk)
                    raise
                created_count += 1
            # Print out a message, if feeling verbose.
            if verbosity >= 2:
                print u"Created %s initial revision(s) for model %s." % (created_count, smart_unicode(model_class._meta.verbose_name))
        else:
            if verbosity >= 2:
                print u"Model %s is not registered."  % (smart_unicode(model_class._meta.verbose_name))