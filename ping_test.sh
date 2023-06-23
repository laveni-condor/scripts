#!/bin/bash
while true; do
	ping_status=$(ping -c 1 -W 1 8.8.4.4 &> /dev/null && echo success || echo fail)
	now=$(date)
	if [ $ping_status = fail ]; then
		echo "${now}        NO" >> ping_test.log
        else
		echo "${now}        YES" >> ping_test.log
	fi
	sleep 10
done
