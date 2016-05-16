
from django.db.models import Func, fields


class ReversionCast(Func):
    """
    Coerce an expression to a new field type.
    """
    function = 'CAST'
    template = '%(function)s(%(expressions)s AS %(db_type)s)'

    mysql_types = {
        fields.CharField: 'char',
        fields.IntegerField: 'signed integer',
        fields.FloatField: 'signed',
    }

    def __init__(self, expression, output_field):
        super(ReversionCast, self).__init__(expression, output_field=output_field)

    def as_sql(self, compiler, connection, **extra_context):
        if 'db_type' not in self.extra:
            self.extra['db_type'] = self._output_field.db_type(connection)
        return super(ReversionCast, self).as_sql(compiler, connection, **extra_context)

    def as_mysql(self, compiler, connection):
        output_field_class = type(self._output_field)
        if output_field_class in self.mysql_types:
            self.extra['db_type'] = self.mysql_types[output_field_class]
        return self.as_sql(compiler, connection)

    def as_postgresql(self, compiler, connection):
        # CAST would be valid too, but the :: shortcut syntax is more readable.
        return self.as_sql(compiler, connection, template='%(expressions)s::%(db_type)s')
