"""Helper functions, taken from pyacaia."""
import logging

from bleak import BleakScanner

from .const import HEADER1, HEADER2, SCALE_START_NAMES

_LOOGER = logging.getLogger(__name__)


async def find_acaia_devices(timeout=10, scanner: BleakScanner | None = None) -> list:
    """Find ACAIA devices."""

    _LOOGER.debug("Looking for ACAIA devices")
    if scanner is None:
        async with BleakScanner() as scanner:
            return await scan(scanner, timeout)
    else:
        return await scan(scanner, timeout)


async def scan(scanner: BleakScanner, timeout) -> list:
    """Scan for devices."""
    addresses = []

    devices = await scanner.discover(timeout=timeout)
    for d in devices:
        if d.name and any(d.name.startswith(name) for name in SCALE_START_NAMES):
            print(d.name, d.address)
            addresses.append(d.address)

    return addresses


def encode(msg_type: int, payload: bytearray | list[int]) -> bytearray:
    """Encode a message to the scale."""
    byte_msg = bytearray(5 + len(payload))

    byte_msg[0] = HEADER1
    byte_msg[1] = HEADER2
    byte_msg[2] = msg_type
    cksum1 = 0
    cksum2 = 0

    for i, p_byte in enumerate(payload):
        val = p_byte & 0xFF
        byte_msg[3 + i] = val
        if i % 2 == 0:
            cksum1 += val
        else:
            cksum2 += val

    byte_msg[len(payload) + 3] = cksum1 & 0xFF
    byte_msg[len(payload) + 4] = cksum2 & 0xFF

    return byte_msg


def encode_id(is_pyxis_style=False) -> bytearray:
    """Encode the scale id."""
    if is_pyxis_style:
        payload = bytearray(
            [
                0x30,
                0x31,
                0x32,
                0x33,
                0x34,
                0x35,
                0x36,
                0x37,
                0x38,
                0x39,
                0x30,
                0x31,
                0x32,
                0x33,
                0x34,
            ]
        )
    else:
        payload = bytearray(
            [
                0x2D,
                0x2D,
                0x2D,
                0x2D,
                0x2D,
                0x2D,
                0x2D,
                0x2D,
                0x2D,
                0x2D,
                0x2D,
                0x2D,
                0x2D,
                0x2D,
                0x2D,
            ]
        )
    return encode(11, payload)


def encode_notification_request() -> bytearray:
    """Encode the notification request."""
    payload = [
        0,  # weight
        1,  # weight argument
        1,  # battery
        2,  # battery argument
        2,  # timer
        5,  # timer argument (number heartbeats between timer messages)
        3,  # key
        4,  # setting
    ]
    byte_msg = bytearray(len(payload) + 1)
    byte_msg[0] = len(payload) + 1

    for i, p_byte in enumerate(payload):
        byte_msg[i + 1] = p_byte & 0xFF

    return encode(12, byte_msg)
