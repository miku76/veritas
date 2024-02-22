import psycopg2
import psycopg2.extras
import atexit
from loguru import logger
from threading import Thread
from queue import Queue


class Database():

    def __init__(self, app=None, uuid=None, database=None, use_queue=False):
        """init veritas database messagesbus"""

        # general
        self.__app_name = app
        self.__uuid = uuid
        self.__queue = Queue()
        self.__use_queue = use_queue

        # database
        self._database = None
        self._db_connection = None
        self._cursor = None
        
        self._database = database
        self._connect_to_db()
        if use_queue:
            # call exit handler to empty queue
            atexit.register(self._empty_queue)

            self._consumer = Thread(target=self._dequeue,
                                    args=(self.__queue,))
            self._consumer.daemon = True
            self._consumer.start()

    def write(self, message):
        """write record either to queue or to database"""
        if self.__use_queue:
            record = message.record
            self.__queue.put(record)
        else:
            self._message_to_database(message)        

    def _message_to_database(self, message):
        record = message.record
        rcd_vals = {
            'record': message.record,
            'levelno': record['level'].no,
            'levelname': record['level'].name,
            'message': record['message'],
            'filename': record['file'].name,
            'pathname ': record['file'].path,
            'lineno': record['line'],
            'module': record['module'],
            'function': record['function'],
            'processname': record['process'].name,
            'threadname': record['thread'].name,
            'exception': record['exception'],
            'extra': record['extra']
        }

        columns = rcd_vals.keys()
        values = [rcd_vals[column] for column in columns]
        sql = 'INSERT INTO log (%s) values %s'
        try:
            self._cursor.execute(sql, (AsIs(','.join(columns)), tuple(values)))
        except Exception as exc:
            logger.error(f'could not add data to logs {rcd_vals}')
        finally:
            self._db_connection.commit()

    # internals

    def _connect_to_db(self):
        """connet to database"""
        self._db_connection = psycopg2.connect(
                host=self._database['host'],
                database=self._database['database'],
                user=self._database['user'],
                password=self._database['password'],
                port=self._database['port'])

        self._cursor = self._db_connection.cursor()

    def _dequeue(self, queue):
        while True:
            record = queue.get()
            self._message_to_database(record)
            # check for stop
            if record is None:
                break
    
    def _empty_queue(self):
        while self.__queue.qsize() > 0:
            record = queue.get()
            self._message_to_database(record)
