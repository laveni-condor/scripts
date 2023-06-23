#!/bin/bash

#configurando repo
echo"[gondor] \
name = gondor \
baseurl = http://192.168.10.139/yum/rh8.7 \
enabled=1 \
gpgcheck=0 " > /etc/yum.repos.d/gondor.repo


# Creando user sipview
groupadd sipview
useradd -m -p saqv55abocvf. -g sipview -G wheel sipview

#Configurando public key.
mkdir /home/sipview/.ssh
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCxZR9B57DKPGY5T+GR9eUPOcpcqPGadMdLZqaJTZ4XQ1ZBJVkWgxfF1nyznuqkrt1yEcQE1yXpR35xhdRgSjblurCPDoW6LhxNr1/RIOYu+1Gs41XmOYfAzmSgn5vC/wK5CQmjT89g0H/L4KZbC0+SN+i3RzAmiCXZoczHUtKJFQdlNQpwNUJqKdOi4B18Opk49gRfFlgQ1PH6p4CBzC0bYrH4RLubJOHlKMXIh15qalCWxcFFrlTwN1bqG3UNd7dYymFNrXn7na1OPCDcT4KAtSyJtwgwkZcI4l8Qqoo4wHPstf/LRvLWgRt9m+qKMhrnT4pFGP/6gw55YbzGsjqJ Generated-by-Nova" > /home/sipview/.ssh/authorized_keys	
chmod 600 /home/sipview/.ssh/authorized_keys
chown -R sipview.sipview /home/sipview

#Configurando sshd
sed -i "s/GSSAPIAuthentication yes/GSSAPIAuthentication no/g" /etc/ssh/sshd_config
systemctl restart sshd

