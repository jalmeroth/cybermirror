#!/bin/sh

# lässt den Mauszeiger verschwinden
unclutter &

# sorg für den Kiosk Modus
matchbox-window-manager & :

# deaktiviert den Bildschirmschoner
xset -dpms
xset s off
xset s noblank

#Die while Schleife sorgt dafür, das der Browser bei einem Absturz neu gestartet wird.
while true; do
	/usr/bin/midori -a $APP_URL -l /tmp/midori.log -e Fullscreen -c "/home/pi/.config/midori"
done
