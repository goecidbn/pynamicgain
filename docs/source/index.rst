.. Pynamic Gain documentation master file.

Welcome to the Pynamic Gain documentation!
==========================================

Introduction
------------

Pynamic Gain is a Python package that facilitates the creation and analysis of **Dynamic Gain** calculations across multiple distributed setups. It serves three main purposes:

* **Distributed setup management**: Maintain an overview of setups and seeds used to ensure reproducibility and uniqueness of stimuli across multiple setups.
* **Create Input Stimuli**: Create input stimuli for subsequent dynamic gain calculation.
* **Online Analysis**: Perform real-time analysis of stimulated recordings to identify appropriate analysis windows for dynamic gain calculation.

In the future, this package will also include the dynamic gain calculation itself.

.. note::

   This project is under active development and will extend in the future. Please write us if you have any questions or suggestions!


----------------

Getting Started
---------------

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: First Steps
      :link: explanations/first_steps
      :link-type: doc

      Installation, environment setup, and creating your first configuration.

   .. grid-item-card:: Usage
      :link: explanations/usage
      :link-type: doc

      CLI commands for generating stimuli and analysing recordings.

   .. grid-item-card:: Motivations
      :link: explanations/motivations
      :link-type: doc

      Design decisions, seed management, and file format choices.

   .. grid-item-card:: API Documentation
      :link: api_documentation
      :link-type: doc

      Full reference for all classes, functions, and dataclasses.


.. grid:: 3
   :gutter: 3

   .. grid-item-card:: Advanced Settings
      :link: explanations/deep_settings
      :link-type: doc

      Full TOML configuration reference.

   .. grid-item-card:: Development
      :link: explanations/development
      :link-type: doc

      Release checklist and build instructions.

   .. grid-item-card:: Software Management Plan
      :link: explanations/SMPR
      :link-type: doc

      SMPR document for this research project.


.. toctree::
   :maxdepth: 1
   :hidden:

   explanations/first_steps.md
   explanations/usage.md
   explanations/motivations.md
   api_documentation.rst
   explanations/deep_settings.md
   explanations/development.md
   explanations/SMPR.md


----------------

Institutions & Funding
======================

.. raw:: html

   <div class="logo-grid">
     <a href="https://uni-goettingen.de/en/608362.html" target="_blank">
       <img src="_static/logo_cidbn.jpg" alt="CIDBN / University of Göttingen" />
     </a>
     <a href="https://www.nxwm.io/" target="_blank">
       <img src="_static/logo_neuronex.png" alt="NeuroNex Working Memory Consortium" />
     </a>
     <a href="https://www.mwk.niedersachsen.de/startseite/" target="_blank">
       <img src="_static/logo_mwk.png" alt="Ministry for Science and Culture of Lower Saxony" />
     </a>
   </div>

The developer team is part of the `Göttingen Campus Institute for Dynamics of Biological Networks (CIDBN) <https://uni-goettingen.de/en/608362.html>`_.
This project is being used in the `NeuroNex Working Memory Consortium <https://www.nxwm.io/>`_ and is partially supported by the
`Ministry for Science and Culture of Lower Saxony (MWK) <https://www.mwk.niedersachsen.de/startseite/>`_.
