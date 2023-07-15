import asyncio

from pyacaia_async import AcaiaScale
from pyacaia_async.decode import notification_handler

async def main():
    scale = await AcaiaScale.create(mac="MAC", callback=notification_handler)

    # await asyncio.sleep(1)
    await scale.tare()

    await asyncio.sleep(1)
    print("starting Timer...")
    await scale.startStopTimer()
    await scale.send_auth()
    await asyncio.sleep(10)

    print("stopping Timer...")
    await scale.startStopTimer()
    await scale.send_notification_request()
    print(f"Timer running: {scale._timer_running}")
    print(scale.timer)
    print("resetting Timer...")
    await scale.resetTimer()

    await asyncio.sleep(2)
    # await scale.send_notification_request()
    print("starting Timer...")
    await scale.startStopTimer()
    print(scale.timer)

    await asyncio.sleep(5)
    print("stopping Timer...")
    await scale.startStopTimer()
    # await asyncio.sleep(5)
    # await scale.startStopTimer()
    # print(scale.timer)

    await scale.disconnect()

asyncio.run(main())