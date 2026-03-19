# Software Management Plan for Research

## General

### Topic

**What is the title of the software project?**

PynamicGain

**Which research field(s) does this software belong to?**

Life Sciences / Neurosciences

**What is the intended use of the software? How will your software
contribute to research?**

Pynamic Gain is a Python package that facilitates the creation and
analysis of Dynamic Gain calculations across multiple distributed
setups. It serves three main purposes: Distributed setup management:
Maintain an overview of setups and seeds used to ensure reproducibility
and uniqueness of stimuli across multiple setups. Create Input Stimuli:
Create input stimuli for subsequent dynamic gain calculation. Online
Analysis: Perform real-time analysis of stimulated recordings to
identify appropriate analysis windows for dynamic gain calculation. In
the future, this package will also include the dynamic gain calculation
itself.

**What function does the new software have that previous software does
not cover? What related software exists and why is it not suitable?**

- create and manage multiple distributed setups ensuring different input
data over all setups - provide help/intuition for dynamic gain patch
clamp measurements

### Software Project Partner(s)

**Who are the project participants that deal with this software?**

-   Institut für Neuroanatomie, Universität Göttingen
-   Neuronex Project 170

**Is there existing (financial/personnel) resources or will there be
specific funding for the software development?**

Neuronex, Project 170: The Fabric of the Primate Neocortex and the
Origin of Mental Representations Ministry for Science and Culture of
Lower Saxony (MWK)

### Software Project Schedule

**When does the software project start?**

April 1, 2024

**When does the software project end?**

July 31, 2025

### Software Project Management

**Which software development process is defined? How will process roles
be assigned?**

No special development progress. New needs are developed in team
meetings between the developer and tester. Developer: Friedrich Schwarz
Tester: Andreas Neef, Stefan Pommer

**How do you track the different tasks and use cases?**

-   GitHub
-   Internal Notes

**Will there be a specification document (briefly) outlining the most
important requirements?**

Yes

### Software Development Requirements

**Are there institutional requirements for software development?**

Publication of the Software.

**Are there requirements regarding the software development form other
parties?**

No.

## Technical

### Code

**Which programming language(s) do you plan to use?**

Python

**Which technology or process is used for versioning?**

Git (GitHub.com)

### Third Party Components and Libraries

**Which external software components will be used? What dependencies on
software libraries do exist? How do you document this?**

Dependencies of I/O libraries for proprietary recording set-up file
formats. Currently used: PyABF (https://github.com/swharden/pyABF)

**What licences are on the third-party software components?**

PyABF (https://github.com/swharden/pyABF): MIT Licence

**What is the process to keep track of the external software components?
Can critical dependencies be eliminated or mitigated?**

PyABF can be forked from GitHub and incorporated, if necessary.

**Do you plan to use third party web services?**

No.

**Does the software refer to other software projects or objects?**

No.

### Infrastructure

**What infrastructure resources are needed? To what extent?**

- GitHub (online) - PyPI (online) - local computer to run the software.

**Is there already existing infrastructure for the software development?
Where is the infrastructure hosted?**

Hosted on standard websites (GitHub and PyPI)

**Are there technical aspects where competences are (still) lacking, so
that support would be helpful?**

Help via the developer.

### Preservation

**How long should the software remain usable? What steps will be taken
to ensure that the software can continue to be used after the project?**

**Does this software have to be preserved for a longer term?**

10 years for academic project storage.

### Security

**Which measures or provisions are in place to ensure software
security?**

2F-Authentification for changes in GitHub., otherwise no special
measures implemented.

**What measures do you take to minimise risks in relation to software
development?**

Online GitHub usage to prevent project loss.

## Quality Assurance

### Governance and Defined Processes

**Do you have a governance model for the software development?**

Motivation and Requirements page within the documentation.

**Do you apply specific coding standards? How do you take care about
code quality control?**

It is planned to use code linting and automated code formatting.
Google-type Docstrings are used within the project.

### Documentation

**How is software documentation created?**

The software documentation is automatically created using Sphinx and
GitHub Pages. This in integrated in a CI/CD workflow for each GitHub
push.

**Where will the documentation be stored or made available? Which
language will be used?**

The documentation is available on
https://goecidbn.github.io/pynamicgain/. It is publicly available and
written in English.

### Testing

**Which software test strategy are you going to follow? Which types of
tests are planned for the project?**

Unit and Integration test will be implemented via GitHub CI/CD. This is
currently not implemented.

**How is testing and test documentation organised?**

Unit and Integration test will be implemented via GitHub CI/CD. This is
currently not implemented.

## Release and Publish

### Releasing

**Are there defined release processes for the software?**

No.

**What is the decision process for releasing? How often will a software
version be released?**

Internal decision for releasing the software. Mayor updates after
internal testing. Otherwise the software will be updated, whenever
needed; e.g., error correction.

**Where will the software be stored? Does the storage place have a clear
preservation policy?**

Major software releases will be added to Zenodo. In the future we might
decide to store software releases used in publications also in re3data.

### Publicly Availability

**Will this software be publicly available?**

Yes

**In which repository or archive will the software be held? How easy can
it be found? What strategy is used to keep the software usable?**

The software will be held on GitHub.com . As the repository there is
publicly available it should be easy to find. Publications are aimed to
be Open-Access. There are no specific strategies in place to keep the
software usable.

**Will users have the possibility to contribute to your software?**

All users should be able to contribute, as long as their contribution
helps the research project and question.

**Is (Open) Peer Review planned for the software?**

Open Peer Review is not specifically planned. However, the code can be
openly accessed, reviews can be done, whenever wanted.

### Metadata

**How do you assign metadata for your software?**

Basic metadata is demanded when a setup is created. Basic metadata is
tracked and written, when the software is used. Users are invited to
provide their metadata to the developer team for central storage.

**Do you give a persistent identifier for you software?**

A Zenodo DOI is aimed for every major release.

### Support

**Do you plan to give support or help to re-users of your software?**

Yes

**How do you organise the support and feedback process with other
users?**

Via personal contact, as the number of collaborators should be limited.

**Does your Software Management Plan relate to other Software/Data
Management Plans?**

Not yet. Maybe in the future.

**Do you intend to make your software management plan publicly available
(later)?**

Yes: https://goecidbn.github.io/pynamicgain/explanations/SMPR.html

## Legal and Ethics

### Intellectual Property Rights

**What is the legal ownership of the software?**

The developer.

**Does the project use and/or produce software that is protected by
third party intellectual or industrial property rights?**

The software is published under the AGPL-3.0 license. This is also
stated at GitHub.

### License

**Under what kind of license(s) will the software be published?**

AGPL-3.0 license

### Dual Use

**Can the software also be used for military purposes?**

No.
