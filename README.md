# **GAR7IC - S7COMM Network Capture and Analysis Tool**

## **📌 Overview**
**GAR7IC** (*Generalized Automatic Recording and Labeling for Industrial Communication*) is a **tool for recording, analyzing, and labeling S7COMM network traffic**.
It captures **Siemens PLC (Programmable Logic Controller) communications**, extracts data values, and stores them in a **PCAP file** or a **structured Pandas table**.

### **🎯 Key Features**
✔ **Captures and analyzes S7COMM packets** from a **PCAP/PCAPNG** file
✔ **Automatically labels packets** based on a YAML configuration file
✔ **Extracts and processes S7COMM functions (READ/WRITE, PLC_STOP, etc.)**
✔ **Supports Data Blocks (DB), Inputs, and Outputs**
✔ **Generates a CSV table with extracted network data**

---

## **📌 System Architecture**
**GAR7IC** processes network data by extracting and analyzing **S7COMM messages** using `pyshark` and `snap7`.

### **🛠 Data Structure in PLC (YAML Configuration)**
The tool uses a **YAML configuration file** to **map PLC addresses to variables**. Example:

```yaml
plc:
  - name: "Machine_1"
    model: "CPU 315-2 PN/DP"
    ip: "192.168.0.1"
    rack: 0
    slot: 0
    port: 102
    io_mapping:
      data_block:
        - name: "DB1"
          number: 1
          variables:
            - name: "Machine State"
              address: 0.0
              type: "BOOL"
            - name: "Temperature"
              address: 4
              type: "REAL"
