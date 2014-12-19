#!/bin/sh

if [ -f /var/log/linstaller/linstaller_latest.log ]; then
	cp /var/log/linstaller/linstaller_latest.log /linstaller/target/var/log/installation.log
	else
	:
fi
exit
