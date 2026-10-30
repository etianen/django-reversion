import ast
import re

from setuptools import find_packages, setup

# Load in babel support, if available.
try:
    from babel.messages import frontend as babel

    cmdclass = {
        "compile_catalog": babel.compile_catalog,
        "extract_messages": babel.extract_messages,
        "init_catalog": babel.init_catalog,
        "update_catalog": babel.update_catalog,
    }
except ImportError:
    cmdclass = {}


def read(filepath):
    with open(filepath, encoding="utf-8") as f:
        return f.read()


def read_version():
    # Read __version__ without importing reversion, which imports Django when it is installed:
    # building must not depend on the installed Django working with this Python.
    match = re.search(r"^__version__ = VERSION = (\(.*\))$", read("reversion/__init__.py"), re.MULTILINE)
    return ".".join(str(x) for x in ast.literal_eval(match.group(1)))


setup(
    name="django-reversion",
    version=read_version(),
    license="BSD",
    description="An extension to the Django web framework that provides version control for model instances.",
    long_description=read("README.rst"),
    author="Dave Hall",
    author_email="dave@etianen.com",
    url="https://github.com/etianen/django-reversion",
    zip_safe=False,
    packages=find_packages(),
    package_data={
        "reversion": ["locale/*/LC_MESSAGES/django.*", "templates/reversion/*.html"]
    },
    cmdclass=cmdclass,
    install_requires=[
        "django>=5.2",
    ],
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Programming Language :: Python :: 3.15",
        "Framework :: Django",
        "Framework :: Django :: 5.2",
        "Framework :: Django :: 6.0",
        "Framework :: Django :: 6.1",
    ],
)
