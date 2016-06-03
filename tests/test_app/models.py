from django.db import models
from django.utils.encoding import python_2_unicode_compatible
import reversion


@reversion.register()
@python_2_unicode_compatible
class TestParentModel(models.Model):

    parent_field = models.CharField(
        max_length=191,
    )


@reversion.register(fields=("field",), exclude=("excluded_field",), follow=("testparentmodel_ptr",))
@python_2_unicode_compatible
class TestModel(TestParentModel):

    field = models.CharField(
        max_length=191,
    )

    excluded_field = models.CharField(
        max_length=191,
    )

    def __str__(self):
        return self.name
