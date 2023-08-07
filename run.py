import asyncio

from pyacaia_async import AcaiaScale
from pyacaia_async.decode import notification_handler

async def main():
    scale = await AcaiaScale.create(mac="11:22:33:44:55", callback=notification_handler)

    # await asyncio.sleep(1)
    # await scale.tare()

    await asyncio.sleep(1)
    print("starting Timer...")
    await scale.startStopTimer()
    
    await asyncio.sleep(21)

    print("stopping Timer...")
    await scale.startStopTimer()

    await asyncio.sleep(5)
    print("resetting Timer...")
    await scale.resetTimer()
    await asyncio.sleep(5)
    print("starting Timer...")
    await scale.startStopTimer()
    await asyncio.sleep(30)
    print("stopping Timer...")
    await scale.startStopTimer()


    # print(f"Timer running: {scale._timer_running}")
    # print(scale.timer)
    # print("resetting Timer...")
    # await scale.resetTimer()

    # await asyncio.sleep(2)
    # print("starting Timer...")
    # await scale.auth()
    # await scale.startStopTimer()
    # print(scale.timer)

    # await asyncio.sleep(5)
    # print("stopping Timer...")
    # await scale.startStopTimer()
    # # await asyncio.sleep(5)
    # # await scale.startStopTimer()
    # print(scale.timer)

    await scale.disconnect()

asyncio.run(main())