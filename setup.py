from setuptools import setup, find_packages


setup(
    name='django-reversion',
    version='2.0.2',
    license='BSD',
    description='An extension to the Django web framework that provides comprehensive version control facilities',
    author='Dave Hall',
    author_email='dave@etianen.com',
    url='http://github.com/etianen/django-reversion',
    package_dir={'reversion': 'reversion'},
    include_package_data=True,
    packages=find_packages(),
    install_requires=[
        'django>=1.6',
        'django-chamber>=0.1.8'
    ],
    extras_require={
        'diff': [
            'diff_match_patch',
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Framework :: Django',
    ],
    dependency_links=[
        'https://github.com/matllubos/django-chamber/tarball/0.1.8#egg=django-chamber-0.1.8',
    ],

)
