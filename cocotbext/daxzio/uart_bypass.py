import logging
from cocotb.triggers import RisingEdge
from cocotbext.uart import UartSource, UartSink
from reue.interfaces.reue import Reue

class UartBypass:
    
    def __init__(self, dut, clk, uart_in=None, uart_out=None, baud=230400):
        self.log = logging.getLogger(f"cocotb.UartBypass")
        self.clk = clk
        self.baud = int(baud)
        self.uart_disable = dut.uart_disable
        self.wfifo_wr_en = dut.wfifo_wr_en
        self.wfifo_din = dut.wfifo_din
        self.rfifo_rd_en = dut.rfifo_rd_en
        self.rfifo_dout = dut.rfifo_dout
        self.rfifo_empty = dut.rfifo_empty
        self.rfifo_full = dut.rfifo_full

        self.uart_disable.setimmediatevalue(0)
        self.wfifo_wr_en.setimmediatevalue(0)
        self.wfifo_din.setimmediatevalue(0)
        self.rfifo_rd_en.setimmediatevalue(0)
        self.enable_logging()
        self.fake_delay = 8


        if uart_in is None:
            uart_in = getattr(dut, 'uart_txd_in')
        self.uart_source = UartSource(uart_in, baud=self.baud, bits=8)
        if uart_out is None:
            uart_out = getattr(dut, 'uart_rxd_out')
        self.uart_sink   = UartSink(uart_out, baud=self.baud, bits=8)
        
        self.reue = Reue()

    def enable_logging(self):
        self.log.setLevel(logging.DEBUG)
    
    def disable_logging(self):
        self.log.setLevel(logging.WARNING)
    
    @property
    def bytes(self):
        return self.reue.bytes
    
    @property
    def data(self):
        return self.reue.data
    
    @property
    def length(self):
        return self.reue.length
    
    @property
    def return_bytes(self):
        return self.reue.return_bytes
    
    @property
    def bytearray(self):
        return self.reue.bytearray
    
    def gen_write(self, *args, **kwargs):
        return self.reue.gen_write(*args, **kwargs)

    def gen_read(self, *args, **kwargs):
        return self.reue.gen_read(*args, **kwargs)

    async def disable_uart(self):
        await RisingEdge(self.clk)
        self.uart_disable.value = 1
        await RisingEdge(self.clk)
    
    async def enable_uart(self):
        await RisingEdge(self.clk)
        self.uart_disable.value = 0
        await RisingEdge(self.clk)

    async def tx_bytes(self):
        if 0 == self.uart_disable.value:
            await self.uart_source.write(self.bytearray)
            await self.uart_source.wait()
        else:
            for x in self.bytes:
                await RisingEdge(self.clk)
                #self.log.debug(f"0x{x:02x}")
                self.wfifo_wr_en.value = 1
                self.wfifo_din.value = x
                await RisingEdge(self.clk)
                self.wfifo_wr_en.value = 0
                self.wfifo_din.value = 0
                for i in range(self.fake_delay):
                    await RisingEdge(self.clk)
    
    async def rx_bytes(self):
        if 0 == len(self.return_bytes):
            return
        self.returned_val = 0
        
        if 0 == self.uart_disable.value:
            for j, x in enumerate(self.return_bytes):
                data = await self.uart_sink.read()
                #self.log.debug(data)
                self.returned_val |= (int.from_bytes(data) << (8*j))
        else:
            while 1 == self.rfifo_empty.value:
                await RisingEdge(self.clk)
            j = 0
            while 0 == self.rfifo_empty.value:
                self.rfifo_rd_en.value = 1
                await RisingEdge(self.clk)
                self.rfifo_rd_en.value = 0
                await RisingEdge(self.clk)
                self.returned_val |= (self.rfifo_dout.value << (8*j))
                for i in range(self.fake_delay):
                    await RisingEdge(self.clk)
                j += 1
    
    async def write(self, addr, data, length=None):
        self.log.debug(f"Write 0x{addr:08x}: 0x{data:08x}")
        self.gen_write(addr, data, length)
        await self.tx_bytes()
        await self.rx_bytes()

    async def read(self, addr, data=None, length=None):
        self.gen_read(addr, data, length)
        await self.tx_bytes()
        await self.rx_bytes()
            
        self.log.debug(f"Read  0x{addr:08x}: 0x{self.returned_val:08x}")
        if not self.returned_val == self.data and not None == self.data:
            raise Exception(f"Expected 0x{self.data:08x} doesn't match returned 0x{self.returned_val:08x}")
