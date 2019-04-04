import uuid
from typing import Sequence

import graphene

from connman import ReDBConnection
from input.vm import AutoInstall, VMInput
from utils.check_user_input import check_user_input
from xenadapter.vdi import VDI
from xenadapter.network import Network

from handlers.graphql.graphql_handler import ContextProtocol
from handlers.graphql.resolvers import with_connection
from authentication import with_authentication, return_if_access_is_not_granted
from handlers.graphql.types.input.createvdi import NewVDI
from handlers.graphql.types.tasks.createvm import CreateVMTask, CreateVMTaskList
from xenadapter.sr import SR
from xenadapter.template import Template
import tornado.ioloop
from xentools.xenadapterpool import XenAdapterPool
from handlers.graphql.types.vm import SetDisksEntry


def createvm(ctx : ContextProtocol, task_id : str, user: str,
             vm_options: VMInput,
             template: str, disks : Sequence[NewVDI], network : str, iso : str =None, install_params : AutoInstall =None,
             Template: Template = None, VDI: VDI = None, Network: Network = None):


    with ReDBConnection().get_connection():
        xen = XenAdapterPool().get()
        task_list = CreateVMTaskList()
        try:
            if not check_user_input(user, ctx.user_authenticator):
                task_list.upsert_task(user, CreateVMTask(id=task_id, ref=None, state='error', message=f'permission denied'))
                return
            def disk_entries():
                for entry in disks:
                    sr = SR(xen, entry.SR)
                    if sr.check_access(ctx.user_authenticator, SR.Actions.vdi_create):
                        yield SetDisksEntry(SR=sr, size=entry.size)


            task_list.upsert_task(user, CreateVMTask(id=task_id, ref=template, state='cloning',
                                                     message=f'cloning template'))
            # TODO: Check quotas here as well as in create vdi method
            provision_config = list(disk_entries())

            vm = Template.clone_as_vm(f"New VM for {user}")

            task_list.upsert_task(user, CreateVMTask(id=task_id, ref=vm.ref, state='cloned', message=f'cloned from {Template}'))

            vm.create(
                insert_log_entry=lambda ref, state, message: task_list.upsert_task(user, CreateVMTask(id=task_id, ref=ref, state=state, message=message)),
                provision_config=provision_config,
                net=Network,
                template=Template,
                iso=VDI,
                install_params=install_params,
                user=user if not user == "root" else None,
                options=vm_options
        )
        finally:
            XenAdapterPool().unget(xen)


class CreateVM(graphene.Mutation):
    task_id = graphene.Field(graphene.ID, required=False, description="Installation task ID")
    granted = graphene.Field(graphene.Boolean, required=True)
    reason = graphene.Field(graphene.String)

    class Arguments:
        vm_options = graphene.Argument(VMInput, required=True, description="Basic VM options. Leave fields empty to use Template options")
        template = graphene.Argument(graphene.ID, required=True, description="Template ID")
        disks = graphene.Argument(graphene.List(NewVDI))
        network = graphene.Argument(graphene.ID, description="Network ID to connect to")
        iso = graphene.Argument(graphene.ID, description="ISO image mounted if conf parameter is null")
        install_params = graphene.Argument(AutoInstall, description="Automatic installation parameters, the installation is done via internet. Only available when template.os_kind is not empty")
        user = graphene.Argument(graphene.String, description="User or group we should create VM as")


    @staticmethod
    @with_connection
    @with_authentication(access_class=Template, access_action=Template.Actions.clone, id_field="template")
    @with_authentication(access_class=VDI, access_action=VDI.Actions.plug, id_field="iso")
    @with_authentication(access_class=Network, access_action=Network.Actions.attaching, id_field="network")
    @return_if_access_is_not_granted([("Template", "template", Template.Actions.clone),
                                      ("VDI", "iso", VDI.Actions.plug),
                                      ("Network", "network", Network.Actions.attaching)])
    def mutate(root, info,  *args, **kwargs):
        task_id  = str(uuid.uuid4())
        ctx :ContextProtocol = info.context
        if 'VDI' in kwargs and kwargs['VDI'].type != 'iso':
            raise TypeError("VDI argument is not ISO image")
        user = kwargs.get('user')
        if user and not user == 'root' and not user == 'any' and not user.startswith('users/') and not user.startswith('groups/'):
            return CreateVM(granted=False, reason="Incorrect 'user' field value")
        if not user:
            if ctx.user_authenticator.is_admin():
                user = ctx.user_authenticator.get_id()
            else:
                user = 'users/' + ctx.user_authenticator.get_id()

            kwargs['user'] = user

        tornado.ioloop.IOLoop.current().run_in_executor(ctx.executor,
        lambda: createvm(ctx, task_id, *args, **kwargs))
        return CreateVM(task_id=task_id, granted=True)
