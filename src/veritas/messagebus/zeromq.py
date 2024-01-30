import zmq
import atexit
import logging
from zmq.log.handlers import PUBHandler
from loguru import logger
from threading import Thread
from queue import Queue


class Zeromq():

    def __init__(self, app=None, uuid=None, zeromq=None, use_queue=False):
        """init veritas messagesbus"""

        zeromq = {'protocol': 'tcp',
                  'host': '127.0.0.1',
                  'port': 12345}

        # general
        self.__app_name = app
        self.__uuid = uuid
        self.__queue = Queue()
        self.__use_queue = use_queue

        # zeromq
        self._zmq_filter = 'zeromq'

        # zeroMQ
        if zeromq:
            protocol = zeromq.get('protocol','tcp')
            host = zeromq.get('host','127.0.0.1')
            port = zeromq.get('port',12345)
            self._zmq_filter = zeromq.get('filter','zeromq')
            context = zmq.Context()
            socket = zmq.Context().socket(zmq.PUB)
            socket.connect(f'{protocol}://{host}:{port}')
            zmq_handler = PUBHandler(socket)
            zmq_handler.setFormatter(logging.Formatter("%(message)s"))
            # we are setting the loglevel to DEBUG because
            # otherwise it would depend on the log level 
            # whether a journal is written or not.
            # In our case, all messages will be sent to the 
            # journal if journal=True is set.

            logger.add(zmq_handler, 
                       filter=self._zeromq_filter,
                       serialize=True,
                       level="DEBUG")

    # internals

    def _zeromq_filter(self, record):
        return True
        # extra = record['extra']
        # if extra.get(self._zmq_filter, False):
        #     # set uuid so that the dispatcher can get the uuid of this app
        #     if self.__uuid:
        #         record['extra']['uuid'] = self.__uuid
        #     return True
        # return False
