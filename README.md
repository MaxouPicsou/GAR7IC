
# GAR7IC - S7COMM Network Analysis Tool  
<p align="center">
  <img src="gar7ic_logo.png" alt="GAR7IC Logo" width="150">
</p>

## 📌 Overview  
**GAR7IC** (*Generalized Automatic Review and Labelling for S7COMM Industrial Communication*) is a **tool for analyzing and labeling S7COMM network traffic**.  
It processes **Siemens PLC (Programmable Logic Controller) communications**, extracts data values, and stores them in a **PCAP file** or a **structured Pandas table**.

### 🎯 Key Features  
- ✅ **Analyzes S7COMM packets** from a **PCAP/PCAPNG** file  
- ✅ **Automatically labels packets** based on a YAML configuration file  
- ✅ **Extracts and processes S7COMM functions** (READ, WRITE, PLC_STOP, etc.)  
- ✅ **Supports Data Blocks (DB), Inputs, and Outputs**  
- ✅ **Generates a CSV table with extracted network data**  

---

## 📌 System Architecture  
**GAR7IC** processes network data by extracting and analyzing **S7COMM messages** using `pyshark` and `snap7`.  

### 🛠 Data Structure in PLC (YAML Configuration)  
The tool uses a **YAML configuration file** to **map PLC addresses to variables**.  

#### 🔹 **Example YAML Configuration**
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
```

### 📡 Data Extracted from PCAP  
Only the **addresses involved in communication** are extracted.  
In the **PCAPNG comments**, **only the variable "name"** is labeled.  

For **CSV table generation**, the following fields are extracted:  

| **Field**                   | **Description**                                   |
|-----------------------------|---------------------------------------------------|
| `Frame_Number`              | Packet frame number in PCAP                      |
| `Timestamp`                 | Capture timestamp                                |
| `Timestamp_Epoch`           | Unix timestamp format                            |
| `Timestamp_Shift`           | Relative timestamp                               |
| `Source_IP` / `Destination_IP` | IP addresses of sender/receiver           |
| `Length`                    | Packet length in bytes                          |
| `Header_Rosctr`             | Request type (JOB, ACK, etc.)                    |
| `Header_PduRef`             | Protocol Data Unit reference number             |
| `Param_Function`            | S7 function (READ, WRITE, PLC_STOP)              |
| `Param_Item_Count`          | Number of items in the request                   |
| `Param_Item_Transport_Size` | Size of transported data                        |
| `Param_Item_Length`         | Length of the data field                        |
| `Param_Item_DB`             | Data Block number                               |
| `Param_Item_Area`           | Memory area (INPUT, OUTPUT, DB)                  |
| `Param_Address_Byte`        | Address byte offset in memory                   |
| `Param_Address_Bit`         | Address bit offset (for BOOL types)             |
| `Variable_Name`             | Extracted variable name (from YAML mapping)      |
| `Data_Type`                 | Data type (BOOL, INT, REAL)                      |
| `Data_Value`                | Extracted value (if applicable)                  |
| `Data_Return_Code`          | Response status code (success, failure, etc.)    |

---

## 📌 Installation  
### 1️⃣ Install Dependencies  
GAR7IC uses Python 3 and several required libraries, which can be installed using **`requirements.txt`**:  
```sh
pip install -r requirements.txt
```
Alternatively, you can install manually:  
```sh
pip install pyshark pyyaml snap7 pandas
```
On **Linux**, you may also need:
```sh
sudo apt install tshark libsnap7-dev
```

### 2️⃣ Run GAR7IC  
#### 🔹 **Option 1: Generate a CSV Table**  
Extract **S7COMM data** into a structured Pandas DataFrame and save as CSV:  
```sh
python gar7ic.py -f capture.pcapng -c config.yaml -t
```
✔ The extracted data will be stored in **`output.csv`**.

#### 🔹 **Option 2: Annotate PCAP with Comments**  
Add **labels/comments** to S7COMM packets in a **PCAP file**:  
```sh
python gar7ic.py -f capture.pcapng -c config.yaml -p
```
✔ The labeled PCAP will be saved as **`output.pcapng`**.

---

## 📌 How It Works  
### 🔹 **Step 1: Read PCAP File**  
- The tool **loads a PCAP file** containing S7COMM packets.  
- Uses **PyShark** to **extract packet details**.  
- Parses **function codes, DB numbers, and memory areas**.  

### 🔹 **Step 2: Process & Label Data**  
- **Matches extracted addresses** with known PLC variables (from YAML).  
- Converts **hexadecimal S7COMM values** into **REAL, INT, or BOOL**.  
- Adds **comments to PCAP packets** based on extracted data.  

### 🔹 **Step 3: Generate Output**  
- If `-t` is used → Saves extracted data as a structured **CSV file**.  
- If `-p` is used → Labels packets inside **PCAPNG** for better analysis in **Wireshark**.  

---

## 📌 Example Output  
### 1️⃣ **Extracted Data (CSV Table)**

| Frame | Timestamp                          | Timestamp_Epoch       | Timestamp_Shift | Source IP  | Destination IP | Length | Header_Rosctr | Header_PduRef | Param_Function | Param_Item_Count | Param_Item_Transport_Size | Param_Item_Length | Param_Item_DB | Param_Item_Area | Param_Address_Byte | Param_Address_Bit | Variable_Name   | Data_Type | Data_Value | Data_Return_Code |
|-------|-----------------------------------|----------------------|----------------|------------|----------------|--------|---------------|---------------|---------------|----------------|------------------------|----------------|--------------|---------------|------------------|----------------|---------------|----------|------------|----------------|
| 1     | Mar 1, 2025 16:07:52.913675704 CET | 1740841672.913675704 | 0.000000000    | 127.0.0.1  | 127.0.0.1      | 97     | JOB           | 5376          | READ          | 1              | BYTE                   | 1              | 1            | DATA_BLOCK    | 0                | 0              | Machine state | BOOL     | Unknown    | Unknown        |
| 2     | Mar 1, 2025 16:07:52.913812951 CET | 1740841672.913812951 | 0.000137247    | 127.0.0.1  | 127.0.0.1      | 92     | ACK_DATA      | 5376          | READ          | 1              | Unknown                | Unknown        | Unknown      | Unknown       | Unknown          | Unknown        | Machine state | BOOL     | True       | SUCCESS        |

### 2️⃣ **Annotated PCAP in Wireshark**  
After processing, packets in **Wireshark** will contain **comments**:
```
Temperature
Machine State
```
🔹 **Only the variable "name" appears in the PCAP comments. No full data values are stored.**  

---

## 📌 License  
This project is licensed under the **MIT License**.

🔹 **Contributions are welcome! 🚀**

