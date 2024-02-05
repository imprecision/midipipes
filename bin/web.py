#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
web.py: MIDI Pipes - A standalone MIDI processing and routing system

Provides a web interface for MIDI Pipes

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

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from lib import *

class SimpleWebServer(BaseHTTPRequestHandler):
    def do_GET(self):

        uriPath = urlparse(self.path).path
        uriQuery = parse_qs(urlparse(self.path).query)

        if uriPath == '/midi-update':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write("true".encode('utf-8'))
            midi()

        elif uriPath == '/midi-view':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write(json.dumps(midi_devices()).encode('utf-8'))

        elif uriPath == '/audio-update':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write("true".encode('utf-8'))
            audio()

        elif uriPath == '/audio-vol':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            vol = -1
            dev = None
            typ = None

            if uriQuery:
                if 'vol' in uriQuery:
                    vol = int(uriQuery['vol'][0])
                if 'dev' in uriQuery:
                    dev = str(uriQuery['dev'][0])
                if 'typ' in uriQuery:
                    typ = str(uriQuery['typ'][0])

            self.wfile.write(json.dumps(audio_volume(vol, dev, typ)).encode('utf-8'))

        elif uriPath == '/audio-out':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if uriQuery:
                if 'out' in uriQuery:
                    out = str(uriQuery['out'][0])
                    current = audio_devices()
                    for device in current["detail"]:
                        if device["type"] == "sink" and device['name'] == out:
                            settings["sink_preference"] = device['name']
                            settings_set(settings)
                            break

            self.wfile.write(json.dumps(audio_devices(), indent=4).encode('utf-8'))

        elif uriPath == '/display':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write("true".encode('utf-8'))
            display()

        elif uriPath == '/shutdown':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write("true".encode('utf-8'))
            bye()
            subprocess.run(["/usr/bin/sudo", "/usr/sbin/halt", "-p", "-f"])

        elif uriPath == '/restart':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write("true".encode('utf-8'))
            bye()
            subprocess.run(["/usr/bin/sudo", "/usr/sbin/halt", "--reboot", "-f"])

        elif uriPath == '/logs':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()

            logs = ""
            with open(file_log, "r") as file:
                logs = file.read()
            self.wfile.write(logs.encode('utf-8'))
        
        elif uriPath == '/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            self.wfile.write(json.dumps(audio_devices(), indent=4).encode('utf-8'))
        
        elif uriPath == '/img-logo':
            self.send_response(200)
            self.send_header('Content-type', 'image/png')
            self.end_headers()

            cur_dir = os.path.dirname(os.path.abspath(__file__))
            with open(cur_dir + "/../lib/logo-web.png", "rb") as file:
                self.wfile.write(file.read())

        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            cur_dir = os.path.dirname(os.path.abspath(__file__))
            html = ""
            with open(cur_dir + "/../lib/web.html", "r") as file:
                html = file.read()
            self.wfile.write(html.encode('utf-8'))

server_address = ('', 80)
httpd = HTTPServer(server_address, SimpleWebServer)
httpd.serve_forever()
