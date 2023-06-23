import subprocess
from dotenv import load_dotenv
import csv
from email.mime.text import MIMEText
import smtplib
import argparse

OSD_HOSTS = [0, 2, 1, 0, 2, 1, 0, 1, 2, 0, 2, 1, 2, 1, 0, 2, 1, 0]
IP_controller_list = ["192.168.100.11", "192.168.100.12", "192.168.100.13"]
compute0_data = ["192.168.100.14", "overcloud-computehci-00.condortech.com.ar"]
compute1_data = ["192.168.100.15", "overcloud-computehci-01.condortech.com.ar"]
compute2_data = ["192.168.100.16", "overcloud-computehci-02.condortech.com.ar"]
controller0_data = ["192.168.100.11", "overcloud-controller-0"]
controller1_data = ["192.168.100.12", "overcloud-controller-1"]
controller2_data = ["192.168.100.13", "overcloud-controller-2"]
MEMORY_THRESHOLD = 60
LOAD_AVG_THRESHOLD_WARNING = 5
LOAD_AVG_THRESHOLD_CRITICAL = 10
IDLE_THRESHOLD_WARNING = 50
IDLE_THRESHOLD_CRITICAL = 35
IOWAIT_THRESHOLD_WARNING = 10
IOWAIT_THRESHOLD_CRITICAL = 25

previous_status = []
with open('current.csv', 'r') as archivo:
    lector = csv.reader(archivo)
    for sublista in lector:
        previous_status.append(sublista)

current_status = [["compute-00_RAM", "OK", ""], ["compute-00_hypervisor", "OK", ""], ["compute-00_loadavg", "OK", ""], ["compute-00_containers", "OK", ""], ["compute-01_RAM", "OK", ""], ["compute-01_hypervisor", "OK", ""], ["compute-01_loadavg", "OK", ""], ["compute-01_containers", "OK", ""], ["compute-02_RAM", "OK", ""], ["compute-02_hypervisor", "OK", ""], ["compute-02_loadavg", "OK", ""], ["compute-02_containers", "OK", ""], ["controller-00_RAM", "OK", ""], ["controller-00_loadavg", "OK", ""], ["controller-00_containers", "OK", ""], ["controller-01_RAM", "OK", ""], ["controller-01_loadavg", "OK", ""], ["controller-01_containers", "OK", ""], ["controller-02_RAM", "OK", ""], ["controller-02_loadavg", "OK", ""], ["controller-02_containers", "OK", ""], ["Ceph_status", "OK", ""], ["Horizon_status", "OK", ""], ["Galera_status", "OK", ""]]

def monitor_computeX (computeX_data):
    command = 'openstack hypervisor show ' + computeX_data[1]  + ' -f value -c memory_mb_used -c memory_mb -c load_average -c running_vms -c state -c vcpus -c vcpus_used'
    temp = subprocess.Popen (command.split (), stdout = subprocess.PIPE) 
    hypervisor_info = str (temp.communicate ()[0], 'utf-8').split ('\n')
    hypervisor_info.pop ()
    
    load_avg = hypervisor_info[0].split (', ')
    load_avg[0] = float (load_avg[0])
    load_avg[1] = float (load_avg[1])
    load_avg[2] = float (load_avg[2])
    memory_mb_total = float (hypervisor_info[1])
    memory_mb_used = float (hypervisor_info[2])
    running_vms = float (hypervisor_info[3])
    hypervisor_status = hypervisor_info[4].lower ()
    cpu_total = float (hypervisor_info[5])
    cpu_used = float (hypervisor_info[6])

    memory_ratio = memory_mb_used/memory_mb_total * 100
   
    command = 'ssh heat-admin@' + computeX_data[0]  + ' "cat data.csv"'
    temp = subprocess.check_output (command, shell=True)
    temp = temp.decode ('utf-8')
    temp = temp.splitlines ()[-1]
    temp = temp.split(',')
    iowait = float(temp [0])
    idle = float(temp [1])

    command = 'ssh heat-admin@' + computeX_data[0]  + ' "sudo podman ps"'
    temp = subprocess.check_output (command, shell=True)
    podman_info = temp.decode ('utf-8')
    podman_list = podman_info.splitlines()
    podman_list.pop (0)
    container_names = [line.split()[-1] for line in podman_list if 'Up' not in line]
    container_names = ", ".join(container_names) 

    if memory_ratio > MEMORY_THRESHOLD:
        ram = ["WARNING", "RAM usage is above threshold: {:.2f}".format(memory_ratio) + ' %']
    else:
        ram = ["OK", "RAM usage: {:.2f}".format(memory_ratio) + ' %']
    if hypervisor_status != "up":
        hypervisor = ["CRITICAL", "Hypervisor is down. Check if server is up."]
    else:
        hypervisor = ["OK", "Hypervisor is up."]
    if load_avg[2] > LOAD_AVG_THRESHOLD_CRITICAL or iowait > IOWAIT_THRESHOLD_CRITICAL or idle < IDLE_THRESHOLD_CRITICAL:
        loadavg = ["CRITICAL", "Load Average is above critical threshold: " + "{:.2f}".format(load_avg[0]) + " {:.2f}".format(load_avg[1]) + " {:.2f}".format(load_avg[2]) + '\n' + 'IOWAIT: ' + "{:.2f}".format(iowait) + '\n' + 'IDLE: ' + "{:.2f}".format(idle)]
    elif load_avg[2] > LOAD_AVG_THRESHOLD_WARNING or iowait > IOWAIT_THRESHOLD_WARNING or idle < IDLE_THRESHOLD_WARNING:
        loadavg = ["WARNING", "Load Average is above threshold: " + "{:.2f}".format(load_avg[0]) + " {:.2f}".format(load_avg[1]) + " {:.2f}".format(load_avg[2]) + '\n' + 'IOWAIT: ' + "{:.2f}".format(iowait) + '\n' + 'IDLE: ' + "{:.2f}".format(idle)]
    else:
        loadavg = ["OK", "Load average: " + "{:.2f}".format(load_avg[0]) + " {:.2f}".format(load_avg[1]) + " {:.2f}".format(load_avg[2]) + '\n' + 'IOWAIT: ' + "{:.2f}".format(iowait) + '\n' + 'IDLE: ' + "{:.2f}".format(idle)]
    if container_names:
        podman = ["WARNING", "The next podman containers are down: " + container_names]
    else:
        podman = ["OK", "All podman containers are up"]

    return ram, hypervisor, loadavg, podman

def monitor_controllerX (controllerX_data):
    command = 'ssh heat-admin@' + controllerX_data[0]  + ' "free -m"'
    temp = subprocess.check_output (command, shell=True)
    temp = temp.decode ('utf-8')
    temp = temp.splitlines ()[1]
    temp = temp.split()
    memory_mb_total = float(temp [1])
    memory_mb_used = float(temp [2])

    command = 'ssh heat-admin@' + controllerX_data[0]  + ' "uptime"'
    temp = subprocess.check_output (command, shell=True)
    temp = temp.decode ('utf-8')
    temp = temp.split()
    load_avg = temp[-3:]
    load_avg[0] = float (load_avg[-3][:-1])  #para sacar la coma del final
    load_avg[1] = float (load_avg[-2][:-1])  #para sacar la coma del final
    load_avg[2] = float (load_avg[-1])       #este no tiene coma al final

    command = 'ssh heat-admin@' + controllerX_data[0]  + ' "cat data.csv"'
    temp = subprocess.check_output (command, shell=True)
    temp = temp.decode ('utf-8')
    temp = temp.splitlines ()[-1]
    temp = temp.split(',')
    iowait = float(temp [0])
    idle = float(temp [1])

    command = 'ssh heat-admin@' + controllerX_data[0]  + ' "sudo podman ps"'
    temp = subprocess.check_output (command, shell=True)
    podman_info = temp.decode ('utf-8')
    podman_list = podman_info.splitlines()
    podman_list.pop (0)
    container_names = [line.split()[-1] for line in podman_list if 'Up' not in line]
    container_names = ", ".join(container_names)

    memory_ratio = memory_mb_used/memory_mb_total * 100

    if memory_ratio > MEMORY_THRESHOLD:
        ram = ["WARNING", "RAM usage is above threshold: {:.2f}".format(memory_ratio) + ' %']
    else:
        ram = ["OK", "RAM usage: {:.2f}".format(memory_ratio) + ' %']
    if load_avg[2] > LOAD_AVG_THRESHOLD_CRITICAL or iowait > IOWAIT_THRESHOLD_CRITICAL or idle < IDLE_THRESHOLD_CRITICAL:
        loadavg = ["CRITICAL", "Load Average is above critical threshold: " + "{:.2f}".format(load_avg[0]) + " {:.2f}".format(load_avg[1]) + " {:.2f}".format(load_avg[2]) + '\n' + 'IOWAIT: ' + "{:.2f}".format(iowait) + '\n' + 'IDLE: ' + "{:.2f}".format(idle)]
    elif load_avg[2] > LOAD_AVG_THRESHOLD_WARNING or iowait > IOWAIT_THRESHOLD_WARNING or idle < IDLE_THRESHOLD_WARNING:
        loadavg = ["WARNING", "Load Average is above threshold: " + "{:.2f}".format(load_avg[0]) + " {:.2f}".format(load_avg[1]) + " {:.2f}".format(load_avg[2]) + '\n' + 'IOWAIT: ' + "{:.2f}".format(iowait) + '\n' + 'IDLE: ' + "{:.2f}".format(idle)]
    else:
        loadavg = ["OK", "Load average: " + "{:.2f}".format(load_avg[0]) + " {:.2f}".format(load_avg[1]) + " {:.2f}".format(load_avg[2]) + '\n' + 'IOWAIT: ' + "{:.2f}".format(iowait) + '\n' + 'IDLE: ' + "{:.2f}".format(idle)]
    if container_names:
        podman = ["WARNING", "The next podman containers are down: " + container_names]
    else:
        podman = ["OK", "All podman containers are up"]

    return ram, loadavg, podman

def monitor_ceph (IP_controller_list):
    x = None
    for i in range (3):
        command = 'ssh heat-admin@' + IP_controller_list[i] + ' "sudo podman ps | grep ceph-mon-overcloud-controller"'
        temp = subprocess.check_output (command, shell=True)
        temp = temp.decode ('utf-8')
        if 'Up' in temp:
            x = i
            break
    
    if x == None:
        ceph = ["CRITICAL", "Ceph is down on every controller."]
    else:
        command = 'ssh heat-admin@' + IP_controller_list[x]  + ' "sudo podman exec -ti ceph-mon-overcloud-controller-' + str(x) + ' ceph osd tree"'
        temp = subprocess.check_output (command, shell=True)
        temp = temp.decode ('utf-8')
        temp = temp.splitlines()
        down_osds = [line.split()[3] for line in temp if 'down' in line]
        
        if len(down_osds) != 0:
            st = "The next OSDs are down: "
            for osd in down_osds:
                temp = osd.split('.')
                st = st + osd + " in overcloud-compute-0" + str(OSD_HOSTS[int(temp[1])]) + ". " 
            ceph = ["WARNING", st]
        else:
            ceph = ["OK", "All OSDs up on every controller."]
    return ceph

def monitor_horizon (IP_controller_list):
    x = None
    for i in range (3):
        command = 'ssh heat-admin@' + IP_controller_list[i] + ' "sudo podman ps | grep horizon"'
        temp = subprocess.check_output (command, shell=True)
        temp = temp.decode ('utf-8')
        if 'Up' in temp:
            x = i
            break
    if x == None:
        horizon = ['CRITICAL', 'Horizon is down on every controller.']
    else:
        horizon = ['OK', 'Horizon is up.']
    return horizon

def monitor_galera (IP_controller_list):
    x = None
    for i in range (3):
        command = 'ssh heat-admin@' + IP_controller_list[i] + ' "sudo podman ps | grep galera"'
        temp = subprocess.check_output (command, shell=True)
        temp = temp.decode ('utf-8')
        if 'Up' in temp:
            x = i
            break

    if x == None:
        galera = ["CRITICAL", "Galera is down on every controller."]
    else:
        command = 'ssh heat-admin@' + IP_controller_list[x]  + ' "sudo podman exec -ti clustercheck clustercheck | grep Galera"'
        temp = subprocess.check_output (command, shell=True)
        temp = temp.decode ('utf-8')
        temp = temp[:-1]
        if 'is synced' in temp:
            galera = ['OK', 'Galera cluster node is synced.']
        else:
            galera = ['WARNING', 'Galera cluster node is not synced.']
    return galera

#PENDIENTE DE DEFINICION DE ESTRATEGIA DE MONITOREO
#def monitor_disk ()

#MAIN
parser = argparse.ArgumentParser()
parser.add_argument("--full_report", help="para ejecutar un reporte completo", type=int)  #0 si no, 1 si si
args = parser.parse_args()

if args.full_report is None or args.full_report != 0 and args.full_report != 1:
    print ('Error en la entrada')
    sys.exit(1)    

load_dotenv('overcloudrc')

#subprocess.call ('openstack image list --fit', shell = True)

ram, hypervisor, loadavg, podman = monitor_computeX (compute0_data)
current_status[0][1:3] = ram
current_status[1][1:3] = hypervisor
current_status[2][1:3] = loadavg
current_status[3][1:3] = podman

ram, hypervisor, loadavg, podman = monitor_computeX (compute1_data)
current_status[4][1:3] = ram
current_status[5][1:3] = hypervisor
current_status[6][1:3] = loadavg
current_status[7][1:3] = podman

ram, hypervisor, loadavg, podman = monitor_computeX (compute2_data)
current_status[8][1:3] = ram
current_status[9][1:3] = hypervisor
current_status[10][1:3] = loadavg
current_status[11][1:3] = podman

ram, loadavg, podman = monitor_controllerX (controller0_data)
current_status[12][1:3] = ram
current_status[13][1:3] = loadavg
current_status[14][1:3] = podman

ram, loadavg, podman = monitor_controllerX (controller1_data)
current_status[15][1:3] = ram
current_status[16][1:3] = loadavg
current_status[17][1:3] = podman

ram, loadavg, podman = monitor_controllerX (controller2_data)
current_status[18][1:3] = ram
current_status[19][1:3] = loadavg
current_status[20][1:3] = podman

ceph = monitor_ceph (IP_controller_list)
current_status[21][1:3] = ceph

horizon = monitor_horizon (IP_controller_list)
current_status[22][1:3] = horizon

galera = monitor_galera (IP_controller_list)
current_status[23][1:3] = galera


#logica de comparacion y generacion de correos
#=============================================
mail_body = ""
asunto = ""

if args.full_report == 0:
    for i in range(len(current_status)):
        if current_status[i][1] != previous_status[i][1] or current_status[i][1] == 'CRITICAL':
            mail_body = mail_body + current_status[i][0] + ': ' + current_status[i][2] + ' (' + current_status[i][1] + ')' + '\n'
            asunto = "ALERTA DE MONITOREO OPENSTACK"


elif args.full_report == 1:
    for i in range(len(current_status)):
        if current_status[i][1] == 'WARNING' or current_status[i][1] == 'CRITICAL':
            mail_body = mail_body + current_status[i][0] + ': ' + current_status[i][2] + ' (' + current_status[i][1] + ')' + '\n'
            asunto = "REPORTE DIARIO DE MONITOREO OPENSTACK"

if mail_body:
    smtp_server = "192.168.10.139"
    smtp_port = 25

    # Configurar los detalles del mensaje
    sender = "support@condortech-services.com.ar"
    #recipient = "infraestructura@condortech.com.ar"
    recipient = "lucas.aveni@condortech.com.ar"
    subject = asunto
    body = mail_body

    # Crear el mensaje
#    message = f"""From: {sender}
#    To: {recipient}
#    Subject: {subject}

#    {body}
# """

    message = MIMEText(body)
    message['From'] = sender
    message['To'] = recipient
    message['Subject'] = subject

    # Enviar el mensaje
    try:
        smtp = smtplib.SMTP(smtp_server, smtp_port)
        smtp.sendmail(sender, recipient, message.as_string())
       # print(message.as_string())
        print("El correo electrónico se envió correctamente")
    except Exception as e:
        print("Error al enviar el correo electrónico:", e)

#=============================================

with open('current.csv', 'w', newline='') as archivo:
    escritor = csv.writer(archivo)
    for sublista in current_status:
        escritor.writerow(sublista)
