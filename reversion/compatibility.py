from distutils.version import StrictVersion

import django
from django.core.management.base import BaseCommand

from optparse import make_option


if StrictVersion(django.get_version()) >= StrictVersion('1.8'):
    from django.apps import apps

    get_app = lambda app_label: apps.get_app_config(app_label).models_module
    get_apps = lambda: [config.models_module for config in apps.get_app_configs()
                        if config.models_module is not None]
    get_model = apps.get_model
    get_models = apps.get_models
elif StrictVersion(django.get_version()) >= StrictVersion('1.7'):
    from django.apps import apps

    get_app = apps.get_app
    get_apps = apps.get_apps
    get_model = apps.get_model
    get_models = apps.get_models
else:
    from django.db.models import get_app, get_apps, get_model, get_models


def urls_wrapper(*urls):
    if StrictVersion(django.get_version()) >= StrictVersion('1.9'):
        return list(urls)
    else:
        from django.conf.urls import patterns

        return patterns('', *urls)


class ProxyParser(object):
    """Faux parser object that will ferry our arguments into options."""

    def __init__(self, command):
        self.command = command

    def add_argument(self, *args, **kwargs):
        self.command.option_list +=  (make_option(*args, **kwargs), )


class CompatibilityBaseCommand(BaseCommand):
    """Provides a compatibility between optparse and argparse transition.

    Starting in Django 1.8, argparse is used. In Django 1.9, optparse support
    will be removed.

    For optparse, you append to the option_list class attribute.
    For argparse, you must define add_arguments(self, parser).
    BaseCommand uses the presence of option_list to decide what course to take.
    """

    def __init__(self, *args, **kwargs):
        if StrictVersion(django.get_version()) < StrictVersion('1.8') and hasattr(self, 'add_arguments'):
            self.option_list = BaseCommand.option_list
            parser = ProxyParser(self)
            self.add_arguments(parser)
        super(CompatibilityBaseCommand, self).__init__(*args, **kwargs)