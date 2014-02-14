Money sharing app. In development. Probably getting a rename later.

Current installation instructions
=================================

1. Create a virtualenv. ``virtualenv django-argus``
2. Activate the virtualenv. ``source django-argus/bin/activate``
3. Install django-argus. ``pip install --no-deps -e git+git@github.com:littleweaver/django-argus.git@master#egg=django-argus``
4. Install django-argus requirements. This might take a while. ``pip install -r django-argus/src/django-argus/test_project/requirements.txt``

Get it running
==============

5. ``cd django-argus/src/django-argus/test_project``
6. ``python manage.py syncdb``
7. ``python manage.py runserver``
8. Navigate to ``http://127.0.0.1/`` in your favorite web browser!
