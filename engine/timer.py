import asyncio


class Timer:
    def __init__(self, time: int, add_time: int):
        self.time = time
        self.add_time = add_time

    async def start(self):
        while self.time > 0:
            await asyncio.sleep(1)
            self.time -= 1

    async def stop(self):
        pass

