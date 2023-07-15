"""Helper functions, taken from pyacaia."""

from bleak import BleakScanner
from .const import HEADER1, HEADER2

async def find_acaia_devices(timeout=10, scanner: BleakScanner = None)  -> list:
    """Find ACAIA devices."""
    
    print('Looking for ACAIA devices...')
    if scanner is None:
        async with BleakScanner() as scanner:
            return await scan(scanner, timeout)
    else:
        return await scan(scanner, timeout)


async def scan(scanner: BleakScanner, timeout) -> list:
    """Scan for devices."""
    addresses=[]

    devices_start_names = [
        'ACAIA',
        'PYXIS',
        'LUNAR',
        'PROCH'
    ]

    devices = await scanner.discover(timeout=timeout)
    for d in devices:
        if (d.name
            and any(d.name.startswith(name) for name in devices_start_names)):
                print (d.name,d.address)
                addresses.append(d.address)

    return addresses


def encode(msgType,payload) -> bytearray:
    bytes=bytearray(5+len(payload))

    bytes[0] = HEADER1
    bytes[1] = HEADER2
    bytes[2] = msgType
    cksum1 = 0
    cksum2 = 0


    for i in range(len(payload)):
        val = payload[i] & 0xff
        bytes[3+i] = val
        if (i % 2 == 0):
            cksum1 += val
        else:
            cksum2 += val

    bytes[len(payload) + 3] = (cksum1 & 0xFF)
    bytes[len(payload) + 4] = (cksum2 & 0xFF)

    return bytes


def encodeId(isPyxisStyle=False) -> bytearray:
    if isPyxisStyle:
        payload = bytearray([0x30,0x31,0x32,0x33,0x34,0x35,0x36,0x37,0x38,0x39,0x30,0x31,0x32,0x33,0x34])
    else:
        payload = bytearray([0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d])
    return encode(11,payload)


def encodeNotificationRequest() -> bytearray:
    payload=[
    	0,  # weight
    	1,  # weight argument
    	1,  # battery
    	2,  # battery argument
    	2,  # timer
    	5,  # timer argument (number heartbeats between timer messages)
    	3,  # key
    	4   # setting
    ]
    bytes= bytearray(len(payload)+1)
    bytes[0] = len(payload) + 1

    for i in range(len(payload)):
        bytes[i+1]=payload[i] & 0xff

    return encode(12,bytes)