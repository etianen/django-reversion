
from django.db.models import Func, fields


class ReversionCast(Func):
    """
    Coerce an expression to a new field type.
    """
    function = 'CAST'
    template = '%(function)s(%(expressions)s AS %(db_type)s)'

    override_types = {
        fields.AutoField: 'integer'
    }

    def __init__(self, expression, output_field):
        super(ReversionCast, self).__init__(expression, output_field=output_field)

    def as_sql(self, compiler, connection, **extra_context):
        if 'db_type' not in self.extra:
            self.extra['db_type'] = self._output_field.db_type(connection)
        return super(ReversionCast, self).as_sql(compiler, connection, **extra_context)

    def as_mysql(self, compiler, connection):
        output_field_class = self._output_field.get_internal_type()
        if output_field_class in self.override_types:
            self.extra['db_type'] = self.override_types[output_field_class]
        return self.as_sql(compiler, connection)

    def as_postgresql(self, compiler, connection):
        output_field_class = self._output_field.get_internal_type()
        if output_field_class in self.override_types:
            self.extra['db_type'] = self.override_types[output_field_class]
        return self.as_sql(compiler, connection)
