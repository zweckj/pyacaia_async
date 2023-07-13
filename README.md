# pyacaia_async
Async implementation of [pyacaia](https://github.com/lucapinello/pyacaia/tree/master/pyacaia), based on `asyncio` and `bleak`
# Usage
```python
import asyncio
from pyacaia_async import AcaiaScale
from pyacaia_async.helpers import find_acaia_devices

async def main()
  addresses = await find_acaia_devices()
  address = addresses[0]
  scale = await AcaiaScale.create(mac=address, isPyxisStyle=False)
  await scale.tare()
  await scale.startStopTimer()
  await scale.resetTimer()

asyncio.run(main())
```
