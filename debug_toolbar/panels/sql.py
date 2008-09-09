from debug_toolbar.panels import DebugPanel
from django.db import connection
from django.db.backends import util
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.utils import simplejson
from time import time

class DatabaseStatTracker(util.CursorDebugWrapper):
    """Replacement for CursorDebugWrapper which stores additional information
    in `connection.queries`."""
    def execute(self, sql, params=()):
        start = time()
        try:
            return self.cursor.execute(sql, params)
        finally:
            stop = time()
            # We keep `sql` to maintain backwards compatibility
            self.db.queries.append({
                'sql': self.db.ops.last_executed_query(self.cursor, sql, params),
                'time': stop - start,
                'raw_sql': sql,
                'params': params,
            })

util.CursorDebugWrapper = DatabaseStatTracker
    
class SQLDebugPanel(DebugPanel):
    """
    Panel that displays information about the SQL queries run while processing the request.
    """
    name = 'SQL'
    
    def process_request(self, request):
        action = request.GET.get('op')
        if action == 'explain':
            # XXX: loop through each sql statement to output explain?
            sql = request.GET.get('sql', '').split(';')[0]
            if sql.lower().startswith('select'):
                if 'params' in request.GET:
                    params = simplejson.loads(request.GET['params'])
                else:
                    params = []
                cursor = connection.cursor()
                cursor.execute("EXPLAIN %s" % (sql,), params)
                response = cursor.fetchall()
                cursor.close()
                context = {'explain': response, 'sql': sql, 'params': params}
                return render_to_response('debug_toolbar/panels/sql_explain.html', context)
            else:
                return HttpResponse('Invalid SQL', mimetype="text/plain", status_code=403)
    
    def title(self):
        total_time = sum(map(lambda q: float(q['time'])*1000, connection.queries))
        return 'SQL: %.2fms (%d queries)' % (total_time, len(connection.queries))

    def url(self):
        return ''

    def content(self):
        queries = [(q['time'], q['sql'], q['raw_sql'], simplejson.dumps(q['params'])) for q in sorted(connection.queries, key=lambda x: x['time'])[::-1]]
        context = {'queries': queries}
        return render_to_string('debug_toolbar/panels/sql.html', context)