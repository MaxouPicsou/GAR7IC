import snap7
from snap7.type import *
from snap7.util import *
import struct
import time
import ctypes

# Configuration du serveur PLC
SERVER_IP = "127.0.0.1"  # Écoute sur toutes les interfaces réseau
SERVER_PORT = 102  # Port standard S7
DB_NUMBER = 1  # Numéro de la DB utilisée
SIZE_DB = 10  # Taille de la DB en bytes

db_data = (ctypes.c_ubyte*8)()

machine_on = False
snap7.util.set_bool(db_data, 0, 0, machine_on)
setpoint = 10
snap7.util.set_int(db_data, 2, setpoint)
current_temperature = 0.0
snap7.util.set_real(db_data, 4, current_temperature)

# Initialisation du serveur
server = snap7.server.Server()
data = server.register_area(SrvArea.DB, DB_NUMBER, db_data)
server.start()

while True:
    event = server.pick_event()

    if event:
        print(event)
        if event.EvtCode == 262144 and event.EvtRetCode == 0:
            if event.EvtParam1 == 132:
                address = event.EvtParam2
                start_address = event.EvtParam3
                write_length = event.EvtParam4
                if start_address == 0:
                    machine_on = snap7.util.get_bool(db_data, start_address, 0)
                    print(f'Machine {"ON" if machine_on else "OFF"} command received')
                elif start_address + write_length >= 2:
                    setpoint = snap7.util.get_int(db_data, start_address)
                    print(f'New setpoint {setpoint}')
        print(server.event_text(event))
    else:
        if machine_on:
            current_temperature = max(current_temperature - 0.05, 0)
        else:
            current_temperature = min(current_temperature + 0.05, 20)
        snap7.util.set_real(db_data, 4, current_temperature)
        time.sleep(.1)