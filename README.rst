Money sharing app. In development. Probably getting a rename later.

Current installation instructions
=================================

1. Create a virtualenv. ``virtualenv django-argus``
2. Activate the virtualenv. ``source django-argus/bin/activate``
3. Install django-argus. ``pip install --no-deps -e git+git@github.com:littleweaver/django-argus.git@master#egg=django-argus``
4. Install django-argus requirements. This might take a while. ``pip install -r django-argus/src/django-argus/test_project/requirements.txt``
5. Ensure you have Bundler to install Ruby requirements ``gem install bundler`` (may need sudo).
6. Install Ruby requirements. ``bundle install --gemfile django-argus/src/django-argus/test_project/Gemfile``

Get it running
==============

5. ``cd django-argus/src/django-argus/test_project``
6. ``python manage.py syncdb``
7. ``python manage.py runserver``
8. Navigate to ``http://127.0.0.1:8000/`` in your favorite web browser!

Modifying the Styles
====================

We use SASS and Compass as our CSS preprocessor. Make sure compass is running when modifying SASS files.

1. If you are not in the same directory as ``config.rb``: ``cd django-argus/src/django-argus``
2. ``compass watch``
