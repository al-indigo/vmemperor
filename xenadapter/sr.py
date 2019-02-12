import graphene

from handlers.graphql.resolvers.diskimage import resolve_vdis, vdiType
from xenadapter.pbd import GPBD, PBD
from xenadapter.xenobject import XenObject, GXenObject
from handlers.graphql.types.gxenobjecttype import GXenObjectType
class SRType(graphene.Enum):
    '''
    For more information on SR types, check out:
    https://docs.citrix.com/en-us/xenserver/current-release/storage/format.html

    '''
    LVM = 'lvm'
    EXT = 'ext'  # EXT3
    ISO = 'iso'
    LVMOFCOE = 'lvmofcoe'  # iSCSI FCoE
    LVMOISCSI = 'lvmoiscsi'  # LVM over iSCSI
    LVMOHBA = 'lvmohba'
    GFS2 = 'gfs2'
    NFS = 'nfs'
    CIFS = 'cifs'  # SMB
    NetApp = 'NetApp'
    EqualLogic = 'EqualLogic'




class GSR(GXenObjectType):
    class Meta:
        interfaces = (GXenObject,)
    PBDs = graphene.Field(graphene.List(GPBD),
                                 required=True, resolver=PBD.resolve_many(index='ref'),
                                 description="Connections to host. Usually one, unless the storage repository is shared: e.g. iSCSI")

    VDIs = graphene.Field(graphene.List(vdiType), resolver=resolve_vdis)
    content_type = graphene.Field(graphene.String, required=True)
    type = graphene.Field(graphene.String, required=True)
    physical_size = graphene.Field(graphene.Float, required=True, description="Physical size in kilobytes")
    virtual_allocation = graphene.Field(graphene.Float, required=True, description="Virtual allocation in kilobytes")
    is_tools_sr = graphene.Field(graphene.Boolean, required=True, description="This SR contains XenServer Tools")
    physical_utilisation = graphene.Field(graphene.Float, required=True, description="Physical utilisation in bytes")
    space_available = graphene.Field(graphene.Float, required=True, description="Available space in bytes")


class SR(XenObject):
    '''
    https://docs.citrix.com/en-us/xenserver/current-release/storage/manage.html
    '''
    api_class = "SR"
    db_table_name = "srs"
    EVENT_CLASSES=["sr"]
    GraphQLType = GSR

    @classmethod
    def process_record(cls, auth, ref, record):

        record['space_available'] = int(record['physical_size']) - int(record['physical_utilisation'])
        return super().process_record(auth, ref, record)



