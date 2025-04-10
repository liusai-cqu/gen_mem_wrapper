import os
import time
import argparse
import logging
import csv  


template_1R1W_TOP = """
`ifndef GM_RAMWRAP_1R1W_TOP_SV_
`define GM_RAMWRAP_1R1W_TOP_SV_
//==========================================================//
// FUNCTION //
//==========================================================//
function integer log2;
    input integer n;
    begin
        log2=1;
        while (2**log2< n) begin
            log2=log2+1;
        end
    end
endfunction

//==========================================================//
// Memory, use Physical Wrap to build
//==========================================================//
`ifdef ASIC_COMPILE
module RAMWRAP_1R1W_TOP #(
    parameter DEPTH = 256,
    parameter WIDTH = 75,
    parameter INPUTPIPELINE = 0,
    parameter DOUTPIPELINE = 0,
    parameter PREFIX_ADDNAME = ""
)(
    //logic
    input CLK,
    input RST,
    //----------Logical read and write port----------//
    input RE,
    input WE,
    input [log2(DEPTH)-1:0] AddrR,
    input [log2(DEPTH)-1:0] AddrW,
    input [WIDTH-1:0] DIN,
    output logic [WIDTH-1:0] DOUT
);

//----------Write channel selector----------//
wire real_we;
wire [WIDTH-1:0] real_din;
wire [log2(DEPTH)-1:0] real_waddr;

assign real_we = WE;
assign real_din = DIN;
assign real_waddr = AddrW;

generate
$MEMWRAPLIST$
endgenerate

`else
//==========================================================//
// Memory Behaviour Model //
//==========================================================//
module RAMWRAP_1R1W_TOP #(
    parameter WIDTH = 256,
    parameter DOUTPIPELINE = 75,
    parameter INPUTPIPELINE = 0,
    parameter PREFIX_ADDNAME = 0
)(
    //logic
    input CLK,
    input RST,
    //----------Logical read and write port----------//
    input RE,
    input WE,
    input [log2(DEPTH)-1:0] AddrR,
    input [log2(DEPTH)-1:0] AddrW,
    input [WIDTH-1:0] DIN,
    output logic [WIDTH-1:0] DOUT
);

logic [WIDTH-1:0] mem [DEPTH-1:0]; 

//----------inner signals----------//
//pipe
logic ppn_re_dly;
logic ppn_we;
logic [WIDTH-1:0] ppn_din;
logic [WIDTH-1:0] ppn_dout;
logic [log2(DEPTH)-1:0] ppn_raddr;
logic [log2(DEPTH)-1:0] ppn_waddr;

//read&write
logic real_we;
logic [WIDTH-1:0] real_din;
logic [WIDTH-1:0] real_dout;
logic [log2(DEPTH)-1:0] real_waddr;

//----------main code----------//
//pipeline Config

data_pipe #(
   .DATA_W (1),
   .PIPE_NUM (1),
   .PIPE_MUX_EN(0),
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_REDLY_PIPE (
   .i_clk (CLK),
   .i_rst (RST),
   .i_vld (1'b1),
   .i_data (ppn_re),
   .o_vld_pp(),
   .o_data_pp(ppn_re_dly)
);

data_pipe #(
   .DATA_W (log2(DEPTH)),
   .PIPE_NUM (INPUTPIPELINE),
   .PIPE_MUX_EN(0),
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_WADDR_PIPE (
   .i_clk (CLK),
   .i_rst (RST),
   .i_vld (WE),
   .i_data (AddrW),
   .o_vld_pp(),
   .o_data_pp(ppn_waddr)
);

data_pipe #(
   .DATA_W (log2(DEPTH)),
   .PIPE_NUM (INPUTPIPELINE),
   .PIPE_MUX_EN(0),
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_RADDR_PIPE (
   .i_clk (CLK),
   .i_rst (RST),
   .i_vld (RE),
   .i_data (AddrR),
   .o_vld_pp(),
   .o_data_pp(ppn_raddr)
);

data_pipe #(
   .DATA_W (WIDTH),
   .PIPE_NUM (INPUTPIPELINE),
   .PIPE_MUX_EN(0),
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_WDATA_PIPE (
   .i_clk (CLK),
   .i_rst (RST),
   .i_vld (WE),
   .i_data (DIN),
   .o_vld_pp(),
   .o_data_pp(ppn_din)
);

data_pipe #(
   .DATA_W (WIDTH),
   .PIPE_NUM (DOUTPIPELINE),
   .PIPE_MUX_EN(0),
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_RDATA_PIPE (
   .i_clk (CLK),
   .i_rst (RST),
   .i_vld (ppn_re_dly),
   .i_data (ppn_dout),
   .o_vld_pp(),
   .o_data_pp(DOUT)
);

//----------channel selector----------//
assign real_we = ppn_we;
assign real_din = ppn_din;
assign real_waddr = ppn_waddr;

//----------write&read function----------//
always @(posedge CLK) begin
    if (real_we) begin
        mem[real_waddr] <= real_din;
    end
    else;
end

always @(posedge CLK) begin
    if (ppn_re) begin
        ppn_dout <= mem[ppn_raddr];
    end
    else;
end

`endif
`endif
"""

class MemWrapTop():
    def __init__(self):
        self.Prefix = ""
        self.Prefix_name = "MemWrapTop"
        self.tag = ""
        self.Type = "1R1W"
        self.Width = 100
        self.Depth = 20
        self.RTL = template_1R1W_TOP
        self.HEADER = ""
        self.BaseName = "RAMWRAP_1R1W_TOP"
        self.Note = "Use Define ASIC_COMPILE macro to use physical memory"


    def loadjson(self, DataDict):
        MEMWRAPLIST = ""
        i = 0
        for name, mem_tmp in DataDict.items():
            if mem_tmp["Type"] != "1R1W":
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
    SGCL0BCSR0UAN_{:d}X{:d}X1M4B memwrap (
       .CK         ( CLK           ),
       .RET        ( RST           ),
       .CSBN       ( real_we       ),
       .CSAN       ( RE            ),
       .A          ( AddrR         ),
       .B          ( real_waddr    ),
       .DI         ( real_din      ),
       .DO         ( DOUT          )
    );
end""".format(tag, int(Depth), int(Width), Prefix, self.Type, Prefix_name, int(Depth), int(Width), int(Depth), int(Width))
            i = i + 1
        self.RTL = self.RTL.replace("$MEMWRAPLIST$", "{:s}".format(MEMWRAPLIST))
        return self.RTL


    def gen_HEADER(self):
        TimeStamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.HEADER = """
//-----------------------------------------------------------------------------
// This file is generated by the script
//-----------------------------------------------------------------------------
// @File: 
// @Date: $TimeStamp$       
// @Note: $NOTE$
//-----------------------------------------------------------------------------
        """
        if TimeStamp != "":
            self.HEADER = self.HEADER.replace('$TimeStamp$', TimeStamp)
        self.HEADER = self.HEADER.replace('$NOTE$', self.Note)
        self.HEADER = self.HEADER.replace("@File:", "@File: RAMWRAP_1R1W_TOP")
        return self.HEADER

    def DumpRTL(self, filename):
        if filename!= "":
            fobj = open(filename, 'w')
            tmp_str = "\n".join([self.HEADER, self.RTL])
            fobj.write(tmp_str)
            logging.info("Write RTL\t{:<10s} into File:\t{:s}".format(self.BaseName, filename))
            fobj.close()
        else:
            logging.error("Filename is not defined %s", self.BaseName)

    def DumpLIST(self, filename):
        if filename!= "":
            fobj = open(filename, 'w')
            tmp_str = "$PROJECT_ROOT/rtl/common/"+"\n".join([filename[2:-2]])+".sv"+"\n"
            tmp_str += "$PROJECT_ROOT/rtl/common/mem/mem_init.v"+"\n"
            tmp_str += "$PROJECT_ROOT/rtl/common/pipe/data_pipe.v"+"\n"
            tmp_str += "$PROJECT_ROOT/rtl/common/ecc/ECC_GEN.sv"+"\n"
            tmp_str += "$PROJECT_ROOT/rtl/common/ecc/ECC_CHK.sv"+"\n"
            tmp_str += "$PROJECT_ROOT/rtl/common/ecc/m_ecc.sv"+"\n"
            fobj.write(tmp_str)
            logging.info("Write LIST\t{:<10s} into File:\t{:s}".format(self.BaseName, filename))
            fobj.close()
        else:
            logging.error("Filename is not defined %s", self.BaseName)

    def DumpTLIST(self, filename):
        if filename!= "":
            fobj = open("memwrapper_filelist.f", 'a')
            tmp_str = "\n" + "\n".join([filename])
            fobj.write(tmp_str)
            fobj.close()
        else:
            logging.error("Filename is not defined %s", self.BaseName)


def pretreatment(filename):  
    csv_tmp = open(filename).readlines()  
    csv_tmp[0] = '' #'delete the first line of csv'  
    with open('beta_memory_list.csv', 'w') as f:  
        f.writelines(csv_tmp)  

def process_csv2dict(filename):  
    pretreatment(filename)  
    mem_dict = dict()  
    table_obj = dict()  
    x = 0  
    with open('beta_memory_list.csv') as f:  
        f_csv = csv.DictReader(f)  
        for row in f_csv:  
            x = x + 1  
            mem_dict["MEM_INDEX_" + str(x)] = row  
        table_obj["MemoryWrapperList"] = mem_dict  
    return table_obj  

def gen_wrap_top(file_name, DIR="./"):
    ram_table = process_csv2dict(file_name)
    ram = dict()

    for k in ram_table["MemoryWrapperList"].keys():
        # print(k)        
        ram_attr_list = ram_table["MemoryWrapperList"][k]
        # print(ram_attr_list)
            
        ram_name = "RAMWRAP_{:s}_{:d}X{:d}".format(
            ram_attr_list["Type"],
            int(ram_attr_list["Depth"]),
            int(ram_attr_list["Width"])
        )
        if "Prefix" in ram_attr_list.keys() and ram_attr_list["Prefix"] != "":
            ram_name = ram_attr_list["Prefix"] + ram_name
        if ram_attr_list["Type"] not in ram.keys():
            ram[ram_attr_list["Type"]] = dict()
        ram[ram_attr_list["Type"]][ram_name] = ram_attr_list  # NOTE:all memory divided by Type
    for t in ram.keys():
        if t == "1R1W":
            MemTop_1R1W = MemWrapTop()
            MemTop_1R1W.gen_HEADER()
            MemTop_1R1W.loadjson(ram[t])
            MemTop_1R1W.DumpRTL(filename=os.path.join(DIR, "BETA_RAMWRAP_" + str(t) + "_TOP.sv"))
        else:
            logging.warning("This type memory (%s) cannot be supported", t)
    return ram

def test(filename):
    datadict = {
        "MEM1": {
            "Type": "1R1W",
            "Depth": 128,
            "Width": 512,
        },
        "MEM2": {
            "Type": "1R1W",
            "Depth": 32,
            "Width": 64,
            "Prefix": "TESTPREFIX"
        },
    }
    mem_tmp = MemWrapTop()
    mem_tmp.gen_HEADER()
    mem_tmp.loadjson(datadict)
    mem_tmp.DumpRTL(filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="program description")
    parser.add_argument("-i", help="input md file name")
    parser.add_argument("-o", help="output directory to store file name")
    parser.add_argument("-log", help="output log to file")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        datefmt="%Y/%m/%d %H:%M:%S",
                        format='%(asctime)s %(levelname)s: %(message)s (%(module)s-%(lineno)d-%(funcName)s)')
    if args.log:
        fhlr = logging.FileHandler(args.log)
        fhlr.setLevel(logging.DEBUG)
        fmt = logging.Formatter('%(asctime)s %(levelname)s: %(message)s (%(module)s-%(lineno)d-%(funcName)s)')
        fhlr.setFormatter(fmt)
        logging.getLogger().addHandler(fhlr)
    if args.i:
        logging.info("Input file is %s", args.i)
        gen_wrap_top(file_name=args.i, DIR=args.o)
    # test(filename="test.sv")