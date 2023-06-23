#!/bin/bash

# Definition of IP addresses
CONTROLLERS=(192.168.100.11 192.168.100.12 192.168.100.13)
COMPUTES=(192.168.100.14 192.168.100.15 192.168.100.16)
if_file=/dev/zero
of_file=/tmp/test.img

# Source the overcloudrc file to access the overcloud
source ~/overcloudrc

#============================COMPUTE NODES=====================================

echo "=======================================COMPUTE NODES==========================================="
echo ""

# Get the hypervisor list
HYPERVISORS=$(openstack hypervisor list -f value -c "Hypervisor Hostname")
i=0
# Print the status for each hypervisor
for HYPERVISOR in $HYPERVISORS
do
    echo "==========================$HYPERVISOR============================"
    echo ""

    # Get the hypervisor information
    HYPERVISOR_INFO=$(openstack hypervisor show $HYPERVISOR -f value \
        -c "memory_mb_used" \
        -c "memory_mb" \
        -c "hypervisor_hostname" \
        -c "load_average" \
        -c "running_vms" \
        -c "state" \
        -c "vcpus" \
        -c "vcpus_used")

    # Parse the hypervisor information
    HYPERVISOR_HOSTNAME=$(echo $HYPERVISOR_INFO | awk -F ' ' '{print $1}')
    LOAD_AVG1=$(echo $HYPERVISOR_INFO | awk -F ' ' '{print $2}')
    LOAD_AVG2=$(echo $HYPERVISOR_INFO | awk -F ' ' '{print $3}')
    LOAD_AVG3=$(echo $HYPERVISOR_INFO | awk -F ' ' '{print $4}')
    MEMORY_MB=$(echo $HYPERVISOR_INFO | awk -F ' ' '{print $5}')
    MEMORY_MB_USED=$(echo $HYPERVISOR_INFO | awk -F ' ' '{print $6}')
    RUNNING_VMS=$(echo $HYPERVISOR_INFO | awk -F ' ' '{print $7}')
    STATE=$(echo $HYPERVISOR_INFO | awk -F ' ' '{print $8}')
    VCPUS=$(echo $HYPERVISOR_INFO | awk -F ' ' '{print $9}')
    VCPUS_USED=$(echo $HYPERVISOR_INFO | awk -F ' ' '{print $10}')

    # Print the information for the hypervisor
    echo "Memory used: $MEMORY_MB_USED MB / $MEMORY_MB MB"
    echo "Virtual CPUs used: $VCPUS_USED / $VCPUS"
    echo "Running VMs: $RUNNING_VMS"
    echo "Load average: $LOAD_AVG1 $LOAD_AVG2 $LOAD_AVG3"
    echo "State: $STATE"
    echo ""
    
    COMPUTE=${COMPUTES[$i]}

    # Check for podman containers that are not UP in compute nodes
    down_containers=$(ssh heat-admin@"$COMPUTE" "sudo podman ps --format '{{.Names}} {{.Status}}' | grep -v -E '(CONTAINER|Up)' | awk '{print \$1}'")
    if [ -z "$down_containers" ]
    then
        echo "All containers are up"
	echo ""
    else
        echo "The following containers are down:"
        echo "$down_containers"
	echo ""
    fi

    ((++i))

done

#========================================CONTROLLER NODES==========================================

echo "====================================CONTROLLER NODES==========================================="
echo ""

# Loop through each controller and display the daemons status and check containers that are not UP
for CONTROLLER in "${CONTROLLERS[@]}"
do
    controller_name=$(ssh heat-admin@"$CONTROLLER" "sudo hostname")
    
    echo "==================================$controller_name======================================="
    echo ""

    # Obtain the status for daemons running in the controller
    ssh heat-admin@$CONTROLLER "sudo pcs status" | sed -n '/Daemon Status:/,$p'
    echo ""

    # Check for podman containers that are not UP
    down_containers=$(ssh heat-admin@"$CONTROLLER" "sudo podman ps --format '{{.Names}} {{.Status}}' | grep -v -E '(CONTAINER|Up)' | awk '{print \$1}'")
    if [ -z "$down_containers" ]
    then
        echo "All containers are up"
	echo ""
    else
        echo "The following containers are down:"
        echo "$down_containers"
	echo ""
    fi
done

#===========================================CLUSTERCHECK============================================
#====================================HORIZON - GALERA - CEPH========================================

echo "==============================================================================================="
echo ""

echo "========================================CEPH STATUS============================================"
echo ""

# Loop through the controllers and execute the ceph -s command
for CONTROLLER in "${CONTROLLERS[@]}"
do
    # Get the podman container name for this controller
    container_name=$(ssh heat-admin@"$CONTROLLER" "sudo podman ps --format '{{.Names}}' | grep ceph-mon-overcloud-controller | awk '{print \$1}'")

    # Execute ceph -s and extract the relevant sections
    output=$(ssh heat-admin@"$CONTROLLER" "sudo podman exec -ti $container_name ceph -s")
    osd=$(echo "$output" | awk '/osd:/ {print $2}')
    if [[ $osd != "18"  ]]; then
            echo "ERROR in the OSD module"
	    echo ""
            ssh heat-admin@"$CONTROLLER" "sudo podman exec -i $container_name ceph osd tree"
	    echo ""
            break
    fi

    show=$(echo "$output" | grep -E "mon:|mgr:|osd:")
    if [[ $show != "" ]]; then
            show=$(echo "$show" | sed 's/^[[:space:]]*//')
	    echo "$show"
	    echo ""
            break
    else
            echo "ERROR: Controller "$CONTROLLER" is DOWN"
	    echo ""
    fi
done

echo "========================================HORIZON STATUS========================================="
echo ""

for CONTROLLER in "${CONTROLLERS[@]}"
do
    horizon_status=$(ssh heat-admin@"$CONTROLLER" "sudo podman ps -f name=horizon --format '{{.Status}}'")

    if [[ "$horizon_status" == "Up"* ]]
    then
        echo "Horizon is UP"
	echo ""
        break
    fi
done

echo "====================================GALERA SYNC STATUS========================================="
echo ""

for CONTROLLER in "${CONTROLLERS[@]}"
do
    galera_status=$(ssh heat-admin@"$CONTROLLER" "sudo podman exec -ti clustercheck clustercheck | grep Galera")

    if [[ "$galera_status" == "Galera cluster node is synced."* ]]
    then
        echo "Galera cluster node is synced."
	echo ""
        break
    fi
done



echo "=====================================DISK SPEED TEST=========================================="
echo ""

output=$(sudo dd if=$if_file of=$of_file bs=64M count=1 oflag=dsync 2>&1)

# Extract the disk speed from the output using grep and awk
disk_speed=$(echo "$output" | grep -o "[0-9.]* MB/s" | awk '{print $1}')
echo "Disk speed: $disk_speed MB/s" 

echo ""
echo "==============================================================================================="
echo ""

