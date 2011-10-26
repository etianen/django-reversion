from distutils.core import setup


# Load in babel support, if available.
try:
    from babel.messages import frontend as babel
    cmdclass = {"compile_catalog": babel.compile_catalog,
                "extract_messages": babel.extract_messages,
                "init_catalog": babel.init_catalog,
                "update_catalog": babel.update_catalog,}
except ImportError:
    cmdclass = {}


setup(name="django-reversion",
      version="1.5.1",
      description="An extension to the Django web framework that provides comprehensive version control facilities",
      author="Dave Hall",
      author_email="dave@etianen.com",
      url="http://github.com/etianen/django-reversion",
      download_url="http://github.com/downloads/etianen/django-reversion/django-reversion-1.5.1.tar.gz",
      zip_safe=False,
      packages=["reversion", "reversion.management", "reversion.management.commands", "reversion.migrations"],
      package_dir={"": "src"},
      package_data = {"reversion": ["locale/*/LC_MESSAGES/django.*", "templates/reversion/*.html"]},
      cmdclass = cmdclass,
      classifiers=["Development Status :: 5 - Production/Stable",
                   "Environment :: Web Environment",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Framework :: Django",])
