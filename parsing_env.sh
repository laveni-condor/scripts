#!/bin/bash

#project_id="$OS_PROJECT_ID"
#project_info=$(openstack project show $project_id)
#project_name=$(echo "$project_info" | awk -F'|' '/name/ {gsub(/^[ \t]+|[ \t]+$/, "", $3); print $3}')
#echo "$project_name"

# Ejecutar el comando openstack y almacenar la salida en la variable 'output'
output=$(openstack server list -f value -c "Name" -c "ID")

# Crear un archivo 'HEAT-environment.project-Volume_v0.yaml' y escribir el encabezado
echo "parameters:" > HEAT-environment.project-Volume_v0.yaml

echo "heat_template_version: 2018-08-31

description: create volumes

parameters:
" > HEAT-template.project-Volume_v0.yaml

# Leer cada línea de la salida y generar las líneas correspondientes en el archivo
while IFS= read -r line; do
  name=$(echo "$line" | awk '{print $2}')  # Obtener el nombre de la instancia
  id=$(echo "$line" | awk '{print $1}')    # Obtener el ID de la instancia
  echo "  ${name}_id: \"$id\"" >> HEAT-environment.project-Volume_v0.yaml
  echo "  ${name}_id:" >> HEAT-template.project-Volume_v0.yaml
  echo "    type: string" >> HEAT-template.project-Volume_v0.yaml
done <<< "$output"

echo "
resources:

  instance_volume:
    type: OS::Cinder::Volume
    properties:
      size: 20

  instance_attachment:
    type: OS::Cinder::VolumeAttachment
    properties:
      volume_id: { get_resource: instance_volume }
      instance_uuid: { get_param: instance_id }
      mountpoint: /dev/vdb" >> HEAT-template.project-Volume_v0.yaml
