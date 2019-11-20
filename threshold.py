import logging
import py
import yaml
import temporary
import os
import sys
from cryptography.fernet import Fernet
from cached_property import cached_property
from datetime import datetime, timedelta


LOG_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
LOG_FORMAT = '%(asctime)s.%(msecs).06dZ - %(process)d - %(name)s - %(levelname)s - %(message)s'
LOG_FILE_NAME = 'svn_changes-{dt}.log'.format(dt = datetime.now().strftime("%d-%m-%Y"))
IBC = {
    #'SVN_URL': 'http://10.171.22.33/svn/ibc/sites/',
     'SVN_URL': 'http://161.85.111.157/svn/ibc/sites/',
    'SVN_USERNAME': 'operator',
    'SVN_PASSWORD': 'st3nt0r',
}
FERNET_SECRET = '-BEhr4qfb-GMRMZU1YK-Q6ifPIrQkKstA5cHbxHaF9M='

def get_logger():
    logging.basicConfig(filename= LOG_FILE_NAME, level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    return logging

log = get_logger()
failed_sites = []

class FernetCrypto(object):
    @staticmethod
    def fernet():
        secret = bytes(FERNET_SECRET)
        return Fernet(secret)

    @classmethod
    def encrypt(cls, value):
        cipher_suite = cls.fernet()
        return cipher_suite.encrypt(value)

    @classmethod
    def decrypt(cls, value):
        cipher_suite = cls.fernet()
        return cipher_suite.decrypt(value)

class LhostYmlFileChangerForMultipleSites():
    def __init__(self):
        self.keyName1 = 'WAITING_WARNING'
        self.keyName2 = 'WAITING_CRITICAL'
        self.keyName3 = 'WAITING_THRESHOLD'
        
    def change_values_for_all_sites(self, site_list, new_value_for_keyname1, new_value_for_keyname2, new_value_for_keyname3):
        for site in site_list:
            try:
                self.change_values_for_one_site(site, new_value_for_keyname1, new_value_for_keyname2, new_value_for_keyname3)
            except Exception as e:
                log.error('while updating the {site} error occured:\n {e}'.format(site = site, e =e))
                failed_sites.append(site)
    
    def change_values_for_one_site(self, site, new_value_for_keyname1, new_value_for_keyname2, new_value_for_keyname3):
        self.set_site_svn_lhost_path(site)
        self.set_subpath_siteid(site)
        with temporary.temp_dir(parent_dir='/tmp/') as tmp_work_dir:
            teml_yml_fl = str(tmp_work_dir) + '/{site}/lhost.yml'.format(site = site)
            self.set_work_dir(tmp_work_dir)
            self.wc.info()
            with open(teml_yml_fl) as scanner_conts:
                lhost_yml_dict = yaml.load(scanner_conts)
                t='threshold_values'
                if t in lhost_yml_dict:
                    lhost_yml_dict['threshold_values'] = lhost_yml_dict.get('threshold_values', {})
                    if self.keyName1 in lhost_yml_dict['threshold_values']:
                        lhost_yml_dict['threshold_values'][self.keyName1] = self.new_value_for_keyname1
                        lhost_yml_dict['threshold_values'][self.keyName2] = self.new_value_for_keyname2
                        lhost_yml_dict['threshold_values'][self.keyName3] = self.new_value_for_keyname3
                    else:
                        d={self.keyName1:new_value_for_keyname1,self.keyName2:new_value_for_keyname2,self.keyName3:new_value_for_keyname3}
                        lhost_yml_dict['threshold_values'].update(d)
                else:
                    p1={t:{self.keyName1:new_value_for_keyname1,self.keyName2:new_value_for_keyname2,self.keyName3:new_value_for_keyname3}}
                    lhost_yml_dict['threshold_values'].update(p1)




                            
            self.process_config_file('/lhost.yml', yaml.safe_dump(lhost_yml_dict, default_flow_style=False))
            self.log_status()
            revision = self.wc.commit(msg='Updated lhost details of siteid:%s as part of %s on %s' % (site, 'FCO83000210' , datetime.now())) # FCO83000210 
            if revision:
                log.info('revision: %s', str(revision))
            else:
                log.debug('No changes, nothing to commit')
                        

    def encrypt(self, new_pass):
        return '{+'+FernetCrypto.encrypt(bytes(new_pass))+'+}'
https://www.w3schools.com/python/python_tuples.asp
    def set_site_svn_lhost_path(self, siteid):
        self.lhost_site_uri_path = IBC['SVN_URL'] + "{siteid}".format(siteid=siteid)

    def get_site_svn_lhost_path(self):
        return self.lhost_site_uri_path

    @property
    def wc(self):
        return self.setup_wc()

    def set_subpath_siteid(self, siteid):
        self.subpath = siteid

    def get_subpath_siteid(self):
        return self.subpath

    def set_work_dir(self,work_dir):
        self.work_dir = str(work_dir)

    def get_work_dir(self):
        return self.work_dir

    def get_subpath_wc(self):
        return os.path.join(self.get_work_dir(),self.get_subpath_siteid() )

    def get_svn_auth(self):
        self.sites_root_url = IBC['SVN_URL']
        return py.path.SvnAuth(IBC['SVN_USERNAME'], IBC['SVN_PASSWORD'], cache_auth=False, interactive=False)

    @property
    def subpath_url(self):
        return os.path.join(self.sites_root_url, self.get_subpath_siteid())

    def setup_wc(self):
        auth = self.get_svn_auth()
        subpath_svn_url = self.subpath_url
        wc = py.path.svnwc(self.get_subpath_wc())
        wc.auth = auth
        wc.checkout(subpath_svn_url)
        return wc

    def log_status(self):
        status = self.wc.status(rec=1)
        attr_to_list = ['added', 'deleted', 'modified', 'conflict', 'unknown']
        for attr in attr_to_list:
            svnwc_files_with_attr = getattr(status, attr)
            with_attr_filenames = [item.strpath for item in svnwc_files_with_attr]
            log.info('%s files: %s', attr, str(with_attr_filenames))

    def process_config_file(self,filename,content):
        if content is None:
            file_to_remove = self.wc.join(filename)
            if file_to_remove.check():
                file_to_remove.remove()
        else:
            file_to_write = self.wc.ensure(filename)
            file_to_write.write(content)
       

if __name__ == "__main__":
    m = LhostYmlFileChangerForMultipleSites()
    sites_list_in_ALLCAPS = [] # Be sure to use only Valid sites and all Sites are capital 
    try : # Try to get all the site id from a file
        with open(sys.argv[1], 'r') as sites_file: # Index Error occur if sites file is not provided
            for line in sites_file:
                sites_list_in_ALLCAPS.append(line.rstrip('\n'))
        new_value_for_WAITING_THRESHOLD = 4 #updated value for the key in plain text
        new_value_for_WAITING_WARNING = 3 #updated value for the key in plain text
        new_value_for_WAITING_CRITICAL = 1
        m.change_values_for_all_sites(sites_list_in_ALLCAPS, new_value_for_WAITING_THRESHOLD, new_value_for_WAITING_WARNING, new_value_for_WAITING_CRITICAL)
        sites_list_in_lowercase = map(lambda x: x.lower(), sites_list_in_ALLCAPS)
        m.change_values_for_all_sites(sites_list_in_lowercase, new_value_for_WAITING_THRESHOLD, new_value_for_WAITING_WARNING, new_value_for_WAITING_CRITICAL)
        if failed_sites == []:
            print 'All Sites Updated Successfully'
        else:
            print 'the following sites failed to update:\t', failed_sites
    except IndexError: 
        print "Error: Please provide sites file as the second argument"

