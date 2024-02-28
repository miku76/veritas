from loguru import logger
import functools
import inspect
import sqlite3
import os
import json


class Scheduler(object):
    """Class to manage the scheduling of tasks

    Parameters
    ----------
    database : dict
        database configuration
    """
    def __init__(self, database:dict=None):
        self._con = None
        self._cursor = None
        self._open_database(database)

    def register_task(self, filename:str, module:str, function:callable, schedule:str, args:str) -> bool:
        """register task

        Parameters
        ----------
        filename : str
            filename of the task
        module : str
            module of the task
        function : callable
            function of the task
        schedule : str
            schedule of the task
        args : str
            arguments of the task

        Returns
        -------
        resposne : bool
            true if the task was registered
        """        
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
        response = self._cursor.execute(sql)
        self._con.commit()
        if response:
            logger.debug(f'registered job {filename}/{module}/{function}')
        else:
            logger.error(f'failed to register job {filename}/{module}/{function}')
        return response

    def reschedule_task(self, id:str, schedule:str) -> bool:
        """reschedule task

        Parameters
        ----------
        id : str
            if of the task
        schedule : str
            new schedule of the task

        Returns
        -------
        resposne : bool
            true if the task was rescheduled
        """        
        sql = """UPDATE jobs SET schedule = '%s' WHERE id = '%s'""" % (schedule, id)
        response = self._cursor.execute(sql)
        self._con.commit()
        if response:
            logger.debug(f'reschedule job {id} to {schedule}')
        else:
            logger.error(f'failed to reschedule job {id}')
        return response

    def deregister_task(self, id:str) -> bool:
        """deregister task

        Parameters
        ----------
        id : str
            id of the task

        Returns
        -------
        response : bool
            true if the task was deregistered
        """        
        sql = """DELETE FROM jobs WHERE id = '%s'""" % id
        response = self._cursor.execute(sql)
        self._con.commit()
        logger.debug(f'deregistered job {id} ({response})')
        return response

    def deregister_all_tasks(self) -> bool:
        """deregister all tasks

        Returns
        -------
        resposne : bool
            true if all tasks were deregistered
        """        
        sql = """DELETE FROM jobs"""
        resposne = self._cursor.execute(sql)
        self._con.commit()
        logger.debug(f'deregistered all job jobs ({resposne})')
        return resposne

    def get_all_tasks(self) -> list:
        """get all tasks

        Returns
        -------
        tasks : list
            list of all tasks
        """        
        sql = """SELECT id, filename, module, function, args, schedule FROM jobs"""
        return self._return_list_of_dicts(sql)

    def get_all_runs(self) -> list:
        """get all runs

        Returns
        -------
        runs : list
            list of all runs
        """        
        sql = """SELECT id, job_id, started, finished, result, error FROM runs"""
        return self._return_list_of_dicts(sql)

    def get_failed_runs(self) -> list:
        """get failed runs

        Returns
        -------
        runs : list
            list of all failed runs
        """        
        sql = """SELECT id, job_id, started, finished, result, error FROM runs WHERE result = 0"""
        return self._return_list_of_dicts(sql)

    def get_task_by_filename(self, filename:str) -> list:
        """get task by filename

        Parameters
        ----------
        filename : str
            filename of the task

        Returns
        -------
        task : list
            list of task
        """        
        sql = """SELECT id, filename, module, function, args, schedule 
                 FROM jobs WHERE filename = '%s'""" % filename
        return self._return_list_of_dicts(sql)

    def add_run(self, job_id:str, started:str, started_int:int, 
                finished:str, finished_int:int, result:str, error:str) -> bool:
        """add run to database

        Parameters
        ----------
        job_id : str
            job id
        started : str
            when the job started
        started_int : int
            when the job started as int
        finished : str
            when the job finished
        finished_int : int
            when the job finished as int
        result : str
            result of the job
        error : str
            error of the job

        Returns
        -------
        response _ bool
            true if the run was added
        """                
        if result:
            result = 1
        else:
            result = 0
        error = error.replace("'","''")
        sql = """INSERT INTO runs(job_id, started, started_int, finished, finished_int, result, error)
                 VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s')
              """ % (job_id, started, started_int, finished, finished_int, result, error)
        response = self._cursor.execute(sql)
        self._con.commit()
        if response:
            logger.debug(f'added job result of job {job_id}')
        else:
            logger.error(f'failed to result of job {job_id}')
        return response

    #
    # internals
    #

    def _open_database(self, database:dict=None) -> None:
        """open database connection

        Parameters
        ----------
        database : dict, optional
            database configuration, by default None
        """        
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

    def _return_list_of_dicts(self, select_query:str) -> list:
        """helper function to execute query and return a list of dicts

        Parameters
        ----------
        select_query : str
            query to execute

        Returns
        -------
        resposne : list
            list of dicts
        """        
        try:
            self._con.row_factory = sqlite3.Row
            data = self._con.execute(select_query).fetchall()
            return [{k: item[k] for k in item.keys()} for item in data]
        except Exception as exc:
            logger.error(f'failed to get data; got exception {exc}')
            return []

def schedule(schedule:str, args:list=None, run:bool=False):
    """decorator to schedule a function

    Parameters
    ----------
    schedule : str
        when to run the function
    args : list, optional
        arguments of the method, by default None
    run : bool, optional
        should the task be run instead of schedule, by default False
    """
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
