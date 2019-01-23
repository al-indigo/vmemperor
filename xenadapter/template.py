from .abstractvm import AbstractVM
from exc import *
import XenAPI
from .vm import VM
from . import use_logger


class Template(AbstractVM):
    ALLOW_EMPTY_XENSTORE = True
    VMEMPEROR_TEMPLATE_PREFIX = 'vm/data/vmemperor/template'
    db_table_name = 'tmpls'

    @classmethod
    def filter_record(cls, record):
        return record['is_a_template']

    @classmethod
    def is_hidden(self, record):
        return 'vmemperor' not in record['tags']

    @classmethod
    def process_record(self, auth, ref, record):
        '''
        Contary to parent method, this method can return many records as one XenServer template may convert to many
        VMEmperor templates
        :param auth:
        :param ref:
        :param record:
        :return:
        '''
        record = super().process_record(auth, ref, record)

        keys = ['hvm', 'name_label', 'uuid', 'ref']
        new_rec = {k: v for k, v in record.items() if k in keys}
        if record['HVM_boot_policy'] == '':
            new_rec['hvm'] = False
        else:
            new_rec['hvm'] = True

        #read xenstore data
        xenstore_data = record['xenstore_data']
        if not self.VMEMPEROR_TEMPLATE_PREFIX in xenstore_data:
            # TODO: Try to detect os_kind from other_config
            if new_rec['hvm'] is False:
                if 'os_kind' in record['other_config']:
                    new_rec['os_kind'] = record['other_config']['os_kind']
                else:
                    if 'reference_label' in record:
                        for OS in 'ubuntu','centos', 'debian':
                            if record['reference_label'].startswith(OS):
                                new_rec['os_kind'] = OS
                                break

            return new_rec

        template_settings = json.load(xenstore_data[self.VMEMPEROR_TEMPLATE_PREFIX])
        new_rec['os_kind'] = template_settings['os_kind']
        return new_rec

    @use_logger
    def clone(self, name_label):
        try:

            new_vm_ref = self.__getattr__('clone')(name_label)
            vm = VM(self.auth, ref=new_vm_ref)
            self.log.info("New VM is created: UUID {0}".format(vm.uuid))
            return vm
        except XenAPI.Failure as f:
            raise XenAdapterAPIError(self.log, "Failed to clone template: {0}".format(f.details))

    @use_logger
    def enable_disable(self, enable):
        '''
        Adds/removes tag 'vmemperor'
        :param enable:
        :return:
        '''
        try:
            if enable:
                self.add_tags('vmemperor')
                self.log.info("Enabled template UUID {0}".format(self.uuid))
            else:
                self.remove_tags('vmemperor')
                self.log.info("Disabled template UUID {0}".format(self.uuid))
        except XenAPI.Failure as f:
            raise XenAdapterAPIError(self.log, "Failed to {0} template: {1}".format(
                'enable' if enable else 'disable', f.details))
