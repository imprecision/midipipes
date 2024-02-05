#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lib.py: MIDI Pipes - A standalone MIDI processing and routing system

Shared library for MIDI Pipes

Copyright (C) 2024 imprecision

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation; either version 3 of the License,
or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

For more details, see the LICENSE file.
"""

import sys
import subprocess
import re
import os
from inky import InkyWHAT
from PIL import Image, ImageFont, ImageDraw
from font_source_sans_pro import SourceSansProSemibold, SourceSansProLight, SourceSansPro, SourceSansProBold
from datetime import datetime, timezone

import qrcode

import socket
import psutil

import json

display_mode = "colourful" # "fast" or "colourful" (slower)
display_title = "MIDI Pipes"
file_log = "/tmp/midi-log.txt"
file_last = "/tmp/midi-last.txt"
file_settings = "/tmp/midi-settings.json"
current_datetime = datetime.now(timezone.utc)
names = [] # Contains the list of MIDI devices found

def getsize(font, text):
    _, _, right, bottom = font.getbbox(text)
    return (right, bottom)

def log(msg):
    """
    Logs a message to the log file.

    Args:
        msg (str): The message to be logged.
    """
    if os.path.exists(file_log):
        set_perms = False
    else:
        set_perms = True

    with open(file_log, "a") as file:
        file.write(current_datetime.strftime("%Y-%m-%d %H:%M:%S") + "\t" + msg + "\n")

    if set_perms:
        os.chmod(file_log, 0o777)

def midi_devices():
    output = subprocess.check_output("/usr/bin/aconnect -i -l", shell=True).decode()
    names = []

    for line in output.splitlines():
        match = re.search(r'client (\d*): \'(.*)\'', line)
        if match and match.group(1) != '0' and 'Through' not in line:
            names.append(match.group(2))

    return sorted(list(set(names)))

def midi():
    """
    Connects MIDI devices using the aconnect command.
    """

    # unconnect everything
    subprocess.run("/usr/bin/aconnect -x", shell=True)

    # get the list of available ports
    output = subprocess.check_output("/usr/bin/aconnect -i -l", shell=True).decode()
    ports = []

    for line in output.splitlines():
        match = re.search(r'client (\d*): \'(.*)\'', line)
        if match and match.group(1) != '0' and 'Through' not in line:
            ports.append(match.group(1))
            names.append(match.group(2))

    # connect ports
    for p1 in ports:
        for p2 in ports:
            if p1 != p2:
                subprocess.run(f"/usr/bin/aconnect {p1}:0 {p2}:0", shell=True)

    if len(names) < 1:
        log("Devices: None found")
    else:
        log("Devices: " + ", ".join(str(name) for name in names))

def display():
    """
    Displays MIDI device information on an InkyWHAT display.
    """

    names_mid = midi_devices()
    names_aud = audio_devices()

    # Check if the last display update was the same, if so exit
    names_combined = json.dumps(names_mid) + "|" + json.dumps(names_aud)

    if os.path.exists(file_last):
        with open(file_last, "r") as file:
            last = file.read()
        if last == names_combined:
            return

    with open(file_last, "w") as file:
        file.write(names_combined)

    if display_mode == "colourful": 
        inky_display = InkyWHAT("yellow") # Colourful but slow (OK for production)
    else:
        inky_display = InkyWHAT("black") # Dull but fast (maintain sanity during development!)

    inky_display.set_border(inky_display.WHITE)

    WIDTH = inky_display.width
    HEIGHT = inky_display.height

    img = Image.new("P", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # Draw the logo
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    img_logo = Image.open(cur_dir + "/../lib/logo-bg.png")
    img.paste(img_logo, (0, 0))

    # Load the fonts
    ts_font = ImageFont.truetype(SourceSansPro, 11)
    info_font_size = 26
    info_font = ImageFont.truetype(SourceSansProSemibold, info_font_size)
    info2_font_size = 16
    info2_font = ImageFont.truetype(SourceSansProLight, info2_font_size)
    info2_font_b = ImageFont.truetype(SourceSansProBold, info2_font_size)

    font_prehdr = ImageFont.truetype(SourceSansProBold, info_font_size)

    y_running = 0
    y_pad = 2
    x_pad = 10

    draw.text((x_pad, y_running), "MIDI", fill=inky_display.BLACK, font=font_prehdr, align="left")
    y_running += info_font_size + y_pad

    for name1 in names_mid:
        text = "• " + name1
        draw.text((x_pad, y_running), text, fill=inky_display.RED, font=info_font, align="left")
        # y_running += info_font_size + y_pad
        y_running += info_font_size

    y_running += 10

    draw.text((x_pad, y_running), "Audio", fill=inky_display.BLACK, font=font_prehdr, align="left")
    y_running += info_font_size + y_pad

    for name2 in names_aud["detail"]:
        if name2["type"] == "sink":
            text = "• " + name2["desc"] + " (" + str(name2["vol"]) + "%)"
            f = info2_font
            if name2["id"] == names_aud["output"]:
                f = info2_font_b
            draw.text((x_pad, y_running), text, fill=inky_display.BLACK, font=f, align="left")
            y_running += info2_font_size + y_pad

    # Network
    ip_address = ""
    ip_interface = ""
    net_interfaces = psutil.net_if_addrs()
    for interface, addrs in net_interfaces.items():
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address != "127.0.0.1":
                ip_address = addr.address
                ip_interface = interface
                break

    # Draw the timestamp, IP address
    msg_mini_bits = []
    msg_mini_bits.append(current_datetime.strftime("%Y-%m-%d"))
    msg_mini_bits.append(current_datetime.strftime("%H:%M:%S"))
    if len(ip_address):
        hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(ip_address)
        msg_mini_bits.append(ip_interface)
        msg_mini_bits.append(ip_address)
        msg_mini_bits.append(hostname)
    draw.multiline_text((0, HEIGHT - 13), "  •  ".join(str(m) for m in msg_mini_bits), fill=inky_display.BLACK, font=ts_font, align="left")

    if len(ip_address):
        # Generate barcode
        url = "http://" + ip_address
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=2,
            border=0,
        )
        qr.add_data(url)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        # Create display-compatible palette
        qr_w, qr_h = qr_image.size
        pal_img = Image.new("P", (1, 1))
        pal_img.putpalette((255, 255, 255, 0, 0, 0, 255, 0, 0) + (0, 0, 0) * 252)
        # Quantize the barcode image to the palette and add it to the canvas
        qr_image = qr_image.convert("RGB").quantize(palette=pal_img)
        img.paste(qr_image, (WIDTH - qr_w - 5, HEIGHT - qr_h - 58))

    flipped = img.rotate(180)
    inky_display.set_image(flipped)
    inky_display.show()

def bye(msg = "", msg_smol = ""):
    inky_display = InkyWHAT("yellow") # Colourful but slow (OK for production)
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    img_logo = Image.open(cur_dir + "/../lib/logo-boot.png")

    if len(msg) or len(msg_smol):
        draw = ImageDraw.Draw(img_logo)
        if len(msg):
            msg_font = ImageFont.truetype(SourceSansProSemibold, 30)
            draw.multiline_text(((inky_display.width / 2) + 6, inky_display.height - 96), msg, fill=inky_display.BLACK, font=msg_font, align="left")
        if len(msg_smol):
            msg_font_smol = ImageFont.truetype(SourceSansProSemibold, 14)
            w, h = getsize(msg_font_smol, msg_smol)
            draw.multiline_text(((inky_display.width / 2) - (w / 2), inky_display.height - 30), msg_smol, fill=inky_display.BLACK, font=msg_font_smol, align="left")
    
    img_logo = img_logo.rotate(180)
    inky_display.set_image(img_logo)
    inky_display.show()

def settings_get():
    settings = {}

    if os.path.exists(file_settings):
        with open(file_settings, "r") as file:
            settings = json.load(file)

    return settings

def settings_set(settings):
    with open(file_settings, "w") as file:
        file.write(json.dumps(settings, indent=4))

def audio_volume(vol = -1, dev = None, type = None):

    vol = int(vol)

    if dev is None:
        aud = audio_devices()
        device = aud["output"]
        type = "sink"
    else:
        device = dev
        if type is None:
            type = "source"

    if vol > -1:
        vol = 0 if vol < 0 else vol
        vol = 100 if vol > 100 else vol
        cmd = "/usr/bin/sudo -u pulse /usr/bin/pactl set-" + type + "-volume " + str(device) + " " + str(vol) + "%"
    else:
        cmd = "/usr/bin/sudo -u pulse /usr/bin/pactl get-" + type + "-volume " + str(device)

    output = subprocess.check_output(cmd, shell=True).decode()

    if vol > -1:
        return vol
    else:
        match = re.search(r' (\d+)% ', output)
        if match:
            return int(match.group(1))
        else:
            return 0

def audio():
    devices_config = audio_devices()
    sinkId = devices_config["output"]
    for sourceId, sourceName in devices_config["source"].items():
        piped = False
        for pipe in devices_config["pipe"]:
            if pipe["source"] == sourceId and pipe["sink"] == sinkId:
                piped = True
                break

        if piped:
            continue

        piped_audio = subprocess.check_output("/usr/bin/sudo -u pulse /usr/bin/pactl load-module module-loopback source=" + sourceId + " sink=" + sinkId, shell=True).decode()

def audio_devices():
    """
    Returns a list of audio devices.
    """

    data = {
        "source": {}, # Audio input devices
        "sink": {}, # Audio output devices
        "output": "", # Audio output device that is preferred
        "pipe": [], # Audio devices that are currently piped (source -> sink)
        "detail": [], # Audio device friendly names
    }

    output = subprocess.check_output("/usr/bin/sudo -u pulse /usr/bin/pactl list", shell=True).decode()

    patterns = {
        "module": re.compile(r'Module #(\d+)'),
        "source": re.compile(r'Source #(\d+)'),
        "sink": re.compile(r'Sink #(\d+)'),
        "argument": re.compile(r'Argument: source=(\d+) sink=(\d+)'),
        "name": re.compile(r'Name: (.+)'),
        "name_has_input": re.compile(r'Name: alsa_input\.usb-(.+)'),
        "desc": re.compile(r'Description: (.+)'),
    }

    if "sink_preference" in settings and settings["sink_preference"] is not None:
        sink_preference = settings["sink_preference"]
    else:
        settings["sink_preference"] = "alsa_output.platform-bcm2835_audio.analog-stereo"
        sink_preference = settings["sink_preference"]
        settings_set(settings)

    def clear_values():
        return {
            "type": "",
            "id": "",
            "name": "",
            "name_has_input": "",
            "desc": "",
            "pipe_source": "",
            "pipe_sink": "",
        }

    values = clear_values()

    for ptn in patterns:
        values[ptn] = ""

    for line in output.split('\n'):
        matches = {}

        for ptn in patterns:
            matches[ptn] = patterns[ptn].search(line)
        
        if matches["module"]:
            values = clear_values()
            values["type"] = "pipe"
            values["id"] = matches["module"].group(1)

        if matches["source"]:
            values = clear_values()
            values["type"] = "source"
            values["id"] = matches["source"].group(1)

        if matches["sink"]:
            values = clear_values()
            values["type"] = "sink"
            values["id"] = matches["sink"].group(1)

        if matches["argument"]:
            values["pipe_source"] = matches["argument"].group(1)
            values["pipe_sink"] = matches["argument"].group(2)

        if matches["name"]:
            values["name"] = matches["name"].group(1)

        if matches["name_has_input"]:
            values["name_has_input"] = matches["name_has_input"].group(1)

        if matches["desc"]:
            values["desc"] = matches["desc"].group(1)

        if len(values["pipe_source"]) and len(values["pipe_sink"]):
            data["pipe"].append({"source": values["pipe_source"], "sink": values["pipe_sink"]})
            values = clear_values()
            continue

        if len(values["name"]) and len(values["desc"]):
            if values["type"] == "sink" and values["name"] == sink_preference:
                data["output"] = values["id"]
            
            if values["type"] == "source" and len(values["name_has_input"]):
                vol = audio_volume(-1, values["id"], "source")
                data["detail"].append({"type": values["type"], "id": values["id"], "name": values["name"], "desc": values["desc"], "vol": vol})
                data[values["type"]][values["id"]] = values["name"]
            
            if values["type"] == "sink":
                vol = audio_volume(-1, values["id"], "sink")
                data["detail"].append({"type": values["type"], "id": values["id"], "name": values["name"], "desc": values["desc"], "vol": vol})
                data[values["type"]][values["id"]] = values["name"]

            values = clear_values()
            continue

    return data

settings = settings_get()
