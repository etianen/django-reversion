"""
Print the query log to standard out.

Useful for optimizing database calls.

Insipired by the method at: <http://www.djangosnippets.org/snippets/344/>
"""


from django import template
from django.conf import settings
from django.db import connection


class QueryLogMiddleware:

    def process_response (self, request, response):
        if settings.DEBUG:
            queries = {}
            for query in connection.queries:
                sql = query["sql"]
                queries.setdefault(sql, 0)
                queries[sql] += 1
            duplicates = sum([count - 1 for count in queries.values()])
            print "------------------------------------------------------"
            print "Total Queries:     %s" % len(queries)
            print "Duplicate Queries: %s" % duplicates
            print
            for query, count in queries.items():
                print "%s x %s" % (count, query)
            print "------------------------------------------------------"
        return response

