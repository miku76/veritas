from loguru import logger

# veritas
from veritas.tools import tools
from veritas.tools import exceptions as veritas_exceptions

class Device:
    """Device class to interact with nautobot to update devices and interfaces

    Parameters
    ----------
    sot : Sot
        Sot object
    device : str
        device name
    """
    def __init__(self, sot, device):
        # init variables
        self._sot = sot
        self._device = device
        self._interface = None

        # open connection to nautobot
        self._nautobot = self._sot.open_nautobot()

    def interface(self, interface_name:str) -> None:
        """set interface name

        If interface is set this script will update the interface indetad of the device.
        The syntax looks like this:

        device.interface('Loopback0').update(description="descr")

        Parameters
        ----------
        interface_name : str
            name of interface

        Returns
        -------
        None
        """        
        self._interface = interface_name
        return self

    def update(self, *unnamed, **named) -> bool:
        """update device or interface

        Parameters
        ----------
        unnamed : list
            list of unnamed arguments
        named : dict
            dictionary of named arguments

        Returns
        -------
        bool
            True if successful, False otherwise
        """        

        properties = tools.convert_arguments_to_properties(*unnamed, **named)
        if self._interface:
            return self.update_interface(properties)
        else:
            return self.update_device(properties)

    def update_device(self, properties:dict) -> bool:
        """update device

        Parameters
        ----------
        properties : dict
            properties to update

        Returns
        -------
        bool
            true if successful, false otherwise
        """
        logger.debug(f'updating device {self._device}')
        device = self._nautobot.dcim.devices.get(name=self._device)
        if device:
            try:
                update = device.update(properties)
                if update:
                    logger.debug(f'device {self._device} updated')
                else:
                    logger.error(f'failed to update device {self._device}')
                return update
            except Exception as exc:
                logger.error(f'failed to update device {self._device}; exc={exc}')
                raise veritas_exceptions.UpdateDeviceError(
                    f'failed to update device {self._device}; exception={exc}',
                    additional_info=f'properties {properties}')
        else:
            logger.error(f'device {self._device} not found')
            raise veritas_exceptions.UnknownDeviceError(
                f'device {self._device} not found',
                additional_info=f'properties {properties}')

    def update_interface(self, properties:dict) -> bool:
        """update interface

        Parameters
        ----------
        properties : dict
            properties to update

        Returns
        -------
        bool
            true if successful, false otherwise
        """
        logger.debug(f'updating interface {self._device} / {self._interface}')

        interface = self._nautobot.dcim.interfaces.get(
                    device=[self._device],
                    name=self._interface)

        if not interface:
            logger.error(f'unknown interface {self._interface} on {self._device}')
            raise veritas_exceptions.UnknownInterfaceError(
                f'interface {self._interface} not found',
                additional_info=f'properties {properties}')
        try:
            update = interface.update(properties)
            if update:
                logger.debug(f'interface {self._interface} updated')
            else:
                logger.error(f'failed to update interface {self._interface}')
        except Exception as exc:
            logger.error(f'failed to update interface; got exception {exc}')
            raise veritas_exceptions.UpdateInterfaceError(
                    f'failed to update interface {self._device} / {self._interface}; exception={exc}',
                    additional_info=f'properties {properties}')

    def delete(self) -> bool:
        """delete device or interface
        """
        if self._interface:
            return self.delete_interface()
        else:
            return self.delete_device()

    def delete_device(self) -> bool:
        """delete device or interface
        """
        logger.debug(f'deleting device {self._device}')
        device = self._nautobot.dcim.devices.get(name=self._device)
        if device:
            try:
                delete = device.delete()
                if delete:
                    logger.debug(f'device {self._device} deleted')
                else:
                    logger.error(f'failed to delte device {self._device}')
                return delete
            except Exception as exc:
                logger.error(f'failed to delete device {self._device}; exc={exc}')
                raise veritas_exceptions.DeleteDeviceError(
                    f'failed to delete device {self._device}; exception={exc}')
        else:
            logger.error(f'device {self._device} not found')
            raise veritas_exceptions.UnknownDeviceError(
                f'device {self._device} not found')

    def delete_interface(self) -> bool:
        """delete interface

        Parameters
        ----------

        Returns
        -------
        bool
            true if successful, false otherwise
        """
        logger.debug(f'deleteing interface {self._device} / {self._interface}')

        interface = self._nautobot.dcim.interfaces.get(
                    device=[self._device],
                    name=self._interface)

        if not interface:
            logger.error(f'unknown interface {self._device} / {self._interface}')
            raise veritas_exceptions.UnknownInterfaceError(
                f'interface {self._interface} not found')
        try:
            delete = interface.delete()
            if delete:
                logger.debug(f'interface {self._device} / {self._interface}')
            else:
                logger.error(f'failed to delte interface {self._interface} on {self._device}')
            return delete
        except Exception as exc:
            logger.error(f'failed to delete interface; got exception {exc}')
            raise veritas_exceptions.DeleteInterfaceError(
                    f'failed to delete interface {self._device} / {self._interface}; exception={exc}')

    def set_tags(self, new_tags:list) -> bool:
        """set tags of device or interface

        Parameters
        ----------
        new_tags : list
            list of tags to set

        Returns
        -------
        bool
            true if successful, false otherwise
        """        
        if self._interface:
            return self.add_interface_tags(new_tags, set_tag=True)
        else:
            return self.add_tags(new_tags, set_tag=True)

    def add_tags(self, new_tags:list, set_tag:bool=False) -> bool:
        """add tags on device

        Parameters
        ----------
        new_tags : list
            list of tags to add
        set_tag : bool, optional
            if true, tags are set otherewise tags are added, by default False

        Returns
        -------
        bool
            true if successful, false otherwise
        """        
        if self._interface:
            return self.add_interface_tags(new_tags, set_tag=False)

        final_list = []

        if not set_tag:
            # if the device already exists there may also be tags
            device = self._nautobot.dcim.devices.get(name=self._device)
            if device is None:
                logger.error(f'unknown device {self._device_name}')
                return False

            for tag in device.tags:
                if tag.name not in new_tags:
                    new_tags.append(tag.name)

            logger.debug(f'current tags: {device.tags}')
            logger.debug(f'updating tags to {new_tags}')

        # check if new tag is known; add id to final list
        for new_tag in new_tags:
            tag = self._nautobot.extras.tags.get(name=new_tag)
            if tag is None:
                logger.error(f'unknown tag {new_tag}')
                raise veritas_exceptions.UnknownValueError(f'unknown tag {new_tag}')
            else:
                final_list.append(tag.id)

        if len(final_list) > 0:
            properties = {'tags': final_list}
            logger.debug(f'final list of tags {properties}')
            return self.update(properties)

    def delete_tags(self, tags_to_delete:list) -> bool:
        """delete tags from device or interface

        Parameters
        ----------
        tags_to_delete : list
            list of tags to delete

        Returns
        -------
        bool
            true if successful, false otherwise
        """        
        if self._interface:
            return self.delete_interface_tags(tags_to_delete)
        
        logger.debug(f'deleting tags {tags_to_delete} on {self._device}')

        # the device must exist; get tags
        device = self._nautobot.dcim.devices.get(name=self._device)
        if device is None:
            logger.error(f'unknown device {self._device}')
            return None

        device_tags = []
        current_tags = []
        for tag in device.tags:
            current_tags.append(tag.name)
            if tag.name not in tags_to_delete:
                device_tags.append(tag)

        logger.debug(f'current tags: {current_tags}')
        logger.debug(f'new tags {device_tags}')

        properties = {'tags': device_tags}
        return self.update(properties)

    def add_interface_tags(self, new_tags:list, set_tag:bool=False) -> bool:
        """add tags on interface

        Parameters
        ----------
        new_tags : list
            list of tags to add
        set_tag : bool, optional
            if true tags are set otherwise tags are added, by default False

        Returns
        -------
        bool
            true if successful, false otherwise
        """        
        final_list = []

        interface = self._nautobot.dcim.interfaces.get(
                    device=[self._device],
                    name=self._interface)

        if not interface:
            logger.error(f'unknown interface {self._interface} on {self._device}')
            raise veritas_exceptions.UnknownInterfaceError(
                f'interface {self._interface} not found',
                additional_info=f'new_tags={new_tags} set_tag={set_tag}')

        if not set_tag:
            for tag in interface.tags:
                if tag.name not in new_tags:
                    new_tags.append(tag.name)

            logger.debug(f'current tags: {interface.tags}')
            logger.debug(f'updating tags to {new_tags}')

        # check if new tag is known; add id to final list
        for new_tag in new_tags:
            tag = self._nautobot.extras.tags.get(name=new_tag)
            if tag is None:
                logger.error(f'unknown tag {new_tag}')
            else:
                final_list.append(tag.name)

        if len(final_list) > 0:
            properties = {'tags': final_list}
            logger.debug(f'final list of tags {properties}')
            try:
                return interface.update(properties)
            except Exception as exc:
                logger.error(f'failed to update interface; got exception {exc}')
                raise veritas_exceptions.UpdateInterfaceError(
                        f'failed to update interface {self._device} / {self._interface}; exception={exc}',
                        additional_info=f'new_tags={new_tags} set_tag={set_tag}')

    def delete_interface_tags(self, tags_to_delete:list) -> bool:
        """delete interface tags

        Parameters
        ----------
        tags_to_delete : list
            list of tags to delete

        Returns
        -------
        bool
            true if successful, false otherwise
        """        
        logger.debug(f'deleting tags {tags_to_delete} on {self._device}/{self._interface}')

        interface = self._nautobot.dcim.interfaces.get(
                    device=[self._device],
                    name=self._interface)

        if not interface:
            logger.error(f'unknown interface {self._interface} on {self._device}')
            raise veritas_exceptions.UnknownInterfaceError(
                f'interface {self._interface} not found',
                additional_info=f'tags_to_delete={tags_to_delete}')

        interface_tags = []
        current_tags = []
        for tag in interface.tags:
            current_tags.append(tag.name)
            if tag.name not in tags_to_delete:
                interface_tags.append(tag)

        logger.debug(f'current tags: {current_tags}')
        logger.debug(f'new tags {interface_tags}')

        properties = {'tags': interface_tags}
        try:
            return interface.update(properties)
        except Exception as exc:
            logger.error(f'failed to delete tag; got exception {exc}')
            raise veritas_exceptions.UpdateInterfaceError(
                    f'failed to update interface {self._device} / {self._interface}; exception={exc}',
                    additional_info=f'tags_to_delete={tags_to_delete}')

    def set_customfield(self, properties:dict) -> bool:
        """set customfield on device or interface

        Parameters
        ----------
        properties : dict
            properties to set

        Returns
        -------
        bool
            true if successful, false otherwise
        """        
        if self._interface:
            return self.set_interface_customfield(properties)

        device = self._nautobot.dcim.devices.get(name=self._device)
        if device:
            try:
                update = device.update(properties)
                logger.debug(f'device updated result={update}')
                return update
            except Exception as exc:
                logger.error(f'failed to update device {self._device}; exc={exc}')
                raise veritas_exceptions.UpdateDeviceError(
                    f'failed to update device {self._device}; exception={exc}',
                    additional_info=f'properties {properties}')
        else:
            logger.error(f'device {self._device} not found')
            raise veritas_exceptions.UnknownDeviceError(
                f'device {self._device} not found',
                additional_info=f'properties {properties}')

    def set_interface_customfield(self, properties:dict) -> bool:
        """set interface customfield

        todo: call update_interface to update customfield

        Parameters
        ----------
        properties : dict
            properties to set

        Returns
        -------
        bool
            true if successful, false otherwise
        """        
        interface = self._nautobot.dcim.interfaces.get(
                    device=[self._device],
                    name=self._interface)

        if not interface:
            logger.error(f'unknown interface {self._interface} on {self._device}')
            raise veritas_exceptions.UnknownInterfaceError(
                f'interface {self._interface} not found',
                additional_info=f'properties {properties}')
        try:
            return interface.update(properties)
        except Exception as exc:
            logger.error(f'failed to update interface; got exception {exc}')
            raise veritas_exceptions.UpdateInterfaceError(
                    f'failed to update interface {self._device} / {self._interface}; exception={exc}',
                    additional_info=f'properties {properties}')
