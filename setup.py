from setuptools import setup, find_packages

__version__ = __import__('argus').__version__


description = "Money sharing app. In development. Probably getting a rename later."


setup(
    name="argus",
    version='.'.join([str(v) for v in __version__]),
    url="http://github.com/littleweaver/django-argus",
    description=description,
    long_description=description,
    maintainer='Little Weaver Web Collective, LLC',
    maintainer_email='hello@littleweaverweb.com',
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Office/Business :: Financial',
    ],
    platforms=['OS Independent'],
    install_requires=[
        'django>=1.7',
        'Pillow>=2.3.0',
    ]
)
