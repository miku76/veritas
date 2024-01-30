import os
import psycopg2
import psycopg2.extras
import uuid
from loguru import logger
from datetime import datetime, timezone

# veritas
from ..tools import tools
import veritas.store


class Journal(object):

    def __init__(self, database=None, uuid=None):

        self._uuid = uuid
        self._database = database
        self._conn = None
        self._cursor = None

        if not database:
            # read config (to connect to the database)
            self._journal_config = tools.get_miniapp_config(
                    appname='journal', 
                    app_path=os.path.abspath(os.path.dirname(__file__)), 
                    config_file='journal.yaml', 
                    subdir="lib")

            if self._journal_config:
                self._database = self._journal_config.get('database')
            else:
                logger.critical('unable to read config')
                return

        # connect to database
        self._connect_to_db()

    def new(self, app=None):
        """create new journal entry"""
        logger.debug('creating new journal entry')

        sql = """INSERT INTO journals(status)
             VALUES('active') RETURNING uuid;"""
        self._cursor.execute(sql, ())

        # get the generated uuid back
        value = self._cursor.fetchone()
        self._uuid = value.get('uuid')

        logger.debug(f'this journal entry has uuid {self._uuid}')

        # commit the changes to the database
        self._conn.commit()

        # return UUID back to user
        return self._uuid

    def close(self, uuid=None):
        """close existing journal entry"""

        if uuid:
            val = uuid
        elif self._uuid:
            val = self._uuid
        else:
            logger.error('nothing to close')
            return False

        logger.debug(f'closing journal {val}')

        closed = datetime.now(timezone.utc)

        sql = """UPDATE metadata SET status = %s, closed = %s WHERE uuid = %s"""
        self._cursor.execute(sql, ('closed', closed, val))

        # Commit the changes to the database
        self._conn.commit()
        # Close communication with the PostgreSQL database
        self._cursor.close()

        return True

    def message(self, app=None, message=''):
        """write message to journal messages"""

        sql = """INSERT INTO messages(uuid, app, message)
             VALUES(%s, %s, %s) RETURNING id;"""
        self._cursor.execute(sql, (self._uuid, app, message))

        # get the generated id back
        value = self._cursor.fetchone()
        id = value.get('id')
        logger.debug(f'this message entry has id {id}')

        # commit the changes to the database
        self._conn.commit()

        # return UUID back to user
        return id

    def activity(self, app=None, activity=''):
        """write activity to journal activities and return corresponding uuid of this activity"""

        sql = """INSERT INTO activities(journal_uuid, app, activity)
             VALUES(%s, %s, %s) RETURNING uuid;"""
        self._cursor.execute(sql, (self._uuid, app, activity))

        # get the generated (activity) uuid back
        value = self._cursor.fetchone()
        uuid = value.get('uuid')

        # commit the changes to the database
        self._conn.commit()

        # return UUID back to user
        return uuid

    def generate_uuid(self):
        """generate uuid"""

        # to convert it back use uuid = uuid.UUID(myuuidStr)
        return str(uuid.uuid4())

    def get_journals(self, opened_gt=None, closed_gt=None, status='active'):
        """get list of journals using time and status"""

        where = []
        # we add the 1=1 to get the ability to add the rest using AND ....
        sql = """SELECT uuid as journal_uuid, opened, closed, status """ \
              """FROM journals WHERE 1 = 1 """ \

        if opened_gt:
            sql += "AND opened > %s"
            where.append(opened_gt)

        if closed_gt:
            sql += "AND closed > %s"
            where.append(closed_gt)

        if status == 'active' or status == 'closed':
            sql += "AND status=%s"
            where.append(status)

        try:
            self._cursor.execute(sql, where)
            return self._cursor.fetchall()
        except Exception as exc:
            logger.error(f'failed to get data from journals {exc}')
            return False

    def get_active_journals(self, status='active'):
        sql = 'SELECT uuid as journal_uuid, opened, closed, status FROM journals WHERE status=%s'
        try:
            self._cursor.execute(sql, (status, ))
            return self._cursor.fetchall()
        except Exception as exc:
            logger.error(f'failed to get data from journals {exc}')
            return False

    def get_activities(self, uuid):
        if uuid == 'all_active':
            sql = """SELECT activities.uuid AS activity_uuid, activities.app, activities.activity, """ \
                  """activities.started, journals.status AS journal_status FROM journals """ \
                  """INNER JOIN activities ON journals.uuid = activities.journal_uuid AND journals.status = %s"""
            value = 'active'
        else:
            sql = """SELECT activities.uuid AS activity_uuid, activities.app, activities.activity, """ \
                  """activities.started, journals.status AS journal_status FROM journals """ \
                  """INNER JOIN activities ON journals.uuid = activities.journal_uuid AND activities.journal_uuid = %s"""
            value = uuid

        try:
            self._cursor.execute(sql, (value, ))
            return self._cursor.fetchall()
        except Exception as exc:
            logger.error(f'failed to get data from journals {exc}')
            return False

    def get_messages(self, uuid):

        sql = """SELECT id, uuid AS message_uuid, app, message FROM messages WHERE uuid=%s"""

        try:
            self._cursor.execute(sql, (uuid, ))
            return self._cursor.fetchall()
        except Exception as exc:
            logger.error(f'failed to get data from metadata {exc}')
            return False

    def get_logs(self, uuid, cols=['*']):

        columns = ','.join(cols)
        sql = f'SELECT {columns} FROM logs WHERE uuid=%s'

        try:
            self._cursor.execute(sql, (uuid, ))
            return self._cursor.fetchall()
        except Exception as exc:
            logger.error(f'failed to get data from metadata {exc}')
            return False


    # ---- internals ----

    def _connect_to_db(self):
        self._conn = psycopg2.connect(
                host=self._database['host'],
                database=self._database.get('database', 'journal'),
                user=self._database['user'],
                password=self._database['password'],
                port=self._database.get('port', 5432)
        )

        self._cursor = self._conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)

    # ---- decorators ----

def activity(journal, app, description):
    def inner_decorator(f):
        def wrapped(*args, **kwargs):
            new_journal = kwargs.get('new_journal', False)

            # if new journal delete store key (if present)
            if new_journal:
                veritas.store.delete(app='journal', key=journal)

            # get the uuid (if present) from the store
            journal_uuid = veritas.store.get(app='journal', key=journal)
            if journal_uuid:
                jrnl = Journal(uuid=journal_uuid)
                logger.debug(f'reusing journal_uuid={journal_uuid}')
            else:
                jrnl = Journal()
                journal_uuid = jrnl.new()
                veritas.store.set(app='journal', key=journal, value=journal_uuid)
                logger.debug(f'new journal_uuid={journal_uuid}')

            kwargs['journal'] = journal

            # create new activity
            uuid = jrnl.activity(app=app, activity=description)
            kwargs['uuid'] = uuid

            response = f(*args, **kwargs)
            return response
        return wrapped
    return inner_decorator

def new(f):
    def wrapped(*args, **kwargs):
        kwargs['new_journal'] = True
        response = f(*args, **kwargs)
        return response
    return wrapped
