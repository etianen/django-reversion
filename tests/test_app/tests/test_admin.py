import re
from datetime import datetime, timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.admin import GenericTabularInline
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete, m2m_changed
from django.shortcuts import resolve_url
from django.test.utils import override_settings

import reversion
from reversion.admin import VersionAdmin
from reversion.models import Revision, Version
from test_app.models import (
    TestModel, TestModelParent, TestModelInline, TestModelGenericInline, TestModelEscapePK, TestModelCustomObjectId,
    TestModelRelated,
)
from test_app.tests.base import TestBase, LoginMixin


class AdminMixin(TestBase):

    def setUp(self):
        super().setUp()
        admin.site.register(TestModelParent, VersionAdmin)
        self.reloadUrls()

    def tearDown(self):
        super().tearDown()
        admin.site.unregister(TestModelParent)
        self.reloadUrls()


class AdminRegisterTest(AdminMixin, TestBase):

    def setAutoRegister(self):
        self.assertTrue(reversion.is_registered(TestModelParent))

    def setAutoRegisterFollowsParent(self):
        self.assertTrue(reversion.is_registered(TestModel))


class AdminAddViewTest(LoginMixin, AdminMixin, TestBase):

    def testAddView(self):
        self.client.post(resolve_url("admin:test_app_testmodelparent_add"), {
            "name": "v1",
            "parent_name": "parent_v1",
        })
        obj = TestModelParent.objects.get()
        self.assertSingleRevision(
            (obj, obj.testmodel_ptr), user=self.user, comment="Added."
        )


class AdminUpdateViewTest(LoginMixin, AdminMixin, TestBase):

    def testUpdateView(self):
        obj = TestModelParent.objects.create()
        self.client.post(resolve_url("admin:test_app_testmodelparent_change", obj.pk), {
            "name": "v2",
            "parent_name": "parent v2",
        })
        self.assertSingleRevision(
            (obj, obj.testmodel_ptr), user=self.user,
            # Django 3.0 changed formatting a bit.
            comment=re.compile(r"Changed [nN]ame and [pP]arent[ _]name\.")
        )


class AdminChangelistView(LoginMixin, AdminMixin, TestBase):

    def testChangelistView(self):
        obj = TestModelParent.objects.create()
        response = self.client.get(resolve_url("admin:test_app_testmodelparent_changelist"))
        self.assertContains(response, resolve_url("admin:test_app_testmodelparent_change", obj.pk))


class AdminRevisionViewTest(LoginMixin, AdminMixin, TestBase):

    def setUp(self):
        super().setUp()
        with reversion.create_revision():
            self.obj = TestModelParent.objects.create()
        with reversion.create_revision():
            self.obj.name = "v2"
            self.obj.parent_name = "parent v2"
            self.obj.save()

    def testRevisionView(self):
        response = self.client.get(resolve_url(
            "admin:test_app_testmodelparent_revision",
            self.obj.pk,
            Version.objects.get_for_object(self.obj)[1].pk,
        ))
        self.assertContains(response, 'value="v1"')
        self.assertContains(response, 'value="parent v1"')
        # Test that the changes were rolled back.
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.name, "v2")
        self.assertEqual(self.obj.parent_name, "parent v2")
        self.assertIn("revert", response.context)
        self.assertTrue(response.context["revert"])

    def testRevisionViewOldRevision(self):
        response = self.client.get(resolve_url(
            "admin:test_app_testmodelparent_revision",
            self.obj.pk,
            Version.objects.get_for_object(self.obj)[0].pk,
        ))
        self.assertContains(response, 'value="v2"')
        self.assertContains(response, 'value="parent v2"')

    def testRevisionViewRevertError(self):
        Version.objects.get_for_object(self.obj).update(format="boom")
        response = self.client.get(resolve_url(
            "admin:test_app_testmodelparent_revision",
            self.obj.pk,
            Version.objects.get_for_object(self.obj)[1].pk,
        ))
        self.assertEqual(
            response["Location"].replace("http://testserver", ""),
            resolve_url("admin:test_app_testmodelparent_changelist"),
        )

    def testRevisionViewRevert(self):
        self.client.post(resolve_url(
            "admin:test_app_testmodelparent_revision",
            self.obj.pk,
            Version.objects.get_for_object(self.obj)[1].pk,
        ), {
            "name": "v1",
            "parent_name": "parent v1",
        })
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.name, "v1")
        self.assertEqual(self.obj.parent_name, "parent v1")


class AdminRevisionViewSignalsTest(LoginMixin, AdminMixin, TestBase):
    """Test that Django model signals are muted during GET requests to revision views."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signal_fired = None

    def signal_receiver(self, sender, **kwargs):
        """Receiver that tracks which signal was fired."""
        self.signal_fired = sender
        raise RuntimeError(f"Django signal was fired for {sender}!")

    def setUp(self):
        super().setUp()
        with reversion.create_revision():
            self.obj = TestModelParent.objects.create()

        # Connect all the model signals that should be muted
        self.signals_to_test = [pre_save, post_save, pre_delete, post_delete, m2m_changed]
        for signal in self.signals_to_test:
            signal.connect(receiver=self.signal_receiver, sender=TestModelParent)

    def tearDown(self):
        # Disconnect all signals
        for signal in self.signals_to_test:
            signal.disconnect(receiver=self.signal_receiver, sender=TestModelParent)
        super().tearDown()

    def testGetForRevisionViewDoesntFireDjangoSignals(self):
        """Test that viewing a revision (GET request) doesn't fire Django model signals."""
        self.signal_fired = None

        # This should NOT fire any signals since it's a GET request
        response = self.client.get(resolve_url(
            "admin:test_app_testmodelparent_revision",
            self.obj.pk,
            Version.objects.get_for_object(self.obj)[0].pk,
        ))

        # The request should succeed (no signal should have been fired)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.signal_fired, "No signals should fire during GET request")

    def testPostForRevisionViewFiresDjangoSignals(self):
        """Test that reverting a revision (POST request) properly fires Django model signals."""
        self.signal_fired = None

        # This SHOULD fire signals since it's a POST request (actual revert)
        with self.assertRaises(RuntimeError) as cm:
            self.client.post(resolve_url(
                "admin:test_app_testmodelparent_revision",
                self.obj.pk,
                Version.objects.get_for_object(self.obj)[0].pk,
            ), {
                "name": "v1",
                "parent_name": "parent v1",
            })

        # Verify that signals were indeed fired during POST
        self.assertIn("Django signal was fired", str(cm.exception))
        self.assertIsNotNone(self.signal_fired, "Signals should fire during POST request")


class AdminRecoverViewTest(LoginMixin, AdminMixin, TestBase):

    def setUp(self):
        super().setUp()
        with reversion.create_revision():
            obj = TestModelParent.objects.create()
        obj.delete()

    def testRecoverView(self):
        response = self.client.get(resolve_url(
            "admin:test_app_testmodelparent_recover",
            Version.objects.get_for_model(TestModelParent).get().pk,
        ))
        self.assertContains(response, 'value="v1"')
        self.assertContains(response, 'value="parent v1"')
        self.assertIn("recover", response.context)
        self.assertTrue(response.context["recover"])

    def testRecoverViewRecover(self):
        self.client.post(resolve_url(
            "admin:test_app_testmodelparent_recover",
            Version.objects.get_for_model(TestModelParent).get().pk,
        ), {
            "name": "v1",
            "parent_name": "parent v1",
        })
        obj = TestModelParent.objects.get()
        self.assertEqual(obj.name, "v1")
        self.assertEqual(obj.parent_name, "parent v1")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AdminPermissionMixin(AdminMixin, TestBase):
    """Logs in a staff user who only has the given permissions on TestModelParent."""

    permissions = ()

    def setUp(self):
        super().setUp()
        self.user = User(username="staff", is_staff=True)
        self.user.set_password("password")
        self.user.save()
        self.user.user_permissions.set(Permission.objects.filter(
            content_type__app_label="test_app",
            codename__in=[f"{action}_testmodelparent" for action in self.permissions],
        ))
        self.client.login(username="staff", password="password")
        self.saved_senders = []
        post_save.connect(self.post_save_receiver)

    def tearDown(self):
        post_save.disconnect(self.post_save_receiver)
        super().tearDown()

    def post_save_receiver(self, sender, **kwargs):
        if sender in (TestModel, TestModelParent):
            self.saved_senders.append(sender)


class AdminRevisionViewNoChangePermissionTest(AdminPermissionMixin, TestBase):

    permissions = ("view",)

    def setUp(self):
        super().setUp()
        with reversion.create_revision():
            self.obj = TestModelParent.objects.create()
        with reversion.create_revision():
            self.obj.name = "v2"
            self.obj.parent_name = "parent v2"
            self.obj.save()
        self.saved_senders.clear()

    def postRevert(self):
        revision_count = Revision.objects.count()
        version_count = Version.objects.count()
        response = self.client.post(resolve_url(
            "admin:test_app_testmodelparent_revision",
            self.obj.pk,
            Version.objects.get_for_object(self.obj)[1].pk,
        ), {
            "name": "v1",
            "parent_name": "parent v1",
        })
        self.assertEqual(response.status_code, 403)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.name, "v2")
        self.assertEqual(self.obj.parent_name, "parent v2")
        self.assertEqual(Revision.objects.count(), revision_count)
        self.assertEqual(Version.objects.count(), version_count)
        self.assertEqual(self.saved_senders, [])

    def testRevisionViewRevertDenied(self):
        self.postRevert()

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ["reversion.middleware.RevisionMiddleware"])
    def testRevisionViewRevertDeniedWithMiddleware(self):
        self.postRevert()

    def testRevisionViewOtherMethodsDontFireSignals(self):
        url = resolve_url(
            "admin:test_app_testmodelparent_revision",
            self.obj.pk,
            Version.objects.get_for_object(self.obj)[1].pk,
        )
        for method in ("HEAD", "OPTIONS", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                self.client.generic(method, url)
                self.obj.refresh_from_db()
                self.assertEqual(self.obj.name, "v2")
                self.assertEqual(self.saved_senders, [])


class AdminRevisionViewNoViewPermissionTest(AdminPermissionMixin, TestBase):

    def setUp(self):
        super().setUp()
        with reversion.create_revision():
            self.obj = TestModelParent.objects.create()
        with reversion.create_revision():
            self.obj.name = "v2"
            self.obj.save()
        self.saved_senders.clear()

    def testRevisionViewDenied(self):
        with patch.object(Revision, "revert") as revert:
            response = self.client.get(resolve_url(
                "admin:test_app_testmodelparent_revision",
                self.obj.pk,
                Version.objects.get_for_object(self.obj)[1].pk,
            ))
        self.assertEqual(response.status_code, 403)
        revert.assert_not_called()
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.name, "v2")
        self.assertEqual(self.saved_senders, [])


class AdminRecoverViewNoChangePermissionTest(AdminPermissionMixin, TestBase):

    permissions = ("add", "view")

    def setUp(self):
        super().setUp()
        with reversion.create_revision():
            obj = TestModelParent.objects.create()
        obj.delete()
        self.saved_senders.clear()

    def testRecoverViewRecoverDenied(self):
        revision_count = Revision.objects.count()
        response = self.client.post(resolve_url(
            "admin:test_app_testmodelparent_recover",
            Version.objects.get_for_model(TestModelParent).get().pk,
        ), {
            "name": "v1",
            "parent_name": "parent v1",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(TestModelParent.objects.exists())
        self.assertEqual(Revision.objects.count(), revision_count)
        self.assertEqual(self.saved_senders, [])


class AdminOtherModelVersionTest(AdminPermissionMixin, TestBase):
    """Versions of other models can't be reverted through this model's admin."""

    permissions = ("add", "change", "view")

    def setUp(self):
        super().setUp()
        reversion.register(TestModelRelated)
        with reversion.create_revision():
            self.related = TestModelRelated.objects.create()
        with reversion.create_revision():
            self.related.name = "v2"
            self.related.save()
        # A TestModelParent sharing the related object's pk, so a cross-model revert would find a form to save.
        with reversion.create_revision():
            TestModelParent.objects.create(pk=self.related.pk)
        self.related_version = Version.objects.get_for_object(self.related)[1]

    def testRevisionViewOtherModelNotFound(self):
        response = self.client.post(resolve_url(
            "admin:test_app_testmodelparent_revision",
            self.related.pk,
            self.related_version.pk,
        ), {
            "name": "v1",
            "parent_name": "parent v1",
        })
        self.assertEqual(response.status_code, 404)
        self.related.refresh_from_db()
        self.assertEqual(self.related.name, "v2")

    def testRecoverViewOtherModelNotFound(self):
        response = self.client.post(resolve_url(
            "admin:test_app_testmodelparent_recover",
            self.related_version.pk,
        ), {
            "name": "v1",
            "parent_name": "parent v1",
        })
        self.assertEqual(response.status_code, 404)
        self.related.refresh_from_db()
        self.assertEqual(self.related.name, "v2")


class AdminRecoverlistViewTest(LoginMixin, AdminMixin, TestBase):

    def testRecoverlistView(self):
        with reversion.create_revision():
            obj = TestModelParent.objects.create()
        obj.delete()
        response = self.client.get(resolve_url("admin:test_app_testmodelparent_recoverlist"))
        self.assertContains(response, resolve_url(
            "admin:test_app_testmodelparent_recover",
            Version.objects.get_for_model(TestModelParent).get().pk,
        ))


class AdminHistoryViewTest(LoginMixin, AdminMixin, TestBase):

    def testHistorylistView(self):
        with reversion.create_revision():
            obj = TestModelParent.objects.create()
        response = self.client.get(resolve_url("admin:test_app_testmodelparent_history", obj.pk))
        self.assertContains(response, resolve_url(
            "admin:test_app_testmodelparent_revision",
            obj.pk,
            Version.objects.get_for_model(TestModelParent).get().pk,
        ))

    def testHistorylistViewOrderDefault(self):
        # Create an object and multiple revisions.
        with reversion.create_revision():
            obj = TestModelParent.objects.create(name="v1", parent_name="p1")
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
        with reversion.create_revision():
            obj.name = "v3"
            obj.save()

        # Fetch history page.
        response = self.client.get(resolve_url("admin:test_app_testmodelparent_history", obj.pk))
        content = response.content.decode()

        # Compute expected order: default VersionAdmin orders by pk ascending (oldest first).
        version_ids = list(Version.objects.get_for_object(obj).values_list("pk", flat=True))
        expected_order = sorted(version_ids)

        # Build the URLs as rendered in the history list and assert their order.
        urls_in_order = [
            resolve_url(
                "admin:test_app_testmodelparent_revision",
                obj.pk,
                vid,
            )
            for vid in expected_order
        ]

        # Ensure each subsequent URL appears later in the content than the previous one.
        last_index = -1
        for url in urls_in_order:
            index = content.find(url)
            self.assertNotEqual(index, -1, f"Expected to find {url} in history page")
            self.assertGreater(index, last_index, "History list is not ordered by ascending version pk (oldest first)")
            last_index = index


class AdminHistoryViewLatestFirstTest(LoginMixin, TestBase):

    class TestModelParentAdminLatestFirst(VersionAdmin):
        history_latest_first = True

    def setUp(self):
        super().setUp()
        # Register a custom admin with history_latest_first enabled
        admin.site.register(TestModelParent, self.TestModelParentAdminLatestFirst)
        self.reloadUrls()

    def tearDown(self):
        super().tearDown()
        admin.site.unregister(TestModelParent)
        self.reloadUrls()

    def testHistorylistViewOrderLatestFirst(self):
        # Create an object and multiple revisions.
        with reversion.create_revision():
            obj = TestModelParent.objects.create(name="v1", parent_name="p1")
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
        with reversion.create_revision():
            obj.name = "v3"
            obj.save()

        # Fetch history page.
        response = self.client.get(resolve_url("admin:test_app_testmodelparent_history", obj.pk))
        content = response.content.decode()

        # Expected order: with history_latest_first=True, versions are ordered by pk descending (newest first).
        version_ids = list(Version.objects.get_for_object(obj).values_list("pk", flat=True))
        expected_order = sorted(version_ids, reverse=True)

        urls_in_order = [
            resolve_url("admin:test_app_testmodelparent_revision", obj.pk, vid)
            for vid in expected_order
        ]

        last_index = -1
        for url in urls_in_order:
            index = content.find(url)
            self.assertNotEqual(index, -1, f"Expected to find {url} in history page")
            self.assertGreater(index, last_index, "History list is not ordered by descending version pk (newest first)")
            last_index = index


class AdminHistoryViewOrderByDateTest(LoginMixin, TestBase):

    class TestModelParentAdminOrderByDate(VersionAdmin):
        history_order_by_date = True

    def setUp(self):
        super().setUp()
        # Register a custom admin with history_order_by_date enabled
        admin.site.register(TestModelParent, self.TestModelParentAdminOrderByDate)
        self.reloadUrls()

    def tearDown(self):
        super().tearDown()
        admin.site.unregister(TestModelParent)
        self.reloadUrls()

    def testHistorylistViewOrderByDate(self):
        # Create an object and multiple revisions with increasing timestamps.
        with reversion.create_revision():
            obj = TestModelParent.objects.create(name="v1", parent_name="p1")
            # Use an out-of-sequence date to verify correct ordering
            reversion.set_date_created(datetime.now() + timedelta(days=1))
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
        with reversion.create_revision():
            obj.name = "v3"
            obj.save()

        # Fetch history page.
        response = self.client.get(resolve_url("admin:test_app_testmodelparent_history", obj.pk))
        content = response.content.decode()

        # Expected order: ordered by revision creation date ascending (oldest date first).
        versions = (
            Version.objects.get_for_object(obj)
            .select_related("revision")
            .order_by("revision__date_created", "pk")
        )
        expected_order = list(versions.values_list("pk", flat=True))

        urls_in_order = [
            resolve_url("admin:test_app_testmodelparent_revision", obj.pk, vid)
            for vid in expected_order
        ]

        last_index = -1
        for url in urls_in_order:
            index = content.find(url)
            self.assertNotEqual(index, -1, f"Expected to find {url} in history page")
            self.assertGreater(index, last_index, "History list is not ordered by revision date (oldest first)")
            last_index = index


class AdminHistoryViewLatestFirstOrderByDateTest(LoginMixin, TestBase):

    class TestModelParentAdminLatestFirstOrderByDate(VersionAdmin):
        history_latest_first = True
        history_order_by_date = True

    def setUp(self):
        super().setUp()
        # Register a custom admin with both flags enabled
        admin.site.register(TestModelParent, self.TestModelParentAdminLatestFirstOrderByDate)
        self.reloadUrls()

    def tearDown(self):
        super().tearDown()
        admin.site.unregister(TestModelParent)
        self.reloadUrls()

    def testHistorylistViewOrderLatestFirstByDate(self):
        # Create an object and multiple revisions with increasing timestamps.
        with reversion.create_revision():
            obj = TestModelParent.objects.create(name="v1", parent_name="p1")
            # Use an out-of-sequence date to verify correct ordering
            reversion.set_date_created(datetime.now() + timedelta(days=1))
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
        with reversion.create_revision():
            obj.name = "v3"
            obj.save()

        # Fetch history page.
        response = self.client.get(resolve_url("admin:test_app_testmodelparent_history", obj.pk))
        content = response.content.decode()

        # Expected order: ordered by revision creation date descending (newest date first).
        versions = (
            Version.objects.get_for_object(obj)
            .select_related("revision")
            .order_by("-revision__date_created", "-pk")
        )
        expected_order = list(versions.values_list("pk", flat=True))

        urls_in_order = [
            resolve_url("admin:test_app_testmodelparent_revision", obj.pk, vid)
            for vid in expected_order
        ]

        last_index = -1
        for url in urls_in_order:
            index = content.find(url)
            self.assertNotEqual(index, -1, f"Expected to find {url} in history page")
            self.assertGreater(index, last_index, "History list is not ordered by revision date (newest first)")
            last_index = index


class AdminHistoryViewCustomOrderingTest(LoginMixin, TestBase):
    class TestModelParentAdminCustomOrdering(VersionAdmin):
        def get_version_ordering(self, request):
            return ("revision__comment",)

    def setUp(self):
        super().setUp()
        # Register a custom admin with history_order_by_date enabled
        admin.site.register(TestModelParent, self.TestModelParentAdminCustomOrdering)
        self.reloadUrls()

    def tearDown(self):
        super().tearDown()
        admin.site.unregister(TestModelParent)
        self.reloadUrls()

    def testHistorylistViewCustomOrdering(self):
        # Create an object and multiple revisions with increasing timestamps.
        with reversion.create_revision():
            obj = TestModelParent.objects.create(name="v1", parent_name="p1")
            reversion.set_comment("B")
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
            reversion.set_comment("A")
        with reversion.create_revision():
            obj.name = "v3"
            obj.save()
            reversion.set_comment("C")

        # Fetch history page.
        response = self.client.get(resolve_url("admin:test_app_testmodelparent_history", obj.pk))
        content = response.content.decode()

        # Expected order: ordered by revision comment ascending.
        versions = (
            Version.objects.get_for_object(obj)
            .select_related("revision")
            .order_by("revision__comment")
        )
        expected_order = list(versions.values_list("pk", flat=True))

        urls_in_order = [
            resolve_url("admin:test_app_testmodelparent_revision", obj.pk, vid)
            for vid in expected_order
        ]

        last_index = -1
        for url in urls_in_order:
            index = content.find(url)
            self.assertNotEqual(index, -1, f"Expected to find {url} in history page")
            self.assertGreater(index, last_index, "History list is not ordered by comment ascending")
            last_index = index


class AdminQuotingTest(LoginMixin, AdminMixin, TestBase):

    def setUp(self):
        super().setUp()
        admin.site.register(TestModelEscapePK, VersionAdmin)
        self.reloadUrls()

    def tearDown(self):
        super().tearDown()
        admin.site.unregister(TestModelEscapePK)
        self.reloadUrls()

    def testHistoryWithQuotedPrimaryKey(self):
        pk = 'ABC_123'
        quoted_pk = admin.utils.quote(pk)
        # test is invalid if quoting does not change anything
        assert quoted_pk != pk

        with reversion.create_revision():
            obj = TestModelEscapePK.objects.create(name=pk)

        revision_url = resolve_url(
            "admin:test_app_testmodelescapepk_revision",
            quoted_pk,
            Version.objects.get_for_object(obj).get().pk,
        )
        history_url = resolve_url(
            "admin:test_app_testmodelescapepk_history",
            quoted_pk
        )
        response = self.client.get(history_url)
        self.assertContains(response, revision_url)
        response = self.client.get(revision_url)
        self.assertContains(response, f'value="{pk}"')


class TestModelInlineAdmin(admin.TabularInline):

    model = TestModelInline


class TestModelGenericInlineAdmin(GenericTabularInline):

    model = TestModelGenericInline


class TestModelParentAdmin(VersionAdmin):

    inlines = (TestModelInlineAdmin, TestModelGenericInlineAdmin)


class AdminRegisterInlineTest(TestBase):

    def setUp(self):
        super().setUp()
        admin.site.register(TestModelParent, TestModelParentAdmin)
        self.reloadUrls()

    def tearDown(self):
        super().tearDown()
        admin.site.unregister(TestModelParent)
        self.reloadUrls()

    def testAutoRegisterInline(self):
        self.assertTrue(reversion.is_registered(TestModelInline))

    def testAutoRegisterGenericInline(self):
        self.assertTrue(reversion.is_registered(TestModelGenericInline))


class TestModelCustomObjectIdAdmin(VersionAdmin):

    def reversion_register(self, model, **kwargs):
        kwargs["object_id_field"] = "slug"
        super().reversion_register(model, **kwargs)


class CustomObjectIdAdminMixin(TestBase):

    def setUp(self):
        super().setUp()
        admin.site.register(TestModelCustomObjectId, TestModelCustomObjectIdAdmin)
        self.reloadUrls()

    def tearDown(self):
        super().tearDown()
        admin.site.unregister(TestModelCustomObjectId)
        self.reloadUrls()


class CustomObjectIdAdminHistoryViewTest(LoginMixin, CustomObjectIdAdminMixin, TestBase):

    def testHistoryView(self):
        with reversion.create_revision():
            obj = TestModelCustomObjectId.objects.create(slug="test", name="v1")
        with reversion.create_revision():
            obj.name = "v2"
            obj.save()
        response = self.client.get(resolve_url("admin:test_app_testmodelcustomobjectid_history", obj.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["action_list"]), 2)


class CustomObjectIdAdminRevisionViewTest(LoginMixin, CustomObjectIdAdminMixin, TestBase):

    def setUp(self):
        super().setUp()
        with reversion.create_revision():
            self.obj = TestModelCustomObjectId.objects.create(slug="test", name="v1")
        with reversion.create_revision():
            self.obj.name = "v2"
            self.obj.save()

    def testRevisionViewGet(self):
        version = Version.objects.get_for_object_reference(TestModelCustomObjectId, "test")[1]
        response = self.client.get(resolve_url(
            "admin:test_app_testmodelcustomobjectid_revision",
            self.obj.slug,
            version.pk,
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="v1"')
        # Verify the revert was rolled back (GET should not persist changes).
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.name, "v2")

    def testRevisionViewRevert(self):
        version = Version.objects.get_for_object_reference(TestModelCustomObjectId, "test")[1]
        self.client.post(resolve_url(
            "admin:test_app_testmodelcustomobjectid_revision",
            self.obj.slug,
            version.pk,
        ), {"slug": "test", "name": "v1"})
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.name, "v1")
