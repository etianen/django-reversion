import decimal
import uuid

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import force_text, python_2_unicode_compatible
try:
    from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
except ImportError:  # Django < 1.9  pragma: no cover
    from django.contrib.contenttypes.generic import GenericRelation, GenericForeignKey

from reversion.models import Revision


@python_2_unicode_compatible
class ReversionTestModelBase(models.Model):

    name = models.CharField(
        max_length=100,
    )

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class ReversionTestModel1(ReversionTestModelBase):

    pass


str_pk_gen = 0


def get_str_pk():
    global str_pk_gen
    str_pk_gen += 1
    return force_text(str_pk_gen)


class ReversionTestModel1Child(ReversionTestModel1):

    pass


class ReversionTestModel2(ReversionTestModelBase):

    id = models.CharField(
        primary_key=True,
        max_length=100,
        default=get_str_pk
    )


class ReversionTestModel3(ReversionTestModelBase):

    pass


class TestFollowModel(ReversionTestModelBase):

    test_model_1 = models.ForeignKey(
        ReversionTestModel1, on_delete=models.CASCADE,
    )

    test_model_2s = models.ManyToManyField(
        ReversionTestModel2,
    )


class ReversionTestModel1Proxy(ReversionTestModel1):

    class Meta:
        proxy = True


class RevisionMeta(models.Model):

    revision = models.OneToOneField(Revision, on_delete=models.CASCADE)

    age = models.IntegerField()


# Admin test models.

@python_2_unicode_compatible
class ParentTestAdminModel(models.Model):

    parent_name = models.CharField(
        max_length=200,
    )

    def __str__(self):
        return self.parent_name


@python_2_unicode_compatible
class ChildTestAdminModel(ParentTestAdminModel):

    child_name = models.CharField(
        max_length=200,
    )

    def __str__(self):
        return self.child_name


@python_2_unicode_compatible
class InlineTestChildGenericModel(models.Model):

    object_id = models.IntegerField(
        db_index=True,
    )

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
    )

    object = GenericForeignKey()

    name = models.CharField(
        max_length=100,
    )

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class InlineTestParentModel(models.Model):

    name = models.CharField(
        max_length=100,
    )

    generic_children = GenericRelation(InlineTestChildGenericModel)

    def __str__(self):
        return self.name


class InlineTestParentModelProxy(InlineTestParentModel):

    class Meta:
        proxy = True


@python_2_unicode_compatible
class InlineTestChildModel(models.Model):

    parent = models.ForeignKey(
        InlineTestParentModel,
        on_delete=models.CASCADE,
        related_name="children",
    )

    name = models.CharField(
        max_length=100,
    )

    def __str__(self):
        return self.name


class InlineTestChildModelProxy(InlineTestChildModel):

    class Meta:
        proxy = True


# Test that reversion handles unrelated inlines.
# Issue https://github.com/etianen/django-reversion/issues/277
class InlineTestUnrelatedParentModel(models.Model):

    pass


class InlineTestUnrelatedChildModel(models.Model):

    parent = models.ForeignKey(
        InlineTestUnrelatedParentModel, on_delete=models.CASCADE,
    )


# Test for Various PK Types
class ReversionTestModelPKAutoInt(models.Model):
    name = models.CharField(max_length=100)


class ReversionTestModelPKBigInt(models.Model):
    id = models.BigIntegerField(primary_key=True, default=models.BigIntegerField.MAX_BIGINT)
    name = models.CharField(max_length=100)


class ReversionTestModelPKString(models.Model):
    id = models.CharField(max_length=191, primary_key=True, default="NEW_ID")
    name = models.CharField(max_length=100)


class ReversionTestModelPKGuid(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=100)


class ReversionTestModelPKDecimal(models.Model):
    id = models.DecimalField(max_digits=19, decimal_places=4, primary_key=True, default=decimal.Decimal('1234.2401'))
    name = models.CharField(max_length=100)


class ReversionTestModelPKFloat(models.Model):
    id = models.FloatField(primary_key=True, default=float(1234.234))
    name = models.CharField(max_length=100)


# Register Failure Tests
class ReversionTestModelPKStringLarge(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=100)
    pass


class ReversionTestModelPKText(models.Model):
    id = models.TextField(max_length=1000, primary_key=True)
    name = models.CharField(max_length=100)
    pass
