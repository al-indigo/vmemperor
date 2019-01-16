import threading
from typing import Dict

from playbookloader import PlaybookLoader
import xenadapter.disk, xenadapter.network, xenadapter.vm, xenadapter.template, xenadapter.task
logger = None # global logger
POSTINST_ROUTE = r'/postinst'


#These objects are thouse who have ACL enabled
objects = [xenadapter.vm.VM, xenadapter.network.Network, xenadapter.disk.VDI, xenadapter.template.Template, xenadapter.task.Task]

user_table_ready = threading.Event()
first_batch_of_events = threading.Event()
need_exit = threading.Event()
xen_events_run = threading.Event()  # called by USR2 signal handler
load_playbooks = threading.Event()
URL = ""
ansible_pubkey = ""
auth_class_name = ""
playbooks = Dict[str, PlaybookLoader]
secrets = {}