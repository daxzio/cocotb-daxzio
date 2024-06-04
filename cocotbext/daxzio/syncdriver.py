from cocotb import start_soon
from cocotb.triggers import RisingEdge, FallingEdge, Timer

class syncDriver:
    def __init__(self, vsync=None, rsync=None, gsync=None, bsync=None, vsync_freq=60, offset_start=10):
        self.offset_start = offset_start
        self.vsync = vsync
        self.vsync_freq = vsync_freq
        self.vsync_delay = 1000000000/self.vsync_freq
        #self.vsync.setimmediatevalue(0x0)
        start_soon(self._vsync())
        
        self.rgbsync = [rsync, gsync, bsync]

        self.t0_delay = [5000, 5000, 5000]
        self.t1_delay = [100000000/self.vsync_freq, 100000000/self.vsync_freq, 100000000/self.vsync_freq]
        
        for i, x in enumerate(self.rgbsync):
            #self.rgbsync[i].setimmediatevalue(0x0)
            start_soon(self._rgbsync(i))
        
    async def _vsync(self):
        self.vsync.value = 0
        v0_delay = self.offset_start
        v1_delay = 500*80
        v2_delay = round(self.vsync_delay, 3) - v1_delay
        await Timer(v0_delay, units='ns')
        while True:
            self.vsync.value = 1
            await Timer(v1_delay, units='ns')
            self.vsync.value = 0
            await Timer(v2_delay, units='ns')

    async def _rgbsync(self, num=0):
        self.rgbsync[num].value = 0
        t0_delay = self.t0_delay[num]
        t1_delay = round(self.t1_delay[num], 0)
        t2_delay = round(self.vsync_delay/2 - t1_delay, 3)
        t0_delay += round(num*(self.vsync_delay/6), 3)
        while True:
            await RisingEdge(self.vsync)
            await FallingEdge(self.vsync)
            await Timer(t0_delay, units='ns')
            for i in range(2):
                self.rgbsync[num].value = 1
                await Timer(t1_delay, units='ns')
                self.rgbsync[num].value = 0
                if 0 == i:
                    await Timer(t2_delay, units='ns')

