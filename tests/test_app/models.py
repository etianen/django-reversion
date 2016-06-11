from django.db import models
from django.contrib.contenttypes.models import ContentType
try:
    from django.contrib.contenttypes.fields import GenericRelation
except ImportError:  # Django < 1.9 pragma: no cover
    from django.contrib.contenttypes.generic import GenericRelation
from reversion.models import Revision


class TestModelGenericInline(models.Model):

    object_id = models.IntegerField()

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
    )

    inline_name = models.CharField(
        max_length=191,
        default="v1",
    )


class TestModel(models.Model):

    name = models.CharField(
        max_length=191,
        default="v1",
    )

    related_instances = models.ManyToManyField(
        "self",
        blank=True,
    )

    generic_inlines = GenericRelation(TestModelGenericInline)


class TestModelParent(TestModel):

    parent_name = models.CharField(
        max_length=191,
        default="parent v1",
    )


class TestModelInline(models.Model):

    test_model = models.ForeignKey(
        TestModel,
        on_delete=models.CASCADE,
    )

    inline_name = models.CharField(
        max_length=191,
        default="v1",
    )


class TestMeta(models.Model):

    revision = models.ForeignKey(
        Revision,
        on_delete=models.CASCADE,
    )

    name = models.CharField(
        max_length=191,
    )
