from django.db import models
from django.utils.encoding import force_text, python_2_unicode_compatible

from reversion.models import Revision


@python_2_unicode_compatible
class ReversionTestModelBase(models.Model):

    name = models.CharField(
        max_length = 100,
    )

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class ReversionTestModel1(ReversionTestModelBase):

    pass


str_pk_gen = 0;

def get_str_pk():
    global str_pk_gen
    str_pk_gen += 1;
    return force_text(str_pk_gen)


class ReversionTestModel2(ReversionTestModelBase):

    id = models.CharField(
        primary_key = True,
        max_length = 100,
        default = get_str_pk
    )


class ReversionTestModel3(ReversionTestModelBase):

    pass



class TestFollowModel(ReversionTestModelBase):

    test_model_1 = models.ForeignKey(
        ReversionTestModel1,
    )

    test_model_2s = models.ManyToManyField(
        ReversionTestModel2,
    )


class ReversionTestModel1Proxy(ReversionTestModel1):

    class Meta:
        proxy = True


class RevisionMeta(models.Model):

    revision = models.OneToOneField(Revision)

    age = models.IntegerField()


# Admin test models.

class ParentTestAdminModel(models.Model):

    parent_name = models.CharField(
        max_length = 200,
    )


@python_2_unicode_compatible
class ChildTestAdminModel(ParentTestAdminModel):

    child_name = models.CharField(
        max_length = 200,
    )

    def __str__(self):
        return self.child_name


class InlineTestParentModel(models.Model):

    name = models.CharField(
        max_length = 100,
    )

    def __str__(self):
        return self.name


class InlineTestChildModel(models.Model):

    parent = models.ForeignKey(
        InlineTestParentModel,
        related_name = "children",
    )

    name = models.CharField(
        max_length = 100,
    )

    def __str__(self):
        return self.name


# Test that reversion handles unrelated inlines.
# Issue https://github.com/etianen/django-reversion/issues/277
class InlineTestUnrelatedParentModel(models.Model):

    pass


class InlineTestUnrelatedChildModel(models.Model):

    pass
