import os
import psycopg2
from importlib.metadata import version
from loguru import logger
from ..tools import tools


__version__ = version("veritas")

def set(app, key, value, database=None):
    """add new entry in out store"""

    if not database:
        store_config = tools.get_miniapp_config(
                appname='store', 
                app_path=os.path.abspath(os.path.dirname(__file__)), 
                config_file='store.yaml', 
                subdir="lib")
        database = store_config.get('database')

    conn, cursor = _connect_to_db(database)

    postgres_insert_query = """INSERT INTO store (APP, KEY, VALUE) VALUES (%s,%s,%s)"""
    record_to_insert = (app, key, value)
    try:
        cursor.execute(postgres_insert_query, record_to_insert)
        # commit the changes to the database
        conn.commit()
    except (Exception, psycopg2.Error) as error:
        logger.error(f'failed to add data to store {error}')
        return False

    return True

def get(app, key, database=None):
    """get value from store"""

    if not database:
        store_config = tools.get_miniapp_config(
                appname='store', 
                app_path=os.path.abspath(os.path.dirname(__file__)), 
                config_file='store.yaml', 
                subdir="lib")
        database = store_config.get('database')

    conn, cursor = _connect_to_db(database)

    sql = 'SELECT value FROM store WHERE APP=%s and KEY=%s'
    try:
        cursor.execute(sql, (app, key))
        value = cursor.fetchall()
        if len(value):
            return value[0][0]
        else:
            return None
    except Exception as exc:
        logger.error(f'failed to get data from store {exc}')
        return False

def delete(app, key, database=None):
    """delete key/value pair in store"""
    if not database:
        store_config = tools.get_miniapp_config(
                appname='store', 
                app_path=os.path.abspath(os.path.dirname(__file__)), 
                config_file='store.yaml', 
                subdir="lib")
        database = store_config.get('database')

    conn, cursor = _connect_to_db(database)

    sql = 'DELETE FROM store WHERE APP=%s and KEY=%s'
    try:
        logger.debug(f'delete store entry app={app} key={key}')
        cursor.execute(sql, (app, key))
        # commit the changes to the database
        conn.commit()
    except Exception as exc:
        logger.error(f'failed to delete {app}/{key} from store {exc}')
        return False

def _connect_to_db(database):
    conn = psycopg2.connect(
            host=database.get('host','127.0.0.1'),
            database=database.get('database', 'journal'),
            user=database['user'],
            password=database['password'],
            port=database.get('port', 5432)
    )

    cursor = conn.cursor()
    return conn, cursor