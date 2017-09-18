import django


def remote_field(field):
    # remote_field is new in Django 1.9
    return field.remote_field if hasattr(field, 'remote_field') else field.rel


def remote_model(field):
    # remote_field is new in Django 1.9
    return field.remote_field.model if hasattr(field, 'remote_field') else field.rel.to


def _choose_is_authenticated():
    # Django version does not change during application life so it could
    # be nicer and faster to know which function to call at import/startup time
    if django.VERSION < (1, 10):
        def pre_django_1_10(user):
            return user.is_authenticated()
        return pre_django_1_10

    def django_1_10_and_later(user):
        return user.is_authenticated
    return django_1_10_and_later


is_authenticated = _choose_is_authenticated()
