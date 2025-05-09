===========
Member Card
===========

.. 
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! This file is generated by oca-gen-addon-readme !!
   !! changes will be overwritten.                   !!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! source digest: sha256:f7efbcabaff73da281c72aab844a4c50ce5664ded015c8896941b77b42959eb5
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-beescoop%2FObeesdoo-lightgray.png?logo=github
    :target: https://github.com/beescoop/Obeesdoo/tree/12.0/member_card
    :alt: beescoop/Obeesdoo

|badge1| |badge2| |badge3|

Create a member card and link it to a partner.

- each member card has a barcode
- create new cards in the "member card" tab of the partner form
- use "Force Barcode" field to set a user defined barcode
- the partner's card and barcode history is visible in the member card tab
- the barcode of a partner is computed from the last active member card
- a boolean "Print Member card?" allows to filter on partners for which you need to print new cards.
- contains a generic template for the member card
- the card template uses field `member_card_logo` rather than the company logo

The wizards "Request member card printing" and "Set member card as printed" allow to

Careful : this module overrides the barcodes already defined on the partners.

If point of sale is installed, the generated barcode matches customer pattern rule.

**Table of contents**

.. contents::
   :local:

Known issues / Roadmap
======================

- factor out wizards "request member card printing" and "set member card as printed"

  - it was used to request a batch of card to print but has no link to the actual template
- use `barcodes_generator_abstract` from the OCA to generate barcodes

**Customer Barcodes**

- odoo/base adds `barcode` field on `res.partner`.
- member_card also adds `barcode` but defines it as computed and stored.

On `member_card` install, odoo will compute the values for barcode field and **erase pre-existing values**.
It will also make it impossible to load data on that field.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/beescoop/Obeesdoo/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us to smash it by providing a detailed and welcomed
`feedback <https://github.com/beescoop/Obeesdoo/issues/new?body=module:%20member_card%0Aversion:%2012.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Authors
~~~~~~~

* BEES coop - Cellule IT
* Coop IT Easy SC

Contributors
~~~~~~~~~~~~

* BEES coop - Cellule IT
* Coop IT Easy SC
* Thibault François

Maintainers
~~~~~~~~~~~

This module is part of the `beescoop/Obeesdoo <https://github.com/beescoop/Obeesdoo/tree/12.0/member_card>`_ project on GitHub.

You are welcome to contribute.
