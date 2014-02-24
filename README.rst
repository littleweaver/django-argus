Money sharing app. In development. Probably getting a rename later.

Development
=============

Prerequisites
-------------

The installation instructions below assume you have the following software on your machine:

* `Python 2.7.x <http://www.python.org/download/releases/2.7.6/>`_
* `Ruby <https://www.ruby-lang.org/en/installation/>`_ 
* `Pip <https://pip.readthedocs.org/en/latest/installing.html>`_
* `virtualenv <http://www.virtualenv.org/en/latest/virtualenv.html#installation>`_ (optional)
* `virtualenvwrapper <http://virtualenvwrapper.readthedocs.org/en/latest/install.html>`_ (optional)

Installation instructions
-------------------------

If you are using virtualenv or virtualenvwrapper, create and activate an environment. E.g.,

.. code:: bash

    mkvirtualenv argus # Using virtualenvwrapper.

Then, to install:

.. code:: bash

    # Clone django-argus to a location of your choice.
    git clone https://github.com/littleweaver/django-argus.git

    # Install django-argus.
    pip install --no-deps -e django-argus

    # Install python requirements. This may take a while.
    pip install -r django-argus/test_project/requirements.txt

Modifying Argus's CSS files requires `SASS <http://sass-lang.com/>`_, `Compass <http://compass-style.org/>`_, and `Bootstrap SASS <http://getbootstrap.com/css/#sass>`_. If you plan to make changes to CSS files, but don't have those installed:

.. code:: bash
    
    gem install bundler # Ensure you have Bundler. May need sudo.
    bundle install --gemfile django-argus/Gemfile # Install Ruby requirements.

Get it running
--------------

.. code:: bash

    cd django-argus/test-project
    python manage.py syncdb    # Create/sync the database.
    python manage.py runserver # Run the server! 

Then, navigate to ``http://127.0.0.1:8000/`` in your favorite web browser!

Modifying the Styles
--------------------

Do not modify any of the files within ``django-argus/static/argus/css/``. That directory is managed by Compass. Instead, edit the compass source files in ``django-argus/sass/``. You will need to use the Compass command line tool to compile stylesheets. E.g.,

.. code:: bash

    cd django-argus/argus # Ensure you are in the directory with config.rb.
    compass watch         # Watch the sass directory for changes.

Or use `Compass.app <http://compass.kkbox.com/>`_.
