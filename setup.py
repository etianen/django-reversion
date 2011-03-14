from distutils.core import setup


setup(name="django-reversion",
      version="1.3.3",
      description="An extension to the Django web framework that provides comprehensive version control facilities",
      author="Dave Hall",
      author_email="dave@etianen.com",
      url="http://github.com/etianen/django-reversion",
      download_url="http://github.com/downloads/etianen/django-reversion/django-reversion-1.3.3.tar.gz",
      zip_safe=False,
      packages=["reversion", "reversion.management", "reversion.templatetags", "reversion.management.commands", "reversion.migrations"],
      package_dir={"": "src"},
      package_data = {"reversion": ["locale/*/LC_MESSAGES/django.*", "templates/reversion/*.html"]},
      classifiers=["Development Status :: 5 - Production/Stable",
                   "Environment :: Web Environment",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Framework :: Django",])
