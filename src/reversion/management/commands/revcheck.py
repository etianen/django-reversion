"""
Check for (and eventually create) a first version for each record for each
versioned models (all if none specified).
"""


from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db.models import get_apps, get_app, get_models, get_model

from reversion import revision
from reversion.models import Version


def version_save(obj):
    """Saves the initial version of an object."""
    obj.save()
    revision.user = None
    revision.comment = "Initial version"
version_save = revision.create_on_success(version_save)


class Command(BaseCommand):
    
    help = "Check for (and eventually create) a first version for each record for each reversioned models (all if none specified)"
    
    args = "[app1 app2.model ...]"

    def handle(self, *app_labels, **options):
        """Executes the command."""
        # Parse arguments.
        verbosity = int(options.get("verbosity", 1))
        # Load admin modules.
        admin.autodiscover()
        # Generate the app list.
        if len(app_labels) == 0:
            app_list = dict((app, None) for app in get_apps())
        else:
            app_list = {}
            for label in app_labels:
                if "." in label:
                    # Load the app.
                    app_label, model_label = label.split(".")
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)
                    # Load the model.
                    model = get_model(app_label, model_label)
                    if model is None:
                        raise CommandError("Unknown model: %s.%s" % (app_label, model_label))
                    elif not revision.is_registered(model):
                        raise CommandError("Model not reversioned: %s.%s" % (app_label, model_label))
                    # Add to the list.
                    if app in app_list.keys():
                        if app_list[app] and model not in app_list[app]:
                            app_list[app].append(model)
                    else:
                        app_list[app] = [model]
                else:
                    # This is just an app - no model qualifier
                    app_label = label
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)
                    app_list[app] = None
        # Having generated the app list, now process the models.
        for app, model_list in app_list.items():
            # Get the list of models.
            if model_list is None:
                model_list = get_models(app)
            # Process each model.
            for model in model_list:
                if not model._meta.proxy:
                    if revision.is_registered(model):
                        if verbosity > 0:
                            print "Checking model %s" % model
                        total = model._default_manager.all().count()
                        versioned = 0
                        for obj in model._default_manager.all():
                            if Version.objects.get_for_object(obj).count() == 0:
                                version_save(obj)
                                versioned += 1
                        if verbosity > 0:
                            print "\tcreated %d version out of %d records\n" % (versioned, total)

