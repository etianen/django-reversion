#!/usr/bin/env python
import sys
from optparse import OptionParser


def main():
    # Parse the command-line options.
    parser = OptionParser()
    parser.add_option("-v", "--verbosity",
        action = "store",
        dest = "verbosity",
        default = "1",
        type = "choice",
        choices = ["0", "1", "2", "3"],
        help = "Verbosity level; 0=minimal output, 1=normal output, 2=all output",
    )
    parser.add_option("--noinput",
        action = "store_false",
        dest = "interactive",
        default = True,
        help = "Tells Django to NOT prompt the user for input of any kind.",
    )
    parser.add_option("--failfast",
        action = "store_true",
        dest = "failfast",
        default = False,
        help = "Tells Django to stop running the test suite after first failed test.",
    )
    options, args = parser.parse_args()
    # Configure Django.
    from django.conf import settings
    settings.configure(
        DEBUG = False,
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
            }
        },
        ROOT_URLCONF = "urls",
        INSTALLED_APPS = (
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.sites",
            "django.contrib.messages",
            "django.contrib.staticfiles",
            "django.contrib.admin",
            "reversion",
            "test_reversion",
        ),
        MIDDLEWARE_CLASSES = (
            "django.middleware.common.CommonMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ),
        USE_TZ = True,
        STATIC_URL = "/static/",
        TEST_RUNNER = "django.test.runner.DiscoverRunner",
    )
    # Run Django setup (1.7+).
    import django
    try:
        django.setup()
    except AttributeError:  # pragma: no cover
        pass  # This is Django < 1.7
    # Configure the test runner.
    from django.test.utils import get_runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(
        verbosity = int(options.verbosity),
        interactive = options.interactive,
        failfast = options.failfast,
    )
    # Run the tests.
    failures = test_runner.run_tests(["test_reversion"])
    if failures:  # pragma: no cover
        sys.exit(failures)


if __name__ == "__main__":
    main()
