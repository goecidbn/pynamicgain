.. Pynamic Gain documentation master file, created by
   sphinx-quickstart on Fri May 31 09:59:39 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the Pynamic Gain documentation!
==========================================


Introduction
------------

Pynamic Gain is a Python package that facilitates the creation and analysis of **Dynamic Gain** calculations across multiple distributed setups. It serves three main purposes:

* **Distributed setup management**: Maintain an overview of setups and seeds used to ensure reproducibility and uniqueness of stimuli across multiple setups.
* **Create Input Stimuli**: Create input stimuli for subsequent dynamic gain calculation.
* **Online Analysis**: Perform real-time analysis of stimulated recordings to identify appropriate analysis windows for dynamic gain calculation.

In the future, this package will also include the dynamic gain calculation itself.

----------------


.. note::

   This project is under active development and will extend in the future. Please write us if you have any questions or suggestions!


----------------

How to start:
-------------

.. toctree::
   :maxdepth: 1
   
   explanations/first_steps.md
   explanations/usage.md
   explanations/motivations.md
   
   api_documentation.rst
   
   explanations/deep_settings.md
   explanations/development.md
   explanations/SMPR.md



..

----------------

Institutions
============


.. image:: _static/logo_cidbn.jpg
   :alt: UniGoettingen Logo
   :align: center

**The developer team is part of the** `Göttingen Campus Institute for Dynamics of Biological Networks (CIDBN) <https://uni-goettingen.de/en/608362.html>`_.

A Software Management Plan for this project can be found `here <https://goecidbn.github.io/pynamicgain/explanations/SMPR.html>`_.

..

----------------

This project is being used in the `NeuroNex Working Memory Consortium <https://www.nxwm.io/>`_.

.. image:: _static/logo_neuronex.png
   :alt: NeuroNex Working Memory Consortium
   :align: center

..

----------------

Funding
-------

This project is partially supported by the `Ministry for Science and Culture of Lower Saxony (MWK) <https://www.mwk.niedersachsen.de/startseite/>`_

.. image:: _static/logo_mwk.png
   :alt: Ministry of Science and Culture of Lower Saxony
   :align: center


.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
