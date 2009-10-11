from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES


for scheme in INSTALL_SCHEMES.values():
    scheme["data"] = scheme["purelib"]


setup(name="django-reversion",
      version="1.2",
      description="An extension to the Django web framework that provides comprehensive version control facilities",
      author="David Hall",
      author_email="david@etianen.com",
      url="http://code.google.com/p/django-reversion/",
      download_url="http://django-reversion.googlecode.com/files/django-reversion-1.2.tar.gz",
      packages=["reversion",],
      package_dir={"reversion": "reversion"},
      data_files=[["reversion/templates/reversion", ["reversion/templates/reversion/object_history.html",
                                                     "reversion/templates/reversion/change_list.html",
                                                     "reversion/templates/reversion/recover_form.html",
                                                     "reversion/templates/reversion/revision_form.html",
                                                     "reversion/templates/reversion/recover_list.html"]]],
      classifiers=["Development Status :: 5 - Production/Stable",
                   "Environment :: Web Environment",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Framework :: Django",])

