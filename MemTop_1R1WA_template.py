import re
import time
import argparse
import logging
import MemBaseClass

template_1RlWA_TOP=""""""


class MemWrapTop(MemBaseClass.MemBase):
    def __init__(self):
        self.Type = "1R1WA"
        self.RTL = template_1RlWA_TOP
        self.HEADER = ""
        self.BaseName = "RAMWRAP_1R1WA_TOP"
        self.Note = "Note: Use Define USE_BEH_MEM to move forward without DB"

    def gen_HEADER(self):
        super().gen_HEADER()
        self.HEADER = self.HEADER.replace("@File:", "@File: RAMWRAP_1R1WA_TOP")

    def loadjson(self, DataDict):
        MEMWRAPLIST = ""
        i = 0
        for name, mem_tmp in DataDict.items():
            if mem_tmp["Type"] != "1R1WA":
                logging.debug("skip this type: %s", mem_tmp["Type"])
                continue
            Depth = mem_tmp["Depth"]
            Width = mem_tmp["Width"]
            if "Prefix" not in mem_tmp.keys():
                Prefix = ""
            else:
                Prefix = mem_tmp["Prefix"]
            if Prefix != "":
                Prefix_name = Prefix + "_"
            else:
                Prefix_name = Prefix
            if i == 0:
                tag = ""
            else:
                tag = "else "
            MEMWRAPLIST += """
{:s} if (DEPTH == {:d} && WIDTH == {:d} && PREFIX_ADDNAME == "{:s}") begin:gen_{:s}{:s}_{:d}X{:d}
    RAMWRAP_{:s}_{:d}X{:d} #(
       .MEMPHY_CTRL_CFG_W(MEMPHY_CTRL_CFG_W),
       .ASYNC_RST_EN(ASYNC_RST_EN),
       .WIDTH(WIDTH),
       .INPUTPIPELINE(INPUTPIPELINE),
       .DOUTPIPELINE(DOUTPIPELINE)
    memwrap (
       .memphy_ctrl_cfg   ( memphy_ctrl_cfg ),
       .i_clk            ( CLKW          ),
       .i_clkr           ( CLKR          ),
       .i_rstw           ( RSTW          ),
       .i_rstr           ( RSTR          ),
       .i_we             ( real_we       ),
       .i_re             ( RE            ),
       .i_raddr          ( AddrR         ),
       .i_waddr          ( real_waddr    ),
       .i_din            ( real_din      ),
       .o_dout           ( DOUT          ),
       .i_set_ecc_sb     ( SET_ECC_SB    ),
       .i_set_ecc_db     ( SET_ECC_DB    ),
       .i_ecc_bypass     ( ECC_bypass    ),
       .o_ecc_sb         ( ECC_sb        ),
       .o_ecc_db         ( ECC_db        ),
       .o_ecc_addr       ( ECC_addr      )
    );
end""".format(tag, int(Depth), int(Width), Prefix, self.Type, Prefix_name, int(Depth), int(Width), self.Type, int(Depth), int(Width))
            i = i + 1
        self.RTL = self.RTL.replace("$MEMWRAPLIST$", "{:s}".format(MEMWRAPLIST))
        return self.RTL


def test(filename):
    datadict = {
        "MEM1": {
            "TYPE": "1R1WA",
            "Depth": 128,
            "Width": 512,
        },
        "MEM2": {
            "TYPE": "1R1WA",
            "Depth": 32,
            "Width": 64,
            "Prefix": "TESTPREFIX"
        },
    }
    mem_tmp = MemWrapTop()
    mem_tmp.Initialize()
    mem_tmp.loadjson(datadict)
    mem_tmp.DumpRTL(filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="program description")
    parser.add_argument('-o', help="output verilog file name")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG,
        datefmt='%Y/%m/%d %H:%M:%S',
        format='%(asctime)s %(levelname)s : %(message)s (%(module)s-%(lineno)d-%(funcName)s)',
    )
    test(filename=args.o)