import logging
from random import randint     
from cocotb import start_soon
from cocotb.triggers import RisingEdge

from cocotbext.ahb import AHBBus
from cocotbext.ahb import AHBLiteMaster
from cocotbext.ahb import AHBMonitor
# from cocotbext.ahb import AHBMaster

from typing import Optional, Sequence, Union, List, Any
import collections.abc
class AHBMonitorDX(AHBMonitor):
    def __init__(
        self, bus: AHBBus, clock: str, reset: str, prefix: str = None, **kwargs: Any
    ) -> None:
        super().__init__(bus, clock, reset, **kwargs)
        self.prefix = prefix
        self.txn_receive = False
        self.enable_log_write = False           
        self.enable_log_read = False           
        start_soon(self._log_txn())

    async def _log_txn(self):
        self.log.setLevel(logging.DEBUG)
        while True:
            self.txn_receive = False
            self.txn = await self.wait_for_recv()
            self.txn_receive = True
            if self.txn.mode:
                if self.enable_log_write:
                    self.log.debug(f'Write {self.prefix} 0x{self.txn.addr:08x} 0x{self.txn.wdata:08x}')
#                     print(f'Write 0x{self.txn.addr:08x} 0x{self.txn.wdata:08x}')
            else:
                if self.enable_log_read:
                    self.log.debug(f'Read  {self.prefix} 0x{self.txn.addr:08x} 0x{self.txn.rdata:08x}')
            await RisingEdge(self.clk)

    def enable_write_logging(self):
        self.log.setLevel(logging.DEBUG)
        self.enable_log_write = True           
    
    def enable_read_logging(self):
        self.log.setLevel(logging.DEBUG)
        self.enable_log_read = True           
    

class AHBLiteMasterDX(AHBLiteMaster):
    
    def __init__(
        self,
        bus: AHBBus,
        clock: str,
        reset: str,
        **kwargs,
    ):
        self.pip = False
        super().__init__(bus, clock, reset, **kwargs)

    def check_read(self):
        if not self.returned_val == self.value and not -1 == self.value:
            raise Exception(f"Expected 0x{self.value:08x} doesn't match returned 0x{self.returned_val:08x}")

# isinstance(x, (tuple, list, str))
    def prepare_addresses(self, address: Union[int, Sequence[int]], value: Union[int, Sequence[int]], length: int = 1):
        if isinstance(address, collections.abc.Sequence):
            self.addresses = address
        else:
            self.addresses = []
            for i in range(length):
                self.addresses.append(address+(i*4))
        if isinstance(value, collections.abc.Sequence):
            self.values = value
        else:
            self.values = []
            for i in range(length):
                if -1 == value:
                    self.values.append(value)
                else:
                    self.values.append((value>>(i*32)) & 0xffffffff)
    
    def enable_backpressure(self):
        self.backpressure = True

    def disable_backpressure(self):
        self.backpressure = False

        

    async def write(
        self,
        address: Union[int, Sequence[int]],
        value: Union[int, Sequence[int]],
        length: Optional[int] = 1,
        **kwargs,
    ) -> Sequence[dict]:
        self.prepare_addresses(address, value, length)

        ret = await super().write(self.addresses, self.values, **kwargs)
        for i, x in enumerate(ret):
            self.log.debug(f"Write 0x{self.addresses[i]:08x}: 0x{self.values[i]:08x}")
        return ret

    async def read(
        self,
        address: Union[int, Sequence[int]],
        value: Optional[Union[int, Sequence[int]]] = -1,
        length: Optional[int] = 1,
        **kwargs,
    ) -> Sequence[dict]:
        self.prepare_addresses(address, value, length)
        ret = await super().read(self.addresses, **kwargs)
        for i, x in enumerate(ret):
            self.returned_val = int(x['data'],16)
            self.value = self.values[i]
            self.log.debug(f"Read  0x{self.addresses[i]:08x}: 0x{self.returned_val:08x}")
            self.check_read()
        return ret
