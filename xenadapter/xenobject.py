import collections

import XenAPI
from xmlrpc.client import DateTime as xmldt
from datetime import datetime
import pytz
from exc import *
from authentication import BasicAuthenticator, AdministratorAuthenticator, NotAuthenticatedException, \
    with_default_authentication
from rethinkdb import RethinkDB

from handlers.graphql.types.gxenobjecttype import GXenObjectType
from handlers.graphql.utils.paging import do_paging

r = RethinkDB()
import logging
from typing import Optional, Type
from xenadapter.helpers import use_logger
import graphene


def dict_deep_convert(d):
    def convert_to_bool(v):
        if isinstance(v, str):
            if v.lower() == 'true':
                return True
            elif v.lower() == 'false':
                return False
        elif isinstance(v, dict):
            return dict_deep_convert(v)

        return v

    return {k: convert_to_bool(v) for k, v in d.items()}



class XenObjectMeta(type):

    def __getattr__(cls, name):
        if name[0] == '_':
            name = name[1:]

        if name.startswith('async_'):
            name = name[6:]
            from .task import Task
            def async_method(auth, *args, **kwargs):
                try:
                    async_method = getattr(auth.xen.api, 'Async')
                    api = getattr(async_method, cls.api_class)
                    attr = getattr(api, name)
                    ret = attr(*args, **kwargs)
                    t = Task(auth=auth, ref=ret)
                    t.manage_actions('run', user=auth.get_id())
                    return t.uuid

                except XenAPI.Failure as f:
                    raise XenAdapterAPIError(auth.xen.log, f"Failed to execute {cls.api_class}::{name} asynchronously", f.details)
            return async_method

        def method(auth, *args, **kwargs):
            if not hasattr(cls, 'api_class'):
                raise XenAdapterArgumentError(auth.xen.log, "api_class not specified for XenObject")

            api_class = getattr(cls, 'api_class')
            api = getattr(auth.xen.api, api_class)
            attr = getattr(api, name)

            try:
                ret = attr(*args, **kwargs)
                if isinstance(ret, dict):
                    ret = dict_deep_convert(ret)
                return ret
            except XenAPI.Failure as f:
                raise XenAdapterAPIError(auth.xen.log, f"Failed to execute static method {api_class}::{name}", f.details)
        return method


    def __init__(cls, what, bases=None, dict=None):
        from rethinkdb_tools.db_classes import create_db_for_me, create_acl_db_for_me
        from xenadapter.event_dispatcher import add_to_event_dispatcher
        super().__init__(what, bases, dict)
        logging.debug(f"Add XenObject class {cls}")
        add_to_event_dispatcher(cls)
        if 'db_table_name' in dict and dict['db_table_name']:
            if any((base.__name__ == 'ACLXenObject' for base in cls.mro())):
                create_acl_db_for_me(cls)
            else:
                create_db_for_me(cls)








class GXenObject(graphene.Interface):
    name_label = graphene.Field(graphene.String, required=True, description="a human-readable name")
    name_description = graphene.Field(graphene.String, required=True, description="a human-readable description")
    ref = graphene.Field(graphene.ID, required=True, description="Unique constant identifier/object reference")
    uuid = graphene.Field(graphene.ID, required=True, description="Unique session-dependent identifier/object reference")


class XenObject(metaclass=XenObjectMeta):
    api_class = None
    GraphQLType : GXenObjectType = None # Specify GraphQL type to access Rethinkdb cache
    REF_NULL = "OpaqueRef:NULL"
    db_table_name = ''
    """
    Database table name for a XenObject. Set by every XenObject class. Don't use field value from the class instance as individual instances may disable
    db caching for themselves by clearing this variable. Instead, use a value provided at class level.
    """
    EVENT_CLASSES=[]
    _db_created = False
    db = None
    FAIL_ON_NON_EXISTENCE = False # Fail if object does not exist in cache database. Usable if you know for sure that filter_record is always true


    def __str__(self):
        return f"<{self.__class__.__name__} \"{self.uuid}\">"

    def __repr__(self):
        return self.__str__()

    def __init__(self, auth : BasicAuthenticator,  uuid:str=None , ref : str =None):
        '''

        :param auth: authenticator
        either
        :param uuid: object uuid
        :param ref: object ref or object
        '''
        self.auth = auth
        # if not isinstance(xen, XenAdapter):
        #          raise AttributeError("No XenAdapter specified")
        self.log = self.auth.xen.log
        self.xen = self.auth.xen

        if uuid:
            if isinstance(uuid, str):
                self.uuid = uuid
            else:
                raise XenAdapterAPIError(auth.xen.log,
                                         f"Failed to initialize object of type {self.__class__.__name__}: invalid type of uuid. Expected: str, got {uuid.__class__.__name__}: {uuid}")
            try:
                getattr(self, 'ref') #uuid check
            except XenAPI.Failure as f:
                raise  XenAdapterAPIError(auth.xen.log,
                                          f"Failed to initialize object of type {self.__class__.__name__} with UUID {self.uuid}",f.details)
        elif ref:
            if isinstance(ref, str):
                self.ref = ref
            else:
                raise ValueError(
                                 f"XenObject:Failed to initialize object of type {self.__class__.__name__}"
                                 f": invalid type of ref. Expected: str, got {ref.__class__.__name__}")

        else:
            raise AttributeError("Not uuid nor ref not specified")



        self.access_prefix = 'vm-data/vmemperor/access'


    @classmethod
    def resolve_one(cls, field_name=None, index='uuid'):
        '''
        Use this method to resolve one XenObject that appears in tables as its uuid under its name
        :param field_name: root's field name to use (by default - this class' name)
        :return resolver for one object that either gets one named argument uuid or
        gets uuid from root's field named after XenObject class, e.g. for VM it will be
        root.VM
        :param index - table's index to use. OVERRIDE WITH CARE, internally we use refs as links between docs, so to use with linked field, call
        resolve_one(index='ref'). Default is resolving via uuid, as uuid is a primary key there
        :sa handlers/graphql/resolvers directory - they use index='ref' and load object classes in them to avoid circular dependencies
        '''

        if not field_name:
            field_name = cls.__name__
        if index not in ('uuid', 'ref'):
            raise ValueError("Index should be 'uuid' or 'ref'")

        from handlers.graphql.resolvers import with_connection

        @with_connection
        @with_default_authentication
        def resolver(root, info, **kwargs):

            if 'uuid' in kwargs:
                uuid = kwargs['uuid']
            else:
                uuid = getattr(root, field_name)
            try:
                if index == 'uuid':
                    obj = cls(uuid=uuid, auth=info.context.user_authenticator)
                else:
                    obj = cls(ref=uuid, auth=info.context.user_authenticator)
            except AttributeError:
                raise NotAuthenticatedException()

            obj.check_access(action=None)

            if index is None:
                record = cls.db.table(cls.db_table_name).get(uuid).run()
            else:
                record = cls.db.table(cls.db_table_name).get_all(uuid, index=index).coerce_to('array').run()
                if not record or not len(record):
                    return None
                else:
                    record = record[0]

            return cls.GraphQLType(**record)

        return resolver

    @classmethod
    def resolve_many(cls, field_name=None, index=None):
        '''
           Use this method to many one XenObject that appears in tables as their  uuids under its name
           :param cls: XenObject class
           :param graphql_type: graphene type
           :return resolver for many object that either gets one named argument uuids with list of uuids or
           gets uuids from root's field named after XenObject class in plural form , e.g. for VM it will be
           root.VMs

           If user does not have access for one of these objects, returns None in its place
           '''

        if not field_name:
            field_name = f'{cls.__name__}s'
        from handlers.graphql.resolvers import with_connection

        @with_connection
        @with_default_authentication
        def resolver(root, info, **kwargs):
            if 'uuids' in kwargs:
                uuids = kwargs['uuids']
            else:
                uuids = getattr(root, field_name)
            if not index:
                records = cls.db.table(cls.db_table_name).get_all(*uuids).coerce_to('array').run()
            else:
                records = cls.db.table(cls.db_table_name).get_all(*uuids, index=index).coerce_to('array').run()

            def create_graphql_type(record):
                try:
                    obj = cls(uuid=record['uuid'], auth=info.context.user_authenticator)
                except AttributeError:
                    raise NotAuthenticatedException()
                try:
                    obj.check_access(action=None)
                except:
                    return None
                return cls.GraphQLType(**record)

            return [create_graphql_type(record) for record in records]

        return resolver

    @classmethod
    def resolve_all(cls):
        '''
        Resolves all objects belonging to a user
        :param cls:

        :return:
        '''
        assert issubclass(cls.GraphQLType, GXenObjectType)
        from handlers.graphql.resolvers import with_connection
        @with_connection
        @with_default_authentication
        def resolver(root, info, **kwargs):
            '''

            :param root:
            :param info:
            :param kwargs: Optional keyword arguments for pagination: "page" and "page_size"

            :return:
            '''

            query =  cls.db.table(cls.db_table_name).coerce_to('array')

            if 'page' in kwargs:
                if 'page_size' in kwargs:
                    query = do_paging(query, kwargs['page'], kwargs['page_size'])
                else:
                    query = do_paging(query, kwargs['page'])

            records = query.run()
            return [cls.GraphQLType(**record) for record in records]

        return resolver


    def check_access(self,  action):
        return True

    def manage_actions(self, action,  revoke=False, user=None, group=None):
        pass

    @classmethod
    def process_event(cls,  auth, event, db, authenticator_name, ):
        '''
        Make changes to a RethinkDB-based cache, processing a XenServer event
        :param auth: auth object
        :param event: event dict
        :param db: rethinkdb DB
        :param authenticator_name: authenticator class name - used by access control
        :return: nothing
        '''
        from rethinkdb_tools.helper import CHECK_ER

        if event['class'] in cls.EVENT_CLASSES:
            if event['operation'] == 'del':
                CHECK_ER(db.table(cls.db_table_name).get_all(event['ref'], index='ref').delete().run())
                return

            record = event['snapshot']
            if not cls.filter_record(record):
                return

            if event['operation'] in ('mod', 'add'):
                new_rec = cls.process_record(auth, event['ref'], record)
                CHECK_ER(db.table(cls.db_table_name).insert(new_rec, conflict='update').run())

    @classmethod
    def create_db(cls, db, indexes=None):
        '''
        Creates a DB table named cls.db_table_name and specified indexes
        :param db:
        :param indexes:
        :return:
        '''
        if not cls.db_table_name:
            return
        def index_yielder():
            yield 'ref'
            if hasattr(indexes, '__iter__'):
                for y in indexes:
                    yield y


        if not cls.db:

            table_list = db.table_list().run()
            if cls.db_table_name not in table_list:
                db.table_create(cls.db_table_name, durability='soft', primary_key='uuid').run()
            index_list = db.table(cls.db_table_name).index_list().coerce_to('array').run()
            for index in index_yielder():
                if not index in index_list:
                    db.table(cls.db_table_name).index_create(index).run()
                    db.table(cls.db_table_name).index_wait(index).run()
                    db.table(cls.db_table_name).wait().run()

            cls.db = db




    @classmethod
    def process_record(cls, auth, ref, record) -> dict:
        '''
        Used by init_db. Should return dict with info that is supposed to be stored in DB
        :param auth: current authenticator
        :param record:
        :return: dict suitable for document-oriented DB
        : default: return record as-is, adding a 'ref' field with current opaque ref
        '''

        def get_real_value(k : str, v, current_type: Optional[Type[GXenObjectType]]):
            if current_type and not issubclass(current_type, GXenObjectType):
                raise ValueError(f"current_type should be a subclass of GXenObjectType. Got: {current_type}")
            if isinstance(v, xmldt):
                try:  # XenAPI standard time format. Z means strictly UTC
                    time = datetime.strptime(v.value, "%Y%m%dT%H:%M:%SZ")
                except ValueError:  # try Python time format
                    time = datetime.strptime(v.value, "%Y%m%dT%H:%M:%S")

                time = time.replace(tzinfo=pytz.utc)
                return time
            elif isinstance(v, collections.abc.Mapping):
                type_for_key = current_type.get_type(k) if current_type else None
                if type_for_key and not issubclass(type_for_key, GXenObjectType):
                    if hasattr(type_for_key, 'serialize'): # When we have a complex structure (Mapping) but Schema insists on plain type, e.g. JSONString or we substitute complex type with ID
                        return type_for_key.serialize(v)
                    else:
                        raise ValueError(f"type_for_key should be a subclass of GXenObjectType or contain serialize method. Got: {type_for_key}")
                return {key: get_real_value(key, value, type_for_key)
                        for key, value in v.items() if not type_for_key or key in type_for_key._meta.fields}
            else:
                if current_type:
                    return current_type.get_type(k).serialize(v)
                else:
                    return v

        if cls.GraphQLType:
            new_record = {k: get_real_value(k, v, cls.GraphQLType if cls.GraphQLType else None)
                          for k, v in record.items() if k in cls.GraphQLType._meta.fields}
        else:
            new_record = {k : get_real_value(k, v, None) for k,v in record.items()}

        new_record['ref'] = ref

        return new_record

    @classmethod
    def filter_record(cls, record):
        '''
        Returns true if record is suitable for a class
        :param record: record from get_all_records (pure XenAPI method)
        :return: true if record is suitable for this class
        '''
        return True

    @classmethod
    def get_all_records(cls, auth):
        method = getattr(cls, '_get_all_records')
        return {k: v for k, v in method(auth).items()
                if cls.filter_record(v)}

    def set_other_config(self, config):
        config = {k : str(v) for k,v in config.items()}
        self.__getattr__('set_other_config')(config)


    def __getattr__(self, name):
        api = getattr(self.xen.api, self.api_class)
        if name == 'uuid': #ленивое вычисление uuid по ref
            def fallback():
                self.uuid = api.get_uuid(self.ref)
                self.db_table_name = ""
            if self.db_table_name:
                try:
                    self.uuid = self.db.table(self.db_table_name).get_all(self.ref, index='ref').pluck('uuid').coerce_to('array').run()[0]['uuid']
                except IndexError as e: # this object is filtered out by DB cache (i.e. for VM can be filtered for being a control domain)
                    if not self.FAIL_ON_NON_EXISTENCE:
                        fallback()
                    else:
                        raise e
            else:
                self.uuid = api.get_uuid(self.ref)

            return self.uuid
        elif name == 'ref': #ленивое вычисление ref по uuid
            def fallback():
                self.ref = api.get_by_uuid(self.uuid)
                self.db_table_name = ""
            if self.db_table_name:
                try:
                    self.ref = self.db.table(self.db_table_name).get(self.uuid).pluck('ref').run()['ref']
                except r.ReqlNonExistenceError as e:
                    if not self.FAIL_ON_NON_EXISTENCE:
                        fallback()
                    else:
                        raise e
                if not self.ref:
                    fallback()
            else:
                self.ref = api.get_by_uuid(self.uuid)
            return self.ref
        if self.GraphQLType and self.db_table_name: #возьми из базы
            if name.startswith("get_"):
                field_name = name[4:]


                if field_name in self.GraphQLType._meta.fields:
                    try:
                        data = self.db.table(self.db_table_name).get(self.uuid).pluck(field_name).run()[field_name]
                        return lambda: data
                    except r.ReqlNonExistenceError as e:
                        pass
                    except KeyError: # Returning a db-only field (i.e. not that of XenAPI) that is not computed (yet or purposefully)
                        return lambda: None



        if name.startswith('async_'):
            async_ = True
            async_method = getattr(self.xen.api, 'Async')
            api = getattr(async_method, self.api_class)
            name = name[6:]
        else:
            async_ = False

        if name[0] == '_':
            name=name[1:]
        attr = getattr(api, name)
        def method (*args, **kwargs):
            try:
                ret = attr(self.ref, *args, **kwargs)
                if async_:
                    from .task import Task
                    t = Task(auth=self.auth, ref=ret)
                    t.manage_actions('run', user=self.auth.get_id())
                    return t.uuid

                elif isinstance(ret, dict):
                    ret = dict_deep_convert(ret)

                return ret
            except XenAPI.Failure as f:
                raise XenAdapterAPIError(self.log, f"Failed to execute {self.api_class}::{name} asynchronously", f.details)
        return method


class GAccessEntry(graphene.ObjectType):
    access = graphene.List(graphene.String, required=True)
    userid = graphene.String(required=True)

class GAclXenObject(GXenObject):
    access = graphene.List(GAccessEntry, required=True)


class ACLXenObject(XenObject):
    VMEMPEROR_ACCESS_PREFIX = 'vm-data/vmemperor/access'

    def get_access_path(self, username=None, is_group=False):
        '''
        used by manage_actions' default implementation
        :param username:
        :param is_group:
        :return:
        '''
        return f'{self.access_prefix}/{self.auth.class_name()}/{"groups" if is_group else "users"}/{username}'

    ALLOW_EMPTY_XENSTORE = False # Empty xenstore for some objects might treat them as for-all-by-default

    @classmethod
    def resolve_all(cls):
        '''
        Resolves all objects belonging to a user
        :param cls:
        :return:
        '''

        from handlers.graphql.resolvers import with_connection
        @with_connection
        def resolver(root, info, **kwargs):
            '''

            :param root:
            :param info:
            :param kwargs: Optional keyword arguments for pagination: "page" and "page_size"

            :return:
            '''
            from constants import user_table_ready

            auth = info.context.user_authenticator
            if isinstance(auth, AdministratorAuthenticator):  # return all
                query = \
                    cls.db.table(cls.db_table_name).coerce_to('array')
            else:
                user_table_ready.wait()
                user_id = auth.get_id()
                entities = (f'users/{user_id}', 'any', *(f'groups/{group_id}' for group_id in auth.get_user_groups()))
                query = \
                    cls.db.table(f'{cls.db_table_name}_user').get_all(*entities, index='userid'). \
                        pluck('uuid').coerce_to('array'). \
                        merge(cls.db.table(cls.db_table_name).get(r.row['uuid']).without('uuid'))

            if 'page' in kwargs:
                page_size = kwargs['page_size']
                query = query.slice((kwargs['page'] - 1) * page_size, page_size)

            records = query.run()
            return [cls.GraphQLType(**record) for record in records]

        return resolver
    @classmethod
    def process_record(cls, auth, ref, record):
        '''
        Adds an 'access' field to processed record containing access rights
        :param auth:
        :param ref:
        :param record:
        :return:
        '''
        new_rec = super().process_record(auth, ref, record)
        new_rec['access'] = cls.get_access_data(record, auth.__name__)
        return new_rec


    @use_logger
    def check_access(self,  action):
        '''
        Check if it's possible to do 'action' with specified Xen Object
        :param action: action to perform. If action is None, check for the fact that user can view this Xen object
        for 'Xen object'  these are

        - launch: can start/stop vm
        - destroy: can destroy vm
        - attach: can attach/detach disk/network interfaces
        :return: True if access granted, False if access denied, None if no info

        Implementation details:
        looks for self.db_table_name and then in db to table $(self.db_table_name)_access
        '''
        if self.auth.is_admin():
            return True # admin can do it all

        self.log.info(
            f"Checking {self.__class__.__name__} {self.uuid} rights for user {self.auth.get_id()}: action {action}")
        from rethinkdb.errors import ReqlNonExistenceError

        db = self.auth.xen.db
        try:
            access_info = db.table(self.db_table_name).get(self.uuid).pluck('access').run()
        except ReqlNonExistenceError:
            access_info = None
            
        access_info = access_info['access'] if access_info else None
        if not access_info:
            if self.ALLOW_EMPTY_XENSTORE:
                    return True
            raise XenAdapterUnauthorizedActionException(self.log,
                                                        f"Unauthorized attempt "
                                                        f"on object {self} (no info on access rights) by {self.auth.get_id()}: {'requested action {action}' if action else ''}")


        username = f'users/{self.auth.get_id()}'
        groupnames = [f'groups/{group}' for group in self.auth.get_user_groups()]
        for item in access_info:
            if ((action in item['access'] or 'all' in item['access'])\
                    or (action is None and len(item['access']) > 0))and\
                    (username == item['userid'] or (item['userid'].startswith('groups/') and item['userid'] in groupnames)):
                self.log.info(
                    f'User {self.auth.get_id()} is allowed to perform action {action} on {self.__class__.__name__} {self.uuid}')
                return True



        raise XenAdapterUnauthorizedActionException(self.log,
            f"Unauthorized attempt on object {self} by {self.auth.get_id()}{': requested action {action}' if action else ''}")

    @classmethod
    def get_access_data(cls, record, authenticator_name):
        '''
        Obtain access data from other_config
        :param record:
        :param authenticator_name:
        :return:
        '''
        other_config = record['other_config']

        def read_other_config_access_rights(other_config):
            from json import JSONDecodeError
            if 'vmemperor' in other_config:
                try:
                    emperor = json.loads(other_config['vmemperor'])
                except JSONDecodeError:
                    emperor = {}

                if 'access' in emperor:
                    if authenticator_name in emperor['access']:
                        auth_dict = emperor['access'][authenticator_name]
                        for k, v in auth_dict.items():
                            yield {'userid': k, 'access': v}
                        else:
                            if cls.ALLOW_EMPTY_XENSTORE:
                                yield {'userid': 'any', 'access': ['all']}

        return list(read_other_config_access_rights(other_config))

    def manage_actions(self, action,  revoke=False, user=None, group=None):
        '''
        Changes action list for a Xen object
        :param action:
        :param revoke:
        :param user: User ID as returned from authenticator.get_id()
        :param group:
        '''
        from json import JSONDecodeError
        if all((user,group)) or not any((user, group)):
            raise XenAdapterArgumentError(self.log, f'Specify user OR group for {self.__class__.__name__}::manage_actions')

        if user:
            real_name = f'users/{user}'
        elif group:
            real_name = f'groups/{group}'

        other_config = self.get_other_config()
        auth_name = self.auth.class_name()
        if 'vmemperor' not in other_config:
            emperor = {'access': {auth_name : {}}}
        else:

            try:
                emperor = json.loads(other_config['vmemperor'])
            except JSONDecodeError:
                emperor = {'access': {auth_name: {}}}

        if auth_name in emperor['access']:
            auth_list = emperor['access'][auth_name]
        else:
            auth_list = []
            emperor['access'][auth_name] = {}

        if real_name in auth_list and isinstance(auth_list[real_name], list) and action != 'all':
            action_list = auth_list[real_name]
        else:
            action_list = []


        if revoke:
            if action in action_list:
                action_list.remove(action)
        else:
            if action not in action_list:
                action_list.append(action)

        if action_list:
            emperor['access'][auth_name][real_name] = action_list
        else:
            del emperor['access'][auth_name][real_name]

        if not emperor['access'][auth_name]:
            del emperor['access'][auth_name]

        other_config['vmemperor'] = json.dumps(emperor)
        self.set_other_config(other_config)

