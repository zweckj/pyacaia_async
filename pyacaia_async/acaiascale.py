"""Client to interact with Acaia scales."""
from __future__ import annotations

import asyncio
import logging
import time

from collections.abc import Awaitable, Callable
from typing import Any

from bleak import BleakClient, BleakGATTCharacteristic, BLEDevice
from bleak.exc import BleakDeviceNotFoundError, BleakError

from .const import (
    DEFAULT_CHAR_ID,
    HEARTBEAT_INTERVAL,
    NOTIFY_CHAR_ID,
    OLD_STYLE_CHAR_ID,
)
from .exceptions import AcaiaDeviceNotFound, AcaiaError
from .const import BATTERY_LEVEL, GRAMS, WEIGHT, UNITS
from .decode import Message, Settings, decode
from .helpers import encode, encode_id, encode_notification_request

_LOGGER = logging.getLogger(__name__)


class AcaiaScale:
    """Representation of an Acaia scale."""

    _default_char_id = DEFAULT_CHAR_ID
    _notify_char_id = NOTIFY_CHAR_ID
    _msg_types = {
        "tare": encode(4, [0]),
        "startTimer": encode(13, [0, 0]),
        "stopTimer": encode(13, [0, 2]),
        "resetTimer": encode(13, [0, 1]),
        "heartbeat": encode(0, [2, 0]),
        "getSettings": encode(6, [0] * 16),
        "notificationRequest": encode_notification_request(),
    }

    def __init__(
        self,
        mac: str | None = None,
        is_new_style_scale: bool = True,
        notify_callback: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the scale."""

        self._mac = mac
        self._is_new_style_scale = is_new_style_scale

        self._client: BleakClient | None = None
        self._connected = False
        self._disconnecting = False
        self._timer_running = False
        self._timestamp_last_command: float | None = None
        self._timer_start: float | None = None
        self._timer_stop: float | None = None
        self._data: dict[str, Any] = {BATTERY_LEVEL: None, UNITS: GRAMS, WEIGHT: 0.0}

        self._queue: asyncio.Queue = asyncio.Queue()
        self._heartbeat_task: asyncio.Task | None = None
        self._process_queue_task: asyncio.Task | None = None

        self._msg_types["auth"] = encode_id(is_pyxis_style=is_new_style_scale)

        if not is_new_style_scale:
            # for old style scales, the default char id is the same as the notify char id
            self._default_char_id = self._notify_char_id = OLD_STYLE_CHAR_ID

        self._notify_callback: Callable[[], None] | None = notify_callback

    @property
    def mac(self) -> str:
        """Return the mac address of the scale in upper case."""
        assert self._mac
        return self._mac.upper()

    @property
    def timer_running(self) -> bool:
        """Return whether the timer is running."""
        return self._timer_running

    @timer_running.setter
    def timer_running(self, value: bool) -> None:
        """Set timer running state."""
        self._timer_running = value

    @property
    def connected(self) -> bool:
        """Return whether the scale is connected."""
        return self._connected

    @connected.setter
    def connected(self, value: bool) -> None:
        """Set connected state."""
        self._connected = value

    @property
    def data(self) -> dict[str, Any]:
        """Return the data of the scale."""
        return self._data

    @classmethod
    async def create(
        cls,
        mac: str | None = None,
        ble_device: BLEDevice | None = None,
        is_new_style_scale: bool = True,
        callback: Callable[[BleakGATTCharacteristic, bytearray], Awaitable[None] | None]
        | None = None,
    ) -> AcaiaScale:
        """Create a new scale."""
        self = cls(mac, is_new_style_scale)

        if ble_device:
            self._client = BleakClient(ble_device)
        elif mac:
            self._client = BleakClient(mac)
        else:
            raise ValueError("Either mac or bleDevice must be specified")

        await self.connect(callback)
        return self

    @property
    def msg_types(self) -> dict:
        """Return the message types."""
        return self._msg_types

    @property
    def timer(self) -> int:
        """Return the current timer value in seconds."""
        if self._timer_start is None:
            return 0
        if self._timer_running:
            return int(time.time() - self._timer_start)
        if self._timer_stop is None:
            return 0

        return int(self._timer_stop - self._timer_start)

    def new_client_from_ble_device(self, ble_device: BLEDevice) -> None:
        """Create a new client from a BLEDevice, used for Home Assistant"""
        self._client = BleakClient(ble_device)

    async def _write_msg(self, char_id: str, payload: bytearray) -> None:
        """wrapper for writing to the device."""
        try:
            if not self._connected:
                return
            assert self._client
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
        """Task to process the queue in the background."""
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
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                return
            except (AcaiaDeviceNotFound, AcaiaError) as ex:
                _LOGGER.debug("Error writing to device: %s", ex)
                return

    async def connect(
        self,
        callback: Callable[[BleakGATTCharacteristic, bytearray], Awaitable[None] | None]
        | None = None,
    ) -> None:
        """Initiate connection to the scale"""
        if not self._client:
            raise AcaiaError("Client not initialized")
        try:
            try:
                await self._client.connect()
            except BleakError as ex:
                _LOGGER.exception("Error during connecting to device: %s", ex)
                raise AcaiaError("Error during connecting to device") from ex

            self._connected = True
            _LOGGER.debug("Connected to Acaia Scale")

            if callback is None:
                callback = self.on_bluetooth_data_received
            try:
                await self._client.start_notify(self._notify_char_id, callback)
                await asyncio.sleep(0.5)
            except BleakError as ex:
                _LOGGER.exception("Error subscribing to notifications: %s", ex)
                raise AcaiaError("Error subscribing to notifications") from ex

            await self.auth()

            if callback is not None:
                await self.send_weight_notification_request()

        except BleakDeviceNotFoundError as ex:
            raise AcaiaDeviceNotFound("Device not found") from ex

        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(
                self._send_heartbeats(
                    interval=HEARTBEAT_INTERVAL if not self._is_new_style_scale else 1,
                    new_style_heartbeat=self._is_new_style_scale,
                )
            )
        if not self._process_queue_task:
            self._process_queue_task = asyncio.create_task(self._process_queue())

    async def auth(self) -> None:
        """Send auth message to scale, if subscribed to notifications returns Settings object"""
        await self._queue.put((self._default_char_id, self.msg_types["auth"]))

    async def send_weight_notification_request(self) -> None:
        """Tell the scale to send weight notifications"""

        await self._queue.put(
            (self._default_char_id, self.msg_types["notificationRequest"])
        )

    async def _send_heartbeats(
        self, interval: int = HEARTBEAT_INTERVAL, new_style_heartbeat: bool = False
    ) -> None:
        """Task to send heartbeats in the background."""
        while True:
            try:
                if not self._connected or self._disconnecting:
                    return

                _LOGGER.debug("Sending heartbeat")
                if new_style_heartbeat:
                    await self._queue.put(
                        (self._default_char_id, self.msg_types["auth"])
                    )

                await self._queue.put(
                    (self._default_char_id, self.msg_types["heartbeat"])
                )

                if new_style_heartbeat:
                    await self._queue.put(
                        (self._default_char_id, self.msg_types["getSettings"])
                    )
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                return
            except asyncio.QueueFull as ex:
                _LOGGER.debug("Error sending heartbeat: %s", ex)
                return

    async def disconnect(self) -> None:
        """Clean disconnect from the scale"""
        if not self._client:
            return
        try:
            _LOGGER.debug("Disconnecting from scale")
            self._disconnecting = True
            await self._queue.join()
            await self._client.disconnect()
            self._connected = False
            _LOGGER.debug("Disconnected from Acaia Scale")
        except BleakError as ex:
            _LOGGER.debug("Error disconnecting from device: %s", ex)

    async def tare(self) -> None:
        """Tare the scale."""
        if not self.connected:
            await self.connect()
        await self._queue.put((self._default_char_id, self.msg_types["tare"]))

    async def start_stop_timer(self) -> None:
        """Start/Stop the timer."""
        if not self.connected:
            await self.connect()
        if not self._timer_running:
            _LOGGER.debug('Sending "start" message.')
            await self._queue.put((self._default_char_id, self.msg_types["startTimer"]))
            self._timer_running = True
            if not self._timer_start:
                self._timer_start = time.time()
        else:
            _LOGGER.debug('Sending "stop" message.')
            await self._queue.put((self._default_char_id, self.msg_types["stopTimer"]))
            self._timer_running = False
            self._timer_stop = time.time()

    async def reset_timer(self) -> None:
        """Reset the timer."""
        if not self.connected:
            await self.connect()
        await self._queue.put((self._default_char_id, self.msg_types["resetTimer"]))
        self._timer_start = None
        self._timer_stop = None

        if self._timer_running:
            await self._queue.put((self._default_char_id, self.msg_types["startTimer"]))
            self._timer_start = time.time()

    async def on_bluetooth_data_received(
        self, characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        """Receive data from scale."""
        msg = decode(data)[0]

        if isinstance(msg, Settings):
            self._data[BATTERY_LEVEL] = msg.battery
            self._data[UNITS] = msg.units
            _LOGGER.debug(
                "Got battery level %s, units %s", str(msg.battery), str(msg.units)
            )

        elif isinstance(msg, Message):
            self._data[WEIGHT] = msg.value
            _LOGGER.debug("Got weight %s", str(msg.value))

        if self._notify_callback is not None:
            self._notify_callback()
