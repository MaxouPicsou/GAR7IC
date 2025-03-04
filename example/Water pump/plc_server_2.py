import snap7
from snap7.type import *
import time
import ctypes

# ===============================
# SYSTEM CONFIGURATION
# ===============================

SERVER_IP = "127.0.0.1"  # Listen on all interfaces
SERVER_PORT = 102  # Standard S7 port
DB_NUMBER = 1  # Data Block number
SIZE_DB = 10  # Size of the DB in bytes

# ===============================
# INITIALIZE MEMORY FOR INPUTS, OUTPUTS, AND DB
# ===============================

# Create memory areas for Inputs, Outputs, and DB
db_data = (ctypes.c_ubyte * SIZE_DB)()
input_data = (ctypes.c_ubyte * 2)()  # 2 bytes for input states
output_data = (ctypes.c_ubyte * 2)()  # 2 bytes for output states

# Initialize Data Block (DB)
snap7.util.set_bool(db_data, 0, 0, False)  # Machine status (BOOL)
snap7.util.set_int(db_data, 2, 50)  # Target water level (INT)
snap7.util.set_real(db_data, 4, 0.0)  # Current water level (REAL)

# Initialize Inputs
snap7.util.set_bool(input_data, 0, 0, False)  # Water level sensor (BOOL)

# Initialize Outputs
snap7.util.set_bool(output_data, 0, 0, False)  # Pump state (BOOL)

# ===============================
# INITIALIZE PLC SERVER
# ===============================

server = snap7.server.Server()
server.register_area(SrvArea.DB, DB_NUMBER, db_data)
server.register_area(SrvArea.PE, 0, input_data)  # PE (Process Input)
server.register_area(SrvArea.PA, 0, output_data)  # PA (Process Output)
server.start()

print("✅ Industrial System Simulation Started.")

# ===============================
# MAIN LOOP
# ===============================

while True:
    event = server.pick_event()
    if event:
        if event.EvtCode == 262144 and event.EvtRetCode == 0:
            if event.EvtParam1 == 132:  # Data Block Write
                start_address = event.EvtParam3
                write_length = event.EvtParam4

                if start_address == 0:
                    machine_running = snap7.util.get_bool(db_data, start_address, 0)
                    print(f"🔹 Machine {'ON' if machine_running else 'OFF'} command received")

                elif start_address + write_length >= 2:
                    setpoint_level = snap7.util.get_int(db_data, start_address)
                    print(f"🔹 New water level setpoint: {setpoint_level}")

        print(server.event_text(event))

    # ===============================
    # READ INPUTS (Sensors)
    # ===============================

    water_sensor_triggered = snap7.util.get_bool(input_data, 0, 0)  # Read water level sensor

    # ===============================
    # PROCESS WATER LEVEL CONTROL
    # ===============================

    machine_running = snap7.util.get_bool(db_data, 0, 0)
    setpoint_level = snap7.util.get_int(db_data, 2)
    water_level = snap7.util.get_real(db_data, 4)

    if machine_running:
        if water_sensor_triggered or water_level < setpoint_level:
            water_level += 0.5  # Pump ON (fills up)
            pump_status = True
        else:
            pump_status = False
    else:
        if water_level > 0:
            water_level -= 0.3  # Water evaporation or leakage
        pump_status = False

    # ===============================
    # UPDATE OUTPUTS AND DB
    # ===============================

    snap7.util.set_real(db_data, 4, water_level)  # Update water level in DB
    snap7.util.set_bool(output_data, 0, 0, pump_status)  # Update pump status in Outputs

    print(f"💧 Water Level: {water_level:.1f} | Pump {'ON' if pump_status else 'OFF'} | Sensor {'TRIGGERED' if water_sensor_triggered else 'OFF'}")

    time.sleep(1)  # 1-second cycle time
