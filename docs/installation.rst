.. _installation:

Installation
*************

To use Formation studio, python 3.9 or higher is required. You can download and install python
`here <https://www.python.org/downloads/>`_. 

Formation studio can be installed using pip:

.. code-block:: bash

    pip install formation-studio

.. note:: Some linux distributions do not include pip and require you to install it separately. You can follow `these instructions <https://pip.pypa.io/en/stable/installing/>`_ to do so.

If you are using multiple versions of python, pip can install Formation studio on a per version basis. For example, if you wanted to specify python 3.8:

.. code-block:: bash

    pip3.8 install formation-studio


Installation on Linux
======================

Formation studio uses tkinter that (depending on your distribution) may or may not
be included by default. If you are using tkinter for the first time it is advised to install ``tkinter`` and ``imagetk``.

For Debian based distributions (i.e. Ubuntu) you would use the following:

.. code-block:: bash

    sudo apt-get install python3-tk, python3-pil.imagetk

.. note::

    If your distribution is not Debian based you will need to subsitute the appropriate installation commands as per your distribution. Furthermore, Formation studio does **not** support ``python 2``. Please ensure you install ``python 3`` packages only.

Launching Formation studio
==========================
Once installed you can launch Formation studio from the command line using the following command:

.. code-block:: bash

    formation-studio
