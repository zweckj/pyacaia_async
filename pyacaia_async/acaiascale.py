from __future__ import annotations
import asyncio
import logging
import time

from bleak import BleakClient, BLEDevice
from bleak.exc import BleakError, BleakDeviceNotFoundError
from .const import (
    DEFAULT_CHAR_ID,
    HEARTBEAT_INTERVAL,
    NOTIFY_CHAR_ID,
    OLD_STYLE_CHAR_ID,
)
from .helpers import encode, encodeId, encodeNotificationRequest
from .exceptions import AcaiaDeviceNotFound, AcaiaError

_LOGGER = logging.getLogger(__name__)

class AcaiaScale():

    def __init__(self, mac: str = None, is_new_style_scale: bool=True):
        """Initialize the scale."""
    
        self._mac = mac
        self._is_new_style_scale = is_new_style_scale

        self._client = None
        self._connected = False
        self._disconnecting = False
        self._timestamp_last_command = None
        self._timer_running = False
        self._timer_start = None
        self._timer_stop = None

        self._queue = asyncio.Queue()

        self._msg_types = {
            "tare": encode(4, [0]),
            "startTimer": encode(13, [0,0]),
            "stopTimer": encode(13, [0,2]),
            "resetTimer": encode(13, [0,1]),
            "heartbeat": encode(0, [2,0]),
            "auth": encodeId(isPyxisStyle=is_new_style_scale),
            "notificationRequest": encodeNotificationRequest(),
        }

        if not is_new_style_scale:
            # for old style scales, the default char id is the same as the notify char id
            DEFAULT_CHAR_ID = NOTIFY_CHAR_ID = OLD_STYLE_CHAR_ID

    @classmethod
    async def create(cls, mac: str = None, bleDevice: BLEDevice = None, is_new_style_scale: bool=True, callback = None) -> AcaiaScale:
        """Create a new scale."""  
        self = cls(mac, is_new_style_scale)

        if bleDevice:
            self._client = BleakClient(bleDevice)
        elif mac:
            self._client = BleakClient(mac)
        else:
            raise ValueError("Either mac or bleDevice must be specified")
        
        await self.connect(callback)
        asyncio.create_task(self._send_heartbeats())
        asyncio.create_task(self._process_queue())
        return self

    @property
    def msg_types(self) -> dict:
        return self._msg_types
    
    @property
    def timer(self) -> int:
        if self._timer_running:
            return int(time.time() - self._timer_start)
        else:
            return int(self._timer_stop - self._timer_start)
        

    def new_client_from_ble_device(self, BLED: BLEDevice) -> None:
        """ Create a new client from a BLEDevice, used for Home Assistant"""
        self._client = BleakClient(BLED)


    async def _write_msg(self, char_id: str, payload: bytearray) -> None:
        """ wrapper for writing to the device."""
        try:
            if not self._connected:
                return
            
            await self._client.write_gatt_char(char_id, payload)
            self._timestamp_last_command = time.time()
        except BleakDeviceNotFoundError as ex:
            self._connected = False
            raise AcaiaDeviceNotFound("Device not found") from ex
        except BleakError as ex:
            self._connected = False
            raise AcaiaError("Error writing to device") from ex
        except Exception as ex:
            self._connected = False
            raise AcaiaError("Unknown error writing to device") from ex
        

    async def _process_queue(self) -> None:
        """ Task to process the queue in the background. """
        while True:
            try:
                if not self._connected:
                    while not self._queue.empty():
                        # empty the queue
                        self._queue.get_nowait()
                        self._queue.task_done()
                    return
                
                if self._disconnecting and self._queue.empty():
                    return
                
                char_id, payload = await self._queue.get()
                await self._write_msg(char_id, payload)   
                self._queue.task_done()

            except asyncio.CancelledError:
                return
            except Exception as ex:
                _LOGGER.debug("Error writing to device: %s", ex)
                return


    async def connect(self, callback = None) -> None:
        """ Initiate connection to the scale """
        try:
            await self._client.connect()
            self._connected = True
            _LOGGER.debug("Connected to Acaia Scale.")

            if callback is not None:
                await self._client.start_notify(NOTIFY_CHAR_ID, callback)
                await asyncio.sleep(0.5)

            await self.auth()

            if callback is not None:
                await self.send_weight_notification_request()

        except BleakDeviceNotFoundError as ex:
            raise AcaiaDeviceNotFound("Device not found") from ex
        except BleakError as ex:
            raise AcaiaError("Error connecting to device") from ex
        

    async def auth(self) -> None:
        """ Send auth message to scale, if subscribed to notifications returns Settings object """
        await self._queue.put((
                DEFAULT_CHAR_ID,
                self.msg_types["auth"]
        ))

    async def send_weight_notification_request(self) -> None:
        """ Tell the scale to send weight notifications """

        await self._queue.put((
                DEFAULT_CHAR_ID,
                self.msg_types["notificationRequest"]
        ))


    async def _send_heartbeats(self) -> None:
        """ Task to send heartbeats in the background. """
        while True:
            try:
                if not self._connected or self._disconnecting:
                    return
                
                _LOGGER.debug("Sending heartbeat.")
                await self._queue.put((
                        DEFAULT_CHAR_ID, 
                        self.msg_types["heartbeat"]
                    ))
                await asyncio.sleep(HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                return
            except Exception as ex:
                _LOGGER.debug("Error sending heartbeat: %s", ex)
                return

    async def disconnect(self) -> None:
        """ Clean disconnect from the scale """
        try:
            _LOGGER.debug("Disconnecting from scale.")
            self._disconnecting = True
            await self._queue.join()
            await self._client.disconnect()
            self._connected = False
            _LOGGER.debug("Disconnected from Acaia Scale.")
        except Exception as ex:
            _LOGGER.debug("Error disconnecting from device: %s", ex)


    async def tare(self) -> None:
        await self._queue.put((
                DEFAULT_CHAR_ID, 
                self.msg_types["tare"]
            ))


    async def startStopTimer(self) -> None:
        if not self._timer_running:
            await self._queue.put((      
                    DEFAULT_CHAR_ID, 
                    self.msg_types["startTimer"]
                ))
            self._timer_running = True
            if not self._timer_start:
                self._timer_start = time.time()
        else:
            await self._queue.put((
                    DEFAULT_CHAR_ID, 
                    self.msg_types["stopTimer"]
                ))
            self._timer_running = False
            self._timer_stop = time.time()


    async def resetTimer(self) -> None:
        await self._queue.put((
                DEFAULT_CHAR_ID, 
                self.msg_types["resetTimer"]
            ))
        self._timer_start = None
        self._timer_stop = None

        if self._timer_running:
            await self._queue.put((
                    DEFAULT_CHAR_ID, 
                    self.msg_types["startTimer"]
                ))
            self._timer_start = time.time()
