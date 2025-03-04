from loguru import logger
import requests
import json

# veritas
from veritas import sot


class Checkmk:
    """Checkmk class to interact with checkmk server

    Parameters
    ----------
    sot : Sot
        Sot object
    url : str
        checkmk url
    site : str
        checkmk site
    username : str
        checkmk username
    password : str
        checkmk password
    
    """
    def __init__(self, sot:sot.sot, url:str, site:str, username:str, password:str):
        self._sot = sot
        self._url = url
        self._site = site
        self._username = username
        self._password = password
        self._session = None
        self._checkmk = None
        self._api_url = None
        self._start_session()

    def _start_session(self) -> None:
        """start session with checkmk server"""
        # baseurl http://hostname/site/check_mk/api/1.0
        api_url = f'{self._url}/{self._site}/check_mk/api/1.0'
        logger.debug(f'starting CMK session for {self._username} on {api_url}')
        self._checkmk = self._sot.rest(url=api_url, 
                                       username=self._username,
                                       password=self._password)
        self._checkmk.session()
        self._checkmk.set_headers({'Content-Type': 'application/json'})

    def get_all_hosts(self) -> list:
        """return a list of all hosts"""
        devicelist = []

        # get a list of all hosts of check_mk
        response = self._checkmk.get(url="/domain-types/host_config/collections/all",
                                     params={"effective_attributes": False, },
                                     format='object')
        if response.status_code != 200:
            logger.error(f'got status code {response.status_code}; giving up')
            return []
        devices = response.json().get('value')
        for device in devices:
            devicelist.append({'host_name': device.get('title'),
                               'folder': device.get('extensions',{}).get('folder'),
                               'ipaddress': device.get('extensions',{}).get('attributes',{}).get('ipaddress'),
                               'snmp': device.get('extensions',{}).get('attributes',{}).get('snmp_community'),
                               'extensions': device.get('extensions',{})
                              })
        return devicelist

    def get_all_host_tags(self) -> dict:
        """get all host tags"""
        host_tags = {}
        response = self._checkmk.get(url="/domain-types/host_tag_group/collections/all")
        for tag in response.json().get('value'):
            del tag['links']
            host_tag = tag.get('id',{})
            host_tags[host_tag] = tag.get('extensions',{}).get('tags')
        
        return host_tags

    def get_etag(self, host:str) -> str:
        """get etag of a host

        Parameters
        ----------
        host : str
            hostname

        Returns
        -------
        etag : str
            etag of the host
        """
        params={"effective_attributes": False}
        response = self._checkmk.get(url=f"/objects/host_config/{host}", params=params)
        if response.status_code == 404:
            return None
        return response.headers.get('ETag')

    def add_hosts(self, devices:dict) -> bool:
        """add hosts to checkmk

        Parameters
        ----------
        devices : dict
            device properties

        Returns
        -------
        bool
            success or failure
        """
        data = {"entries": devices}
        params={"bake_agent": False}
        host = self._checkmk.post(url="/domain-types/host_config/actions/bulk-create/invoke",
                                  json=data, 
                                  params=params)
        status = host.status_code
        if status == 200:
            logger.debug('host added to check_mk')
            return True
        elif status == 500:
            logger.error(f'got status {status}; maybe host is already in check_mk')
            return False
        else:
            logger.error(f'got status {status}; error: {host.content}')
            return False

    def activate_all_changes(self) -> bool:
        """activate all changes

        Returns
        -------
        bool
            success or failure
        """
        logger.debug('activating all changes')
        response = self.activate_etag('*',[ self._site ])
        if not response:
            return 
        # content = json.loads(response.content)
        # id = content.get('id')
        # title = content.get('title')
        # if response.status_code not in {200, 412}:
        #     logger.error(f'got status {response.status_code} could not activate changes; error: {response.content}')
        #     return False
        # print(title)
        # print(f'activation started with id {id}')
        # print(content)
        # print(json.dumps(content.get('extensions'), indent=4))
        return True

    def show_activation_status(self, id) -> bool:
        """check last activation status

        Returns
        -------
        bool
            success or failure
        """
        logger.debug('checking last activating status')
        response = self._checkmk.get(url=f'/objects/activation_run/{id}')
        if response.status_code not in {200, 412}:
            logger.error(f'got status {response.status_code} could not activate changes; error: {response.content}')
            return False
        content = json.loads(response.content)
        title = content.get('title')
        extensions = content.get('extensions')
        print(title)
        print(json.dumps(extensions, indent=4))
        return True

    def show_pending_changes(self) -> bool:
        """show pending changes

        Returns
        -------
        bool
            success or failure
        """
        logger.debug('showing pending changes')
        response = self._checkmk.get(url="/domain-types/activation_run/collections/pending_changes")
        if response.status_code == 200:
            etag = response.headers.get('ETag')
            content = json.loads(response.content)
            if len(content.get('value')) == 0:
                print('there are no pending changes')
                return True
            print(json.dumps(content.get('value'), indent=4))
            print(f'etag: {etag}')
            return True
        else:
            logger.error(f'got status {response.status_code} could not show pending changes; error: {response.content}')
            return False

    def activate_etag(self, etag:str, site:list=None) -> requests.Response:
        """activate etag

        Parameters
        ----------
        etag : str
            etag
        site : str
            site

        Returns
        -------
        requests.Response
            response
        """
        site = site if site else [self._site]
        headers={
                "If-Match": etag,
                "Content-Type": 'application/json',
            }
        data = {"redirect": False,
                "sites": site,
                "force_foreign_changes": True}

        response = self._checkmk.post(url="/domain-types/activation_run/actions/activate-changes/invoke", 
                                      json=data, 
                                      headers=headers)
        if response.status_code == 422:
            logger.info('Currently there are no changes to activate.')
            return False
        elif response.status_code == 200:
            content = json.loads(response.content)
            title = content.get('title')
            id = content.get('id')
            print(title)
            print(json.dumps(content.get('extensions'), indent=4))
            print(f'activation_run id: {id}')
        else:
            logger.error(f'got status code {response.status_code}; error: {response.content}')
            logger.error(f'failed to activate changes {etag} on site {site}')
        
        return response

    def move_host_to_folder(self, hostname:str, etag:str, new_folder:str) -> bool:
        """move host to folder

        Parameters
        ----------
        hostname : str
            hostname
        etag : str
            etag
        new_folder : str
            name of the new folder

        Returns
        -------
        bool
            success or failure
        """        
        data={"target_folder": new_folder}
        headers={
            "If-Match": etag,
            "Content-Type": 'application/json',
        }

        logger.debug(f'sending request {data} {headers}')
        response = self._checkmk.post(url=f"/objects/host_config/{hostname}/actions/move/invoke", 
                                       json=data,
                                       headers=headers)
        status = response.status_code
        if status == 200:
            logger.debug('moved successfully')
            return True
        else:
            logger.error(f'status {status}; error: {response.content}')
            return False

    def update_host_in_cmk(self, hostname:str, etag:str, update_attributes:bool, remove_attributes:bool) -> bool:
        """update host in check mk

        Parameters
        ----------
        hostname : str
            hostname
        etag : str
            etag of host
        update_attributes : bool
            should attributes be updated
        remove_attributes : bool
            should attributes be removed

        Returns
        -------
        bool
            success or failure
        """        
        logger.debug(f'updating host {hostname}')
        data = {}
        if update_attributes:
            data.update({"update_attributes": update_attributes})
        if remove_attributes:
            data.update({"remove_attributes": remove_attributes})

        if len(data) == 0:
            logger.error(f'no update of {hostname} needed but update_host_in_cmk called')
            return

        headers={
            "If-Match": etag,
            "Content-Type": 'application/json',
        }
        logger.debug(f'sending request {data} {headers}')
        response = self._checkmk.put(url=f"/objects/host_config/{hostname}", 
                                     json=data,
                                     headers=headers)
        if response.status_code == 200:
            logger.debug('updated successfully')
            return True
        else:
            logger.error(f'status {response.status_code}; error: {response.content}')
            return False

    def delete_hosts(self, devices:list, bulk:bool=True) -> bool:
        """delete hosts from checkmk

        Parameters
        ----------
        devices : list
            list of devices to be deleted
        bulk : bool
            send bulk request

        Returns
        -------
        bool
            success or failure
        """    
        if bulk:
            # the BULK delete is a POST request to check mk
            response = self._checkmk.post(url="/domain-types/host_config/actions/bulk-delete/invoke", json={'entries': devices})
            if response.status_code == 200 or response.status_code == 204 :
                logger.debug(f'hosts {len(devices)} successfully deleted')
                return True
            else:
                logger.error(f'error removing hosts; status {response.status_code}; error: {response.content}')
                return False
        else:
            overall = True
            errors = 0
            for device in devices:
                response = self._checkmk.delete(url=f"/objects/host_config/{device}")
                if response.status_code == 200 or response.status_code == 204 :
                    logger.info(f'host {device} successfully deleted')
                else:
                    logger.error(f'error removing hosts; status {response.status_code}; error: {response.content}')
                    overall = False
                    errors += 1

            if overall:
                logger.info(f'removed {len(devices)} in cmk')
            else:
                logger.error(f'failed to remove {errors} devices')
            return overall

    def repair_services(self) -> bool:
        """repair services

        Returns
        -------
        bool
            success or failure
        """
        devices = self.get_all_hosts()
        hosts_with_no_services = []
        for device in devices:
            hostname = device.get('host_name')
            params={
                "query": '{"op": "=", "left": "host_name", "right": "' + hostname + '"}',
                "columns": ['host_name', 'description'],
            }
            response = self._checkmk.get(url=f"/objects/host/{hostname}/collections/services", params=params)
            if response.status_code == 200 and len(response.json()['value']) <= 2:
                logger.info(f'host {hostname} has only {len(response.json()["value"])} services')
                hosts_with_no_services.append({'host_name': hostname})
        
        if len(hosts_with_no_services) > 0:
            self._start_single_discovery(self._check_mk_config, hosts_with_no_services, self._check_mk)

    def start_single_discovery(self, devices:list) -> bool:
        """start single discovery

        Parameters
        ----------
        devices : list
            list of devices to discover

        Returns
        -------
        bool
            success or failure
        """        
        logger.debug('starting Host discovery')
        for device in devices:
            hostname = device.get('host_name')
            logger.info(f'starting discovery on {hostname}')
            # in cmk 2.2 you can add: 'do_full_scan': True,
            data = {'host_name': hostname, 
                    'mode': 'fix_all'}
            response = self._checkmk.post(url="/domain-types/service_discovery_run/actions/start/invoke", json=data)
            status = response.status_code
            if status == 200:
                logger.debug('started successfully')
                return True
            else:
                logger.error(f'status {status}; error: {response.content}')
                return False

    def update_folders(self, devices:list, default_config:dict=None) -> bool:
        """update folders

        Parameters
        ----------
        devices : list
            list of devices
        default_config : dict, optional
            default config, by default None

        Returns
        -------
        bool
            success or failure
        """        
        for device in devices:
            fldrs = device.get('folder')
            response = self._checkmk.get(url=f"/objects/folder_config/{fldrs}")
            status = response.status_code
            if status == 200:
                logger.debug(f'{fldrs} found in check_mk')
            elif status == 404:
                # one or more parent folders are missing
                # we have to check the complete path
                logger.debug(f'{fldrs} does not exist; creating it')
                path = fldrs.split('~')
                for i in range(1, len(path)):
                    pth = '~'.join(path[1:i])
                    logger.debug(f'checking if ~{pth} exists')
                    response = self._checkmk.get(url=f"/objects/folder_config/~{pth}")
                    if response.status_code == 404:
                        logger.debug(f'{pth} does not exists')
                        i = pth.rfind('~')
                        name = pth[i+1:]
                        if i == -1:
                            parent = "~"
                        else:
                            parent = "~%s" % pth[0:i]
                        data = {"name": name, 
                                "title": name, 
                                "parent": parent }
                        folder_config = self.get_folder_config(default_config, name)
                        if folder_config is not None:
                            data.update({'attributes': folder_config})
                        logger.debug(f'creating folder {name} in {parent}')
                        response = self._checkmk.post(url="/domain-types/folder_config/collections/all", json=data)
                        if response.status_code == 200:
                            logger.debug(f'folder {name} added in {parent}')
                        else:
                            logger.error(f'could not add folder; error: {response.content}')
                # now we have the path upto our folder
                i = fldrs.rfind('~')
                name = fldrs[i+1:]
                if i == -1:
                    parent = "~"
                else:
                    parent = fldrs[0:i]
                logger.debug(f'creating folder {name} in {parent}')
                data = {"name": name, 
                        "title": name, 
                        "parent": parent }
                folder_config = self.get_folder_config(default_config, name)
                if folder_config is not None:
                            data.update({'attributes': folder_config})
                response = self._checkmk.post(url="/domain-types/folder_config/collections/all", json=data)
                if response.status_code == 200:
                    logger.debug(f'folder {name} added in {parent}')
                    return True
                else:
                    logger.error(f'could not add folder; error: {response.content}')
                    return False
            else:
                logger.debug(f'got status: {status}')
                return False

    def get_folder_config(self, folders_config:dict, folder_name:str) -> dict:
        """return folder config

        Parameters
        ----------
        folders_config : dict
            folder config
        folder_name : str
            name of the folder

        Returns
        -------
        dict
            success or failure
        """        
        default = None
        for folder in folders_config:
            if folder['name'] == folder_name:
                response = dict(folder)
                del response['name']
                return response
            elif folder['name'] == 'default':
                response = dict(folder)
                del response['name']
                default = response
        return default

    def add_folder(self, folder:dict, default_config:dict=None) -> bool:
        """add folder to checkmk

        Parameters
        ----------
        folder : dict
            folder properties
        default_config : dict, optional
            default config, by default None

        Returns
        -------
        bool
            _description_
        """        
        name = folder.get('name')
        parent = folder.get('parent','')
        data = {"name": name,
                "title": folder.get('title', name),
                "parent": parent
               }
        folder_config = self.get_folder_config(default_config, name)
        if folder_config is not None:
            data.update({'attributes': folder_config})
        logger.debug(f'creating folder {name} in {parent}')
        response = self._checkmk.post(url="/domain-types/folder_config/collections/all", json=data)
        if response.status_code == 200:
            logger.info(f'folder {name} added in {parent}')
            return True
        else:
            logger.error(f'could not add folder; error: {response.content}')
            return False

    def add_config(self, config:dict, url:str) -> bool:
        """add config to checkmk

        Parameters
        ----------
        config : dict
            new config
        url : str
            url to add config

        Returns
        -------
        bool
            success or failure
        """        
        response = self._checkmk.post(url=url, json=config)
        if response.status_code == 200:
            logger.info('adding config successfully')
            return True
        else:
            logger.error(f'adding config failed; error: {response.content}')
            return False

    def get_host_internal(self, hostname:str) -> dict:
        # get host internals (site and is_cluster) from check mk
        response = self._checkmk.get(url=f"/objects/host_config_internal/{hostname}",
                                     format='object')
        if response.status_code != 200:
            logger.error(f'got status code {response.status_code}; giving up')
            return None

        return response.json()

    def get(self, url:str, params:dict=None, format:str=None) -> requests.Response:
        """make get request

        Parameters
        ----------
        url : str
            url
        params : _type_, optional
            parameter to use, by default None
        format : str, optional
            which format to get, by default None

        Returns
        -------
        requests.Response
            _description_
        """        
        logger.debug(f'getting url:{url} params:{params} format:{format}')
        if url and params and format:
            return self._checkmk.get(url=url,
                                     params=params,
                                     format=format)
        elif url and params:
            return self._checkmk.get(url=url,
                                     params=params)
        else:
            return self._checkmk.get(url=url)
