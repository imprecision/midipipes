#!/bin/bash
# Title: fs.sh
# Description: MIDI Pipes - Filesystem read / write switch
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

if [ -e /boot/firmware/config.txt ] ; then
  FIRMWARE=/firmware
else
  FIRMWARE=
fi

is_pi () {
  ARCH=$(dpkg --print-architecture)
  if [ "$ARCH" = "armhf" ] || [ "$ARCH" = "arm64" ] ; then
    return 0
  else
    return 1
  fi
}

if is_pi ; then
  if [ -e /proc/device-tree/chosen/os_prefix ]; then
    PREFIX="$(cat /proc/device-tree/chosen/os_prefix | tr -d '\0')"
  fi
  CMDLINE="/boot${FIRMWARE}/${PREFIX}cmdline.txt"
else
  CMDLINE=/proc/cmdline
fi

check_overlayroot() {
  if grep -q overlayroot= $CMDLINE ; then
    return 0
  else
    return 1
  fi
}

rw() {
  if check_overlayroot ; then
    mount -o remount,rw /boot${FIRMWARE} 2>/dev/null
    sed -i $CMDLINE -e "s/\(.*\)overlayroot=tmpfs \(.*\)/\1\2/"
    echo 1
  else
    echo 0
  fi
}

ro() {
  if ! check_overlayroot ; then
    mount -o remount,rw /boot${FIRMWARE} 2>/dev/null
    sed -i $CMDLINE -e "s/^/overlayroot=tmpfs /"
    echo 1
  else
    echo 0
  fi
}

ARG_VALUE=""

while [[ $# -gt 0 ]]
do
    case $1 in
        -fs|--filesystem)
            ARG_VALUE="$2"
            shift
            shift
            ;;
        *)
            shift
            ;;
    esac
done

if [ "$ARG_VALUE" == "ro" ]; then
  ro
elif [ "$ARG_VALUE" == "rw" ]; then
  rw
else
  clear

  echo
  echo " 🎹 MIDI Pipes: Filesystem read / write switch"
  echo
  echo " 🔺 Switch to read-only or read-write?"
  echo "    Proceeding will reboot your system!"
  echo
  read -p "    Options: 'ro' read-only, 'rw' read-write or 'c' cancel (ro/rw/c): " USER_CONFIRMATION
  echo

  if [[ $USER_CONFIRMATION = "rw" ]]
  then
    RES=$(rw)
    if [ "$RES" == "0" ]; then
      echo " 👍 Filesystem already read-write, no changes made."
      echo
    else
      echo " 👌 Done, time to reboot!"
      echo
      reboot
    fi
  else
    if [[ $USER_CONFIRMATION = "ro" ]]
    then
      RES=$(ro)
      if [ "$RES" == "0" ]; then
        echo " 👍 Filesystem already read-only, no changes made."
        echo
      else
        echo " 👌 Done, time to reboot!"
        echo
        reboot
      fi
    else
      echo " 👍 Filesystem changes cancelled, no changes made."
      echo
    fi
  fi
fi
