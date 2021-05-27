.. _installation:

Installation
*************

To use formation studio you will need to have installed python version 3.6 or higher. You can
`download and install python <https://www.python.org/downloads/>`_ first. Proceed then and install formation using pip

.. note:: For some linux distributions you will need to have installed pip separately, follow `these instructions <http://www.techmint.com/install-pip-in-linux/amp/>`_ instructions

.. code-block:: bash

    pip install formation-studio

if you have multiple python versions installed, to install for say python 3.7, use its pip tool

.. code-block:: bash

    pip3.7 install formation-studio


Installation on Linux
======================

Formation studio uses tkinter and depending on the distro you are using it may or may not
be installed by default. If you are using tkinter for the first time on your machine you
might want to first install ``tkinter`` and ``imagetk`` after completing the installation procedure above.
For debian based distros it should be something like

.. code-block:: bash

    sudo apt-get install python3-tk, python3-pil.imagetk

.. note::

    These are instructions for Debian based distros and is only assured to work on Ubuntu. For
    other distros, sub the installation command with the right one. Also, these commands install
    to ``python 3`` installations. Formation studio does **not** support ``python 2`` so ensure you install
    ``python 3`` packages only.

Launching
=========
After a successful installation you can launch the studio from the command line using the command

.. code-block:: bash

    formation-studio
