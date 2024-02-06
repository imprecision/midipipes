#!/bin/bash
# Title: install.sh
# Description: MIDI Pipes - Install script
#
# Copyright (C) 2024 imprecision
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation; either version 3 of the License,
# or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# For more details, see the LICENSE file.

clear

current_user=$(whoami)
current_dir=$(pwd)

echo
echo " 🎹 MIDI Pipes: Install Script"
echo
echo "MIDI Pipes is a set of scripts and configuration files to enable USB and Bluetooth MIDI support on a Raspberry Pi."
echo
echo " 🎉 Features:"
echo
echo "  ♪ Automatically connect to a USB or Bluetooth MIDI device."
echo "  ♪ Display status information on a Pimoroni Inky wHAT display."
echo "  ♪ Provide a web interface for status and basic control."
echo
echo "It's been developed and tested on a Raspberry Pi 4 (4GB) running Raspberry OS Lite 64-bit (Debian Bookworm, 2023-12-11)."
echo
echo " 🚨 WARNINGS:"
echo
echo "  🔺 This is going to install packages and make changes to your system."
echo "  🔺 Only run this on a freshly installed copy of Raspberry OS."
echo
read -p " 🎹 Are you sure you want to continue? (y/n) " USER_CONFIRMATION
echo

if [[ $USER_CONFIRMATION =~ ^[Yy]$ ]]
then
    echo " 🎹 Installation starting..."
else
    echo " 👍 Installation cancelled."
    echo
    exit 1
fi

echo
echo " 🎹 Updating system packages..."
echo

apt update && apt upgrade -y && apt autoremove -y

echo
echo " 🎹 Installing git and pip for installation and runtime support..."
echo

apt install -y git pip

echo
echo " 🎹 Installing overlayroot for read-only filesystem support..."
echo

apt install -y overlayroot

echo
echo " 🎹 Installing build tools, etc., for Bluez..."
echo

apt install -y autotools-dev libtool autoconf libasound2-dev libusb-dev libdbus-1-dev libglib2.0-dev libudev-dev libical-dev libreadline-dev build-essential

echo
echo " 🎹 Installing alsa-utils and pulseaudio for USB audio routing..."
echo

apt install -y alsa-utils pulseaudio

echo
echo " 🎹 Cloning Bluez repository..."
echo

git clone https://github.com/oxesoft/bluez

cd "$current_dir/bluez"

echo
echo " 🎹 Patching Bluez for Raspberry Pi OS Lite 64-bit (Debian Bookworm, 2023-12-11) support..."
echo

git apply ../lib/midi-bluez-changes.patch

echo
echo " 🎹 Building Bluez for bluetooth MIDI support..."
echo

autoupdate
./bootstrap
./bootstrap # Twice because the 1st time doesn't put ltmain.sh in the right place???
./configure --enable-midi --prefix=/usr --mandir=/usr/share/man --sysconfdir=/etc --localstatedir=/var
make
make install
apt install -y --reinstall bluez

cd "$current_dir"

echo
echo " 🎹 Enable SPI for GPIO display support..."
echo

echo "dtparam=spi=on" | tee -a /boot/firmware/config.txt

echo
echo " 🎹 Installing pip packages for display support..."
echo

pip3 install --break-system-packages Pillow numpy font_source_sans_pro inky[rpi] qrcode psutil

echo
echo " 🎹 Applying new udev, systemd and pulseaudio configs..."
echo

sh -c "sed 's|{MIDIPI_USER}|$current_dir|g' './lib/33-midipipes-midiusb.rules' > '/etc/udev/rules.d/33-midipipes-midiusb.rules'"
sh -c "sed 's|{MIDIPI_USER}|$current_dir|g' './lib/44-midipipes-bt.rules' > '/etc/udev/rules.d/44-midipipes-bt.rules'"
sh -c "sed 's|{MIDIPI_USER}|$current_user|g' './lib/midipipes-btmidi.service' > '/lib/systemd/system/midipipes-btmidi.service'"
sh -c "sed 's|{MIDIPI_USER}|$current_dir|g' './lib/midipipes-midi.service' > '/lib/systemd/system/midipipes-midi.service'"
sh -c "sed 's|{MIDIPI_USER}|$current_dir|g' './lib/midipipes-pulseaudio.service' > '/lib/systemd/system/midipipes-pulseaudio.service'"
sh -c "sed 's|{MIDIPI_USER}|$current_dir|g' './lib/midipipes-web.service' > '/lib/systemd/system/midipipes-web.service'"

sh -c "echo 'system-instance = yes' >> /etc/pulse/daemon.conf"
sh -c "echo 'disallow-module-loading = no' >> /etc/pulse/daemon.conf"
sh -c "echo 'allow-module-loading = yes' >> /etc/pulse/daemon.conf"
sh -c "echo 'autospawn = no' >> /etc/pulse/client.conf"

echo
echo " 🎹 Restarting udev and systemd daemons..."
echo

udevadm control --reload
service udev restart

systemctl daemon-reload

systemctl enable midipipes-midi.service
systemctl start midipipes-midi.service

systemctl enable midipipes-btmidi.service
systemctl start midipipes-btmidi.service

systemctl enable midipipes-pulseaudio
systemctl start midipipes-pulseaudio

systemctl enable midipipes-web.service
systemctl start midipipes-web.service

echo
echo " 🎹 Ensuring all scripts are executable..."
echo

chmod +x ./bin/midi.py
chmod +x ./bin/audio.py
chmod +x ./bin/display.py
chmod +x ./bin/web.py

echo
echo " 🎹 Configuring display updater..."
echo

crontab -l | { echo "* * * * * /usr/bin/python $current_dir/bin/display.py"; } | crontab -

echo
echo " 🎹 Setting system to read-only..."
echo

bash ./fs.sh -fs ro

echo
echo " 🎹 👌 Done, time to reboot!"
echo

reboot
