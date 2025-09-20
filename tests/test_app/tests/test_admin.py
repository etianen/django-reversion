import re
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete, m2m_changed
from django.shortcuts import resolve_url
import reversion
from reversion.admin import VersionAdmin
from reversion.models import Version
from test_app.models import TestModel, TestModelParent, TestModelInline, TestModelGenericInline, TestModelEscapePK
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
