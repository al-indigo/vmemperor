import graphene

from handlers.graphql.graphql_handler import ContextProtocol
from handlers.graphql.mutation_utils.mutationmethod import MutationMethod, MutationHelper
from handlers.graphql.resolvers import with_connection
from authentication import with_authentication, with_default_authentication, return_if_access_is_not_granted
from handlers.graphql.types.input.abstractvm import AbstractVMInput
from xenadapter.template import Template

class TemplateInput(AbstractVMInput):
    enabled = graphene.InputField(graphene.Boolean,
                                description="Should this template be enabled, i.e. used in VMEmperor by users")


class TemplateMutation(graphene.Mutation):
    granted = graphene.Field(graphene.Boolean, required=True, description="If access is granted")
    reason = graphene.Field(graphene.String, required=False, description="If access is not granted, return reason why")

    class Arguments:
        template = graphene.Argument(TemplateInput, description="Template to change", required=True)

    @staticmethod
    @with_default_authentication
    @with_connection
    def mutate(root, info, template : TemplateInput):
        ctx : ContextProtocol = info.context

        t = Template(xen=ctx.xen, ref=template.ref)

        mutations = [
            MutationMethod(func="enabled", access_action=None)
        ]

        helper = MutationHelper(mutations, ctx, t)
        granted, reason = helper.perform_mutations(template)
        return TemplateMutation(granted, reason)

class TemplateCloneMutation(graphene.Mutation):
    task_id = graphene.ID(required=False, description="clone task ID")
    granted = graphene.Boolean(required=True, description="Shows if access to clone is granted")
    reason = graphene.String()

    class Arguments:
        ref = graphene.ID(required=True)
        name_label = graphene.String(required=True, description="New name label")

    @staticmethod
    @with_authentication(access_class=Template, access_action=Template.Actions.clone)
    @return_if_access_is_not_granted([("Template", "ref", Template.Actions.clone)])
    def mutate(root, info, ref, name_label, Template : Template):
        return TemplateCloneMutation(granted=True, task_id=Template.async_clone(name_label))

class TemplateDestroyMutation(graphene.Mutation):
    task_id = graphene.ID(required=False, description="destroy task ID")
    granted = graphene.Boolean(required=True, description="Shows if access to destroy is granted")
    reason = graphene.String()

    class Arguments:
        ref = graphene.ID(required=True)

    @staticmethod
    @with_authentication(access_class=Template, access_action=Template.Actions.destroy)
    @return_if_access_is_not_granted([("Template", "ref", Template.Actions.destroy)])
    def mutate(root, info, ref, Template : Template):
        return TemplateDestroyMutation(granted=True, task_id=Template.async_destroy())
