import graphene

from graphene import ObjectType, Schema

from handlers.graphql.resolvers.subscription_utils import MakeSubscription, resolve_item_by_key, \
    MakeSubscriptionWithChangeType, resolve_all_items_changes
from handlers.graphql.types.input.createvm import CreateVM
from handlers.graphql.types.input.vm import VMMutation, VMStartMutation, VMShutdownMutation, VMRebootMutation, \
    VMPauseMutation, VMDeleteMutation
from handlers.graphql.types.playbook import GPlaybook, resolve_playbooks, resolve_playbook
from handlers.graphql.types.playbooklauncher import PlaybookLaunchMutation
from handlers.graphql.types.tasks.playbook import PlaybookTask, PlaybookTaskList
from playbookloader import PlaybookLoader
from xenadapter.disk import GISO, GVDI, ISO, VDI
from xenadapter.host import Host, GHost
from xenadapter.pool import GPool, Pool
from xenadapter.task import GTask
from xenadapter.template import Template, GTemplate
from xenadapter.sr import SR, GSR
from xenadapter.vm import VM, GVM
from xenadapter.network import Network, GNetwork

from handlers.graphql.types.input.template import TemplateMutation
from rethinkdb import RethinkDB
from tornado.options import options as opts
r = RethinkDB()

class Query(ObjectType):

    vms = graphene.List(GVM, required=True, resolver=VM.resolve_all(), description="All VMs available to user")
    vm = graphene.Field(GVM, required=True, uuid=graphene.ID(), resolver=VM.resolve_one())

    templates = graphene.List(GTemplate, required=True, resolver=Template.resolve_all(), description="All Templates available to user")
    template = graphene.Field(GVM, required=True, uuid=graphene.ID(), resolver=Template.resolve_one())

    hosts = graphene.List(GHost, required=True, resolver=Host.resolve_all())
    host = graphene.Field(GHost, required=True, uuid=graphene.ID(), resolver=Host.resolve_one())

    pools = graphene.List(GPool, required=True, resolver=Pool.resolve_all())
    pool = graphene.Field(GPool, required=True, uuid=graphene.ID(), resolver=Pool.resolve_one())

    networks = graphene.List(GNetwork, required=True, resolver=Network.resolve_all(), description="All Networks available to user")
    network = graphene.Field(GNetwork, required=True, uuid=graphene.ID(), resolver=Network.resolve_one(), description="Information about a single network")

    srs = graphene.List(GSR, required=True, resolver=SR.resolve_all(),
                             description="All Storage repositories available to user")
    sr = graphene.Field(GSR, required=True, uuid=graphene.ID(), resolver=SR.resolve_one(), description="Information about a single storage repository")


    vdis = graphene.List(GVDI, required=True, resolver=VDI.resolve_all(), description="All Virtual Disk Images (hard disks), available for user")
    vdi = graphene.Field(GVDI, required=True, uuid=graphene.ID(), resolver=VDI.resolve_one(), description="Information about a single virtual disk image (hard disk)")

    isos = graphene.List(GISO, required=True, resolver=ISO.resolve_all(), description="All ISO images available for user")
    iso = graphene.Field(GVDI, required=True, uuid=graphene.ID(), resolver=ISO.resolve_one(),
                         description="Information about a single ISO image")

    playbooks = graphene.List(GPlaybook,  required=True, resolver=resolve_playbooks, description="List of Ansible-powered playbooks")
    playbook = graphene.Field(GPlaybook, required=True, id=graphene.ID(), resolver=resolve_playbook,
                              description="Information about Ansible-powered playbook")


class Mutation(ObjectType):
    create_VM = CreateVM.Field(description="Create a new VM")
    template = TemplateMutation.Field(description="Edit template options")
    vm = VMMutation.Field(description="Edit VM options")
    vm_start = VMStartMutation.Field(description="Start VM")
    vm_shutdown = VMShutdownMutation.Field(description="Shut down VM")
    vm_reboot = VMRebootMutation.Field(description="Reboot VM")
    vm_pause = VMPauseMutation.Field(description="If VM is Running, pause VM. If Paused, unpause VM")
    playbook_launch = PlaybookLaunchMutation.Field(description="Launch an Ansible Playbook on specified VMs")
    vm_delete = VMDeleteMutation.Field(description="Delete a Halted VM")


class Subscription(ObjectType):
    '''
    All subscriptions must return  Observable
    '''
    vms = graphene.Field(MakeSubscriptionWithChangeType(GVM), required=True, description="Updates for all VMs")
    vm = graphene.Field(MakeSubscription(GVM), uuid=graphene.ID(), description="Updates for a particular VM")

    hosts = graphene.Field(MakeSubscriptionWithChangeType(GHost), required=True, description="Updates for all Hosts")
    host = graphene.Field(MakeSubscription(GHost), uuid=graphene.ID(), description="Updates for a particular Host")

    pools = graphene.Field(MakeSubscriptionWithChangeType(GPool), required=True, description="Updates for all pools available in VMEmperor")
    pool = graphene.Field(MakeSubscription(GPool), required=True, uuid=graphene.ID(), description="Updates for a particular Pool")

    task = graphene.Field(MakeSubscription(GTask),  uuid=graphene.ID(), description="Updates for a particular XenServer Task")

    playbook_task = graphene.Field(MakeSubscription(PlaybookTask), required=True, id=graphene.ID(), description="Updates for a particular Playbook installation Task")
    playbook_tasks = graphene.Field(MakeSubscriptionWithChangeType(PlaybookTask), required=True, description="Updates for all Playbook Tasks")


    def resolve_task(*args, **kwargs):
        return resolve_item_by_key(GTask, r.db(opts.database), 'tasks', key_name='uuid')(*args, **kwargs)

    def resolve_vms(*args, **kwargs):
        return resolve_all_items_changes(GVM, r.db(opts.database), 'vms')(*args, **kwargs)

    def resolve_vm(*args, **kwargs):
        return resolve_item_by_key(GVM, r.db(opts.database), 'vms', key_name='uuid')(*args, **kwargs)

    def resolve_hosts(*args, **kwargs):
        return resolve_all_items_changes(GHost, r.db(opts.database), 'hosts')(*args, **kwargs)

    def resolve_host(*args, **kwargs):
        return resolve_item_by_key(GHost, r.db(opts.database), 'hosts', key_name='uuid')(*args, **kwargs)

    def resolve_pools(*args, **kwargs):
        return resolve_all_items_changes(GPool,  r.db(opts.database), 'pools')(*args, **kwargs)

    def resolve_pool(*args, **kwargs):
        return resolve_item_by_key(GPool, r.db(opts.database), 'pools', key_name='uuid')(*args, **kwargs)

    def resolve_playbook_task(*args, **kwargs):
        return resolve_item_by_key(PlaybookTask, r.db(opts.database), 'tasks_playbooks', key_name='id')(*args, **kwargs)

    def resolve_playbook_tasks(*args, **kwargs):
        return resolve_all_items_changes(PlaybookTask, r.db(opts.database), 'tasks_playbooks')(*args, **kwargs)









schema = Schema(query=Query, mutation=Mutation, types=[GISO, GVDI], subscription=Subscription)