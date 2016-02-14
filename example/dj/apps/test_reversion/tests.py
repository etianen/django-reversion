"""
Tests for the django-reversion API.

These tests require Python 2.5 to run.
"""

from __future__ import unicode_literals

import datetime
from unittest import skipUnless

from django.db import models
from django.test import TestCase
from django.core.management import call_command
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.contrib import admin
try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5  pragma: no cover
    from django.contrib.auth.models import User
else:
    User = get_user_model()
from django.db.models.signals import pre_delete
from django.utils import timezone

import reversion
from reversion.revisions import RegistrationError, RevisionManager
from reversion.models import Revision, Version, AuditLog

from test_reversion.models import (
    ReversionTestModel1,
    ReversionTestModel1Child,
    ReversionTestModel2,
    ReversionTestModel3,
    TestFollowModel,
    ReversionTestModel1Proxy,
    RevisionMeta,
    ParentTestAdminModel,
    ChildTestAdminModel,
    InlineTestParentModel,
    InlineTestChildModel,
    InlineTestChildGenericModel
)

try:
    from reversion.helpers import generate_patch, generate_patch_html
except ImportError:  # pragma: no cover
    can_test_patch = False
else:
    can_test_patch = True

from germanium.tools import assert_true, assert_false, assert_equal, assert_raises


ZERO = datetime.timedelta(0)


class ReversionTestBase(TestCase):

    def setUp(self):
        # Unregister all registered models.
        self.initial_registered_models = []
        for registered_model in reversion.get_registered_models():
            self.initial_registered_models.append((registered_model, reversion.get_adapter(registered_model).__class__))
            reversion.unregister(registered_model)
        # Register the test models.
        reversion.register(ReversionTestModel1)
        reversion.register(ReversionTestModel2)
        reversion.register(ReversionTestModel3, eager_signals=[pre_delete])
        # Create some test data.
        self.test11 = ReversionTestModel1.objects.create(name='model1 instance1 version1')
        self.test12 = ReversionTestModel1.objects.create(name='model1 instance2 version1')
        self.test21 = ReversionTestModel2.objects.create(name='model2 instance1 version1')
        self.test22 = ReversionTestModel2.objects.create(name='model2 instance2 version1')
        self.test31 = ReversionTestModel3.objects.create(name='model3 instance1 version1')
        self.test32 = ReversionTestModel3.objects.create(name='model3 instance2 version1')
        self.user = User.objects.create(username='user1')

    def tearDown(self):
        # Unregister the test models.
        reversion.unregister(ReversionTestModel1)
        reversion.unregister(ReversionTestModel2)
        reversion.unregister(ReversionTestModel3)
        # Delete the test models.
        ReversionTestModel1.objects.all().delete()
        ReversionTestModel2.objects.all().delete()
        ReversionTestModel3.objects.all().delete()
        User.objects.all().delete()
        del self.test11
        del self.test12
        del self.test21
        del self.test22
        del self.test31
        del self.test32
        del self.user
        # Delete the revisions index.
        Revision.objects.all().delete()
        # Unregister all remaining models.
        for registered_model in reversion.get_registered_models():
            reversion.unregister(registered_model)
        # Re-register initial registered models.
        for initial_model, adapter in self.initial_registered_models:
            reversion.register(initial_model, adapter_cls=adapter)
        del self.initial_registered_models


class RevisionTestBase(ReversionTestBase):

    @reversion.create_revision()
    def setUp(self):
        super(RevisionTestBase, self).setUp()


# test preserve deleted User Revisions
class DeleteUserTest(RevisionTestBase):

    def test_delete_user(self):
        assert_equal(Revision.objects.count(), 1)
        assert_equal(Version.objects.count(), 4)
        rev = Revision.objects.all()[0]
        rev.user = self.user
        rev.save()
        self.user.delete()
        assert_equal(Revision.objects.count(), 1)
        assert_equal(Version.objects.count(), 4)


class PatchTestCase(RevisionTestBase):

    def setUp(self):
        super(PatchTestCase, self).setUp()
        with reversion.create_revision():
            self.test11.name = 'model1 instance1 version2'
            self.test11.save()
        self.version2, self.version1 = reversion.get_for_object(self.test11)

    def tearDown(self):
        super(PatchTestCase, self).tearDown()
        del self.version1
        del self.version2

    @skipUnless(can_test_patch, 'Diff match patch library not installed')
    def test_can_generate_patch(self):
        assert_equal(
            generate_patch(self.version1, self.version2, 'name'),
            '@@ -17,9 +17,9 @@\n  version\n-1\n+2\n',
        )

    @skipUnless(can_test_patch, 'Diff match patch library not installed')
    def test_can_generate_path_html(self):
        assert_equal(
            generate_patch_html(self.version1, self.version2, 'name'),
            '<span>model1 instance1 version</span><del style="background:#ffe6e6;">1</del><ins style="background:#e6ffe6;">2</ins>',
        )


class RevisionMiddlewareTestCase(ReversionTestBase):

    def test_middleware_create_revision(self):
        assert_equal(Revision.objects.count(), 0)
        assert_equal(Version.objects.count(), 0)
        self.client.get('/success/')
        assert_equal(Revision.objects.count(), 1)
        assert_equal(Version.objects.count(), 4)

    def test_revision_middleware_invalidates_revision_on_error(self):
        assert_equal(Revision.objects.count(), 0)
        assert_equal(Version.objects.count(), 0)
        assert_raises(Exception, lambda: self.client.get('/error/'))
        assert_equal(Revision.objects.count(), 0)
        assert_equal(Version.objects.count(), 0)

    def test_revision_middleware_error_on_double_middleware(self):
        assert_raises(ImproperlyConfigured, lambda: self.client.get('/double/'))


class CreateInitialRevisionsCommandTestCase(ReversionTestBase):

    def test_create_initial_revisions(self):
        assert_equal(Revision.objects.count(), 0)
        assert_equal(Version.objects.count(), 0)
        call_command('createinitialrevisions')
        revcount = Revision.objects.count()
        vercount = Version.objects.count()
        assert_true(revcount >= 4)
        assert_true(vercount >= 4)
        call_command('createinitialrevisions')
        assert_equal(Revision.objects.count(), revcount)
        assert_equal(Version.objects.count(), vercount)

    def test_create_initial_revisions_specific_apps(self):
        call_command('createinitialrevisions', 'test_reversion')
        assert_equal(Revision.objects.count(), 6)
        assert_equal(Version.objects.count(), 6)

    def test_create_initial_revisions_specific_models(self):
        call_command('createinitialrevisions', 'test_reversion.ReversionTestModel1')
        assert_equal(Revision.objects.count(), 2)
        assert_equal(Version.objects.count(), 2)
        call_command('createinitialrevisions', 'test_reversion.ReversionTestModel2')
        assert_equal(Revision.objects.count(), 4)
        assert_equal(Version.objects.count(), 4)

    def test_create_initial_revisions_specific_comment(self):
        call_command('createinitialrevisions', comment='Foo bar')
        assert_equal(Revision.objects.all()[0].comment, 'Foo bar')


excluded_revision_manager = RevisionManager('excluded')


class ExcludedFieldsTestCase(RevisionTestBase):

    def setUp(self):
        excluded_revision_manager.register(ReversionTestModel1, fields=('id',))
        excluded_revision_manager.register(ReversionTestModel2, exclude=('name',))
        super(ExcludedFieldsTestCase, self).setUp()

    def tearDown(self):
        super(ExcludedFieldsTestCase, self).tearDown()
        excluded_revision_manager.unregister(ReversionTestModel1)
        excluded_revision_manager.unregister(ReversionTestModel2)

    def test_excluded_revision_manager_is_separate(self):
        assert_equal(excluded_revision_manager.get_for_object(self.test11).count(), 1)

    def testE_excluded_fields_are_respected(self):
        assert_equal(excluded_revision_manager.get_for_object(self.test11)[0].field_dict['id'], self.test11.id)
        assert_equal(excluded_revision_manager.get_for_object(self.test11)[0].field_dict['name'], '')
        assert_equal(excluded_revision_manager.get_for_object(self.test21)[0].field_dict['id'], self.test21.id)
        assert_equal(excluded_revision_manager.get_for_object(self.test21)[0].field_dict['name'], '')


class FollowModelsTestCase(ReversionTestBase):

    @reversion.create_revision()
    def setUp(self):
        super(FollowModelsTestCase, self).setUp()
        reversion.unregister(ReversionTestModel1)
        reversion.register(ReversionTestModel1, follow=('testfollowmodel_set',))
        reversion.register(TestFollowModel, follow=('test_model_1', 'test_model_2s',))
        self.follow1 = TestFollowModel.objects.create(name='related instance1 version 1', test_model_1=self.test11)
        self.follow1.test_model_2s.add(self.test21, self.test22)

    def tearDown(self):
        reversion.unregister(TestFollowModel)
        TestFollowModel.objects.all().delete()
        del self.follow1
        super(FollowModelsTestCase, self).tearDown()

    def test_relations_followed(self):
        assert_equal(Revision.objects.count(), 1)
        assert_equal(Version.objects.count(), 5)
        with reversion.create_revision():
            self.follow1.save()
        assert_equal(Revision.objects.count(), 2)
        assert_equal(Version.objects.count(), 9)

    def test_revert_with_delete(self):
        with reversion.create_revision():
            test23 = ReversionTestModel2.objects.create(name='model2 instance3 version1')
            self.follow1.test_model_2s.add(test23)
            self.follow1.save()
        assert_equal(reversion.get_for_object(test23).count(), 1)
        assert_equal(self.follow1.test_model_2s.all().count(), 3)
        # Test that a revert with delete works.
        test23_pk = test23.pk
        assert_equal(ReversionTestModel2.objects.count(), 3)
        with reversion.create_revision():
            reversion.get_for_object(self.follow1)[1].revision.revert(delete=True)
        assert_equal(ReversionTestModel1.objects.get(id=self.test11.pk).name, 'model1 instance1 version1')
        assert_equal(ReversionTestModel2.objects.get(id=self.test22.pk).name, 'model2 instance2 version1')
        assert_equal(ReversionTestModel2.objects.count(), 2)
        assert_raises(ReversionTestModel2.DoesNotExist, lambda: ReversionTestModel2.objects.get(id=test23_pk))
        # Roll back to the revision where all models were present.
        reversion.get_for_object(self.follow1)[1].revision.revert()
        assert_equal(self.follow1.test_model_2s.all().count(), 3)
        # Roll back to a revision where a delete flag is present.
        reversion.get_for_object(self.follow1)[0].revision.revert(delete=True)
        assert_equal(self.follow1.test_model_2s.all().count(), 2)

    def test_reverse_relations_followed(self):
        assert_equal(Revision.objects.count(), 1)
        assert_equal(Version.objects.count(), 5)
        with reversion.create_revision():
            self.test11.save()
        assert_equal(Revision.objects.count(), 2)
        assert_equal(Version.objects.count(), 9)

    def test_reverse_follow_revert_with_delete(self):
        with reversion.create_revision():
            follow2 = TestFollowModel.objects.create(name='related instance2 version 1', test_model_1=self.test11)
        # Test that a revert with delete works.
        follow2_pk = follow2.pk
        reversion.get_for_object(self.test11)[1].revision.revert(delete=True)
        assert_equal(TestFollowModel.objects.count(), 1)
        assert_raises(TestFollowModel.DoesNotExist, lambda: TestFollowModel.objects.get(id=follow2_pk))

    def test_recover_deleted(self):
        # Delete the test model.
        with reversion.create_revision():
            self.test11.delete()
        assert_equal(TestFollowModel.objects.count(), 0)
        assert_equal(ReversionTestModel1.objects.count(), 1)
        # Recover the test model.
        with reversion.create_revision():
            reversion.get_deleted(ReversionTestModel1)[0].revision.revert()
        # Make sure it was recovered.
        assert_equal(TestFollowModel.objects.count(), 1)
        assert_equal(ReversionTestModel1.objects.count(), 2)


class ReversionTestModel1ChildProxy(ReversionTestModel1Child):
    class Meta:
        proxy = True


class ProxyModelApiTestCase(RevisionTestBase):

    def setUp(self):
        super(ProxyModelApiTestCase, self).setUp()
        reversion.register(ReversionTestModel1Proxy)
        self.concrete = self.test11
        self.proxy = ReversionTestModel1Proxy.objects.get(pk=self.concrete.pk)

        with reversion.create_revision():
            self.proxy.name = 'proxy model'
            self.proxy.save()

    def test_can_get_for_object_reference(self):
        # Can get version for proxy model
        proxy_versions = reversion.get_for_object_reference(ReversionTestModel1Proxy, self.proxy.id)
        assert_equal(len(proxy_versions), 2)
        assert_equal(proxy_versions[0].field_dict['name'], self.proxy.name)
        assert_equal(proxy_versions[1].field_dict['name'], self.concrete.name)

        # Can get the same version for concrete model
        concrete_versions = reversion.get_for_object_reference(ReversionTestModel1, self.concrete.id)
        assert_equal(list(concrete_versions), list(proxy_versions))

    def test_can_get_for_object(self):
        # Can get version for proxy model
        proxy_versions = reversion.get_for_object(self.proxy)
        assert_equal(len(proxy_versions), 2)
        assert_equal(proxy_versions[0].field_dict['name'], self.proxy.name)
        assert_equal(proxy_versions[1].field_dict['name'], self.concrete.name)

        # Can get the same version for concrete model
        concrete_versions = reversion.get_for_object(self.concrete)
        assert_equal(list(concrete_versions), list(proxy_versions))

    def test_can_revert_version(self):
        assert_equal(ReversionTestModel1.objects.get(pk=self.concrete.pk).name, self.proxy.name)
        reversion.get_for_object(self.proxy)[1].revert()
        assert_equal(ReversionTestModel1.objects.get(pk=self.concrete.pk).name, self.concrete.name)

    def test_multi_table_inheritance_proxy_model(self):
        reversion.register(ReversionTestModel1Child, follow=('reversiontestmodel1_ptr',))
        reversion.register(ReversionTestModel1ChildProxy, follow=('reversiontestmodel1_ptr',))

        with reversion.create_revision():
            concrete = ReversionTestModel1Child.objects.create(name='modelchild1 instance1 version 1')

        proxy = ReversionTestModel1ChildProxy.objects.get(pk=concrete.pk)
        with reversion.create_revision():
            proxy.name = 'proxy model'
            proxy.save()

        proxy_versions = reversion.get_for_object(proxy)

        assert_equal(proxy_versions[0].field_dict['name'], proxy.name)
        assert_equal(proxy_versions[1].field_dict['name'], concrete.name)


class MultiTableInheritanceApiTestCase(RevisionTestBase):

    def setUp(self):
        super(MultiTableInheritanceApiTestCase, self).setUp()
        reversion.register(ReversionTestModel1Child, follow=('reversiontestmodel1_ptr',))
        with reversion.create_revision():
            self.testchild1 = ReversionTestModel1Child.objects.create(name='modelchild1 instance1 version 1')

    def tearDown(self):
        super(MultiTableInheritanceApiTestCase, self).tearDown()
        del self.testchild1

    def testCanRetreiveFullFieldDict(self):
        assert_equal(reversion.get_for_object(self.testchild1)[0].field_dict['name'],
                     'modelchild1 instance1 version 1')


class ApiTestCase(RevisionTestBase):

    def setUp(self):
        super(ApiTestCase, self).setUp()
        with reversion.create_revision():
            self.test11.name = 'model1 instance1 version2'
            self.test11.save()
            self.test12.name = 'model1 instance2 version2'
            self.test12.save()
            self.test21.name = 'model2 instance1 version2'
            self.test21.save()
            self.test22.name = 'model2 instance2 version2'
            self.test22.save()

    def test_revision_signals(self):
        pre_revision_receiver_called = []

        def pre_revision_receiver(**kwargs):
            assert_equal(kwargs['instances'], [self.test11])
            assert_true(isinstance(kwargs['revision'], Revision))
            assert_equal(len(kwargs['versions']), 1)
            pre_revision_receiver_called.append(True)
        post_revision_receiver_called = []

        def post_revision_receiver(**kwargs):
            assert_equal(kwargs['instances'], [self.test11])
            assert_true(isinstance(kwargs['revision'], Revision))
            assert_equal(len(kwargs['versions']), 1)
            post_revision_receiver_called.append(True)
        reversion.pre_revision_commit.connect(pre_revision_receiver)
        reversion.post_revision_commit.connect(post_revision_receiver)
        # Create a revision.
        with reversion.create_revision():
            self.test11.save()
        # Check the signals were called.
        assert_true(pre_revision_receiver_called)
        assert_true(post_revision_receiver_called)

    def test_can_get_for_object_reference(self):
        # Test a model with an int pk.
        versions = reversion.get_for_object_reference(ReversionTestModel1, self.test11.pk)
        assert_equal(len(versions), 2)
        assert_equal(versions[0].field_dict['name'], 'model1 instance1 version2')
        assert_equal(versions[1].field_dict['name'], 'model1 instance1 version1')
        # Test a model with a str pk.
        versions = reversion.get_for_object_reference(ReversionTestModel2, self.test21.pk)
        assert_equal(len(versions), 2)
        assert_equal(versions[0].field_dict['name'], 'model2 instance1 version2')
        assert_equal(versions[1].field_dict['name'], 'model2 instance1 version1')

    def test_can_get_for_object(self):
        # Test a model with an int pk.
        versions = reversion.get_for_object(self.test11)
        assert_equal(len(versions), 2)
        assert_equal(versions[0].field_dict['name'], 'model1 instance1 version2')
        assert_equal(versions[1].field_dict['name'], 'model1 instance1 version1')
        # Test a model with a str pk.
        versions = reversion.get_for_object(self.test21)
        assert_equal(len(versions), 2)
        assert_equal(versions[0].field_dict['name'], 'model2 instance1 version2')
        assert_equal(versions[1].field_dict['name'], 'model2 instance1 version1')

    def test_can_get_unique_for_object(self):
        with reversion.create_revision():
            self.test11.save()
            self.test21.save()
        # Test a model with an int pk.
        assert_equal(reversion.get_for_object(self.test11).count(), 3)
        assert_equal(len(reversion.get_unique_for_object(self.test11)), 2)
        # Test a model with a str pk.
        assert_equal(reversion.get_for_object(self.test21).count(), 3)
        assert_equal(len(reversion.get_unique_for_object(self.test21)), 2)

    def test_can_get_for_date(self):
        now = timezone.now()
        # Test a model with an int pk.
        version = reversion.get_for_date(self.test11, now)
        assert_equal(version.field_dict['name'], 'model1 instance1 version2')
        assert_raises(Version.DoesNotExist, lambda: reversion.get_for_date(self.test11, datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)))
        # Test a model with a str pk.
        version = reversion.get_for_date(self.test21, now)
        assert_equal(version.field_dict['name'], 'model2 instance1 version2')
        assert_raises(Version.DoesNotExist, lambda: reversion.get_for_date(self.test21, datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)))

    def test_can_get_deleted(self):
        with reversion.create_revision():
            self.test11.delete()
            self.test21.delete()
        # Test a model with an int pk.
        versions = reversion.get_deleted(ReversionTestModel1)
        assert_equal(len(versions), 1)
        assert_equal(versions[0].field_dict['name'], 'model1 instance1 version2')
        # Test a model with a str pk.
        versions = reversion.get_deleted(ReversionTestModel2)
        assert_equal(len(versions), 1)
        assert_equal(versions[0].field_dict['name'], 'model2 instance1 version2')

    def test_can_revert_version(self):
        reversion.get_for_object(self.test11)[1].revert()
        assert_equal(ReversionTestModel1.objects.get(id=self.test11.pk).name, 'model1 instance1 version1')

    def test_can_revert_revision(self):
        reversion.get_for_object(self.test11)[1].revision.revert()
        assert_equal(ReversionTestModel1.objects.get(id=self.test11.pk).name, 'model1 instance1 version1')
        assert_equal(ReversionTestModel1.objects.get(id=self.test12.pk).name, 'model1 instance2 version1')
        assert_equal(ReversionTestModel2.objects.get(id=self.test22.pk).name, 'model2 instance2 version1')
        assert_equal(ReversionTestModel2.objects.get(id=self.test22.pk).name, 'model2 instance2 version1')

    def test_can_revert_revision_with_deleted_versions(self):
        assert_equal(ReversionTestModel1.objects.count(), 2)
        assert_equal(ReversionTestModel2.objects.count(), 2)
        with reversion.create_revision():
            self.test11.name = 'model1 instance1 version3'
            self.test11.save()
            self.test12.delete()
            self.test21.name = 'model2 instance1 version3'
            self.test21.save()
            self.test22.delete()
        assert_equal(ReversionTestModel1.objects.count(), 1)
        assert_equal(ReversionTestModel2.objects.count(), 1)
        with reversion.create_revision():
            self.test11.name = 'model1 instance1 version4'
            self.test11.save()
            self.test21.name = 'model2 instance1 version4'
            self.test21.save()
        assert_equal(ReversionTestModel1.objects.count(), 1)
        assert_equal(ReversionTestModel2.objects.count(), 1)
        # Revert to a revision where some deletes were logged.
        reversion.get_for_object(self.test11)[1].revision.revert()
        assert_equal(ReversionTestModel1.objects.count(), 1)
        assert_equal(ReversionTestModel2.objects.count(), 1)
        assert_equal(ReversionTestModel1.objects.get(id=self.test11.id).name, 'model1 instance1 version3')
        assert_equal(ReversionTestModel2.objects.get(id=self.test21.id).name, 'model2 instance1 version3')
        # Revert the a revision before the deletes were logged.
        reversion.get_for_object(self.test11)[2].revision.revert()
        assert_equal(ReversionTestModel1.objects.count(), 2)
        assert_equal(ReversionTestModel2.objects.count(), 2)

    def test_can_add_meta_to_revision(self):
        # Create a revision with lots of meta data.
        with reversion.create_revision():
            self.test11.save()
            reversion.set_comment('Foo bar')
            assert_equal(reversion.get_comment(), 'Foo bar')
            reversion.set_user(self.user)
            assert_equal(reversion.get_user(), self.user)
            reversion.add_meta(RevisionMeta, age=5)
        # Test the revision data.
        revision = reversion.get_for_object(self.test11)[0].revision
        assert_equal(revision.user, self.user)
        assert_equal(revision.comment, 'Foo bar')
        assert_equal(revision.revisionmeta.age, 5)


class InternalsTestCase(RevisionTestBase):

    def test_revisions_created(self):
        assert_equal(Revision.objects.count(), 1)
        assert_equal(Version.objects.count(), 4)

    def test_context_manager(self):
        # New revision should be created.
        with reversion.create_revision():
            with reversion.create_revision():
                self.test11.name = 'model1 instance1 version2'
                self.test11.save()
        assert_equal(Revision.objects.count(), 2)
        assert_equal(Version.objects.count(), 5)

    def test_empty_revision_not_created(self):
        with reversion.create_revision():
            pass
        assert_equal(Revision.objects.count(), 1)
        assert_equal(Version.objects.count(), 4)

    def test_revision_context_abandoned_on_error(self):
        with reversion.create_revision():
            try:
                with reversion.create_revision():
                    self.test11.name = 'model1 instance1 version2'
                    self.test11.save()
                    raise Exception('Foo')
            except:
                pass
        assert_equal(Revision.objects.count(), 1)
        assert_equal(Version.objects.count(), 4)

    def test_revision_decorator_abandoned_on_error(self):
        @reversion.create_revision()
        def make_revision():
            self.test11.name = 'model1 instance1 version2'
            self.test11.save()
            raise Exception('Foo')
        try:
            make_revision()
        except:
            pass
        assert_equal(Revision.objects.count(), 1)
        assert_equal(Version.objects.count(), 4)

    def test_revision_created_on_delete(self):
        with reversion.create_revision():
            self.test31.delete()
        assert_equal(Revision.objects.count(), 2)
        assert_equal(Version.objects.count(), 5)

    def test_no_version_for_object_created_and_deleted(self):
        with reversion.create_revision():
            new_object = ReversionTestModel1.objects.create()
            new_object.delete()
        # No Revision and no Version should have been created.
        assert_equal(Revision.objects.count(), 1)
        assert_equal(Version.objects.count(), 4)


class RegistrationTestCase(TestCase):

    def check_registration(self, test_model):
        # Register the model and test.
        reversion.register(test_model)
        self.assertTrue(reversion.is_registered(test_model))
        assert_raises(RegistrationError, lambda: reversion.register(test_model))
        self.assertTrue(test_model in reversion.get_registered_models())
        self.assertTrue(isinstance(reversion.get_adapter(test_model), reversion.VersionAdapter))

    def check_deregistration(self, test_model):
        # Unregister the model and text.
        reversion.unregister(test_model)
        self.assertFalse(reversion.is_registered(test_model))
        assert_raises(RegistrationError, lambda: reversion.unregister(test_model))
        self.assertTrue(test_model not in reversion.get_registered_models())
        assert_raises(RegistrationError, lambda: isinstance(reversion.get_adapter(test_model)))

    def test_registration(self):
        self.check_registration(ReversionTestModel1)
        self.check_deregistration(ReversionTestModel1)

    def test_proxy_registration(self):
        # ProxyModel registered as usual model
        self.check_registration(ReversionTestModel1Proxy)
        self.check_deregistration(ReversionTestModel1Proxy)
        # TODO: proxy model does not unregister concrete model
        self.check_deregistration(ReversionTestModel1)

    def test_decorator(self):
        # Test the use of register as a decorator
        @reversion.register
        class DecoratorModel(models.Model):
            pass
        self.assertTrue(reversion.is_registered(DecoratorModel))

    def test_decorator_args(self):
        # Test a decorator with arguments
        @reversion.register(format='yaml')
        class DecoratorArgsModel(models.Model):
            pass
        self.assertTrue(reversion.is_registered(DecoratorArgsModel))

    def test_eager_registration(self):
        # Register the model and test.
        reversion.register(ReversionTestModel3, eager_signals=[pre_delete])
        self.assertTrue(reversion.is_registered(ReversionTestModel3))
        assert_raises(RegistrationError, lambda: reversion.register(ReversionTestModel3, eager_signals=[pre_delete]))
        self.assertTrue(ReversionTestModel3 in reversion.get_registered_models())
        self.assertTrue(isinstance(reversion.get_adapter(ReversionTestModel3), reversion.VersionAdapter))
        self.assertEquals([], reversion.default_revision_manager._signals[ReversionTestModel3])
        self.assertEquals([pre_delete], reversion.default_revision_manager._eager_signals[ReversionTestModel3])
        # Unregister the model and text.
        reversion.unregister(ReversionTestModel3)
        self.assertFalse(reversion.is_registered(ReversionTestModel3))
        assert_raises(RegistrationError, lambda: reversion.unregister(ReversionTestModel3))
        self.assertTrue(ReversionTestModel3 not in reversion.get_registered_models())
        assert_raises(RegistrationError, lambda: isinstance(reversion.get_adapter(ReversionTestModel3)))
        self.assertFalse(ReversionTestModel3 in reversion.default_revision_manager._signals)
        self.assertFalse(ReversionTestModel3 in reversion.default_revision_manager._eager_signals)


class AuditLogTestCase(TestCase):

    def setUp(self):
        reversion.register(ReversionTestModel1)

    def tearDown(self):
        reversion.unregister(ReversionTestModel1)

    def test_audit_log_is_not_created_for_block_without_reversion(self):
        assert_false(AuditLog.objects.exists())
        reversion.create_audit_log('Test audit log')
        assert_false(AuditLog.objects.exists())

    def test_audit_log_is_created_for_block_with_reversion(self):
        with reversion.create_revision():
            assert_false(AuditLog.objects.exists())
            reversion.create_audit_log('Test audit log')
            assert_equal(AuditLog.objects.count(), 1)

    def test_audit_log_contains_related_versions(self):
        test_inst1 = ReversionTestModel1.objects.create(name='model1 instance1')
        test_inst2 = ReversionTestModel1.objects.create(name='model1 instance2')

        with reversion.create_revision():
            assert_false(AuditLog.objects.exists())
            reversion.create_audit_log('Test audit log', objects=[test_inst1])
            assert_equal(AuditLog.objects.count(), 1)

            reversion.create_audit_log('Test audit log', objects=[test_inst2])
            assert_equal(AuditLog.objects.count(), 2)

            reversion.create_audit_log('Test audit log', objects=[test_inst1, test_inst2])
            assert_equal(AuditLog.objects.count(), 3)
        assert_equal(Version.objects.count(), 2)
        assert_equal(Version.objects.filter(type=Version.TYPE.AUDIT).count(), 2)

        audit_logs = AuditLog.objects.all()

        assert_false(set(audit_logs[2].versions.values_list('object_id_int', flat=True)) ^ {test_inst1.pk})
        assert_false(set(audit_logs[1].versions.values_list('object_id_int', flat=True)) ^ {test_inst2.pk})
        assert_false(set(audit_logs[0].versions.values_list('object_id_int', flat=True)) ^ {test_inst1.pk, test_inst2.pk})

    def test_versions_is_not_removed_after_removing_audit_log(self):
        with reversion.create_revision():
            test_inst1 = ReversionTestModel1.objects.create(name='model1 instance1')
            test_inst2 = ReversionTestModel1.objects.create(name='model1 instance2')

            assert_false(AuditLog.objects.exists())
            reversion.create_audit_log('Test audit log', objects=[test_inst1, test_inst2])
            assert_equal(AuditLog.objects.count(), 1)
        assert_equal(Version.objects.count(), 2)
        assert_equal(Version.objects.filter(type=Version.TYPE.CREATED).count(), 2)

        audit_log = AuditLog.objects.first()
        assert_false(set(audit_log.versions.values_list('object_id_int', flat=True)) ^ {test_inst1.pk, test_inst2.pk})

        audit_log.delete()
        assert_equal(Version.objects.filter(type=Version.TYPE.CREATED).count(), 2)
