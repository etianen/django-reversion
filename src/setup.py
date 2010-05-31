from glob import glob
from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES


for scheme in INSTALL_SCHEMES.values():
    scheme["data"] = scheme["purelib"]
    
    
setup(name="django-reversion",
      version="1.3",
      description="An extension to the Django web framework that provides comprehensive version control facilities",
      author="Dave Hall",
      author_email="dave@etianen.com",
      url="http://code.google.com/p/django-reversion/",
      download_url="http://django-reversion.googlecode.com/files/django-reversion-1.3.tar.gz",
      packages=["reversion", "reversion.templatetags", "reversion.management"],
      package_dir={"reversion": "reversion"},
      data_files=[("", glob("reversion/templates/reversion/*.html")),
                  ("", glob("reversion/locale/*/LC_MESSAGES/django.*"))],
      classifiers=["Development Status :: 5 - Production/Stable",
                   "Environment :: Web Environment",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Framework :: Django",])

