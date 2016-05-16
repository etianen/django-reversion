
from django.db.models import Func, fields


class ReversionCast(Func):
    """
    Coerce an expression to a new field type.
    """
    function = 'CAST'
    template = '%(function)s(%(expressions)s AS %(db_type)s)'

    override_mysql_types = {
        'AutoField': 'signed',
        'CharField': 'char',
        'FloatField': 'signed',
        'DecimalField': 'decimal(%(max_digits)s, %(decimal_places)s)',
        'IntegerField': 'signed',
        'BigIntegerField': 'signed',
        'OneToOneField': 'signed',
        'PositiveIntegerField': 'unsigned',
        'PositiveSmallIntegerField': 'unsigned',
        'SlugField': 'char',
        'SmallIntegerField': 'signed',
    }

    override_postgresql_types = {
        'AutoField': 'integer',
    }

    def __init__(self, expression, output_field):
        super(ReversionCast, self).__init__(expression, output_field=output_field)

    def as_sql(self, compiler, connection, **extra_context):
        if 'db_type' not in self.extra:
            self.extra['db_type'] = self._output_field.db_type(connection)
        return super(ReversionCast, self).as_sql(compiler, connection, **extra_context)

    def as_mysql(self, compiler, connection):
        output_field_class = self._output_field.get_internal_type()
        if output_field_class in self.override_mysql_types:
            self.extra['db_type'] = self.override_mysql_types[output_field_class]
        template = self.template
        if output_field_class == 'CharField':
            template = '%(function)s(%(expressions)s AS %(db_type)s) COLLATE ''utf8_unicode_ci'''
        return self.as_sql(compiler, connection, template=template)

    def as_postgresql(self, compiler, connection):
        output_field_class = self._output_field.get_internal_type()
        if output_field_class in self.override_postgresql_types:
            self.extra['db_type'] = self.override_postgresql_types[output_field_class]
        # CAST would be valid too, but the :: shortcut syntax is more readable.
        return self.as_sql(compiler, connection, template='%(expressions)s::%(db_type)s')
