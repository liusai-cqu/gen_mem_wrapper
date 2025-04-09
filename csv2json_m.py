
import sys  
import re  
import json  
import argparse  
import csv  

def pretreatment(filename):  
    csv_tmp = open(filename).readlines()  
    csv_tmp[0] = '' #'delete the first line of csv'  
    with open('taurus_memory_list.csv', 'w') as f:  
        f.writelines(csv_tmp)  

def process_csv2dict(filename):  
    pretreatment(filename)  
    mem_dict = dict()  
    table_obj = dict()  
    x = 0  
    with open('taurus_memory_list.csv') as f:  
        f_csv = csv.DictReader(f)  
        for row in f_csv:  
            x = x + 1  
            mem_dict["MEM_INDEX_" + str(x)] = row  
        table_obj["MemoryWrapperList"] = mem_dict  
    return table_obj  

def dump_json(dict_obj):  
    json_str_out = json.dumps(dict_obj, sort_keys=False, indent=4, separators=(',', ': '))  


    return json_str_out  


if __name__ == "__main__":  
    parser = argparse.ArgumentParser(description="program description")  
    parser.add_argument('-i', help="input ntbl file name")  
    parser.add_argument('-o', help="output json file name")  
    args = parser.parse_args()  
    json_string = dump_json(process_csv2dict(args.i))  
    fobj = open(args.o, 'w')  
    fobj.write(json_string)  
    fobj.close()  
    