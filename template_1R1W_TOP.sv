`ifndef GM_RAMWRAP_1R1WA_TOP_SV_
`define GM_RAMWRAP_1R1WA_TOP_SV_

`ifndef __ECC_BIT_CALC_FUNC__
`define __ECC_BIT_CALC_FUNC__
function automatic integer ecc_bit_calc;
    input integer k;
    integer m;
    begin
        m = 1;
        while (2**m < m + k + 1) m++;
        ecc_bit_calc = m + 1;
    end
endfunction //calculate m
`endif

//==========================================================//
// Memory Behaviour Model //
//==========================================================//
`ifdef USE_BEH_MEM
module RAMWRAP_1R1WA_TOP #(
    parameter WIDTH = 256,
    parameter DOUTPIPELINE = 75,
    parameter INPUTPIPELINE = 0,
    parameter PREFIX_ADDNAME = 0,
    parameter ASYN_RST_EN = 0, //default sync reset
    parameter INIT_ENABLE = 1'b0,
    parameter INIT_DATA_VAL = {WIDTH{1'b0}}, //the initial data value
    parameter USER_DEFINE_UNIQUE_NAME = "NO_SPECIFIED",
    //drived parameter
    parameter MEMPHY_CTRL_CFG_W = 24
)(
    //config
    input [MEMPHY_CTRL_CFG_W-1:0] memphy_ctrl_cfg,
    //logic
    input CLKR,
    input CLKW,
    input RSTR,
    input RSTW,
    //----------Logical read and write port----------//
    input RE,
    input WE,
    input [log2(DEPTH)-1:0] AddrR,
    input [log2(DEPTH)-1:0] AddrW,
    input [WIDTH-1:0] DIN,
    output logic [WIDTH-1:0] DOUT,
    //----------Initialize the port----------//
    input INIT_START,
    output logic INIT_DONE,
    //----------ecc function port----------//
    input SET_ECC_SB, //use CLKR
    input SET_ECC_DB,
    input ECC_bypass,
    output logic ECC_sb,
    output logic ECC_db,
    output logic [log2(DEPTH)-1:0] ECC_addr
);

// local parameter //
`ifdef BEH_MEM_WITHOUT_ECC //1014 zlin:just for top dv to speed up simulation now,should be forbidden later
localparam ECC_WIDTH = 0;
`else
localparam ECC_WIDTH = (PREFIX_ADDNAME == "NO_ECC")? 0 : ecc_bit_calc(WIDTH);
`endif;
localparam TOT_WIDTH = WIDTH + ECC_WIDTH;

//----------inner signals----------//
//pipe
logic ppn_re_dly;
logic ppn_we;
logic [WIDTH-1:0] ppn_din;
logic [WIDTH-1:0] ppn_dout;
logic [log2(DEPTH)-1:0] ppn_raddr;
logic [log2(DEPTH)-1:0] ppn_waddr;
logic [log2(DEPTH)-1:0] ppn_ecc_sb;
logic [log2(DEPTH)-1:0] ppn_ecc_db;
logic [log2(DEPTH)-1:0] ppn_ecc_addr;
//init
logic mem_init_wr; //the init write enable
logic [log2(DEPTH)-1:0] mem_init_waddr; //the RAM address
logic [WIDTH-1:0] mem_init_wdata; //the write data
//read&write
logic real_we;
logic [WIDTH-1:0] real_din;
logic [WIDTH-1:0] real_dout;
logic [log2(DEPTH)-1:0] real_waddr;
//ecc
logic [TOT_WIDTH-1:0] mem [DEPTH-1:0]; ///*synthesis syn_ramstyle = "block_ram"*/
logic [TOT_WIDTH-1:0] ecc_gen_dout;
logic [TOT_WIDTH-1:0] ecc_chk_din;
logic [WIDTH-1:0] ecc_chk_dout;
logic [WIDTH-1:0] ecc_sb, ecc_db;
logic set_sb_dly, set_db_dly;
logic ecc_sb_flag, ecc_db_flag;
logic w_set_sb_rise, w_set_db_rise;

//----------main code----------//
//pipeline Config
//RAMWRAP_PIPE should support the condition (p=0)
//----------//
//----------//
data_pipe #(
   .DATA_W (1),
   .PIPE_NUM (1),
   .PIPE_MUX_EN(0),
    // 0: directly use the all pipe structure;
    // 0: the input data is directly write into MUX array;
    // 0: the output from MUX array will be directly outputted
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_REDLY_PIPE (
    //----clk&rst----//
   .i_clk (CLKR),
   .i_rst (RSTR),
    //----pipe in----//
   .i_vld (1'b1),
   .i_data (ppn_re),
    //----pipe out----//
   .o_vld_pp(),
   .o_data_pp(ppn_re_dly)
);

data_pipe #(
   .DATA_W (2),
   .PIPE_NUM (DOUTPIPELINE),
   .PIPE_MUX_EN(0),
    // 0: directly use the all pipe structure;
    // 0: the input data is directly write into MUX array;
    // 0: the output from MUX array will be directly outputted
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_ECC_SB_DB_PIPE (
    //----clk&rst----//
   .i_clk (CLKR),
   .i_rst (RSTR),
    //----pipe in----//
   .i_vld (1'b1),
   .i_data (ppn_ecc_sb, ppn_ecc_db),
    //----pipe out----//
   .o_vld_pp(),
   .o_data_pp(ECC_sb, ECC_db)
);

data_pipe #(
   .DATA_W (log2(DEPTH)),
   .PIPE_NUM (INPUTPIPELINE),
   .PIPE_MUX_EN(0),
    // 0: directly use the all pipe structure;
    // 0: the input data is directly write into MUX array;
    // 0: the output from MUX array will be directly outputted
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_WADDR_PIPE (
    //----clk&rst----//
   .i_clk (CLKW),
   .i_rst (RSTW),
    //----pipe in----//
   .i_vld (WE),
   .i_data (AddrW),
    //----pipe out----//
   .o_vld_pp(),
   .o_data_pp(ppn_waddr)
);

data_pipe #(
   .DATA_W (log2(DEPTH)),
   .PIPE_NUM (INPUTPIPELINE),
   .PIPE_MUX_EN(0),
    // 0: directly use the all pipe structure;
    // 0: the input data is directly write into MUX array;
    // 0: the output from MUX array will be directly outputted
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_RADDR_PIPE (
    //----clk&rst----//
   .i_clk (CLKR),
   .i_rst (RSTR),
    //----pipe in----//
   .i_vld (RE),
   .i_data (AddrR),
    //----pipe out----//
   .o_vld_pp(),
   .o_data_pp(ppn_raddr)
);

data_pipe #(
   .DATA_W (WIDTH),
   .PIPE_NUM (INPUTPIPELINE),
   .PIPE_MUX_EN(0),
    // 0: directly use the all pipe structure;
    // 0: the input data is directly write into MUX array;
    // 0: the output from MUX array will be directly outputted
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_WDATA_PIPE (
    //----clk&rst----//
   .i_clk (CLKW),
   .i_rst (RSTW),
    //----pipe in----//
   .i_vld (WE),
   .i_data (DIN),
    //----pipe out----//
   .o_vld_pp(),
   .o_data_pp(ppn_din)
);

data_pipe #(
   .DATA_W (WIDTH),
   .PIPE_NUM (DOUTPIPELINE),
   .PIPE_MUX_EN(0),
    // 0: directly use the all pipe structure;
    // 0: the input data is directly write into MUX array;
    // 0: the output from MUX array will be directly outputted
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_RDATA_PIPE (
    //----clk&rst----//
   .i_clk (CLKR),
   .i_rst (RSTR),
    //----pipe in----//
   .i_vld (ppn_re_dly),
   .i_data (ppn_dout),
    //----pipe out----//
   .o_vld_pp(),
   .o_data_pp(DOUT)
);

data_pipe #(
   .DATA_W (log2(DEPTH)),
   .PIPE_NUM (DOUTPIPELINE+1),
   .PIPE_MUX_EN(0),
    // 0: directly use the all pipe structure;
    // 0: the input data is directly write into MUX array;
    // 0: the output from MUX array will be directly outputted
   .FLOP_IN (0),
   .FLOP_OUT (0)
) U_ECC_ADDR_PIPE (
    //----clk&rst----//
   .i_clk (CLKR),
   .i_rst (RSTR),
    //----pipe in----//
   .i_vld (ppn_re),
   .i_data (ppn_raddr),
    //----pipe out----//
   .o_vld_pp(),
   .o_data_pp(ECC_addr)
);

//----------initialization function----------//
generate
    if (INIT_ENABLE == 0) begin:NO_MEM_INIT_BLK
        assign mem_init_wr = 1'b0;
        assign mem_init_waddr = {log2(DEPTH){1'b0}};
        assign mem_init_wdata = {WIDTH{1'b0}};
        assign INIT_DONE = 1'b1;
    end//NO_MEM_INIT_BLK
    else begin:WITH_MEM_INIT_BLK
        mem_init #(
           .ASYN_RST_EN(ASYN_RST_EN),
           .MEM_DEPTH(DEPTH),
           .DATA_W(WIDTH),
           .INIT_DATA_VAL(INIT_DATA_VAL)
        ) m_init (
           .i_clk (CLKW),
           .i_rst (RSTW),
           .i_init_start (INIT_START),
           .o_mem_init_wr (mem_init_wr),
           .o_mem_init_waddr (mem_init_waddr),
           .o_mem_init_wdata (mem_init_wdata),
           .o_INIT_DONE (ff_mem_init_done)
        );
    end//WITH_MEM_INIT_BLK
endgenerate

//----------ecc function----------//
//----------//
`ifdef BEH_MEM_WITHOUT_ECC
assign ecc_gen_dout = real_din;
assign ecc_chk_dout = ecc_chk_din[WIDTH-1:0];
assign ecc_sb = 1'b0;
assign ecc_db = 1'b0;
`else
generate
    if(PREFIX_ADDNAME == "NO_ECC")begin:BEH_NO_ECC
        assign ecc_gen_dout = real_din;
        assign ecc_chk_dout = ecc_chk_din[WIDTH-1:0];
        assign ecc_sb = 1'b0;
        assign ecc_db = 1'b0;
    end//BEH_NO_ECC
    else begin:BEH_WITH_ECC
        ECC_gen #(
           .WIDTH(WIDTH)
        ) U_ECC_GEN (
           .datain (real_din),
           .dataout (ecc_gen_dout)
        );
        ECC_chk#(
           .WIDTH(WIDTH)
        ) U_ECC_CHK (
           .datain (ecc_chk_din),
           .dataout (ecc_chk_dout),
           .ECC_bypass (ECC_bypass),
           .sb (ecc_sb),
           .db (ecc_db)
        );
    end//BEH_WITH_ECC
endgenerate
`endif
assign ppn_dout = ecc_chk_dout;

//----------write&read function----------//
//----------//
always @(posedge CLKW) begin
    if (real_we) begin
        mem[real_waddr] <= ecc_gen_dout;
    end
    else;
end

always @(posedge CLKR) begin
    if (ppn_re) begin
        ecc_chk_din <= mem[ppn_raddr];
    end
    else;
end

//----------channel selector----------//
//----------//
assign real_we = mem_init_wr? mem_init_wr : ppn_we;
assign real_din = mem_init_wr? mem_init_wdata : ppn_din;
assign real_waddr = mem_init_wr? mem_init_waddr : ppn_waddr;

//----------ecc error set----------//
//----------//
generate
    if(ASYN_RST_EN ==0)begin:SYNC_RST
        always_ff @(posedge CLKR) begin
            if(RSTR) begin
                set_sb_dly <= 1'h0;
                set_db_dly <= 1'h0;
            end else begin
                set_sb_dly <= SET_ECC_SB;
                set_db_dly <= SET_ECC_DB;
            end
        end
        always @(posedge CLKR) begin
            if(RSTR) begin
                ecc_sb_flag <= 1'b0;
            end else if(w_set_sb_rise) begin
                ecc_sb_flag <= 1'b1;
            end else if(ppn_re_dly) begin
                ecc_sb_flag <= 1'b0;
            end
        end
        always @(posedge CLKR) begin
            if(RSTR) begin
                ecc_db_flag <= 1'b0;
            end else if(w_set_db_rise) begin
                ecc_db_flag <= 1'b1;
            end else if(ppn_re_dly) begin
                ecc_db_flag <= 1'b0;
            end
        end
    end
    else begin:ASYN_RST
        always_ff @(posedge CLKR or posedge RSTR) begin
            if(RSTR) begin
                set_sb_dly <= 1'h0;
                set_db_dly <= 1'h0;
            end else begin
                set_sb_dly <= SET_ECC_SB;
                set_db_dly <= SET_ECC_DB;
            end
        end
        always @(posedge CLKR or posedge RSTR) begin
            if(RSTR) begin
                ecc_sb_flag <= 1'b0;
            end else if(w_set_sb_rise) begin
                ecc_sb_flag <= 1'b1;
            end else if(ppn_re_dly) begin
                ecc_sb_flag <= 1'b0;
            end
        end
        always @(posedge CLKR or posedge RSTR) begin
            if(RSTR) begin
                ecc_db_flag <= 1'b0;
            end else if(w_set_db_rise) begin
                ecc_db_flag <= 1'b1;
            end else if(ppn_re_dly) begin
                ecc_db_flag <= 1'b0;
            end
        end
    end
endgenerate

assign w_set_sb_rise = ({set_sb_dly, SET_ECC_SB} == 2'b01);
assign w_set_db_rise = ({set_db_dly, SET_ECC_DB} == 2'b01);
assign ppn_ecc_sb = ppn_re_dly? ecc_sb_flag | ecc_sb : 1'b0;
assign ppn_ecc_db = ppn_re_dly? ecc_db_flag | ecc_db : 1'b0;

//----------backdoor----------//
//----------//
`ifdef PHY_BACKDOOR
logic [WIDTH+2-1:0]data_tmp;
task read_word(input [log2(DEPTH)-1:0] address_r,
               output [WIDTH-1:0] data_out,
               output ecc_sb, ecc_db);
    ecc_db = 1'b0 ;
    ecc_sb = 1'b0 ;
    data_out = mem[address_r];
endtask

task write_word(input [log2(DEPTH)-1:0] address_w,
                input [WIDTH-1:0] data_in,
                int idx1=-1, int idx2=-1);
    mem [address_w] = data_in;
endtask

task glb_write_word(
    input [WIDTH-1:0] data_in
);
    for(integer i=0;i<DEPTH;i=i+1)begin
        mem[i] = data_in;
    end
endtask

`ifdef FAST_INIT
initial begin
    # FAST_INIT_DLY;
    glb_write_word(INIT_DATA_VAL);
end
`endif

import uvm_pkg::*;
initial begin
    `uvm_info("",$sformatf("IMPORTANT_INFO: %m is the hierarchy of user defined unique memory name: %0s, it should be defined as macro for backdoor task of both RTL and gate - sim DV",USER_DEFINE_UNIQUE_NAME,UVM_HIGH))
end
`endif //`ifdef PHY_BACKDOOR

//==========================================================//
// Memory, use Physical Wrap to build
//==========================================================//
`else
module RAMWRAP_1R1WA_TOP #(
    parameter DEPTH = 256,
    parameter WIDTH = 75,
    parameter INPUTPIPELINE = 0,
    parameter DOUTPIPELINE = 0,
    parameter PREFIX_ADDNAME = "",
    parameter ASYN_RST_EN = 1'b0, //default sync reset
    parameter INIT_ENABLE = 1'b0,
    parameter INIT_DATA_VAL = {WIDTH{1'b0}}, //the initial data value
    parameter USER_DEFINE_UNIQUE_NAME = "NO_SPECIFIED",
    //drived parameter
    parameter MEMPHY_CTRL_CFG_W = 24
)(
    //config
    input [MEMPHY_CTRL_CFG_W-1:0] memphy_ctrl_cfg,
    //logic
    input CLKW,
    input CLKR,
    input RSTW,
    input RSTR,
    //----------Logical read and write port----------//
    input RE,
    input WE,
    input [log2(DEPTH)-1:0] AddrR,
    input [log2(DEPTH)-1:0] AddrW,
    input [WIDTH-1:0] DIN,
    output logic [WIDTH-1:0] DOUT,
    //----------Initialize the port----------//
    input INIT_START,
    output logic INIT_DONE,
    //----------ecc function port----------//
    input SET_ECC_SB, //use CLKR
    input SET_ECC_DB,
    input ECC_bypass,
    output logic ECC_sb,
    output logic ECC_db,
    output logic [log2(DEPTH)-1:0] ECC_addr
);

//----------initialization function----------//
reg mem_init_wr; //the init write enable
reg [log2(DEPTH)-1:0] mem_init_waddr; //the RAM address
reg [WIDTH-1:0] mem_init_wdata; //the write data
reg ff_mem_init_done;

generate
    if (INIT_ENABLE == 0) begin:NO_MEM_INIT_BLK
        assign mem_init_wr = 1'b0;
        assign mem_init_waddr = {log2(DEPTH){1'b0}};
        assign mem_init_wdata = {WIDTH{1'b0}};
        assign INIT_DONE = 1'b1;
    end//NO_MEM_INIT_BLK
    else begin:WITH_MEM_INIT_BLK
        mem_init #(
           .ASYN_RST_EN(ASYN_RST_EN),
           .MEM_DEPTH(DEPTH),
           .DATA_W(WIDTH),
           .INIT_DATA_VAL(INIT_DATA_VAL)
        ) m_init (
           .i_clk (CLKW),
           .i_rst (RSTW),
           .i_init_start (INIT_START),
           .o_mem_init_wr (mem_init_wr),
           .o_mem_init_waddr (mem_init_waddr),
           .o_mem_init_wdata (mem_init_wdata),
           .o_INIT_DONE (ff_mem_init_done)
        );
    end//WITH_MEM_INIT_BLK
endgenerate

//----------Write channel selector----------//
wire real_we;
wire [WIDTH-1:0] real_din;
wire [log2(DEPTH)-1:0] real_waddr;

assign real_we = mem_init_wr? mem_init_wr : WE;
assign real_din = mem_init_wr? mem_init_wdata : DIN;
assign real_waddr = mem_init_wr? mem_init_waddr : AddrW;

//----------Backdoor----------//
`ifdef PHY_BACKDOOR
task read_word(input [log2(DEPTH)-1:0] address_r,
               output [WIDTH-1:0] data_out,
               output ecc_sb, ecc_db);
    gen.memwrap.read_word(address_r,data_out,ecc_sb,ecc_db);
endtask

task write_word(input [log2(DEPTH)-1:0] address_w,
                input [WIDTH-1:0] data_in,
                int idx1=-1, int idx2=-1);
    gen.memwrap.write_word(address_w,data_in,idx1,idx2);
endtask

task glb_write_word(
    input [WIDTH-1:0] data_in
);
    gen.memwrap.glb_write_word(data_in);
endtask

`ifdef FAST_INIT
initial begin
    wait(RSTR==1);//read side will reset first
    @(negedge RSTW);//write side will release later
    @(negedge CLKW);
    glb_write_word(INIT_DATA_VAL);
end
`endif
import uvm_pkg::*;
initial begin
    `uvm_info("",$sformatf("IMPORTANT_INFO: %m is the hierarchy of user defined unique memory name: %0s, it should be defined as macro for backdoor task of both RTL and gate - sim DV",USER_DEFINE_UNIQUE_NAME,UVM_HIGH))
end
`endif //`ifdef PHY_BACKDOOR

//----------//
assign INIT_DONE = (PREFIX_ADDNAME == "FF_BASE_MEM")? ff_mem_init_done : mem_init_done;

generate
// $MEMWRAPLIST$
    if(PREFIX_ADDNAME == "FF_BASE_MEM")begin:gen
        FF_BASE_1R1WA_MEM #(
           .ASYN_RST_EN(ASYN_RST_EN),
           .DEPTH(DEPTH),
           .WIDTH(WIDTH),
           .INPUTPIPELINE(INPUTPIPELINE),
           .DOUTPIPELINE(DOUTPIPELINE),
           .INIT_ENABLE(INIT_ENABLE),
           .INIT_DATA_VAL(INIT_DATA_VAL)
        ) memwrap (
           .CLKW (CLKW),
           .CLKR (CLKR),
           .RSTW (RSTW),
           .RSTR (RSTR),
           .WE (WE),
           .RE (RE),
           .AddrR (AddrR),
           .AddrW (AddrW),
           .DIN (DIN),
           .DOUT (DOUT),
           .INIT_START (INIT_START),
           .INIT_DONE (ff_mem_init_done),
           .SET_ECC_SB (SET_ECC_SB),
           .SET_ECC_DB (SET_ECC_DB),
           .ECC_bypass (ECC_bypass),
           .ECC_sb (ECC_sb),
           .ECC_db (ECC_db),
           .ECC_addr (ECC_addr)
        );
    end
    else if (PREFIX_ADDNAME == "FF_1R1WA_MEM")begin:gen
        FF_1R1WA_MEM #(
           .ASYN_RST_EN(ASYN_RST_EN),
           .DEPTH(DEPTH),
           .WIDTH(WIDTH),
           .INPUTPIPELINE(INPUTPIPELINE),
           .DOUTPIPELINE(DOUTPIPELINE),
           .INIT_ENABLE(INIT_ENABLE),
           .INIT_DATA_VAL(INIT_DATA_VAL)
        ) memwrap (
           .CLKW (CLKW),
           .CLKR (CLKR),
           .RSTW (RSTW),
           .RSTR (RSTR),
           .WE (WE),
           .RE (RE),
           .AddrR (AddrR),
           .AddrW (AddrW),
           .DIN (DIN),
           .DOUT (DOUT),
           .INIT_START (INIT_START),
           .INIT_DONE (ff_mem_init_done),
           .SET_ECC_SB (SET_ECC_SB),
           .SET_ECC_DB (SET_ECC_DB),
           .ECC_bypass (ECC_bypass),
           .ECC_sb (ECC_sb),
           .ECC_db (ECC_db),
           .ECC_addr (ECC_addr)
        );
    `ifdef SYNTHESIS
    `else
        initial begin
            $error("ERROR: %m DEPTH(%0d), WIDTH(%0d) parameter value dont match any specified RAMWRAP_1R1WA modules", DEPTH, WIDTH);
        end
    `endif
    end
endgenerate

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

//== using fake module to make VCS compile passed once memwrap is failed to match parameter of DEPTH, WIDTH and prefix. In this way, a ERROR can be reported ==//
module FF_BASE_1R1WA_MEM #(
    parameter DEPTH = 256,
    parameter WIDTH = 75,
    parameter INPUTPIPELINE = 0,
    parameter DOUTPIPELINE = 0,
    parameter PREFIX_ADDNAME = "",
    parameter ASYN_RST_EN = 1'b0, //default sync reset
    parameter INIT_ENABLE = 1'b0,
    parameter INIT_DATA_VAL = {WIDTH{1'b0}}, //the initial data value
    parameter USER_DEFINE_UNIQUE_NAME = "NO_SPECIFIED"
)(
    input CLKW,
    input CLKR,
    input RSTW,
    input RSTR,
    //----------Logical read and write port----------//
    input RE,
    input WE,
    input [log2(DEPTH)-1:0] AddrR,
    input [log2(DEPTH)-1:0] AddrW,
    input [WIDTH-1:0] DIN,
    output logic [WIDTH-1:0] DOUT,
    //----------Initialize the port----------//
    input INIT_START,
    output logic INIT_DONE,
    //----------ecc function port----------//
    input SET_ECC_SB, //use CLKR
    input SET_ECC_DB,
    input ECC_bypass,
    output logic ECC_sb,
    output logic ECC_db,
    output logic [log2(DEPTH)-1:0] ECC_addr
);

    // local parameter //
    localparam ECC_WIDTH = 6; //NOTE by zlin:FF_BASE must have no ecc
    localparam TOT_WIDTH = WIDTH + ECC_WIDTH;

    //----------inner signals----------//
    //pipe
    logic ppn_re;
    logic ppn_re_dly;
    logic ppn_we;
    logic [WIDTH-1:0] ppn_din;
    logic [WIDTH-1:0] ppn_dout;
    logic [log2(DEPTH)-1:0] ppn_raddr;
    logic [log2(DEPTH)-1:0] ppn_waddr;
    logic [log2(DEPTH)-1:0] ppn_ecc_sb;
    logic [log2(DEPTH)-1:0] ppn_ecc_db;
    logic [log2(DEPTH)-1:0] ppn_ecc_addr;
    //init
    logic mem_init_wr; //the init write enable
    logic [log2(DEPTH)-1:0] mem_init_waddr; //the RAM address
    logic [WIDTH-1:0] mem_init_wdata; //the write data
    //read&write
    logic real_we;
    logic [WIDTH-1:0] real_din;
    logic [log2(DEPTH)-1:0] real_waddr;
    //ecc
    logic [TOT_WIDTH-1:0] mem [DEPTH-1:0]; ///*synthesis syn_ramstyle = "block_ram"*/
    logic [TOT_WIDTH-1:0] ecc_gen_dout;
    logic [TOT_WIDTH-1:0] ecc_chk_din;
    logic [WIDTH-1:0] ecc_chk_dout;
    logic [WIDTH-1:0] ecc_sb, ecc_db;
    logic set_sb_dly, set_db_dly;
    logic ecc_sb_flag, ecc_db_flag;
    logic w_set_sb_rise, w_set_db_rise;

    //----------main code----------//
    //pipeline Config
    //RAMWRAP_PIPE should support the condition (p=0)
    //----------//
    data_pipe #(
       .DATA_W (1),
       .PIPE_NUM (1),
       .PIPE_MUX_EN(0),
        // 0: directly use the all pipe structure;
        // 0: the input data is directly write into MUX array;
        // 0: the output from MUX array will be directly outputted
       .FLOP_IN (0),
       .FLOP_OUT (0)
    ) U_REDLY_PIPE (
        //----clk&rst----//
       .i_clk (CLKR),
       .i_rst (RSTR),
        //----pipe in----//
       .i_vld (1'b1),
       .i_data (ppn_re),
        //----pipe out----//
       .o_vld_pp(),
       .o_data_pp(ppn_re_dly)
    );

    data_pipe #(
       .DATA_W (2),
       .PIPE_NUM (DOUTPIPELINE),
       .PIPE_MUX_EN(0),
        // 0: directly use the all pipe structure;
        // 0: the input data is directly write into MUX array;
        // 0: the output from MUX array will be directly outputted
       .FLOP_IN (0),
       .FLOP_OUT (0)
    ) U_ECC_SB_DB_PIPE (
        //----clk&rst----//
       .i_clk (CLKR),
       .i_rst (RSTR),
        //----pipe in----//
       .i_vld (1'b1),
       .i_data (ppn_ecc_sb, ppn_ecc_db),
        //----pipe out----//
       .o_vld_pp(),
       .o_data_pp(ECC_sb, ECC_db)
    );

    data_pipe #(
       .DATA_W (log2(DEPTH)),
       .PIPE_NUM (INPUTPIPELINE),
       .PIPE_MUX_EN(0),
        // 0: directly use the all pipe structure;
        // 0: the input data is directly write into MUX array;
        // 0: the output from MUX array will be directly outputted
       .FLOP_IN (0),
       .FLOP_OUT (0)
    ) U_WADDR_PIPE (
        //----clk&rst----//
       .i_clk (CLKW),
       .i_rst (RSTW),
        //----pipe in----//
       .i_vld (WE),
       .i_data (AddrW),
        //----pipe out----//
       .o_vld_pp(),
       .o_data_pp(ppn_waddr)
    );

    data_pipe #(
       .DATA_W (log2(DEPTH)),
       .PIPE_NUM (INPUTPIPELINE),
       .PIPE_MUX_EN(0),
        // 0: directly use the all pipe structure;
        // 0: the input data is directly write into MUX array;
        // 0: the output from MUX array will be directly outputted
       .FLOP_IN (0),
       .FLOP_OUT (0)
    ) U_RADDR_PIPE (
        //----clk&rst----//
       .i_clk (CLKR),
       .i_rst (RSTR),
        //----pipe in----//
       .i_vld (RE),
       .i_data (AddrR),
        //----pipe out----//
       .o_vld_pp(),
       .o_data_pp(ppn_raddr)
    );

    data_pipe #(
       .DATA_W (WIDTH),
       .PIPE_NUM (INPUTPIPELINE),
       .PIPE_MUX_EN(0),
        // 0: directly use the all pipe structure;
        // 0: the input data is directly write into MUX array;
        // 0: the output from MUX array will be directly outputted
       .FLOP_IN (0),
       .FLOP_OUT (0)
    ) U_WDATA_PIPE (
        //----clk&rst----//
       .i_clk (CLKW),
       .i_rst (RSTW),
        //----pipe in----//
       .i_vld (WE),
       .i_data (DIN),
        //----pipe out----//
       .o_vld_pp(),
       .o_data_pp(ppn_din)
    );

    data_pipe #(
       .DATA_W (WIDTH),
       .PIPE_NUM (DOUTPIPELINE),
       .PIPE_MUX_EN(0),
        // 0: directly use the all pipe structure;
        // 0: the input data is directly write into MUX array;
        // 0: the output from MUX array will be directly outputted
       .FLOP_IN (0),
       .FLOP_OUT (0)
    ) U_RDATA_PIPE (
        //----clk&rst----//
       .i_clk (CLKR),
       .i_rst (RSTR),
        //----pipe in----//
       .i_vld (ppn_re_dly),
       .i_data (ppn_dout),
        //----pipe out----//
       .o_vld_pp(),
       .o_data_pp(DOUT)
    );

    data_pipe #(
       .DATA_W (log2(DEPTH)),
       .PIPE_NUM (DOUTPIPELINE+1),
       .PIPE_MUX_EN(0),
        // 0: directly use the all pipe structure;
        // 0: the input data is directly write into MUX array;
        // 0: the output from MUX array will be directly outputted
       .FLOP_IN (0),
       .FLOP_OUT (0)
    ) U_ECC_ADDR_PIPE (
        //----clk&rst----//
       .i_clk (CLKR),
       .i_rst (RSTR),
        //----pipe in----//
       .i_vld (ppn_re),
       .i_data (ppn_raddr),
        //----pipe out----//
       .o_vld_pp(),
       .o_data_pp(ECC_addr)
    );

    assign ppn_dout = ecc_chk_dout;

    //----------write&read function----------//
    always @(posedge CLKW) begin
        if (real_we) begin
            mem[real_waddr] <= ecc_gen_dout;
        end
        else;
    end

    always @(posedge CLKR) begin
        if (ppn_re) begin
            ecc_chk_din <= mem[ppn_raddr];
        end
        else;
    end

    //----------channel selector----------//
    assign real_we = mem_init_wr? mem_init_wr : ppn_we;
    assign real_din = mem_init_wr? mem_init_wdata : ppn_din;
    assign real_waddr = mem_init_wr? mem_init_waddr : ppn_waddr;

    //----------ecc error set----------//
    generate
        if(ASYN_RST_EN ==0)begin:SYNC_RST
            always_ff @(posedge CLKR) begin
                if(RSTR) begin
                    set_sb_dly <= 1'h0;
                    set_db_dly <= 1'h0;
                end else begin
                    set_sb_dly <= SET_ECC_SB;
                    set_db_dly <= SET_ECC_DB;
                end
            end
            always @(posedge CLKR) begin
                if(RSTR) begin
                    ecc_sb_flag <= 1'b0;
                end else if(w_set_sb_rise) begin
                    ecc_sb_flag <= 1'b1;
                end else if(ppn_re_dly) begin
                    ecc_sb_flag <= 1'b0;
                end
            end
            always @(posedge CLKR) begin
                if(RSTR) begin
                    ecc_db_flag <= 1'b0;
                end else if(w_set_db_rise) begin
                    ecc_db_flag <= 1'b1;
                end else if(ppn_re_dly) begin
                    ecc_db_flag <= 1'b0;
                end
            end
        end
        else begin:ASYN_RST
            always_ff @(posedge CLKR or posedge RSTR) begin
                if(RSTR) begin
                    set_sb_dly <= 1'h0;
                    set_db_dly <= 1'h0;
                end else begin
                    set_sb_dly <= SET_ECC_SB;
                    set_db_dly <= SET_ECC_DB;
                end
            end
            always @(posedge CLKR or posedge RSTR) begin
                if(RSTR) begin
                    ecc_sb_flag <= 1'b0;
                end else if(w_set_sb_rise) begin
                    ecc_sb_flag <= 1'b1;
                end else if(ppn_re_dly) begin
                    ecc_sb_flag <= 1'b0;
                end
            end
            always @(posedge CLKR or posedge RSTR) begin
                if(RSTR) begin
                    ecc_db_flag <= 1'b0;
                end else if(w_set_db_rise) begin
                    ecc_db_flag <= 1'b1;
                end else if(ppn_re_dly) begin
                    ecc_db_flag <= 1'b0;
                end
            end
        end
    endgenerate

    assign w_set_sb_rise = ({set_sb_dly, SET_ECC_SB} == 2'b01);
    assign w_set_db_rise = ({set_db_dly, SET_ECC_DB} == 2'b01);
    assign ppn_ecc_sb = ppn_re_dly? ecc_sb_flag | ecc_sb : 1'b0;
    assign ppn_ecc_db = ppn_re_dly? ecc_db_flag | ecc_db : 1'b0;

    //----------backdoor----------//
    `ifdef PHY_BACKDOOR
    logic [WIDTH+2-1:0]data_tmp;
    task read_word(input [log2(DEPTH)-1:0] address_r,
                   output [WIDTH-1:0] data_out,
                   output ecc_sb, ecc_db);
        ecc_db = 1'b0 ;
        ecc_sb = 1'b0 ;
        data_out = mem[address_r];
    endtask

    task write_word(input [log2(DEPTH)-1:0] address_w,
                    input [WIDTH-1:0] data_in,
                    int idx1=-1, int idx2=-1);
        mem [address_w] = data_in;
    endtask

    task glb_write_word(
        input [WIDTH-1:0] data_in
    );
        for(integer i=0;i<DEPTH;i=i+1)begin:
            mem[i] = data_in;
        end
    endtask

    `ifdef FAST_INIT
    initial begin
        # FAST_INIT_DLY;
        glb_write_word(INIT_DATA_VAL);
    end
    `endif

    import uvm_pkg::*;
    initial begin
        `uvm_info("",$sformatf("IMPORTANT_INFO: %m is the hierarchy of user defined unique memory name: %0s, it should be defined as macro for backdoor task of both RTL and gate - sim DV",USER_DEFINE_UNIQUE_NAME,UVM_HIGH))
    end
    `endif

endmodule
`endif
`endif
