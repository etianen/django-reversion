import django


def remote_field(field):
    # remote_field is new in Django 1.9
    return field.remote_field if hasattr(field, 'remote_field') else field.rel


def remote_model(field):
    # remote_field is new in Django 1.9
    return field.remote_field.model if hasattr(field, 'remote_field') else field.rel.to


def is_authenticated(user):
    if django.VERSION < (1, 10):
        return user.is_authenticated()
    return user.is_authenticated
