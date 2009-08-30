"""
Doctests for Reversion.

These tests require Python version 2.5 or higher to run.

Register a model with Reversion:

    >>> reversion.register(Site)
    >>> reversion.is_registered(Site)
    True
    >>> registration_info = reversion.revision.get_registration_info(Site)
    >>> registration_info.fields
    ('id', 'domain', 'name')
    >>> [field.name for field in registration_info.file_fields]
    []
    
Save a model without an active revision:

    >>> unversioned_site = Site.objects.create(name="unversioned", domain="www.unversioned.com")
    >>> Version.objects.get_for_object(unversioned_site)
    []
    
Save a model using the context manager:

    >>> with reversion.revision:
    ...     versioned_site = Site.objects.create(name="versioned_site", domain="www.site-rev-1.com")
    ...
    >>> Version.objects.get_for_object(versioned_site)
    [<Version: www.site-rev-1.com>]
    
Check that the revision is abandoned in the case of error:

   >>> try:
   ...     with reversion.revision:
   ...         versioned_site.domain = None
   ...         versioned_site.save()
   ... except:
   ...     "Exception caught"
   ...     transaction.rollback()
   ...
   'Exception caught'
   >>> Version.objects.get_for_object(versioned_site)
   [<Version: www.site-rev-1.com>]
    
Save a model using the function decorator:

    >>> @reversion.revision.create_on_success
    ... def save_new_version(obj):
    ...     obj.save()
    ...
    >>> versioned_site.domain = "www.site-rev-2.com"
    >>> save_new_version(versioned_site)
    >>> Version.objects.get_for_object(versioned_site)
    [<Version: www.site-rev-1.com>, <Version: www.site-rev-2.com>]
    
Check that the revision is abandoned in the case of error:

   >>> versioned_site.domain = None
   >>> try:
   ...     save_new_version(versioned_site)
   ... except:
   ...     "Exception caught"
   ...     transaction.rollback()
   ...
   'Exception caught'
   >>> Version.objects.get_for_object(versioned_site)
   [<Version: www.site-rev-1.com>, <Version: www.site-rev-2.com>]
    
Get the latest version of the site by date:
    
    >>> Version.objects.get_for_date(versioned_site, datetime.datetime.now())
    <Version: www.site-rev-2.com>
    
Revert to a previous version:

    >>> with reversion.revision:
    ...     Version.objects.get_for_object(versioned_site)[0].revert()
    ...
    >>> versioned_site = Site.objects.get(name="versioned_site")
    >>> Version.objects.get_for_object(versioned_site)
    [<Version: www.site-rev-1.com>, <Version: www.site-rev-2.com>, <Version: www.site-rev-1.com>]
    
View unique versions of an object:

    >>> save_new_version(versioned_site)
    >>> Version.objects.get_for_object(versioned_site)
    [<Version: www.site-rev-1.com>, <Version: www.site-rev-2.com>, <Version: www.site-rev-1.com>, <Version: www.site-rev-1.com>]
    >>> Version.objects.get_unique_for_object(versioned_site)
    [<Version: www.site-rev-1.com>, <Version: www.site-rev-2.com>, <Version: www.site-rev-1.com>]
    
Delete a version controlled object:

    >>> versioned_site.delete()
    >>> Version.objects.get_deleted(Site)
    [<Version: www.site-rev-1.com>]
    
Recover a deleted object:

    >>> Site.objects.filter(name="versioned_site")
    []
    >>> Version.objects.get_deleted(Site)[0].revert()
    >>> Site.objects.filter(name="versioned_site")
    [<Site: www.site-rev-1.com>]
    >>> Version.objects.get_deleted(Site)
    []
    
Create a revision containing two different sites:

    >>> with reversion.revision:
    ...     site_1 = Site.objects.create(name="site_1", domain="www.site-1-rev-1.com")
    ...     site_2 = Site.objects.create(name="site_2", domain="www.site-2-rev-1.com")
    ...
    >>> with reversion.revision:
    ...     site_1.domain = "www.site-1-rev-2.com"
    ...     site_1.save()
    ...     site_2.domain = "www.site-2-rev-2.com"
    ...     site_2.save()
    ...
    >>> Version.objects.get_for_object(site_1)
    [<Version: www.site-1-rev-1.com>, <Version: www.site-1-rev-2.com>]
    >>> Version.objects.get_for_object(site_2)
    [<Version: www.site-2-rev-1.com>, <Version: www.site-2-rev-2.com>]
    
Perform a revert to the previous revision:

    >>> with reversion.revision:
    ...     Version.objects.get_for_object(site_1)[0].revision.revert()
    ...
    >>> Version.objects.get_for_object(site_1)
    [<Version: www.site-1-rev-1.com>, <Version: www.site-1-rev-2.com>, <Version: www.site-1-rev-1.com>]
    >>> Version.objects.get_for_object(site_2)
    [<Version: www.site-2-rev-1.com>, <Version: www.site-2-rev-2.com>, <Version: www.site-2-rev-1.com>]
    
Unregister the model with Reversion:

    >>> reversion.unregister(Site)
    >>> reversion.is_registered(Site)
    False
    
Check that field limitations work correctly:

    >>> reversion.register(Site, fields=("name",))
    >>> with reversion.revision:
    ...     field_limited_site = Site.objects.create(name="site_rev_1", domain="www.site-rev-1.com")
    ...
    >>> with reversion.revision:
    ...     field_limited_site.name = "site_rev_2"
    ...     field_limited_site.domain = "www.site-rev-2.com"
    ...     field_limited_site.save()
    ...
    >>> with reversion.revision:
    ...     Version.objects.get_for_object(field_limited_site)[0].revert()
    ...
    >>> field_limited_site = Site.objects.get(name="site_rev_1")
    >>> field_limited_site.domain
    u''
    >>> reversion.unregister(Site)
    >>> Revision.objects.all().delete()

Check that the follow functionality works for many-to-one relationships:

    >>> reversion.register(LogEntry, follow=("user",))
    >>> reversion.register(User)
    >>> user = User.objects.create(username="user_rev_1", password="password")
    >>> with reversion.revision:
    ...     log_entry = LogEntry.objects.create(user=user, object_repr="entry_rev_1", content_type=ContentType.objects.all()[0], action_flag=DELETION)
    ...
    >>> user.username = "user_rev_2"
    >>> user.save()
    >>> with reversion.revision:
    ...     log_entry.object_repr = "entry_rev_2"
    ...     log_entry.save()
    ...
    >>> Version.objects.get_for_object(log_entry)[0].revision.revert()
    >>> log_entry = LogEntry.objects.get(object_repr="entry_rev_1")
    >>> log_entry.user
    <User: user_rev_1>
    >>> LogEntry.objects.all().delete()
    >>> reversion.unregister(LogEntry)
    >>> User.objects.all().delete()
    >>> reversion.unregister(User)
    >>> Revision.objects.all().delete()
    
Check that the follow functionality works for many-to-many relationships:

    >>> reversion.register(User, follow=("groups",))
    >>> reversion.register(Group)
    >>> group = Group.objects.create(name="group_rev_1")
    >>> with reversion.revision:
    ...     user = User.objects.create(username="user_rev_1", password="password")
    ...     user.groups.add(group)
    ...
    >>> user.groups.all()
    [<Group: group_rev_1>]
    >>> group.name = "group_rev_2"
    >>> group.save()
    >>> with reversion.revision:
    ...     user.username = "user_rev_2"
    ...     user.save()
    ...
    >>> user.groups.all()
    [<Group: group_rev_2>]
    >>> Version.objects.get_for_object(user)[0].revision.revert()
    >>> user = User.objects.get(username="user_rev_1")
    >>> user.groups.all()
    [<Group: group_rev_1>]
    >>> User.objects.all().delete()
    >>> reversion.unregister(User)
    >>> Group.objects.all().delete()
    >>> reversion.unregister(Group)
    >>> Revision.objects.all().delete()
    
Check that follow functionality works for one-to-many relationships:

    >>> reversion.register(User, follow=("logentry_set",))
    >>> reversion.register(LogEntry, follow=("user",))
    >>> with reversion.revision:
    ...     user = User.objects.create(username="user_rev_1", password="password")
    ...     log_entry_1 = LogEntry.objects.create(user=user, object_repr="entry_1_rev_1", content_type=ContentType.objects.all()[0], action_flag=DELETION)
    ...
    >>> [entry.object_repr for entry in user.logentry_set.all()]
    [u'entry_1_rev_1']
    >>> log_entry_1.object_repr = "entry_1_rev_2"
    >>> log_entry_1.save()
    >>> with reversion.revision:
    ...     user.username = "user_rev_2"
    ...     user.save()
    ...     log_entry_2 = LogEntry.objects.create(user=user, object_repr="entry_2_rev_2", content_type=ContentType.objects.all()[0], action_flag=DELETION)
    ...
    >>> sorted([entry.object_repr for entry in user.logentry_set.all()])
    [u'entry_1_rev_2', u'entry_2_rev_2']
    >>> Version.objects.get_for_object(user)[0].revision.revert()
    >>> user = User.objects.get(username="user_rev_1")
    >>> sorted([entry.object_repr for entry in user.logentry_set.all()])
    [u'entry_1_rev_1', u'entry_2_rev_2']
    >>> Version.objects.get_for_object(user)[0].revision.revert(delete=True)
    >>> user = User.objects.get(username="user_rev_1")
    >>> [entry.object_repr for entry in user.logentry_set.all()]
    [u'entry_1_rev_1']
    
Check that the patch_admin helper works:
    
    >>> admin.autodiscover()
    >>> isinstance(admin.site._registry[Group], VersionAdmin)
    False
    >>> patch_admin(Group)
    >>> isinstance(admin.site._registry[Group], VersionAdmin)
    True
    
All done!
"""


from __future__ import with_statement

import datetime, unittest

from django.contrib import admin
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import models, transaction

import reversion
from reversion.admin import VersionAdmin
from reversion.helpers import patch_admin
from reversion.models import Version, Revision


try:
    from reversion.helpers import generate_patch, generate_patch_html
except ImportError:
    pass
else:
    
    class PatchTest(unittest.TestCase):
        
        """Tests the patch generation functionality."""
        
        def setUp(self):
            """Sets up a versioned site model to test."""
            reversion.register(Site)
            with reversion.revision:
                site = Site.objects.create(name="site", domain="www.site-rev-1.com")
            with reversion.revision:
                site.domain = "www.site-rev-2.com"
                site.save()
            self.site = site
        
        def testCanGeneratePatch(self):
            """Tests that text and HTML patches can be generated."""
            version_0 = Version.objects.get_for_object(self.site)[0]
            version_1 = Version.objects.get_for_object(self.site)[1]
            self.assertEqual(generate_patch(version_0, version_1, "domain"),
                             "@@ -10,9 +10,9 @@\n rev-\n-1\n+2\n .com\n")
            self.assertEqual(generate_patch_html(version_0, version_1, "domain"),
                             u'<SPAN TITLE="i=0">www.site-rev-</SPAN><DEL STYLE="background:#FFE6E6;" TITLE="i=13">1</DEL><INS STYLE="background:#E6FFE6;" TITLE="i=13">2</INS><SPAN TITLE="i=14">.com</SPAN>')
        
        def tearDown(self):
            """Deletes the versioned site model."""
            reversion.unregister(Site)
            self.site.delete()
            Version.objects.all().delete()
            
            