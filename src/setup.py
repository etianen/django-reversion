from distutils.core import setup


setup(name="django-reversion",
      version="1.1",
      description="An extension to the Django web framework that provides comprehensive version control facilities",
      author="David Hall",
      author_email="david@etianen.com",
      url="http://code.google.com/p/django-reversion/",
      packages=["reversion",],
      package_dir={"reversion": "reversion"},
      classifiers=["Development Status :: 5 - Production/Stable",
                   "Environment :: Web Environment",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Framework :: Django",])