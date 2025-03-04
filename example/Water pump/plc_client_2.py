import snap7
from snap7.util import get_bool, get_int, get_real, set_bool, set_int
import time

# === Configuration du client S7 ===
PLC_IP = "127.0.0.1"   # Adresse IP du serveur S7 (doit être identique au serveur)
RACK = 0               # Rack du PLC (0 par défaut)
SLOT = 1               # Slot du PLC (1 pour les CPU Siemens)
DB_NUMBER = 1          # Numéro du Data Block (DB) utilisé dans le serveur
SIZE_DB = 10           # Taille du DB en bytes (doit correspondre au serveur)
INPUT_SIZE = 2         # Taille des entrées (Process Input - PE)
OUTPUT_SIZE = 2        # Taille des sorties (Process Output - PA)

# Connexion au serveur S7
plc = snap7.client.Client()
plc.connect(PLC_IP, RACK, SLOT, 102)
print("✅ Client connecté au serveur S7!")

# Fonction pour lire les valeurs du Data Block
def read_db_values():
    data = plc.read_area(snap7.type.Areas.DB, DB_NUMBER, 0, SIZE_DB)

    machine_on = get_bool(data, 0, 0)
    setpoint_level = get_int(data, 2)
    current_water_level = get_real(data, 4)

    print("\n📡 Données du Data Block (DB):")
    print(f"   ▶ Machine state: {'ON' if machine_on else 'OFF'}")
    print(f"   ▶ Setpoint Level: {setpoint_level} cm")
    print(f"   ▶ Current Water Level: {current_water_level:.1f} cm")
    return data

# Fonction pour lire les entrées (capteur d'eau)
def read_inputs():
    data = plc.read_area(snap7.type.Areas.PE, 0, 0, INPUT_SIZE)
    water_sensor_triggered = get_bool(data, 0, 0)

    print("\n📡 Entrées (Sensors):")
    print(f"   ▶ Water Sensor: {'TRIGGERED' if water_sensor_triggered else 'OFF'}")
    return data

# Fonction pour lire les sorties (état de la pompe)
def read_outputs():
    data = plc.read_area(snap7.type.Areas.PA, 0, 0, OUTPUT_SIZE)
    pump_status = get_bool(data, 0, 0)

    print("\n📡 Sorties (Actuators):")
    print(f"   ▶ Pump State: {'ON' if pump_status else 'OFF'}")
    return data

# Fonction pour écrire une nouvelle valeur dans le Data Block
def write_db_values(data, machine_on=None, setpoint=None):
    if machine_on is not None:
        set_bool(data, 0, 0, machine_on)
    if setpoint is not None:
        set_int(data, 2, setpoint)

    plc.write_area(snap7.type.Areas.DB, DB_NUMBER, 0, data)
    print("\n✅ Valeurs mises à jour dans le PLC.")

# === Exemple d'utilisation ===
# 1️⃣ Lire les valeurs initiales
db_data = read_db_values()
input_data = read_inputs()
output_data = read_outputs()

# 2️⃣ Modifier la valeur du Setpoint (nouveau niveau d'eau cible)
new_setpoint = 80  # Exemple : Changer le niveau d'eau cible à 80 cm
write_db_values(db_data, setpoint=new_setpoint)

# 3️⃣ Activer la machine (démarrer la pompe)
write_db_values(db_data, machine_on=True)

# 4️⃣ Lire les nouvelles valeurs pour vérifier la mise à jour
read_db_values()
read_inputs()
read_outputs()

# Déconnexion
plc.disconnect()
print("\n🔌 Déconnexion du client S7.")
