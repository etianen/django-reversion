from setuptools import find_packages, setup

from reversion import __version__

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


setup(
    name="django-reversion",
    version=".".join(str(x) for x in __version__),
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
        "django>=4.2",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: Django",
    ],
)
