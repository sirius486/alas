import numpy as np

import module.config.server as server
from module.base.decorator import run_once
from module.base.timer import Timer
from module.campaign.campaign_event import CampaignEvent
from module.combat.assets import *
from module.exception import ScriptError
from module.logger import logger
from module.map.map_operation import MapOperation
from module.ocr.ocr import Digit, DigitCounter
from module.raid.assets import *
from module.raid.combat import RaidCombat
from module.ui.assets import RAID_CHECK


class OilExhausted(Exception):
    pass


class RaidCounter(DigitCounter):
    def pre_process(self, image):
        image = super().pre_process(image)
        image = np.pad(image, ((2, 2), (0, 0)), mode='constant', constant_values=255)
        return image


def raid_name_shorten(name):
    """
    Args:
        name (str): Raid name, such as raid_20200624, raid_20210708.

    Returns:
        str: Prefix of button name, such as ESSEX, SURUGA.
    """
    if name == 'raid_20200624':
        return 'ESSEX'
    elif name == 'raid_20210708':
        return 'SURUGA'
    elif name == 'raid_20220127':
        return 'BRISTOL'
    elif name == 'raid_20220630':
        return 'IRIS'
    elif name == "raid_20221027":
        return "ALBION"
    elif name == "raid_20230118":
        return "KUYBYSHEY"
    else:
        raise ScriptError(f'Unknown raid name: {name}')


def raid_entrance(raid, mode):
    """
    Args:
        raid (str): Raid name, such as raid_20200624, raid_20210708.
        mode (str): easy, normal, hard

    Returns:
        Button:
    """
    key = f'{raid_name_shorten(raid)}_RAID_{mode.upper()}'
    try:
        return globals()[key]
    except KeyError:
        raise ScriptError(f'Raid entrance asset not exists: {key}')


def raid_ocr(raid, mode):
    """
    Args:
        raid (str): Raid name, such as raid_20200624, raid_20210708.
        mode (str): easy, normal, hard, ex

    Returns:
        DigitCounter:
    """
    raid = raid_name_shorten(raid)
    key = f'{raid}_OCR_REMAIN_{mode.upper()}'
    try:
        button = globals()[key]
        # Old raids use RaidCounter to compatible with old OCR model and its assets
        # New raids use DigitCounter
        if raid == 'ESSEX':
            return RaidCounter(button, letter=(57, 52, 255), threshold=128)
        elif raid == 'SURUGA':
            return RaidCounter(button, letter=(49, 48, 49), threshold=128)
        elif raid == 'BRISTOL':
            return RaidCounter(button, letter=(214, 231, 219), threshold=128)
        elif raid == 'IRIS':
            # Font is not in model 'azur_lane', so use general ocr model
            if server.server == 'en':
                # Bold in EN
                return RaidCounter(button, letter=(148, 138, 123), threshold=80, lang='cnocr')
            if server.server == 'jp':
                return RaidCounter(button, letter=(148, 138, 123), threshold=128, lang='cnocr')
            else:
                return DigitCounter(button, letter=(148, 138, 123), threshold=128, lang='cnocr')
        elif raid == "ALBION":
            return DigitCounter(button, letter=(99, 73, 57), threshold=128)
        elif raid == 'KUYBYSHEY':
            if mode == 'ex':
                return Digit(button, letter=(189, 203, 214), threshold=128)
            else:
                return DigitCounter(button, letter=(231, 239, 247), threshold=128)
    except KeyError:
        raise ScriptError(f'Raid entrance asset not exists: {key}')


def pt_ocr(raid):
    """
    Args:
        raid (str): Raid name, such as raid_20200624, raid_20210708.

    Returns:
        Digit:
    """
    raid = raid_name_shorten(raid)
    key = f'{raid}_OCR_PT'
    try:
        button = globals()[key]
        if raid == 'IRIS':
            return Digit(button, letter=(181, 178, 165), threshold=128)
        elif raid == "ALBION":
            return Digit(button, letter=(23, 20, 9), threshold=128)
        elif raid == 'KUYBYSHEY':
            return Digit(button, letter=(16, 24, 33), threshold=64)
    except KeyError:
        # raise ScriptError(f'Raid pt ocr asset not exists: {key}')
        return None


class Raid(MapOperation, RaidCombat, CampaignEvent):
    def combat_preparation(self, balance_hp=False, emotion_reduce=False, auto=True, fleet_index=1):
        """
        Args:
            balance_hp (bool):
            emotion_reduce (bool):
            auto (bool):
            fleet_index (int):
        """
        logger.info('Combat preparation.')
        skip_first_screenshot = True
        # No need, already waited in `raid_execute_once()`
        # if emotion_reduce:
        #     self.emotion.wait(fleet_index)

        @run_once
        def check_oil():
            if self.get_oil() < max(500, self.config.StopCondition_OilLimit):
                logger.hr('Triggered oil limit')
                raise OilExhausted

        @run_once
        def check_coin():
            self.handle_task_balancer()

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear(BATTLE_PREPARATION, offset=(30, 20)):
                if self.handle_combat_automation_set(auto=auto == 'combat_auto'):
                    continue
                check_oil()
                check_coin()
            if self.handle_raid_ticket_use():
                continue
            if self.handle_retirement():
                continue
            if self.handle_combat_low_emotion():
                continue
            if self.appear_then_click(BATTLE_PREPARATION, offset=(30, 20), interval=2):
                continue
            if self.handle_combat_automation_confirm():
                continue
            if self.handle_story_skip():
                continue

            # End
            if self.is_combat_executing():
                if emotion_reduce:
                    self.emotion.reduce(fleet_index)
                break

    def handle_raid_ticket_use(self):
        """
        Returns:
            bool: If clicked.
        """
        if self.appear(TICKET_USE_CONFIRM, offset=(30, 30), interval=1):
            if self.config.Raid_UseTicket:
                self.device.click(TICKET_USE_CONFIRM)
            else:
                self.device.click(TICKET_USE_CANCEL)
            return True

        return False

    def raid_enter(self, mode, raid, skip_first_screenshot=True):
        """
        Args:
            mode:
            raid:
            skip_first_screenshot:

        Pages:
            in: page_raid
            out: BATTLE_PREPARATION
        """
        entrance = raid_entrance(raid=raid, mode=mode)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear(entrance, offset=(10, 10), interval=5):
                # Items appear from right
                # Check PT when entrance appear
                if self.event_pt_limit_triggered():
                    self.config.task_stop()
                self.device.click(entrance)
                continue
            if self.appear_then_click(RAID_FLEET_PREPARATION, offset=(20, 20), interval=5):
                continue

            # End
            if self.combat_appear():
                break

    def raid_expected_end(self):
        return self.appear(RAID_CHECK, offset=(30, 30))

    def raid_execute_once(self, mode, raid):
        """
        Args:
            mode:
            raid:

        Returns:
            in: page_raid
            out: page_raid
        """
        logger.hr('Raid Execute')
        self.config.override(
            Campaign_Name=f'{raid}_{mode}',
            Campaign_UseAutoSearch=False,
            Fleet_FleetOrder='fleet1_all_fleet2_standby'
        )

        if mode == 'ex':
            backup = self.config.temporary(
                Submarine_Fleet=1,
                Submarine_Mode='every_combat'
            )

        self.emotion.check_reduce(1)

        self.raid_enter(mode=mode, raid=raid)
        self.combat(balance_hp=False, expected_end=self.raid_expected_end)

        if mode == 'ex':
            backup.recover()

        logger.hr('Raid End')

    def get_event_pt(self):
        """
        Returns:
            int: Raid PT, 0 if raid event is not supported

        Pages:
            in: page_raid
        """
        skip_first_screenshot = True
        timeout = Timer(1.5, count=5).start()
        ocr = pt_ocr(self.config.Campaign_Event)
        if ocr is not None:
            # 70000 seems to be a default value, wait
            while 1:
                if skip_first_screenshot:
                    skip_first_screenshot = False
                else:
                    self.device.screenshot()

                pt = ocr.ocr(self.device.image)
                if timeout.reached():
                    logger.warning('Wait PT timeout, assume it is')
                    return pt
                if pt in [70000, 70001]:
                    continue
                else:
                    return pt
        else:
            logger.info(f'Raid {self.config.Campaign_Event} does not support PT ocr, skip')
            return 0
