.. _diffs:

Generating Diffs
================

A common problem when dealing with version-controlled text is generating diffs to highlight changes between different versions.

django-reversion comes with a number of helper functions that make generating diffs easy.  They all rely on the `google-diff-match-patch <http://code.google.com/p/google-diff-match-patch/>`_ library, so make sure you have this installed before trying to use the functions.

Low-Level API
-------------

It is possible to generate two types of diff using the diff helper functions.  For the purpose of these examples, it is assumed that you have created a model called ``Page``, which contains a text field called ``content``.

First of all, you need to use the :ref:`low level API <api>` to retrieve the versions you want to compare.

::

    from reversion.helpers import generate_patch

    # Get the page object to generate diffs for.
    page = Page.objects.all()[0]

    # Get the two versions to compare.
    available_versions = reversion.get_for_object(page)

    old_version = available_versions[0]
    new_version = available_versions[1]

Now, in order to generate a text patch::

    from reversion.helpers import generate_patch

    patch = generate_patch(old_version, new_version, "content")

Or, to generate a pretty HTML patch::

    from reversion.helpers import generate_patch_html

    patch_html = generate_patch_html(old_version, new_version, "content")

Because text diffs can often be fragmented and hard to read, an optional ``cleanup`` parameter may be passed to generate friendlier diffs.

::

    patch_html = generate_patch_html(old_version, new_version, "content", cleanup="semantic")
    patch_html = generate_patch_html(old_version, new_version, "content", cleanup="efficiency")

Of the two cleanup styles, the one that generally produces the best result is 'semantic'.

Admin Integration
-----------------

The admin integration for django-reversion does not currently support diff generation.  This is a deliberate design decision, as it would make the framework a lot more heavyweight, as well as carrying the risk of confusing non-technical end users.

While future versions may support a more advanced admin class, for the time being it is left up to your own imagination for ways in which to integrate diffs with your project.
