from bleak import BleakClient
import asyncio


CHAR_ID = "49535343-8841-43f4-a8d4-ecbe34729bb3"
HEADER1 = 0xef
HEADER2 = 0xdd

def encode(msgType,payload):
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


msgs = {
    "tare": encode(4, [0]),
    "startTimer": encode(13, [0,0]),
    "stopTimer": encode(13, [0,2]),
    "resetTimer": encode(13, [0,1]),
    "heartbeat": encode(0, [2,0])
}

def encodeId(isPyxisStyle=False):
    if isPyxisStyle:
        payload = bytearray([0x30,0x31,0x32,0x33,0x34,0x35,0x36,0x37,0x38,0x39,0x30,0x31,0x32,0x33,0x34])
    else:
        payload = bytearray([0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d,0x2d])
    return encode(11,payload)

async def main():
    async with BleakClient("33:11:22:33:44") as client:
        print("connected")
        print("Writing id...")
        await client.write_gatt_char(CHAR_ID, encodeId(isPyxisStyle=False))
        for i in msgs:
            if i == "heartbeat":
                continue
            await asyncio.sleep(5)
            await client.write_gatt_char(CHAR_ID, msgs["heartbeat"])
            await asyncio.sleep(1)
            print(f"Writing {i}...")
            print(f"Writing {msgs[i]}...")
            await client.write_gatt_char(CHAR_ID, msgs[i])

asyncio.run(main())