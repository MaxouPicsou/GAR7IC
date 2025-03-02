import os
import argparse
import pyshark
import yaml
import binascii
import snap7
import pandas as pd
from enum import Enum

# ===============================
# ENUMS FOR S7COMM INTERPRETATION
# ===============================

class S7CommParamFunction(Enum):
    """ Enumeration of S7COMM parameter functions. """
    READ = 0x04
    WRITE = 0x05
    PLC_STOP = 0x29

class S7CommHeaderRosctr(Enum):
    """ Enumeration of S7COMM ROSCTR header types. """
    JOB = 0x01
    ACK = 0x02
    ACK_DATA = 0x03

class S7CommMemoryArea(Enum):
    """ Enumeration of S7COMM memory areas. """
    INPUT = 0x81
    OUTPUT = 0x82
    DATA_BLOCK = 0x84

class S7CommTransportSize(Enum):
    """ Enumeration of transport sizes in S7COMM. """
    BIT = 0x01
    BYTE = 0x02
    CHAR = 0x03
    WORD = 0x04
    INT = 0x05

class S7CommItemResponse(Enum):
    """ Enumeration of response codes for S7COMM operations. """
    SUCCESS = 0xFF
    HARDWARE_FAULT = 0x01
    OBJECT_DOES_NOT_EXIST = 0x0A
    ACCESS_NOT_ALLOWED = 0x03
    ADDRESS_OUT_OF_RANGE = 0x05
    DATA_TYPE_NOT_SUPPORTED = 0x06
    DATA_TYPE_INCONSISTENT = 0x07
    RESERVED = 0x00


# ===============================
# UTILITY FUNCTIONS
# ===============================

def build_fast_lookup(plcs):
    """
    Builds a fast-access dictionary indexed by PLC IP address.

    :param plcs: List of PLCs from the YAML configuration.
    :return: Dictionary {IP: {"data_block": [{address, name, type}], "input": [], "output": []}}
    """
    lookup = {}

    for plc in plcs:
        ip = plc["ip"]
        lookup[ip] = {
            "data_block": [],
            "input": [],
            "output": []
        }

        # DATA_BLOCK
        for db in plc["io_mapping"].get("data_block", []):
            db_number = db["number"]
            for var in db["variables"]:
                lookup[ip]["data_block"].append({
                    "ip": ip,
                    "db_number": db_number,
                    "address": var["address"],
                    "name": var["name"],
                    "type": var["type"],
                    "area": "DATA_BLOCK"
                })

        # INPUT
        if "input" in plc["io_mapping"]:
            for var in plc["io_mapping"]["input"]:
                lookup[ip]["input"].append({
                    "ip": ip,
                    "address": var["address"],
                    "name": var["name"],
                    "type": var["type"],
                    "area": "INPUT"
                })

        # OUTPUT
        if "output" in plc["io_mapping"]:
            for var in plc["io_mapping"]["output"]:
                lookup[ip]["output"].append({
                    "ip": ip,
                    "address": var["address"],
                    "name": var["name"],
                    "type": var["type"],
                    "area": "OUTPUT"
                })

    return lookup


def find_variable(ip, byte_address, bit_address, data_type, lookup):
    """
    Searches for a variable in the lookup dictionary based on its address and type.

    :param ip: PLC IP address.
    :param byte_address: Byte address of the variable.
    :param bit_address: Bit address within the byte.
    :param data_type: Data type ('data_block', 'input', 'output').
    :param lookup: Fast-access dictionary with PLC mappings.
    :return: Dictionary containing variable information or a default "Unknown" value.
    """

    if ip not in lookup:
        return "Unknown IP address"

    if not isinstance(data_type, int):
        data_type = S7CommMemoryArea[data_type].value

    for var in lookup[ip].get(S7CommMemoryArea(data_type).name.lower(), []):
        if str(var["address"]) == str(byte_address) + "." + str(bit_address):
            return var

    return None


def convert_s7_hex_to_value(hex_str, data_type, bit_index=0):
    """
    Convert a hexadecimal string "xx:xx:xx:xx" into a value based on the specified type.

    :param hex_str: The hexadecimal string in the format "xx:xx:xx:xx"
    :param data_type: Expected data type ('BOOL', 'REAL', 'INT')
    :param bit_index: (Optional) Bit index for BOOL (0-7) if applicable
    :return: Converted value
    """

    # Hexadecimal convertion
    data_bytes = binascii.unhexlify(hex_str.replace(':', ''))
    _data = bytearray(data_bytes)

    # Select right type
    if data_type == "REAL":
        return snap7.util.get_real(_data, 0)  # Float IEEE 754 on 4 bytes
    elif data_type == "INT":
        return snap7.util.get_int(_data, 0)
    elif data_type == "BOOL":
        return snap7.util.get_bool(_data, 0, bit_index)
    else:
        raise ValueError(f"Unsupported type: {data_type}")

# ===============================
# SCRIPT ARGUMENTS
# ===============================

parser = argparse.ArgumentParser(description="GAR7IC is a tool read S7COMM capture and labelling it according to configuration file.")

parser.add_argument("-f", "--file", type=str, help="", required=True)
parser.add_argument("-c", "--configuration", type=str, help="", required=True)
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("-t", "--table", help="Generate pandas table of S7COMM communication.", action="store_true")
group.add_argument("-p", "--pcap", help="Comment integration into pcap file according to configuration file.", action="store_true")

args = parser.parse_args()

# ===============================
# LOAD YAML CONFIGURATION
# ===============================

with open(args.configuration, "r") as file:                         # Read PLC architecture configuration file
    config = yaml.safe_load(file)

fast_lookup = build_fast_lookup(config["plc"])                      # Extract PLC IP to identify them and associated addresses

# ===============================
# PROCESSING PCAP FILE
# ===============================

packets = pyshark.FileCapture(args.file, display_filter="s7comm")   # Reading PCAP file
buffer_pduref = {}                                                  # Create buffer to stock request before receiving response

if args.pcap:

    os.system("cp " + args.file + " output.pcapng")                 # Duplicate pcap file

    # Processing each packet
    for packet in packets:
        # Extract packet information (packet number and ip src/dst)
        packet_number = packet.number
        packet_ip_src = packet.ip.src
        packet_ip_dst = packet.ip.dst

        # Extract ROSCTR to identify communication direction
        header_rosctr = int(getattr(packet.s7comm, 'header_rosctr'))
        param_func = int(getattr(packet.s7comm, 'param_func'), 16)

        # Protocol data unit reference
        header_pduref = int(getattr(packet.s7comm, 'header_pduref'))

        # JOB (request)
        if header_rosctr == S7CommHeaderRosctr.JOB.value:

            param_item_area = int(getattr(packet.s7comm, 'param_item_area'), 16)
            param_item_address = int(getattr(packet.s7comm, 'param_item_address'), 16)
            param_item_address_byte = param_item_address // 8
            param_item_address_bit = param_item_address % 8

            variable_info = find_variable(packet_ip_dst, param_item_address_byte, param_item_address_bit, param_item_area, fast_lookup)
            buffer_pduref[header_pduref] = variable_info

            os.system("editcap -a " + packet_number + ":'" + variable_info['name'] + "' output.pcapng output.pcapng")

        # ACK_DATA (response with data)
        elif header_rosctr == S7CommHeaderRosctr.ACK_DATA.value:

            if header_pduref in buffer_pduref:
                variable_info = buffer_pduref[header_pduref]

            os.system("editcap -a " + packet_number + ":'" + variable_info['name'] + "' output.pcapng output.pcapng")

        else:
            os.system("editcap -a " + packet_number + ":'Unknown S7COMM device.' output.pcapng output.pcapng")

    packets.close()

elif args.table:
    # Dataframe creation
    df = pd.DataFrame(columns=[
        "Frame_Number", "Timestamp", "Timestamp_Epoch", "Timestamp_Shift", "Source_IP", "Destination_IP", "Length",
        "Header_Rosctr", "Header_PduRef", "Param_Function", "Param_Item_Count",
        "Param_Item_Transport_Size", "Param_Item_Length", "Param_Item_DB", "Param_Item_Area",
        "Param_Address_Byte", "Param_Address_Bit", "Variable_Name", "Data_Type", "Data_Value", "Data_Return_Code"
    ])

    # Reading PCAP file
    packets = pyshark.FileCapture(args.file, display_filter="s7comm")

    # Create buffer to stock request before receiving response
    buffer_pduref = {}

    # Read PLC architecture configuration file
    with open(args.configuration, "r") as file:
        config = yaml.safe_load(file)

    # Extract PLC IP to identify them and associated addresses
    fast_lookup = build_fast_lookup(config["plc"])

    for packet in packets:

        # ======= Main information =======
        frame_number = packet.number
        timestamp = packet.frame_info.time
        timestamp_epoch = packet.frame_info.time_epoch
        timestamp_shift = packet.frame_info.time_relative

        src_ip = getattr(packet.ip, "src", "Unknown")
        dst_ip = getattr(packet.ip, "dst", "Unknown")
        length = getattr(packet.frame_info, "len", "Unknown")

        # ======= S7COMM information =======
        # === HEADER ===
        header_rosctr = getattr(packet.s7comm, "header_rosctr", "Unknown")
        if header_rosctr != "Unknown":
            header_rosctr = S7CommHeaderRosctr(int(header_rosctr, 16)).name

        header_pduref = getattr(packet.s7comm, "header_pduref", "Unknown")
        header_datlg = getattr(packet.s7comm, "header_datlg", "Unknown")

        # === PARAMETER ===
        param_func = S7CommParamFunction(int(getattr(packet.s7comm, "param_func", "Unknown"), 16)).name
        param_itemcount = getattr(packet.s7comm, "param_itemcount", "Unknown")

        param_item_transp_size = getattr(packet.s7comm, "param_item_transp_size", "Unknown")
        if param_item_transp_size != "Unknown":
            param_item_transp_size = S7CommTransportSize(int(param_item_transp_size, 16)).name

        param_item_length = getattr(packet.s7comm, "param_item_length", "Unknown")
        param_item_db = getattr(packet.s7comm, "param_item_db", "Unknown")

        param_item_area = getattr(packet.s7comm, "param_item_area", "Unknown")
        if param_item_area != "Unknown":
            param_item_area = S7CommMemoryArea(int(param_item_area, 16)).name

        param_item_address = getattr(packet.s7comm, 'param_item_address', "Unknown")
        if param_item_address != "Unknown":
            param_item_address = int(param_item_address, 16)
            param_item_address_byte = param_item_address // 8
            param_item_address_bit = param_item_address % 8
        else:
            param_item_address_byte = "Unknown"
            param_item_address_bit = "Unknown"

        # === DATA ===
        data_returncode = getattr(packet.s7comm, "data_returncode", "Unknown")
        if data_returncode != "Unknown":
            data_returncode = S7CommItemResponse(int(data_returncode, 16)).name

        data_value = "Unknown"

        if header_datlg:
            if header_rosctr == S7CommHeaderRosctr.JOB.name:
                variable_info = find_variable(dst_ip, param_item_address_byte, param_item_address_bit, param_item_area,
                                              fast_lookup)
                if param_func == S7CommParamFunction.WRITE.name:
                    resp_data = getattr(packet.s7comm, 'resp_data')
                    data_value = convert_s7_hex_to_value(resp_data, variable_info["type"])

                buffer_pduref[header_pduref] = variable_info

            else:
                if header_pduref in buffer_pduref:
                    variable_info = buffer_pduref[header_pduref]

                if param_func == S7CommParamFunction.READ.name:
                    resp_data = getattr(packet.s7comm, 'resp_data')
                    data_value = convert_s7_hex_to_value(resp_data, variable_info["type"])

        new_row = pd.DataFrame([{"Frame_Number": frame_number,
                                    "Timestamp": timestamp,
                                    "Timestamp_Epoch": timestamp_epoch,
                                    "Timestamp_Shift": timestamp_shift,
                                    "Source_IP": src_ip,
                                    "Destination_IP": dst_ip,
                                    "Length": length,
                                    "Header_Rosctr": header_rosctr,
                                    "Header_PduRef": header_pduref,
                                    "Param_Function": param_func,
                                    "Param_Item_Count": param_itemcount,
                                    "Param_Item_Transport_Size": param_item_transp_size,
                                    "Param_Item_Length": param_item_length,
                                    "Param_Item_DB": param_item_db,
                                    "Param_Item_Area": param_item_area,
                                    "Param_Address_Byte": param_item_address_byte,
                                    "Param_Address_Bit": param_item_address_bit,
                                    "Variable_Name": variable_info["name"],
                                    "Data_Type": variable_info["type"],
                                    "Data_Value": data_value,
                                    "Data_Return_Code": data_returncode
                            }])
        df = pd.concat([df, new_row], ignore_index=True)

    df.to_csv("output.csv", index=False, encoding="utf-8")
    print("Data saved to 'output.csv'.")







