from loguru import logger
import functools
import inspect
import sqlite3
import os
import json


class Scheduler(object):

    def __init__(self, database=None):
        self._con = None
        self._cursor = None
        self._open_database(database)

    def register_task(self, filename, module, function, schedule, args):
        # if args == "null":
        #     args = "None"
        filename = os.path.abspath(filename)
        file_in_db = self.get_task_by_filename(filename)
        if file_in_db:
            for job in file_in_db:
                if job.get('module') == module and \
                  job.get('function') == function and \
                  job.get('schedule') == schedule and \
                  job.get('args') == str(args):
                    logger.info(f'this job is already registered {filename}')
                    return
        sql = """INSERT INTO jobs(filename, module, function, args, schedule)
                 VALUES('%s','%s' ,'%s' , '%s', '%s');""" % (filename, module,function, args, schedule)
        success = self._cursor.execute(sql)
        self._con.commit()
        if success:
            logger.debug(f'registered job {filename}/{module}/{function}')
        else:
            logger.error(f'failed to register job {filename}/{module}/{function}')
        return success

    def reschedule_task(self, id, schedule):
        sql = """UPDATE jobs SET schedule = '%s' WHERE id = '%s'""" % (schedule, id)
        success = self._cursor.execute(sql)
        self._con.commit()
        if success:
            logger.debug(f'reschedule job {id} to {schedule}')
        else:
            logger.error(f'failed to reschedule job {id}')
        return success

    def deregister_task(self, id):
        sql = """DELETE FROM jobs WHERE id = '%s'""" % id
        success = self._cursor.execute(sql)
        self._con.commit()
        logger.debug(f'deregistered job {id} ({success})')
        return success

    def deregister_all_tasks(self):
        sql = """DELETE FROM jobs"""
        success = self._cursor.execute(sql)
        self._con.commit()
        logger.debug(f'deregistered all job jobs ({success})')
        return success

    def get_all_tasks(self):
        sql = """SELECT id, filename, module, function, args, schedule FROM jobs"""
        return self._return_list_of_dicts(sql)

    def get_all_runs(self):
        sql = """SELECT id, job_id, started, finished, result, error FROM runs"""
        return self._return_list_of_dicts(sql)

    def get_failed_runs(self):
        sql = """SELECT id, job_id, started, finished, result, error FROM runs WHERE result = 0"""
        return self._return_list_of_dicts(sql)

    def get_task_by_filename(self, filename):
        sql = """SELECT id, filename, module, function, args, schedule 
                 FROM jobs WHERE filename = '%s'""" % filename
        return self._return_list_of_dicts(sql)

    def add_run(self, job_id, started, started_int, finished, finished_int, result, error):
        if result:
            result = 1
        else:
            result = 0
        error = error.replace("'","''")
        sql = """INSERT INTO runs(job_id, started, started_int, finished, finished_int, result, error)
                 VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s')
              """ % (job_id, started, started_int, finished, finished_int, result, error)
        success = self._cursor.execute(sql)
        self._con.commit()
        if success:
            logger.debug(f'added job result of job {job_id}')
        else:
            logger.error(f'failed to result of job {job_id}')
        return success

    #
    # internals
    #

    def _open_database(self, database=None):
        if not database:
            directory = '/'.join(__file__.rsplit('/')[:-1])
            database = f'{directory}/cron_db.sq3'

        if os.path.isfile(database):
            logger.debug(f'open database {database}')
            self._con = sqlite3.connect(database)
            self._cursor = self._con.cursor()
        else:
            logger.debug(f'create database {database}')
            self._con = sqlite3.connect(database)
            self._cursor = self._con.cursor()
            self._cursor.execute("""
                CREATE TABLE jobs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    module TEXT,
                    function TEXT,
                    args TEXT,
                    schedule TEXT)""")
            self._cursor.execute("""
                CREATE TABLE runs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER,
                    started datetime,
                    started_int INT,
                    finished datetime,
                    finished_int INT,
                    result BOOLEAN NOT NULL CHECK (result IN (0, 1)),
                    error TEXT)""")
            self._con.commit()

    def _return_list_of_dicts(self, select_query):
        try:
            self._con.row_factory = sqlite3.Row
            data = self._con.execute(select_query).fetchall()
            return [{k: item[k] for k in item.keys()} for item in data]
        except Exception as exc:
            logger.error(f'failed to get data; got exception {exc}')
            return []

def schedule(schedule, args=None, run=False):
    def decorator_on(func):
        @functools.wraps(func)
        def wrapper_on_day(*wrapper_args, **wrapper_kwargs):
            # if no_decorator is True we run the function
            # in this case the scheduler has called it
            if wrapper_kwargs.pop("no_decorator", False) is True or run:
                if args:
                    if isinstance(args, dict):
                        wrapper_kwargs.update(args)
                return func(*wrapper_args, **wrapper_kwargs)
            module = func.__module__
            name = func.__name__
            scheduler = Scheduler()
            args_json = json.dumps(args)
            scheduler.register_task(inspect.getfile(func), module, name, schedule, args_json)
            return None
        return wrapper_on_day
    return decorator_on
