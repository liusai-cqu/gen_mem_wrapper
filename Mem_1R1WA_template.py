import logging
import re
import sys
import argparse
import math
import MemBaseClass
# import synopsys_db_mem_inst_template
synopsys_db_mem_inst_template = """"""

template_1R1WA = """
`ifndef GM_$BaseName$_SV_
`define GM_$BaseName$_SV_

module $BaseName$ #(
    parameter MEMPHY_CTRL_CFG_W = 24,
    parameter DEPTH             = $DEPTHS$,
    parameter WIDTH             = $WIDTHS$,
    parameter ASYN_RST_EN       = 0,    //default sync reset
    parameter INPUTPIPELINE = 0,
    parameter DOUTPIPELINE  = 1
)(
    //config
    input   logic [MEMPHY_CTRL_CFG_W-1:0]    memphy_ctrl_cfg,
    input   logic                             i_clkw,
    input   logic                             i_clkr,
    input   logic                             i_rstw,
    input   logic                             i_rstr,
    //----------------//
    input   logic                             i_re,
    input   logic [WIDTH-1:0]                 i_we,
    input   logic [$clog2(DEPTH)-1:0]         i_raddr,
    input   logic [$clog2(DEPTH)-1:0]         i_waddr,
    input   logic [WIDTH-1:0]                 i_din,
    output  logic [WIDTH-1:0]                 o_dout,
    //----ecc----//
    input   logic                             i_set_ecc_sb,
    input   logic                             i_set_ecc_db,
    input   logic                             i_ecc_bypass,
    output  logic                             o_ecc_sb,
    output  logic                             o_ecc_db,
    output  logic [$clog2(DEPTH)-1:0]         o_ecc_addr
);

//Reserve cutwrap & pipeline DEF
//----------------------------//
logic                           we_ppn    ;
logic                           re_ppn    ;
logic [$clog2(DEPTH)-1:0]       cutwrap_rvld   ;
logic [$clog2(DEPTH)-1:0]       waddr_ppn   ;
logic [$clog2(DEPTH)-1:0]       raddr_ppn   ;
logic [WIDTH-1:0]               din_ppn     ;
logic [WIDTH-1:0]               dout_ppn    ;
logic                           ecc_sb_ppn  ;
logic                           ecc_db_ppn  ;
logic [$clog2(DEPTH)-1:0]       ecc_addr_ppn;

//Reserve cutWrap Instantiate
//----------------------------//
$CUTWRAP_INST$

//Pipeline Config
//Here the RAMWRAP_PIPE parameter is greater than 1 to take effect
//----------------------------//
generate
    if (DOUTPIPELINE==0) begin:CUT_REDLY_EQ_ONE_BLK
        data_pipe #(
           .DATA_W     (1),
           .PIPE_NUM   (INPUTPIPELINE+1),
           .PIPE_MUX_EN(0),
            // 0: directly use the all pipe structure;
            // 0: the input data is directly write into MUX array;
            // 0: the output from MUX array will be directly outputted
           .FLOP_IN    (0),
           .FLOP_OUT   (0)
        ) U_CUT_REDLY_PIPE (
            //----clk&rst----//
           .i_clk   (i_clkr),
           .i_rst   (i_rstr),
            //----pipe in----//
           .i_vld   (1'b1),
           .i_data  (i_re),
            //----pipe out----//
           .o_vld_pp(),
           .o_data_pp(cutwrap_rvld)
        );
    end//CUT_REDLY_EQ_ONE_BLK
    else begin:CUT_REDLY_EQ_TWO_BLK
        data_pipe #(
           .DATA_W     (1),
           .PIPE_NUM   (INPUTPIPELINE+2),
           .PIPE_MUX_EN(0),
            // 0: directly use the all pipe structure;
            // 0: the input data is directly write into MUX array;
            // 0: the output from MUX array will be directly outputted
           .FLOP_IN    (0),
           .FLOP_OUT   (0)
        ) U_CUT_REDLY_PIPE (
            //----clk&rst----//
           .i_clk   (i_clkr),
           .i_rst   (i_rstr),
            //----pipe in----//
           .i_vld   (1'b1),
           .i_data  (i_re),
            //----pipe out----//
           .o_vld_pp(),
           .o_data_pp(cutwrap_rvld)
        );
    end//CUT_REDLY_EQ_TWO_BLK
endgenerate

generate
    if (DOUTPIPELINE == 0 || DOUTPIPELINE == 1) begin:NO_PIPE_AF_ECC_CHK_BLK
        assign o_dout   = dout_ppn    ;
        assign o_ecc_sb = ecc_sb_ppn  ;
        assign o_ecc_db = ecc_db_ppn  ;
        assign o_ecc_addr = ecc_addr_ppn ;
    end//NO_PIPE_AF_ECC_CHK_BLK
    else begin:PIPE_ONE_AF_ECC_CHK_BLK
        data_pipe #(
           .DATA_W     (WIDTH+($clog2(DEPTH))),
           .PIPE_NUM   (DOUTPIPELINE-1),
           .PIPE_MUX_EN(0),
            // 0: directly use the all pipe structure;
            // 0: the input data is directly write into MUX array;
            // 0: the output from MUX array will be directly outputted
           .FLOP_IN    (0),
           .FLOP_OUT   (0)
        ) U_DOUT_ECC_ADDR_PIPE (
            //----clk&rst----//
           .i_clk   (i_clkr),
           .i_rst   (i_rstr),
            //----pipe in----//
           .i_vld   (cutwrap_rvld),
           .i_data  ({dout_ppn,ecc_addr_ppn}),
            //----pipe out----//
           .o_vld_pp(),
           .o_data_pp({o_dout,o_ecc_addr})
        );
    end
endgenerate

generate
    if (INPUTPIPELINE == 0 || INPUTPIPELINE == 1) begin:NO_EXTRA_INPUT_PIPE_BLK
        assign we_ppn   = i_we    ;
        assign re_ppn   = i_re    ;
        assign waddr_ppn = i_waddr ;
        assign raddr_ppn = i_raddr ;
        assign din_ppn  = i_din   ;
    end//NO_EXTRA_INPUT_PIPE_BLK
    else begin:EXTRA_INPUT_PIPE_BLK
        data_pipe #(
           .DATA_W     (WIDTH+($clog2(DEPTH))),
           .PIPE_NUM   (INPUTPIPELINE-1),
           .PIPE_MUX_EN(0),
            // 0: directly use the all pipe structure;
            // 0: the input data is directly write into MUX array;
            // 0: the output from MUX array will be directly outputted
           .FLOP_IN    (0),
           .FLOP_OUT   (0)
        ) U_DIN_WADDR_PIPE (
            //----clk&rst----//
           .i_clk   (i_clkw),
           .i_rst   (i_rstw),
            //----pipe in----//
           .i_vld   (1'b1),
           .i_data  ({i_din,i_waddr}),
            //----pipe out----//
           .o_vld_pp(we_ppn),
           .o_data_pp({din_ppn,waddr_ppn})
        );
        data_pipe #(
           .DATA_W     ($clog2(DEPTH)),
           .PIPE_NUM   (INPUTPIPELINE-1),
           .PIPE_MUX_EN(0),
            // 0: directly use the all pipe structure;
            // 0: the input data is directly write into MUX array;
            // 0: the output from MUX array will be directly outputted
           .FLOP_IN    (0),
           .FLOP_OUT   (0)
        ) U_RADDR_PIPE (
            //----clk&rst----//
           .i_clk   (i_clkr),
           .i_rst   (i_rstr),
            //----pipe in----//
           .i_vld   (1'b1),
           .i_data  (i_raddr),
            //----pipe out----//
           .o_vld_pp(re_ppn),
           .o_data_pp(raddr_ppn)
        );
    end
endgenerate

//PHY_BACKDOOR
//physical memory backdoor tasks
//----------------------------//
`ifdef PHY_BACKDOOR
localparam ECCGRP_NUM  = $ECCGRPNUM$;
localparam ECC_WIDTH   = $ECCWIDTH$;
localparam ECCGRP_DWIDTH = $ECCGRPDWIDTH$-$ECC_WIDTH$/$ECCGRP_NUM$;
localparam ECCGRP_WIDTH = $ECCGRPWIDTH$;

$READ_DEF$
logic [ECCGRP_WIDTH*ECCGRP_NUM-1:0] mem_dout;
task read_word(input [$clog2(DEPTH)-1:0] address_r,
               output [WIDTH-1:0] data_out,
               output           ecc_sb,
               output           ecc_db);
    ecc_function#(.WIDTH(ECCGRP_DWIDTH)) ecc_func;
    ecc_func = new();
$READ_WORD$
endtask

$WRITE_DEF$
task write_word(input [$clog2(DEPTH)-1:0] address_w,
                input [WIDTH-1:0] data_in,
                int idx1=1,      int idx2=1);
    logic [WIDTH+ECC_WIDTH-1:0] task_din;
    logic [ECC_WIDTH-1:0]       ecc_data;
    ecc_function#(.WIDTH(ECCGRP_DWIDTH)) ecc_func;
    ecc_func = new();
$ECC_PACKET$
    if(ECC_WIDTH>0)
        task_din = {ecc_data,data_in};
    else
        task_din = data_in;
    if((idx1>=WIDTH+ECC_WIDTH)||(idx2>=WIDTH+ECC_WIDTH))
        $error(" << Flip parameter out of range,Please check the parameters!>>");
    if(idx1 >=0) task_din[idx1] = ~task_din[idx1];
    if(idx2 >=0) task_din[idx2] = ~task_din[idx2];
$WRITE_WORD$
endtask

$GLB_WRITE_DEF$
task glb_write_word(
    input [WIDTH-1:0] data_in
);
    logic [WIDTH+ECC_WIDTH-1:0] task_din;
    logic [ECC_WIDTH-1:0]       ecc_data;
    ecc_function#(.WIDTH(ECCGRP_DWIDTH)) ecc_func;
    ecc_func = new();
$ECC_PACKET$
    task_din = {ecc_data,data_in};
$GLB_WRITE_WORD$
endtask
`endif

endmodule

//cut wrapper of $TYPE$ $DEPTH$X$WIDTH$
//----------------------------------------//
module $BaseName$_cutwrap #(
    parameter MEMPHY_CTRL_CFG_W = 21,
    parameter INPUTPIPELINE = 1,
    parameter DOUTPIPELINE  = 1,
    parameter ASYN_RST_EN   = 0,    //default sync reset
    parameter DEPTH         = $DEPTH$,
    parameter WIDTH         = $WIDTH$
)(
    input   [MEMPHY_CTRL_CFG_W-1:0]memphy_ctrl_cfg,
    input   logic                   i_cut_clkw,
    input   logic                   i_cut_clkr,
    input   logic                   i_cut_rstw,
    input   logic                   i_cut_rstr,
    //----------------//
    input   logic                   i_cut_re,
    input   logic [WIDTH-1:0]       i_cut_we,
    input   logic [$clog2(DEPTH)-1:0] i_cut_raddr,
    input   logic [$clog2(DEPTH)-1:0] i_cut_waddr,
    input   logic [WIDTH-1:0]       i_cut_din,
    output  logic [WIDTH-1:0]       o_cut_dout,
    //----ecc----//
    input   logic                   i_cut_set_ecc_sb,
    input   logic                   i_cut_set_ecc_db,
    input   logic                   i_cut_ecc_bypass,
    output  logic                   o_cut_ecc_sb,
    output  logic                   o_cut_ecc_db,
    output  logic [$clog2(DEPTH)-1:0] o_cut_ecc_addr
);

//localparam
//----------------------------//
localparam ECCGRP_NUM  = $ECCGRPNUM$;
localparam ECC_WIDTH   = $ECCWIDTH$;
localparam ECCGRP_DWIDTH = $ECCGRPDWIDTH$;
localparam ECCGRP_WIDTH = $ECCGRPWIDTH$;

//ecc logic Instantiation
//----------------------------//
$ECC_DEF$

//ecc signal merging and splitting
//----------------------------//
assign ecc_gen_din = $ECC_GEN_DIN$;
$ECC_N$
$ECC_CHK_DIN$
assign ecc_sb_merge = $ECC_SB_MERGE$;
assign ecc_db_merge = $ECC_DB_MERGE$;

assign cut_phy_din   = $CUT_PHY_DIN$;
assign cut_phy_dout_tmp = $CUT_PHY_DOUT$;
assign o_cut_dout    = $CUT_DOUT$;

//ECC flag set
//----------------------------//
generate
    if(ASYN_RST_EN==0)begin:SYNC_RST
        always_ff @(posedge i_cut_clkr) begin
            if(i_cut_rstr)begin:
                set_sb_dly <= 1'h0 ;
                set_db_dly <= 1'h0 ;
            end else begin:
                set_sb_dly <= i_cut_set_ecc_sb ;
                set_db_dly <= i_cut_set_ecc_db ;
            end
        end
        always @(posedge i_cut_clkr) begin
            if(i_cut_rstr) begin:
                ecc_sb_flag <= 1'b0 ;
            end else if(w_set_sb_rise) begin:
                ecc_sb_flag <= 1'b1 ;
            end else if(cutwrap_rdata_vld) begin:
                ecc_sb_flag <= 1'b0 ;
            end
        end
        always @(posedge i_cut_clkr) begin
            if(i_cut_rstr) begin:
                ecc_db_flag <= 1'b0 ;
            end else if(w_set_db_rise) begin:
                ecc_db_flag <= 1'b1 ;
            end else if(cutwrap_rdata_vld) begin:
                ecc_db_flag <= 1'b0 ;
            end
        end
    end
    else begin:ASYN_RST
        always_ff @(posedge i_cut_clkr or posedge i_cut_rstr) begin
            if(i_cut_rstr) begin:
                set_sb_dly <= 1'h0 ;
                set_db_dly <= 1'h0 ;
            end else begin:
                set_sb_dly <= i_cut_set_ecc_sb ;
                set_db_dly <= i_cut_set_ecc_db ;
            end
        end
        always @(posedge i_cut_clkr or posedge i_cut_rstr) begin
            if(i_cut_rstr) begin:
                ecc_sb_flag <= 1'b0 ;
            end else if(w_set_sb_rise) begin:
                ecc_sb_flag <= 1'b1 ;
            end else if(cutwrap_rdata_vld) begin:
                ecc_sb_flag <= 1'b0 ;
            end
        end
        always @(posedge i_cut_clkr or posedge i_cut_rstr) begin
            if(i_cut_rstr) begin:
                ecc_db_flag <= 1'b0 ;
            end else if(w_set_db_rise) begin:
                ecc_db_flag <= 1'b1 ;
            end else if(cutwrap_rdata_vld) begin:
                ecc_db_flag <= 1'b0 ;
            end
        end
    end
endgenerate

assign w_set_sb_rise = (set_sb_dly,i_cut_set_ecc_sb) == 2'b01;
assign w_set_db_rise = (set_db_dly,i_cut_set_ecc_db) == 2'b01;
assign o_cut_ecc_sb = cutwrap_rdata_vld? ecc_sb_flag | ecc_sb_merge : 1'b0;
assign o_cut_ecc_db = cutwrap_rdata_vld? ecc_db_flag | ecc_db_merge : 1'b0;

//Pipeline Config
//Here the RAMWRAP_PIPE parameter is Only one shot
//----------------------------//
data_pipe #(
   .DATA_W     (1),
   .PIPE_NUM   (1),
   .PIPE_MUX_EN(0),
    // 0: directly use the all pipe structure;
    // 0: the input data is directly write into MUX array;
    // 0: the output from MUX array will be directly outputted
   .FLOP_IN    (0),
   .FLOP_OUT   (0)
) U_PRE_REDLY_PIPE (
    //----clk&rst----//
   .i_clk   (i_cut_clkr),
   .i_rst   (i_cut_rstr),
    //----pipe in----//
   .i_vld   (1'b1),
   .i_data  (i_cut_re_ppl),
    //----pipe out----//
   .o_vld_pp(),
   .o_data_pp(cut_re_ppl_dly)
);

data_pipe #(
   .DATA_W     ($clog2(DEPTH)),
   .PIPE_NUM   (1),
   .PIPE_MUX_EN(0),
    // 0: directly use the all pipe structure;
    // 0: the input data is directly write into MUX array;
    // 0: the output from MUX array will be directly outputted
   .FLOP_IN    (0),
   .FLOP_OUT   (0)
) U_CUTADDR_PIPE (
    //----clk&rst----//
   .i_clk   (i_cut_clkr),
   .i_rst   (i_cut_rstr),
    //----pipe in----//
   .i_vld   (1'b1),
   .i_data  (i_cut_raddr_ppl),
    //----pipe out----//
   .o_vld_pp(),
   .o_data_pp(raddr_ppn)
);

generate
    if (DOUTPIPELINE == 0) begin:NO_PIPE_AF_DB_BLK
        assign cut_phy_dout    = cut_phy_dout_pre ;
        assign cutwrap_rdata_vld = cut_re_ppl_dly ;
        assign o_cut_ecc_addr   = cut_raddr_ppl_dly ;
    end//NO_PIPE_AF_DB_BLK
    else begin:PIPE_AF_DB_BLK
        data_pipe #(
           .DATA_W     (($clog2(DEPTH))+(ECCGRP_WIDTH+ECCGRP_NUM)),
           .PIPE_NUM   (1),
           .PIPE_MUX_EN(0),
            // 0: directly use the all pipe structure;
            // 0: the input data is directly write into MUX array;
            // 0: the output from MUX array will be directly outputted
           .FLOP_IN    (0),
           .FLOP_OUT   (0)
        ) U_ECCADDR_RDATA_PIPE (
            //----clk&rst----//
           .i_clk   (i_cut_clkr),
           .i_rst   (i_cut_rstr),
            //----pipe in----//
           .i_vld   (cut_re_ppl_dly),
           .i_data  ({cut_raddr_ppl_dly,cut_phy_dout_pre}),
            //----pipe out----//
           .o_vld_pp (cutwrap_rdata_vld),
           .o_data_pp ({o_cut_ecc_addr,cut_phy_dout})
        );
    end
endgenerate

generate
    if (INPUTPIPELINE == 0) begin:NO_PIPE_AF_ECC_GEN_BLK
        assign cut_we_ppl   = i_cut_we    ;
        assign cut_re_ppl   = i_cut_re    ;
        assign cut_waddr_ppl = i_cut_waddr ;
        assign cut_raddr_ppl = i_cut_raddr ;
        assign cut_phy_din_ppl = cut_phy_din ;
    end//NO_PIPE_AF_ECC_GEN_BLK
    else begin:PIPE_ONE_AF_ECC_GEN_BLK
        data_pipe #(
           .DATA_W     ($clog2(DEPTH)+WIDTH+ECC_WIDTH),
           .PIPE_NUM   (1),
           .PIPE_MUX_EN(0),
            // 0: directly use the all pipe structure;
            // 0: the input data is directly write into MUX array;
            // 0: the output from MUX array will be directly outputted
           .FLOP_IN    (0),
           .FLOP_OUT   (0)
        ) U_WADDR_WDATA_PIPE (
            //----clk&rst----//
           .i_clk   (i_cut_clkw),
           .i_rst   (i_cut_rstw),
            //----pipe in----//
           .i_vld   (1'b1),
           .i_data  ({i_cut_waddr,cut_phy_din}),
            //----pipe out----//
           .o_vld_pp (cut_we_ppl),
           .o_data_pp ({cut_waddr_ppl,cut_phy_din_ppl})
        );
        data_pipe #(
           .DATA_W     ($clog2(DEPTH)),
           .PIPE_NUM   (1),
           .PIPE_MUX_EN(0),
            // 0: directly use the all pipe structure;
            // 0: the input data is directly write into MUX array;
            // 0: the output from MUX array will be directly outputted
           .FLOP_IN    (0),
           .FLOP_OUT   (0)
        ) U_RADDR_PIPE (
            //----clk&rst----//
           .i_clk   (i_cut_clkr),
           .i_rst   (i_cut_rstr),
            //----pipe in----//
           .i_vld   (1'b1),
           .i_data  (i_cut_raddr),
            //----pipe out----//
           .o_vld_pp (cut_re_ppl),
           .o_data_pp (cut_raddr_ppl)
        );
    end
endgenerate

//PHYWRAPPER
//Realize memory splicing
//----------------------------//
$PHYWRAP_DEF$
reg [WIDTH+ECC_WIDTH-1:0] phy_din ;
//physical memory instantiation
//----------------------------//
$PHYWRAP_INST$

assign phy_din        = cut_phy_din_ppl;
assign cut_phy_dout_pre = $PHY_DOUTS$;
//----//
$PHY_RE$
assign phy_raddr      = $PHY_RADDRS$;
assign phy_waddr      = $PHY_WADDRS$;
assign phy_dout_tmp   = $PHY_DOUT_TMPS$;
always_ff @(posedge i_cut_clkr) begin
    $PHY_RE_OLT$
end

endmodule

`endif

//PHYSICAL_DB
//use vendor physical memory
//----------------------------//
`ifndef $PHYWRAPNAME$_SV
`define $PHYWRAPNAME$_SV
module $PHYWRAPNAME$ #(
    parameter MEMPHY_CTRL_CFG_W    = 21,
    parameter DB_WIDTH             = $DBWIDTH$,
    parameter DB_ADDRWIDTH         = $DBADDRWIDTH$
)(
    //config default is {1'b0,1'b0,1'b0,1'b1,4'b0011,1'b1,4'b0011,1'b1,4'b0011,3'b101,3'b000}
    //TEST1:[23],TEST_RNW:[22],TESTRM[21],RME:[20],RM:[19:16],RMA:[15],RMA:[14:11],RMB:[10],EMB:[9:6],WA:[5:3],MPULSE:[2:0]}
    input   [MEMPHY_CTRL_CFG_W-1:0] memphy_ctrl_cfg,
    input   logic                   i_phy_clkw,
    input   logic                   i_phy_clkr,
    input   logic                   i_phy_re,
    input   logic                   i_phy_we,
    input   [DB_ADDRWIDTH-1:0]      i_phy_raddr,
    input   [DB_ADDRWIDTH-1:0]      i_phy_waddr,
    input   [DB_WIDTH-1:0]          i_phy_din,
    output  logic [DB_WIDTH-1:0]    o_phy_dout
);

$PHY_DB_INST$

endmodule
`endif

//Script testing is dedicated, no real physical_db is required
//----------------------------//
`ifdef FAKE_PHY_MEM
`ifndef $DBNAME$_SV
`define $DBNAME$_SV
module $MDU_DBNAME$#(
    parameter DB_WIDTH     = $DBWIDTH$,
    parameter DB_ADDRWIDTH = $DBADDRWIDTH$
)(
    input           CLKR,
    input           REB,
    input           WEB,
    input [DB_ADDRWIDTH-1:0] ARA,
    input [DB_ADDRWIDTH-1:0] AMA,
    input [DB_ADDRWIDTH-1:0] AMB,
    input [DB_WIDTH-1:0]    DADIO,
    input           REDENIO,
    input           DFEN,
    input           DFTBYP,
    input           STC,
    input [1:0]     SID,
    output [1:0]    SOC,
    output [1:0]    SOD,
    input [1:0]     DSLPLV,
    input [1:0]     KP,
    input [1:0]     WCT,
    input [1:0]     RCT
);

//---- readMemory;
task readMemory;
    input [DB_ADDRWIDTH-1:0] address_w;
    $display ("This is a fake physical DB");
endtask

//---- writeMemory;
task writeMemory;
    input [DB_ADDRWIDTH-1:0] address_r;
    input [DB_ADDRWIDTH-1:0] data_in;
    input [DB_WIDTH-1:0]    data_out;
    $display ("This is a fake physical DB");
endtask

task printMemory;
    $display ("This is a fake physical DB");
endtask
endmodule
`endif
`endif

"""

class Mem1R1WA(MemBaseClass.MemBase_Cut):
    def __init__(self, Depth, Width, DB_Depth, DB_Width, DB_Name, ECC_Grp, Fadio_dict, Type_list, ECC_enable="NO"):
        super().__init__(Depth, Width, DB_Depth, DB_Width, DB_Name, ECC_Grp, Fadio_dict, Type_list, ECC_enable)
        logging.debug("==Generating Mem1R1WA Obj.===")
        self.Type = "1R1WA"
        self.RTL = template_1R1WA

    def Rep_CUTWRAP_INST(self):
        CUTWRAP_INST = """
{:s}_cutwrap = 
   .MEMPHY_CTRL_CFG_W(MEMPHY_CTRL_CFG_W),
   .ASYNC_RST_EN(ASYNC_RST_EN),
   .INPUTPIPELINE(INPUTPIPELINE),
   .DOUTPIPELINE(DOUTPIPELINE)
cutwrap (
   .memphy_ctrl_cfg   ( memphy_ctrl_cfg ),
   .i_cut_clk         ( i_cut_clk       ),
   .i_cut_rst         ( i_cut_rst       ),
   .i_cut_rstw        ( i_cut_rstw      ),
   .i_cut_we          ( we_ppn          ),
   .i_cut_raddr       ( r_addr_ppn      ),
   .i_cut_waddr       ( waddr_ppn       ),
   .i_cut_din         ( din_ppn         ),
   .o_cut_dout        ( dout_ppn        ),
   .i_cut_set_ecc_sb  ( i_set_ecc_sb    ),
   .i_cut_set_ecc_db  ( i_set_ecc_db    ),
   .i_cut_ecc_bypass  ( i_cut_ecc_bypass),
   .o_cut_ecc_sb      ( ecc_sb_ppn      ),
   .o_cut_ecc_addr    ( ecc_addr_ppn    )
);
""".format(self.BaseName)
        CUTWRAP_INST = CUTWRAP_INST.replace("\n\n", "\n").strip("\n")
        self.RTL = self.RTL.replace("$CUTWRAP_INST$", "{:s}".format(CUTWRAP_INST))
        return self.RTL

    def PHY_DB_INST(self):
        if (self.Type_list[0] == "drl") and (self.Type_list[1] == "0"):
            PHY_DB_INST = synopsys_db_mem_inst_template.PHY_DB_INST_DRL_NOMASK
        elif (self.Type_list[0] == "drl") and (self.Type_list[1] == "1"):
            PHY_DB_INST = synopsys_db_mem_inst_template.PHY_DB_INST_DRL_MASK
        elif (self.Type_list[0] == "cul") or (self.Type_list[0] == "sul") and (self.Type_list[1] == "0"):
            PHY_DB_INST = synopsys_db_mem_inst_template.PHY_DB_INST_CUL_SUL_NOMASK
        elif (self.Type_list[0] == "cul") or (self.Type_list[0] == "sul") and (self.Type_list[1] == "1"):
            PHY_DB_INST = synopsys_db_mem_inst_template.PHY_DB_INST_CUL_SUL_MASK
        else:
            logging.error("the 1r1wa memory is not among drl/cul/sul")
        PHY_DB_INST = PHY_DB_INST.replace("$MDU_DBNAME$", "{:s}".format(self.DB_Name.lower()))

        if (self.Type_list[2] == "00"):  # not split SI_DA/SI_OB/SO_DA/SO_OB
            SI_SO_PORT = """"
           .SI_DA(1'b0),
           .SO_DA(    ),
           .SI_QB(1'b0),
           .SO_QB(    )
           """
        elif (self.Type_list[2] == "10"):
            SI_SO_PORT = """
.SI_D_HA(1'b0),
.SO_D_LA(
.SI_Q_LB(1'b0),
.SI_Q_HB(1'b0),
.SO_Q_LB(
.SO_Q_HB(
"""
        PHY_DB_INST = PHY_DB_INST.replace("$PHY_RE_INST$", "i_phy_re")
        PHY_DB_INST = PHY_DB_INST.replace("$PHY_DOUT_INST$", "o_phy_dout")
        PHY_DB_INST = PHY_DB_INST.replace("$SI_SO_PORT$", "{:s}".format(SI_SO_PORT))
        PHY_DB_INST = PHY_DB_INST.replace("$ASYNC_WCLK$", "i_phy_clk")
        PHY_DB_INST = PHY_DB_INST.replace("$ASYNC_RCLK$", "i_phy_clk")
        self.RTL = self.RTL.replace("$PHY_DB_INST$", "{:s}".format(PHY_DB_INST))
        return self.RTL

    # def Rep_BACKDOOR(self):
    #     READ_DEF = ""
    #     WRITE_DEF = ""
    #     READ_WORD = ""
    #     WRITE_WORD = ""
    #     ECC_CHECK = ""
    #     ECC_PACKET = ""
    #     DATATMPLIST = list()
    #     ECCGRP_DATALIST = list()
    #     READ_DATAXLIST = list()
    #     READ_DATATMPLIST = list()
    #     WC_DATALIST = list()
    #     ECC_RDATALIST = list()
    #     # READ_DEF
    #     for i in range(self.db.dp.x):
    #         READ_DATAXLIST.append("".join(["datax{:d}".format(i)]))
    #     READ_DEF += "    *0+logic [{}:0]".format(self.db.width - 1,)+",".join(READ_DATAXLIST)+";\n"
    #     for i in range(self.ECC_Grp):
    #         READ_DATATMPLIST.append("".join(["datatmp{:d}".format(i)]))
    #     READ_DEF += "    *0+logic [{}:0]".format(ECCGRP_WIDTH - 1,)+",".join(ECCGRP_DATALIST)+";\n"
    #     READ_DEF += "    *4+logic [{}:0]".format(ECCGRP_WIDTH * 2 - 1,)+",".join(READ_DATATMPLIST)+";\n"
    #     if ((self.selbits_h == -1) and (self.selbits_l == -1)) or (self.selbits_h == self.phyaddr_h):
    #         READ_DEF += "    *0+logic sel;\n"
    #         WRITE_DEF += "    *4+logic sel;\n"
    #         WRITE_WORD += "    *4+sel = 1'b0;\n"
    #     elif (self.selbits_h != -1) and (self.selbits_l != -1):
    #         READ_DEF += "    *0+logic sel;\n"
    #         READ_WORD += "    *4+sel = address_r[{}:{}];\n".format(self.selbits_h, self.selbits_l)
    #         WRITE_WORD += "    *4+sel = address_w[{}:{}];\n".format(self.selbits_h, self.selbits_l)
    #     else:
    #         READ_DEF += "    *0+logic [{}:{}] sel;\n".format(self.selbits_h - self.selbits_l, 0)
    #         WRITE_DEF += "    *4+logic [{}:{}] sel;\n".format(self.selbits_h - self.selbits_l, 0)
    #         READ_WORD += "    *4+sel = address_r[{}:{}];\n".format(self.selbits_h, self.selbits_l)
    #         WRITE_WORD += "    *4+sel = address_w[{}:{}];\n".format(self.selbits_h, self.selbits_l)
    #         READ_WORD += "    *4+logic [{}:{}] addr;\n".format(self.phyaddr_h - self.phyaddr_l, 0)
    #         WRITE_WORD += "    *4+logic [{}:{}] addr;\n".format(self.phyaddr_h - self.phyaddr_l, 0)
    #     # READ_WORD += "    *0+ifdef FAKE_PHY_MEM\n"
    #     # READ_WORD += "    *0+else\n"
    #     READ_WORD += "    *4+case(sel)\n"
    #     WRITE_WORD += "    *4+addr = address_w[{}:{}];\n".format(self.phyaddr_h, self.phyaddr_l)
    #     WRITE_WORD += "    *4+case(sel)\n"
    #     for i in range(self.ECC_Grp):
    #         tmp_high = (i + 1) * self.ECCGRP_Dwidth - 1
    #         tmp_low = i * self.ECCGRP_Dwidth
    #         if tmp_high < self.Width:
    #             ECC_WDATALIST.append("".join(["ecc_func_get_rtl_ecc(data_in[{}:{}])".format(tmp_high, tmp_low)]))
    #         else:
    #             ECC_WDATALIST.append("".join(["ecc_func_get_rtl_ecc({}d{}ho,data_in[{}:{}d{}])".format(tmp_high - self.Width + 1, self.Width - 1, tmp_high, tmp_low)]))
    #     ECC_PACKET = "    *4+ecc_data = {{"+",".join(ECC_WDATALIST[:-1])+"}};\n"

    #     if self.db.x == 1:
    #         tmp_width = self.db.Width
    #     else:
    #         tmp_width = self.db.Width
    #     # for i in range(self.db.y):
    #     #     counter=0
    #     #     READ_WORD += "    *8+str({})+":+"begin"+"\n"
    #     #     WRITE_WORD += "    *8+str({})+":+"begin"+"\n"
    #     #     for j in range(self.db.x):
    #     #         tmp_high = min((counter + 1) * tmp_width - 1, self.Width - 1 + (self.ECC_bits))
    #     #         tmp_low = counter * tmp_width
    #     #         counter = counter + 1
    #     #         WRITE_WORD += "    *12+cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.mem_core_array[addr] = task_din[{}:{}];\n".format(j, i, tmp_high, tmp_low)
    #     #         READ_WORD += "    *12+datax{{:d}}=cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.mem_core_array[addr];\n".format(j, j, i)
    #     #         READ_WORD += "    *12+cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.write_mem_red(addr, task_din[{}:{}]);\n".format(j, i, tmp_high, tmp_low)
    #     #     # SYNOPSYS model
    #     #     READ_WORD += "    *8+end"+"\n"
    #     #     WRITE_WORD += "    *8+end"+"\n"
    #     # #READ_WORD += "    *4+endcase"+"\n"
    #     # #WRITE_WORD += "    *4+endcase"+"\n"
    #     for i in range(self.db.y):
    #         counter = 0
    #         READ_WORD += "    "*8+str(i)+":"+"begin"+"\n"
    #         WRITE_WORD += "   "*8+str(i)+":"+"begin"+"\n"
    #         READ_WORD += "    "*12+"`ifdef FAST_PHY_MODEL\n"
    #         WRITE_WORD += "    "*12+"`ifdef FAST_PHY_MODEL\n"
    #         for j in range(self.db.x):
    #             tmp_high = min((counter + 1) * tmp_width - 1, self.Width - 1 + (self.ECC_bits))
    #             tmp_low = counter * tmp_width
    #             counter = counter + 1
    #             WRITE_WORD += "    *12+cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.mem_core_array[addr] = task_din[{}:{}];\n".format(j, i, tmp_high, tmp_low)
    #             # SYNOPSYS no - fast model
    #             READ_WORD += "    *12+datax{{:d}}=cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.mem_core_array[addr];\n".format(j, j, i)
    #             READ_WORD += "    *12+cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.write_mem_red(addr, task_din[{}:{}]);\n".format(j, i, tmp_high, tmp_low)
    #         READ_WORD += "    *12+else\n"
    #         WRITE_WORD += "    *12+else\n"
    #         for j in range(self.db.x):
    #             tmp_high = min((counter + 1) * tmp_width - 1, self.Width - 1 + (self.ECC_bits))
    #             tmp_low = counter * tmp_width
    #             counter = counter + 1
    #             WRITE_WORD += "    *12+cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.write_mem_red(addr, task_din[{}:{}]);\n".format(j, i, tmp_high, tmp_low)
    #             # SYNOPSYS no - fast model
    #             READ_WORD += "    *12+cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.read_mem_red(datax{{:d}}, addr);\n".format(j, i, j)
    #         READ_WORD += "    *12+endif\n"
    #         WRITE_WORD += "    *12+endif\n"
    #         READ_WORD += "    *8+end"+"\n"
    #         WRITE_WORD += "    *8+end"+"\n"
    #     # READ_WORD += "    *4+endcase"+"\n"
    #     # WRITE_WORD += "    *4+endcase"+"\n"

    #     # generate glb_write_task here
    #     # for i in range(self.db.y):
    #     GLB_WRITE_WORD += "    *4+for(integer k=0;k<{};k=k+1)begin\n".format(self.db.Depth)
    #     counter = 0
    #     for j in range(self.db.x):
    #         tmp_high = min((counter + 1) * tmp_width - 1, self.Width - 1 + (self.ECC_bits))
    #         tmp_low = counter * tmp_width
    #         counter = counter + 1
    #         GLB_WRITE_WORD += "    *8+cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.mem_core_array[k]= task_din[{}:{}];\n".format(j, i, tmp_high, tmp_low)
    #         GLB_WRITE_WORD += "    *8+cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.write_mem_red(k, task_din[{}:{}]);\n".format(j, i, tmp_high, tmp_low)
    #     GLB_WRITE_WORD += "    *4+end\n"

    #     for i in range(self.db.y):
    #         GLB_WRITE_WORD += "    *4+for(integer k=0;k<{};k=k+1)begin\n".format(self.db.Depth)
    #         counter = 0
    #         GLB_WRITE_WORD += "    *8+ifdef FAST_PHY_MODEL\n"
    #         for j in range(self.db.x):
    #             tmp_high = min((counter + 1) * tmp_width - 1, self.Width - 1 + (self.ECC_bits))
    #             tmp_low = counter * tmp_width
    #             counter = counter + 1
    #             GLB_WRITE_WORD += "    *8+cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.mem_core_array[k]= task_din[{}:{}];\n".format(j, i, tmp_high, tmp_low)
    #         GLB_WRITE_WORD += "    *8+else\n"
    #         for j in range(self.db.x):
    #             tmp_high = min((counter + 1) * tmp_width - 1, self.Width - 1 + (self.ECC_bits))
    #             tmp_low = counter * tmp_width
    #             counter = counter + 1
    #             GLB_WRITE_WORD += "    *8+cutwrap.phywrapx{{:d}y{:d}}.memCell.uut.write_mem_red(k, task_din[{}:{}]);\n".format(j, i, tmp_high, tmp_low)
    #         GLB_WRITE_WORD += "    *8+endif\n"
    #         GLB_WRITE_WORD += "    *4+end\n"

    #     # merge parsing ecc
    #     for j in range(self.db.x):
    #         ECC_RDATALIST.append("".join(["datax{}{}".format(j)]))
    #     ECC_CHECK += "    *4+mem_dout = {{"+",".join(ECC_RDATALIST[:-1])+"}};\n"
    #     for i in range(self.ECC_Grp):
    #         tmp_high = (i + 1) * self.ECCGRP_Dwidth - 1
    #         tmp_low = i * self.ECCGRP_Dwidth
    #         tmp_ecc = self.Width * self.ECCGRP_Dwidth / self.ECC_Grp
    #         DATATMPLIST.append("".join(["datatmp{{:d}}".format(i)]))
    #         if (self.ECC_bits != 0):
    #             if (self.ECCGRP_Dwidth * self.ECC_Grp != self.Width) and (i == self.ECC_Grp - 1):
    #                 ECC_CHECK += "    *4+data_eccgrp{{:d}}.format(i)+ = {mem_dout[{}:{}],mem_dout[{}:{}]};".format(tmp_ecc_h, tmp_ecc_l, tmp_high, tmp_low)+"\n"
    #             else:
    #                 ECC_CHECK += "    *4+data_eccgrp{{:d}}.format(i)+ = data_eccgrp{{:d}}.format(i)+ = {mem_dout[{}:{}]};".format(tmp_high, tmp_low)+"\n"
    #         else:
    #             ECC_CHECK += "    *4+data_eccgrp{{:d}}.format(i)+ = data_eccgrp{{:d}}.format(i)+ = data_eccgrp{{:d}}.format(i)+;\n"
    #             ECC_CHECK += "    *4+data_eccgrp{{:d}}.format(i)+ = ecc_func.con_rtl_ecc(data_eccgrp{{:d}}[ECCGRP_WIDTH - 1:0],".format(i)+"\n"+"    \t*9+data_eccgrp{{:d}}[ECCGRP_WIDTH - 1:ECCGRP_WIDTH]);".format(i)+"\n"
    #     if (self.ECC_bits != 0):
    #         ECC_DEF += "    *0+logic [{}:0]".format(ECC_WIDTH + ECCGRP_NUM - 1,)+"    *7+, ".join(["ecc_"+str(i) for i in range(self.ECC_Grp)])+"\n"
    #         ECC_DEF = ECC_DEF.replace("\n\n", "\n").strip("\n")
    #         self.RTL = self.RTL.replace("$ECC_DEFS$", "{:s}".format(ECC_DEF))
    #     return self.RTL

    def Rep_ECC_INST(self):
        ECC_INST = ""
        for i in range(self.ECC_Grp):
            ECC_INST_TMP = """
generate
    if(ECC_WIDTH==0) begin:NO_ECC_GEN_CHK_SNS_BLK
        assign ecc_gen_dout_SNS = $ECC_GEN_DIN$ ;
        assign ecc_chk_dout_SNS = ecc_chk_din_SNS;
        assign ecc_sb_SNS = 1'b0 ;
        assign ecc_db_SNS = 1'b0 ;
    end //NO_ECC_GEN_CHK_SNS_BLK
    else begin:WITH_ECC_GEN_CHK_SNS_BLK
        U_ECC_GEN #(WIDTH(ECCGRP_WIDTH - ECC_WIDTH/ECCGRP_NUM)
        ) U_ECC_GEN_SNS (
           .dataout   ( $ECC_GEN_DIN$ ),
           .dataout   ( ecc_gen_dout_SNS  )
        );
        ECC_chk #(.WIDTH(ECCGRP_WIDTH - ECC_WIDTH/ECCGRP_NUM)
        ) U_ECC_CHK_SNS (
           .datain    ( ecc_chk_din_SNS ),
           .dataout   ( ecc_chk_dout_SNS ),
           .ECC_bypass( i_cut_ecc_bypass ),
           .db        ( ecc_db_SNS       )
        );
    end //WITH_ECC_GEN_CHK_SNS_BLK
endgenerate
"""
            tmp_high = (i + 1) * self.ECCGRP_Dwidth - 1
            tmp_low = i * self.ECCGRP_Dwidth
            ecc_gen_din = "ecc_gen_din[{}:{}]".format(tmp_high, tmp_low)
            ECC_INST_TMP = ECC_INST_TMP.replace("$ECC_GEN_DIN$", "{:s}".format(ecc_gen_din))
            ECC_INST_TMP = ECC_INST_TMP.replace("$SNS$", str(i))
            ECC_INST += ECC_INST_TMP
        ECC_INST = ECC_INST.replace("\n\n", "\n").strip("\n")
        self.RTL = self.RTL.replace("$ECC_INST$", "{:s}".format(ECC_INST))
        return self.RTL

    def Rep_ECC_ASSIGN(self):
        ECC_N = ""
        CUT_DOUT = ""
        ECC_GEN_DIN = ""
        ECC_CHK_DIN = ""
        CUT_PHY_DIN = ""
        CUT_PHY_DOUT = ""
        ECC_SB_MERGE = ""
        ECC_DB_MERGE = ""
        ECC_GENLIST = list()
        ECC_CHKLIST = list()
        for i in range(self.ECC_Grp):
            ECC_GENLIST.append("".join(["ecc_{:d}".format(self.ECC_Grp - i)] + ","))
            ECC_CHKLIST.append("".join(["ecc_chk_dout_{:d}".format(self.ECC_Grp - i - 1)]))
        if (self.ECCGRP_Dwidth * self.ECC_Grp != self.Width):
            ECC_GEN_DIN = "    *0+{i_cut_din}"
        else:
            ECC_GEN_DIN = "    *0+{"+",".join(ECC_GENLIST)+"i_cut_din}"
        CUT_PHY_DIN = "    *0+{"+",".join(["ecc_sb_{:d}".format(i) for i in range(self.ECC_Grp)])+"}"
        ECC_DB_MERGE = "    *0+{"+",".join(["ecc_db_{:d}".format(i) for i in range(self.ECC_Grp)])+"}"
        ECC_N += "assign ecc_{:d}+ = *8+== ecc_gen_dout_{:d}+reg;".format(self.ECCGRP_dwidth - 1, self.ECCGRP_dwidth - int(self.ECC_bits / self.ECC_Grp))+"\n"
        if (self.ECCGRP_Dwidth * self.ECC_Grp == self.Width) and (i == self.ECC_Grp - 1):
            ECC_CHK_DIN += "assign ecc_chk_din_{:d}+ = {cut_phy_dout[{}:{}],cut_phy_dout[{}:{}]};".format(self.Width + (i + 1) * self.ECC_bits / self.ECC_Grp - 1, self.Width + i * self.ECC_bits / self.ECC_Grp, self.Width + (i + 1) * self.ECC_bits / self.ECC_Grp - 1, (i + 1) * self.ECCGRP_Dwidth - 1, i * self.ECCGRP_Dwidth)+"\n"
        else:
            ECC_CHK_DIN += "assign ecc_chk_din_{:d}+ = {cut_phy_dout[{}:{}],cut_phy_dout[{}:{}]};".format((i + 1) * self.ECCGRP_Dwidth - 1, i * self.ECCGRP_Dwidth, (i + 1) * self.ECCGRP_Dwidth - 1)+"\n"
        CUT_PHY_DIN = "    *0+i_cut_din"
        ECC_SB_MERGE = "    *0+1'b0"
        ECC_DB_MERGE = "    *0+1'b0"
        for i in range(self.ECC_Grp):
            ECC_N += "assign ecc_{:d}+str(i)+ = *8+== ecc_gen_dout_{:d}+str(i)+reg;".format(i, i)+"\n"
        CUT_DOUT = "    *0+{"+",".join(["cut_phy_dout_tmp[{}:{}]".format(self.Width - 1, 0)])+"}"
        ECC_N = ECC_N.replace("\n\n", "\n").strip("\n")
        ECC_CHK_DIN = ECC_CHK_DIN.replace("\n\n", "\n").strip("\n")
        self.RTL = self.RTL.replace("$ECC_N$", "{:s}".format(ECC_N))
        self.RTL = self.RTL.replace("$CUT_DOUT$", "{:s}".format(CUT_DOUT))
        self.RTL = self.RTL.replace("$ECC_GEN_DIN$", "{:s}".format(ECC_GEN_DIN))
        self.RTL = self.RTL.replace("$ECC_CHK_DIN$", "{:s}".format(ECC_CHK_DIN))
        self.RTL = self.RTL.replace("$CUT_PHY_DIN$", "{:s}".format(CUT_PHY_DIN))
        self.RTL = self.RTL.replace("$CUT_PHY_DOUT$", "{:s}".format(CUT_PHY_DOUT))
        self.RTL = self.RTL.replace("$ECC_SB_MERGE$", "{:s}".format(ECC_SB_MERGE))
        self.RTL = self.RTL.replace("$ECC_DB_MERGE$", "{:s}".format(ECC_DB_MERGE))
        return self.RTL

    def Rep_PHYWRAP_DEF(self):
        PHYWRAP_DEF = """
    *0+reg {},".join(["phy_we_y{}".format(i) for i in range(self.db.y)])+";\n"
    *0+reg {},".join(["phy_re_y{}".format(i) for i in range(self.db.y)])+";\n"
    *0+reg [{}:0] phy_raddr;".format(self.db.Addrwidth - 1)+"\n"
    *0+reg [{}:0] phy_waddr;".format(self.db.Addrwidth - 1)+"\n"
    *0+wire [{}:0] phy_dout_x".format(self.db.Width - 1)+"*y*str(i)+"*z*str(j)+" ;\n"
""".format(self.db.x, self.db.x)
        if self.db.x != 1:
            PHYWRAP_DEF += "    *0+wire {},".join(["{{:d}:0] phy_dout_tmp".format(self.db.Width * self.db.x)])+";\n"
        PHYWRAP_DEF = PHYWRAP_DEF.replace("\n\n", "\n").strip("\n")
        self.RTL = self.RTL.replace("$PHYWRAP_DEFS$", "{:s}".format(PHYWRAP_DEF))
        return self.RTL

    def Rep_PHYWRAP_INST(self):
        # Phyiscal Wrapper inst
        if self.db.x == 1:
            tmp_width = self.Width
        else:
            tmp_width = self.db.Width
        PHYWRAPINST = ""
        for y in range(self.db.y):
            for x in range(self.db.x):
                counter = 0
                PHYWRAPINST_TMP = """
{:s}_{:s}_{:d}X{:d} phywrap #(
   .MEMPHY_CTRL_CFG_W ( MEMPHY_CTRL_CFG_W  )
) phywrapx${X}$y${Y}$ (
   .i_phy_clk         ( i_cut_clk         ),
   .i_phy_re          ( phy_re_y${Y}$     ),
   .i_phy_we          ( phy_we_y${Y}$     ),
   .i_phy_raddr       ( phy_raddr         ),
   .i_phy_waddr       ( phy_waddr         ),
   .o_phy_dout        ( phy_dout_X${X}$y${Y}$ )
);
""".format(self.BaseName, self.tag, self.db.Depth, self.db.Width, X=x, Y=y)
                tmp_high = min((counter + 1) * tmp_width - 1, self.Width - 1 + (self.ECC_bits))
                tmp_low = counter * tmp_width
                if (tmp_high + 1 - tmp_low < self.db.Width):
                    PHY_DIN = "{width}d{ho},phy_din[{width}d{lo}]".format(width=self.db.Width - (tmp_high + 1 - tmp_low), ho=tmp_high, lo=tmp_low)
                else:
                    PHY_DIN = "phy_din[{:d}:{:d}]".format(tmp_high, tmp_low)
                PHYWRAPINST_TMP = PHYWRAPINST_TMP.replace("phy_din", PHY_DIN)
                PHYWRAPINST += PHYWRAPINST_TMP
                counter += 1
        self.RTL = self.RTL.replace("$PHYWRAP_INST$", "{:s}".format(PHYWRAPINST))
        return self.RTL



    def Rep_PHYWRAP_ASSIGN(self):
        PHY_RE = ""
        PHY_WE = ""
        PHY_RE_SEL = ""
        PHY_WE_SEL = ""
        PHY_RE_DLY = ""
        PHY_RADDR = "cut_raddr_ppl[{:d}:{:d}]".format(self.phyaddr_h, self.phyaddr_l)
        PHY_WADDR = "cut_waddr_ppl[{:d}:{:d}]".format(self.phyaddr_h, self.phyaddr_l)
        PHY_DOUT = "phy_dout_tmp[{:d}:0]".format(self.width + self.ECC_bits - 1)
        PHYWRAP_DOUT_TMP_LIST = list()
        for j in range(self.db.y):
            if self.selbits_h == -1 and self.selbits_l == -1:
                PHY_RE_SEL = "+"  # /
            else:
                PHY_RE_SEL = "&& (cut_raddr_ppl[{:d}:{:d}]=={:d})".format(self.selbits_h, self.selbits_l, j) + ";\n"
                PHY_WE_SEL = "&& (cut_waddr_ppl[{:d}:{:d}]=={:d})".format(self.selbits_h, self.selbits_l, j) + ";\n"
            PHY_RE += "assign phy_re_y{:d} = {}{};\n".format(j, "phy_re_reg", PHY_RE_SEL)
            PHY_WE += "assign phy_we_y{:d} = {}{};\n".format(j, "phy_we_reg", PHY_WE_SEL)
            PHY_RE_DLY += "assign phy_re_ydly{:d} <= #dly phy_re_y{:d};\n".format(j, j)
            PHYWRAP_DOUT_TMP_LIST.append("({%d{phy_re_y%d_dly}} & {"%((self.db.Width * self.db.x),j)+",".join(["phy_dout_x%dy%d"%(i,j) for i in range(self.db.x)[::-1]])+"})")
            PHY_RE = PHY_RE.replace("\n\n", "\n").strip("\n")
            PHY_WE = PHY_WE.replace("\n\n", "\n").strip("\n")
            PHY_RE_DLY = PHY_RE_DLY.replace("\n\n", "\n").strip("\n")
            PHY_DOUT_TMP = "|".join(PHYWRAP_DOUT_TMP_LIST)
            self.RTL = self.RTL.replace("$PHY_RE$", "{:s}".format(PHY_RE))
            self.RTL = self.RTL.replace("$PHY_WE$", "{:s}".format(PHY_WE))
            self.RTL = self.RTL.replace("$PHY_RE_DLY$", "{:s}".format(PHY_RE_DLY))
            self.RTL = self.RTL.replace("$PHY_RADDR$", "{:s}".format(PHY_RADDR))
            self.RTL = self.RTL.replace("$PHY_WADDR$", "{:s}".format(PHY_WADDR))
            self.RTL = self.RTL.replace("$PHY_DOUT$", "{:s}".format(PHY_DOUT))
            self.RTL = self.RTL.replace("$PHY_DOUT_TMP$", "{:s}".format(PHY_DOUT_TMP))
        return self.RTL

    def Initialize(self):
        self.gen_HEADER = ()
        self.GeneralProcess = ()
        self.Rep_CUTWRAP_INST = ()
        self.PHY_DB_INST = ()
        #self.Rep_BACKDOOR = ()
        #self.Rep_ECC_DEF = ()
        self.Rep_ECC_INST = ()
        self.Rep_ECC_ASSIGN = ()
        self.Rep_PHYWRAP_DEF = ()
        self.Rep_PHYWRAP_INST = ()
        self.Rep_PHYWRAP_ASSIGN = ()

def test(filename):
    mem = Mem1R1WA(
        Depth=4096,
        Width=1536,
        DB_Depth=4096,
        DB_Width=133,
        DB_Name="DB_NAME",
        ECC_Grp=2,
        Fadio_dict={"fadio": 1},
        Type_list=["drl", "0", "00"],
        ECC_enable="NO"
    )
    mem.Prefix = "Test"
    mem.Initialize()
    mem.DumpRTL(filename=filename)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="program description")
    parser.add_argument('-o', help="output verilog file name")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG,
        datefmt="%Y/%m/%d %H:%M:%S",
        format='%(asctime)s %(levelname)s : %(message)s (%(module)s-%(lineno)d-%(funcName)s)',
    )
    test(filename=args.o)       