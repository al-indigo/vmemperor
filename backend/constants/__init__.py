import threading
from typing import Dict

from playbookloader import PlaybookLoader

logger = None # global logger
POSTINST_ROUTE = r'/postinst'
AUTOINSTALL_ROUTE = r'/autoinstall'

first_batch_of_events = threading.Event()
need_exit = threading.Event()
xen_events_run = threading.Event()  # called by USR2 signal handler
load_playbooks = threading.Event()
URL = ""
ansible_pubkey = ""
playbooks = Dict[str, PlaybookLoader]
secrets = {}
tmpdir_path = '/tmp/vmemperor-'