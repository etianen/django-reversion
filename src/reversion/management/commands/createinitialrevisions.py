import sys

from django import VERSION
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import models
from django.utils.importlib import import_module
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext as _

from reversion import revision
from reversion.models import Version


class Command(BaseCommand):
    
    args = "[appname, appname.ModelName, ...]"
    help = "Creates initial revisions for a given app [and model]."

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        # Be safe for future django versions.
        if VERSION[0] == 1 and VERSION[1] <= 2:
            self.stdout = sys.stdout

    def handle(self, *app_labels, **options):
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
        for app, model_classes in app_list.items ():
            for model_class in model_classes:
                self.create_initial_revisions (app, model_class)

    @revision.create_on_success
    def version_save(self, obj):
        """Saves the initial version of an object."""
        obj.save()
        revision.user = None
        revision.comment = _(u"Initial version.")

    def create_initial_revisions(self, app, model_class, verbosity=2, **kwargs):
        """Creates the set of initial revisions for the given model."""
        # Import the relevant admin module.
        try:
            import_module("%s.admin" % app.__name__.rsplit(".", 1)[0])
        except ImportError:
            pass
        # Check all models for empty revisions.
        if revision.is_registered(model_class):
            created_count = 0
            # HACK: This join can't be done in the database, due to incompatibilities
            # between unicode object_ids and integer pks on strict backends like postgres.
            for obj in model_class._default_manager.iterator():
                if Version.objects.get_for_object(obj).count() == 0:
                    self.version_save(obj)
                    created_count += 1
            # Print out a message, if feeling verbose.
            if created_count > 0 and verbosity >= 2:
                self.stdout.write(u"Created %s initial revisions for model %s.\n" % (created_count, model_class._meta.verbose_name))
        else:
            if verbosity >= 2:
                self.stdout.write(u"Model %s is not registered.\n"  % (model_class._meta.verbose_name))