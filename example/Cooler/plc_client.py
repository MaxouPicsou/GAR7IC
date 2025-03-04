import snap7
import time


client = snap7.client.Client()
client.connect('127.0.0.1', 0, 0)

print(client.get_cpu_info())
while True:
    data = client.db_read(1, 0, 1)
    machine_status = snap7.util.get_bool(data, 0, 0)
    data = client.db_read(1, 2, 2)
    set_point = snap7.util.get_int(data, 0)
    data = client.db_read(1, 4, 4)
    current_temperature = snap7.util.get_real(data, 0)
    print(f'Current temperature {current_temperature:.2f}')
    if not machine_status and current_temperature>set_point+2.0:
        command = bytearray(2)
        snap7.util.set_bool(command, 0, 0, True)
        client.db_write(1, 0, command)
        print('Sent machine ON')
    elif machine_status and current_temperature<set_point-2.0:
        command = bytearray(2)
        snap7.util.set_bool(command, 0, 0, False)
        client.db_write(1, 0, command)
        print('Sent machine OFF')
    time.sleep(1)