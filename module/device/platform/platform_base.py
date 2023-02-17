import typing as t

import yaml
from pydantic import BaseModel, SecretStr

from module.device.connection import Connection
from module.device.platform.emulator_base import EmulatorInstanceBase, EmulatorManagerBase
from module.logger import logger
from module.map.map_grids import SelectedGrids
from module.base.decorator import cached_property, del_cached_property


class EmulatorData(BaseModel):
    emulator: str = ''
    name: str = ''
    path: str = ''

    # For APIs of chinac.com, a phone cloud platform.
    access_key: SecretStr = ''
    secret: SecretStr = ''


class PlatformBase(Connection, EmulatorManagerBase):
    """
    Base interface of a platform, platform can be various operating system or phone clouds.
    For each `Platform` class, the following APIs must be implemented.
    - all_emulators()
    - all_emulator_instances()
    - emulator_start()
    - emulator_stop()
    """

    def emulator_start(self):
        """
        Start a emulator, until startup completed.
        - Retry is required.
        - Using bored sleep to wait startup is forbidden.
        """
        pass

    def emulator_stop(self):
        """
        Stop a emulator.
        """
        pass

    @cached_property
    def emulator_data(self) -> EmulatorData:
        try:
            data = yaml.safe_load(self.config.RestartEmulator_EmulatorData)
            return EmulatorData(**data)
        except Exception as e:
            logger.error(e)
            logger.error("Failed to load EmulatorData, no emulator_instance")
            return EmulatorData()

    @cached_property
    def emulator_instance(self) -> t.Optional[EmulatorInstanceBase]:
        """
        Returns:
            EmulatorInstanceBase: Emulator instance or None
        """
        data = self.emulator_data
        old_info = dict(
            emulator=data.emulator,
            path=data.path,
            name=data.name,
        )
        instance = self.find_emulator_instance(
            serial=str(self.config.Emulator_Serial).strip(),
            name=data.name,
            path=data.path,
            emulator=data.emulator,
        )

        # Write complete emulator data
        new_info = dict(
            emulator=instance.type,
            path=instance.path,
            name=instance.name,
        )
        if new_info != old_info:
            self.config.RestartEmulator_EmulatorData = yaml.safe_dump(new_info).strip()
            del_cached_property(self, 'emulator_data')

        return instance

    def find_emulator_instance(
            self,
            serial: str,
            name: str = None,
            path: str = None,
            emulator: str = None
    ) -> t.Optional[EmulatorInstanceBase]:
        """
        Args:
            serial: Serial like "127.0.0.1:5555"
            name: Instance name like "Nougat64"
            path: Emulator install path like "C:/Program Files/BlueStacks_nxt/HD-Player.exe"
            emulator: Emulator type defined in Emulator class, like "BlueStacks5"

        Returns:
            EmulatorInstance: Emulator instance or None if no instances not found.
        """
        logger.hr('Find emulator instance')
        instances = SelectedGrids(self.all_emulator_instances)
        for instance in instances:
            logger.info(instance)
        search_args = dict(serial=serial)

        # Search by serial
        select = instances.select(**search_args)
        if select.count == 0:
            logger.warning(f'No emulator instance with {search_args}')
            return None
        if select.count == 1:
            instance = select[0]
            logger.info(f'Found emulator instance: {instance}')
            return instance

        # Multiple instances in given serial, search by name
        if name:
            search_args['name'] = name
            select = instances.select(**search_args)
            if select.count == 0:
                logger.warning(f'No emulator instances with {search_args}')
                return None
            if select.count == 1:
                instance = select[0]
                logger.info(f'Found emulator instance: {instance}')
                return instance

        # Multiple instances in given serial and name, search by path
        if path:
            search_args['path'] = path
            select = instances.select(**search_args)
            if select.count == 0:
                logger.warning(f'No emulator instances with {search_args}')
                return None
            if select.count == 1:
                instance = select[0]
                logger.info(f'Found emulator instance: {instance}')
                return instance

        # Multiple instances in given serial, name and path, search by emulator
        if emulator:
            search_args['type'] = emulator
            select = instances.select(**search_args)
            if select.count == 0:
                logger.warning(f'No emulator instances with {search_args}')
                return None
            if select.count == 1:
                instance = select[0]
                logger.info(f'Found emulator instance: {instance}')
                return instance

        # Still too many instances
        logger.warning(f'Found multiple emulator instances with {search_args}')
        return None


if __name__ == '__main__':
    self = PlatformBase('alas')
    d = self.emulator_instance
    print(d)
