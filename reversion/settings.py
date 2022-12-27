"""
Settings for `Reversion` are all namespaced in the REVERSION setting.

For example your project's `settings.py` file might look like this:

REVERSION = {
    'DEFAULT_FORMAT': 'xml',
}

This module provides the `app_setting` object, that is used to access
Reversion settings, checking for user settings first, then falling
back to the defaults.

"""
from django.conf import settings


DEFAULTS = {
    "DEFAULT_FORMAT": "json",
}


class AppSettings:
    """
    A settings object that allows Reversion settings to be
    accessed as properties. For example:

        from reversion.settings import app_settings
        print(app_settings.DEFAULT_FORMAT)

    Note: This is an internal class that is only compatible with
    settings namespaced under the REVERSION name. It is not
    intended to be used by 3rd-party apps, and test helpers like
    `override_settings` may not work as expected.

    """

    def __getattr__(self, attribute):
        if attribute not in DEFAULTS:
            raise AttributeError("Invalid Reversion setting: '%s'" % attr)

        try:
            user_settings = getattr(settings, 'REVERSION', {})
            value = user_settings[attribute]
        except KeyError:
            value = DEFAULTS[attribute]

        return value


app_settings = AppSettings()
