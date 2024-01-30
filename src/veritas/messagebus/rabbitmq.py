import pika
import sys
import json
from datetime import date, datetime, timedelta
from loguru import logger


class Rabbitmq():

    def __init__(self, app=None, rabbitmq=None, uuid=None):
        """init veritas messagesbus"""

        # general
        self._app = app
        self._uuid = uuid

        host = rabbitmq.get('host', '127.0.0.1')
        port = rabbitmq.get('port', '5672')

        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=host))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(exchange='veritas_logs', exchange_type='topic')

    def write(self, message):
        record = message.record
        response = {
            'app': self._app,
            'elapsed': str(record['elapsed']),
            'time': str(record['time']),
            'level': {'no': record['level'].no, 'name': record['level'].name},
            'message': record['message'],
            'file': {'name': record['file'].name, 'path': record['file'].path},
            'line': record['line'],
            'module': record['module'],
            'name': record['name'],
            'function': record['function'],
            'process': {'id': record['process'].id, 'name': record['process'].name},
            'thread': {'id': record['thread'].id, 'name': record['thread'].name},
            'exception': record['exception'],
            'extra': record['extra']
        }
        if self._uuid:
            response.update({'uuid': self._uuid})

        level = record["level"].name.lower()
        routing_key = f'{self._app}.{level}'
        self._channel.basic_publish(
            exchange='veritas_logs', routing_key=routing_key, body=json.dumps(response))
