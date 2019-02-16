import copy
import queue
from collections import OrderedDict
from threading import Thread

from connman import ReDBConnection
from loggable import Loggable

from tornado.options import options as opts

from xenadapter import XenAdapterPool
from xenadapter.event_dispatcher import EVENT_DISPATCHER
import json
from datetimeencoder import DateTimeEncoder

def print_event(event):
    ordered = OrderedDict(event)
    ordered.move_to_end("operation", last=False)
    ordered.move_to_end("class", last=False)
    return ordered

class EventQueue(queue.Queue, Loggable):
    def __init__(self, authenticator, db,  num_workers=16):
        super().__init__()
        super().init_log()
        self.db = db
        self.authenticator= authenticator
        self.log.debug(f"Processing Xen events using {num_workers} workers")
        self.log.debug(f"Event dispatcher configuration: {EVENT_DISPATCHER}")

        for i in range(num_workers):
            t = Thread(target=self.process_events, args=[copy.copy(self.authenticator)])
            t.daemon = True
            t.start()


    def __repr__(self):
        return 'EventQueue'

    def process_events(self, authenticator):
        with ReDBConnection().get_connection():
            authenticator.xen = XenAdapterPool().get()
            while True:
                event = self.get()

                if event['class'] == 'message':
                    self.task_done()
                    continue  # temporary hardcode to fasten event handling
                log_this = opts.log_events and event['class'] in opts.log_events.split(',') \
                           or not opts.log_events

                if not event['class'] in EVENT_DISPATCHER:
                    if log_this:
                        self.log.debug(
                            f"Ignored Event: {json.dumps(print_event(event), cls=DateTimeEncoder)}")
                    self.task_done()
                    continue

                if log_this:
                    self.log.debug(f"Event: {json.dumps(print_event(event), cls=DateTimeEncoder)}")

                for ev_class in EVENT_DISPATCHER[event['class']]:
                    try:

                        ev_class.process_event(authenticator, event, self.db, self.authenticator.__name__)
                    except Exception as e:
                        self.log.error(f"Failed to process event by {ev_class.__name__}: {e}")
                self.task_done()
