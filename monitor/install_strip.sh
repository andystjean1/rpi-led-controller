#!/bin/sh
# One-time setup of the LED strip daemon on the Pi. Run with sudo:
#   ssh -t pi 'sudo sh ~/hp-monitor/install_strip.sh'
# Frees GPIO 18's PWM from the analog audio driver (needs a reboot to take effect), then installs
# and starts the root `strip-daemon` systemd service.
set -e
echo "blacklist snd_bcm2835" > /etc/modprobe.d/blacklist-snd-bcm2835.conf
sed -i 's/^dtparam=audio=on/dtparam=audio=off/' /boot/firmware/config.txt
cat > /etc/systemd/system/strip-daemon.service <<'EOF'
[Unit]
Description=LED strip for the laptop status monitor
After=multi-user.target

[Service]
ExecStart=/home/bananaman/led-test/env/bin/python /home/bananaman/hp-monitor/strip_daemon.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable strip-daemon
echo "Installed. Reboot now (sudo reboot) so the audio driver is gone, then the strip starts itself."
