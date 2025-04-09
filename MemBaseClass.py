import logging
import re
import time
import argparse
import math
import os
import sys
import json
from pathlib import Path


class MemBase():
    def __init__(self, Depth, Width):
        self.Prefix = ""
        self.Type = ""
        self.Depth = Depth
        self.Width = Width
        self.HEADER = ""
        self.RTL = ""
        self.Note = ""
        self.BaseName = "RAMWRAP"
        self.tag = ""

    def Initialize(self):
        self.gen_HEADER()
        self.GeneralProcess()

    def gen_HEADER(self):
        TimeStamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.HEADER = """
        """
        if TimeStamp != "":
            self.HEADER = self.HEADER.replace('$TimeStamp$', TimeStamp)
        self.HEADER = self.HEADER.replace('$NOTE$', self.Note)
        return self.HEADER

    def GeneralProcess(self):
        if self.Prefix:
            self.Prefix_name = ""
        else:
            self.Prefix_name = self.Prefix+"_"
        self.BaseName = "{}_{}_{}_{}X{}".format(self.Prefix_name, self.tag, self.Type, self.Depth, self.Width)
        self.RTL = self.RTL.replace("$BaseName$", "{}".format(self.BaseName))
        self.RTL = self.RTL.replace("$PREFIX$", "{}".format(self.Prefix_name))
        self.RTL = self.RTL.replace("$TYPE$", "{}".format(self.Type))
        self.RTL = self.RTL.replace("$WIDTH$", "{}".format(self.Width))
        self.RTL = self.RTL.replace("$DEPTH$", "{}".format(self.Depth))

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


class MemBase_Cut(MemBase):
    def __init__(self, Depth, Width, DB_Depth, DB_Width, DB_Name, ECC_Grp, Fadio_dict, Type_list, ECC_enable="YES"):
        logging.info("Depth=%d, Width=%d, DB_Depth=%d, DB_Width=%d, ECC_Grp=%s, ECC_enable=%s", Depth, Width, DB_Depth, DB_Width, ECC_Grp, ECC_enable)
        super().__init__(Depth, Width)
        self.Type_list = Type_list
        self.DB_Name = DB_Name
        self.db = PhysicalDB(Depth=DB_Depth, Width=DB_Width, Name=DB_Name, Fadio_dict=Fadio_dict)
        if ECC_enable == "YES":
            self.Cut = WrapCut(Width=self.Width)
            self.ECC_bits = int(self.Cut.calculate()) + ECC_Grp
            self.ECCGRP_Dwidth = self.Cut.Width
            self.ECCGRP_Dwidth = self.ECCGRP_Dwidth + int(self.ECC_bits / ECC_Grp)

    def splice_init(self):
        if self.Depth % self.db.Depth!= 0:
            self.db.y = int(self.Depth / self.db.Depth) + 1
        else:
            self.db.y = int(self.Depth / self.db.Depth)
        if (self.Width + self.ECC_bits) % self.db.Width!= 0:
            self.db.x = int((self.Width + self.ECC_bits) / self.db.Width) + 1
        else:
            self.db.x = int((self.Width + self.ECC_bits) / self.db.Width)
        self.addrwidth = int(math.ceil(math.log(self.Depth, 2)))
        if self.Depth / self.db.Depth <= 1:  # no splice
            self.selbits_h = -1
            self.selbits_l = -1
            self.phyaddr_h = self.addrwidth - 1
        elif (int(self.db.Depth) & (int(self.db.Depth) - 1)) == 0:  # zlin:changed by zlin.bank number is 2^N and each depth's depth may not equal 2^N
            if (math.ceil(self.Depth / self.db.Depth) & (math.ceil(self.Depth / self.db.Depth) - 1)) == 0:
                self.selbits_h = int(math.log(math.ceil(self.Depth / self.db.Depth), 2)) - 1  # changed by lz
            else:
                print("pd make an error:bank's number must be 2^N when each db depth don't equals 2^N")
                self.selbits_l = 0
                self.phyaddr_h = self.addrwidth - 1
        else:  # zlin:NOTE here only support bank number equals 2^N
            if (int(self.Depth % self.db.Depth) == 0):  # Low - level selection  eg :sel [2:0] addr [4:3]
                if (int(self.Depth / self.db.Depth) & (int(self.Depth / self.db.Depth) - 1)) == 0:
                    self.db.y = int(self.Depth / self.db.Depth)
                else:
                    # case4
                    if (self.selbits_h >= self.selbits_l):
                        self.db.y = int((self.Depth - 1) >> self.selbits_l) + 1  # zlin:NOTE:for example,depth is 90,db_depth is 30,use 4 bank,but i think this won't happen,and '>>self.selbits_l' is also wrong
                        print("pd make an error:bank's number must be 2^N when each db depth don't equals 2^N")
            else:  # case6
                if (self.selbits_h >= self.selbits_l):
                    self.db.y = int((self.Depth - 1) >> self.selbits_l) + 1  # delete by lz
                    if (math.ceil(self.Depth / self.db.Depth) & (math.ceil(self.Depth / self.db.Depth) - 1)) == 0:
                        self.db.y = int(self.Depth / self.db.Depth)
                    else:
                        print("pd make an error:bank's number must be 2^N when each db depth don't equals 2^N")

    def GeneralProcess(self):
        super().GeneralProcess()
        self.RTL = self.RTL.replace("$ECCGRPNUM$", "{}".format(self.ECC_Grp))
        self.RTL = self.RTL.replace("$ECCWIDTH$", "{}".format(self.ECC_bits))  # ECC data total bits
        self.RTL = self.RTL.replace("$ECCGRPDWIDTH$", "{}".format(self.ECCGRP_Dwidth))  # ECC GRP total bits
        self.RTL = self.RTL.replace("$DBNAME$", "{}".format(self.db.Name))
        self.RTL = self.RTL.replace("$MDU_DBNAME$", "{}".format(self.db.Name.lower()))
        self.RTL = self.RTL.replace("$FADIO_W$", "{}".format(self.db.Fadio_dict[self.db.Name]))
        self.RTL = self.RTL.replace("$SI_SO_PORTS$", "{}".format(self.db.Fadio_dict[self.db.Name]))
        self.RTL = self.RTL.replace("$DBWIDTH$", "{}".format(self.db.Width))
        self.RTL = self.RTL.replace("$DBDEPTH$", "{}".format(self.db.Depth))
        self.RTL = self.RTL.replace("$DBADDRWIDTH$", "{}".format(self.db.AddrWidth))
        self.RTL = self.RTL.replace("$CUTWRAPIDTH$", "{}".format(self.Width + self.ECC_bits))
        self.RTL = self.RTL.replace("$PHYWRAPNAME$", "{}_{}_{}_{}X{}_phywrap".format(self.Prefix_name, self.tag, self.Type, self.db.Depth, self.db.Width))


def roundup(a, b):
    if a % b == 0:
        return int(a / b)
    else:
        return int(a / b) + 1


class PhysicalDB():
    def __init__(self, Depth, Width, Name, Fadio_dict):
        self.Depth = Depth
        self.Width = Width
        self.Name = Name
        self.Fadio_dict = Fadio_dict
        self.x = 0
        self.y = 0
        self.AddrWidth = 0
        self.Process()
        logging.debug("DB.Depth=%d, DB.Width=%s, DB.AddrWidth=%d", self.Depth, self.Width, self.AddrWidth)

    def Process(self):
        self.AddrWidth = math.ceil((math.log(self.Depth, 2)))


class WrapCut():
    def __init__(self, width):
        self.Width = width
        self.Num = 0
        self.ECCOverhead = 0

    def calculate(self):
        m = 0
        while (2 ** m < self.Width + 1):
            m += 1
        self.ECCOverhead = m + 1
        return self.ECCOverhead