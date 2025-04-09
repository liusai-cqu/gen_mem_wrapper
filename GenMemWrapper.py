import os
import sys
sys.path.append("./fscripts/")

from pprint import pprint  # ZLIN_DBG
#from Mem_1RW_template import Mem1RW
#from Mem_1RWM_template import Mem1RWM
#from Mem_1R1W_template import Mem1R1W
#from Mem_1R1WM_template import Mem1R1WM
from Mem_1R1WA_template import Mem1R1WA
#from Tcam_1RWS_template import Tcam1RWS



import MemTop_1R1WA_template




import json
import re
import argparse
import logging
import csv2json_m


def json2ram(file_name, DIR="./"):
    ram_table = csv2json_m.process_csv2dict(file_name)
    ram = dict()


    fadio_dict = grep_some_info_from_beh_model()  #

    for k in ram_table["MemoryWrapperList"].keys():
        print(k)

        
        ram_attr_list = ram_table["MemoryWrapperList"][k]
        print(ram_attr_list)
        gen_memwrapper(mdict=ram_attr_list, DIR=DIR, fadio_dict=fadio_dict)
        
        
        
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
        # if t == "1RW":
        #     MemTop_1RW = MemTop_1RW_template.MemWrapTop()
        #     MemTop_1RW.Initialize()
        #     MemTop_1RW.loadjson(ram[t])
        #     MemTop_1RW.DumpRTL(filename=os.path.join(DIR, "RAMWRAP_" + str(t) + "_TOP.sv"))
        # elif t == "1RWM":
        #     MemTop_1RWM = MemTop_1RWM_template.MemWrapTop()
        #     MemTop_1RWM.Initialize()
        #     MemTop_1RWM.loadjson(ram[t])
        #     MemTop_1RWM.DumpRTL(filename=os.path.join(DIR, "RAMWRAP_" + str(t) + "_TOP.sv"))
        # elif t == "1R1W":
        #     MemTop_1R1W = MemTop_1R1W_template.MemWrapTop()
        #     MemTop_1R1W.Initialize()
        #     MemTop_1R1W.loadjson(ram[t])
        #     MemTop_1R1W.DumpRTL(filename=os.path.join(DIR, "RAMWRAP_" + str(t) + "_TOP.sv"))
        # elif t == "1R1WM":
        #     MemTop_1R1WM = MemTop_1R1WM_template.MemWrapTop()
        #     MemTop_1R1WM.Initialize()
        #     MemTop_1R1WM.loadjson(ram[t])
        #     MemTop_1R1WM.DumpRTL(filename=os.path.join(DIR, "RAMWRAP_" + str(t) + "_TOP.sv"))
        # elif t == "1R1WA":
        if t == "1R1WA":
            MemTop_1R1WA = MemTop_1R1WA_template.MemWrapTop()
            MemTop_1R1WA.Initialize()
            MemTop_1R1WA.loadjson(ram[t])
            MemTop_1R1WA.DumpRTL(filename=os.path.join(DIR, "RAMWRAP_" + str(t) + "_TOP.sv"))
        # elif t == "RWS":
        #     TcamTop_1RWS = Tcam_1RWS_template.TcamWrapTop()
        #     TcamTop_1RWS.Initialize()
        #     TcamTop_1RWS.loadjson(ram[t])
        #     TcamTop_1RWS.DumpRTL(filename=os.path.join(DIR, "TCAMWRAP_" + str(t) + "_TOP.sv"))


        else:
            logging.warning("This type memory (%s) cannot be supported", t)
    return ram
def extr_db_attr(db_name="", mem_name=""):
    if db_name != "":
        mask_flag = "0"
        type_str = ""
        si_so_split_flag = ""
        type_list = []
        type_str_re = re.compile(r"^sa(\w\w\w)\w\d")
        type_str_mo = type_str_re.search(db_name.lower())
        if type_str_mo:
            type_str = type_str_mo.group(1).rstrip()
            mask_flag = re.search(r"\d+x\d+m\d+b\dw(\d)c(\d)p(\d)", db_name.lower()).group(1).rstrip()
            si_so_split_flag =re.search(r"c(\d)p(\d)",db_name.lower()).group(1).rstrip()+re.search(r"c(\d)p(\d)",db_name.lower()).group(2).rstrip()
        else:
            type_str = "NONE"
            mask_flag = "-1"
        if type_str == "dcl" or type_str == "ssl" or type_str == "srl" or type_str == "crl":
            type_str = "dcl_ssl_srl_crl"
        else:
            type_str = type_str
        type_list = [type_str, mask_flag, si_so_split_flag]

        if re.search(r"\d+X\d+", db_name):
            tmp_str = re.search(r"\d+X\d+", db_name).group(0)
            db_depth = int(tmp_str.split("X")[0])
            db_width = int(tmp_str.split("X")[1])
            logging.info("Find Phy MEM: %s DEPTH: %d, WIDTH: %d", db_name, db_depth, db_width)
        elif re.search(r"\d+x\d+x\d", db_name):
            tmp_str = re.search(r"\d+x\d+x\d", db_name).group(0)
            db_depth = int(tmp_str.split("x")[0])
            db_width = int(tmp_str.split("x")[1])
            logging.info("Find Phy TCAM: %s DEPTH: %d, WIDTH: %d", db_name, db_depth, db_width)
        else:
            logging.error("Cannot parse depth and width of physical MEM/TCAM: %s", db_name)
    else:
        logging.error("MEM: %s missing physical memory db config in recipe", mem_name)

        db_depth = 1024
        db_width = 133

    return db_depth, db_width, type_list

def grep_some_info_from_beh_model():
    fadio_dict = {}
    pd_dir = "./" #"/workspace/PD/IPLIB/PM99"
    verilog_file_path = ""
    si_so_high_regex = re.compile(r'^\s*output\+s+S0_D_HA;')

    folder_name_regx = re.compile(r'^(sa.*zh(__\d)?)$')
    folder_list = []
    folder_list_of_remove = []
    folder_list = os.listdir(pd_dir)
    for i in range(len(folder_list)):
        mbr = folder_list[i]
        if os.path.isdir(os.path.join(pd_dir, mbr)):
            folder_list_of_remove.append(mbr)


    for i in range(len(folder_list_of_remove)):

        folder_name_mo = folder_name_regx.search(folder_list_of_remove[i])
        find_so_si_flag = 0
        so_si_string = ""
        if folder_name_mo:
            db_name = folder_name_mo.group(1).upper()

            verilog_file_path = f"/workspace/PD/IPLIB/PM999/{folder_name_mo.group(0)}/ff/fgp0825v125c/{db_name.lower()}.v"


            with open(verilog_file_path, 'r') as rd_obj:
                lines = rd_obj.readlines()
                for line in lines:
                    line = line.rstrip()
                    si_so_high_mo = si_so_high_regex.search(line)
                    if si_so_high_mo:
                        find_so_si_flag = 1

                    fadio_dict[int(si_so_high_mo.group(1)) + 1] = si_so_high_mo.group(3)
                    break

    return fadio_dict

def gen_memwrapper(mdict, fadio_dict, DIR=""):


    (db_depth, db_width, type_list) = extr_db_attr(
                            db_name=mdict["PhysicalDB"].upper().strip(),
                            #mdict["PhysicalDB"].strip(),
                            mem_name=mdict["Table name"],
                            )
    db_depth = int(mdict["phy_depth"]) 
    db_width = int(mdict["phy_width"])
    # if (mdict["Type"] == "1RW"):
    #     mem = Mem1RW()
    #     Type_list = type_list
    #     Depth = int(mdict["Depth"])
    #     Width = int(mdict["Width"])
    #     DB_Depth = db_depth
    #     DB_Width = db_width
    #     ECC_Group = int(mdict["ECC_GRP"])
    #     ECC_Enable = mdict["ECC"]
    #     DB_Name = (mdict["PhysicalDB"]).upper().strip()
    #     Fadio_dict = fadio_dict
    #     if (len(mdict["Prefix"].split()) > 0):
    #         mem.Prefix = mdict["Prefix"]
    #     mem.Initialize()
    #     mem.DumpRTL(filename=os.path.join(DIR, mem.BaseName + ".sv"))
    #     mem.DumpLST(filename=os.path.join(DIR, mem.BaseName + ".f"))
    #     mem.DumpTLIST(filename=f"$PROJECT_ROOT/rtl/common/mem_list/" + mem.BaseName + ".sv")
    # elif (mdict["Type"] == "1RWM"):
    #     mem = Mem1RWM()
    #     Type_list = type_list
    #     Depth = int(mdict["Depth"])
    #     Width = int(mdict["Width"])
    #     DB_Depth = db_depth
    #     DB_Width = db_width
    #     ECC_Group = int(mdict["ECC_GRP"])
    #     ECC_Enable = mdict["ECC"]
    #     DB_Name = (mdict["PhysicalDB"]).upper().strip()
    #     Fadio_dict = fadio_dict
    #     if (len(mdict["Prefix"].split()) > 0):
    #         mem.Prefix = mdict["Prefix"]
    #     mem.Initialize()
    #     mem.DumpRTL(filename=os.path.join(DIR, mem.BaseName + ".sv"))
    #     mem.DumpLST(filename=os.path.join(DIR, mem.BaseName + ".f"))
    #     mem.DumpTLIST(filename=f"$PROJECT_ROOT/rtl/common/mem_list/" + mem.BaseName + ".sv")
    # elif (mdict["Type"] == "1R1W"):
    #     mem = Mem1R1W()
    #     Type_list = type_list
    #     Depth = int(mdict["Depth"])
    #     Width = int(mdict["Width"])
    #     DB_Depth = db_depth
    #     DB_Width = db_width
    #     ECC_Group = int(mdict["ECC_GRP"])
    #     ECC_Enable = mdict["ECC"]
    #     DB_Name = (mdict["PhysicalDB"]).upper().strip()
    #     Fadio_dict = fadio_dict
    #     if (len(mdict["Prefix"].split()) > 0):
    #         mem.Prefix = mdict["Prefix"]
    #     mem.Initialize()
    #     mem.DumpRTL(filename=os.path.join(DIR, mem.BaseName + ".sv"))
    #     mem.DumpLST(filename=os.path.join(DIR, mem.BaseName + ".f"))
    #     mem.DumpTLIST(filename=f"$PROJECT_ROOT/rtl/common/mem_list/" + mem.BaseName + ".sv")
    # elif (mdict["Type"] == "1R1WM"):
    #     mem = Mem1R1WM()
    #     Type_list = type_list
    #     Depth = int(mdict["Depth"])
    #     Width = int(mdict["Width"])
    #     DB_Depth = db_depth
    #     DB_Width = db_width
    #     ECC_Group = int(mdict["ECC_GRP"])
    #     ECC_Enable = mdict["ECC"]
    #     DB_Name = (mdict["PhysicalDB"]).upper().strip()
    #     Fadio_dict = fadio_dict
    #     if (len(mdict["Prefix"].split()) > 0):
    #         mem.Prefix = mdict["Prefix"]
    #     mem.Initialize()
    #     mem.DumpRTL(filename=os.path.join(DIR, mem.BaseName + ".sv"))
    #     mem.DumpLST(filename=os.path.join(DIR, mem.BaseName + ".f"))
    #     mem.DumpTLIST(filename=f"$PROJECT_ROOT/rtl/common/mem_list/" + mem.BaseName + ".sv")
    # elif (mdict["Type"] == "1R1WA"):
    if (mdict["Type"] == "1R1WA"):
        mem = Mem1R1WA(
                Type_list = type_list,
                Depth = int(mdict["Depth"]),
                Width = int(mdict["Width"]),
                DB_Depth = db_depth,
                DB_Width = db_width,
                ECC_Grp = int(mdict["ECC_GRP"]),
                ECC_enable = mdict["ECC"],
                DB_Name = (mdict["PhysicalDB"]).upper().strip(),
                Fadio_dict = fadio_dict,
        )
        if (len(mdict["Prefix"].split()) > 0):
            mem.Prefix = mdict["Prefix"]
        mem.Initialize()
        mem.DumpRTL(filename=os.path.join(DIR, mem.BaseName + ".sv"))
        mem.DumpLIST(filename=os.path.join(DIR, mem.BaseName + ".f"))
        mem.DumpTLIST(filename=f"$PROJECT_ROOT/rtl/common/mem_list/" + mem.BaseName + ".sv")
    # elif (mdict["Type"] == "RWS"):
    #     mem = Tcam1RWS()
    #     Type_list = type_list
    #     Depth = int(mdict["Depth"])
    #     Width = int(mdict["Width"])
    #     DB_Depth = db_depth
    #     DB_Width = db_width
    #     ECC_Group = int(mdict["ECC_GRP"])
    #     ECC_Enable = mdict["ECC"]
    #     DB_Name = (mdict["PhysicalDB"]).upper().strip()
    #     Fadio_dict = fadio_dict
    #     if (len(mdict["Prefix"].split()) > 0):
    #         mem.Prefix = mdict["Prefix"]
    #     mem.Initialize()
    #     mem.DumpRTL(filename=os.path.join(DIR, mem.BaseName + ".sv"))
    #     mem.DumpLST(filename=os.path.join(DIR, mem.BaseName + ".f"))
    #     mem.DumpTLIST(filename=f"$PROJECT_ROOT/rtl/common/mem_list/" + mem.BaseName + ".sv")
    else:
        logging.error("This Mem Type:%s has not been supported yet", mdict["Type"])
        return


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
    if args.o:
        json2ram(file_name=args.i, DIR=args.o)
    else:
        json2ram(file_name=args.i, DIR=os.getcwd())
    #gen_memwrapper(mdict=mem_dict, DIR=args.o)