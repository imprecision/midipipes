# MIDI Pipes

### Development

#### Debug

Check MIDI Pipes logs:

    watch cat /tmp/midi-log.txt

Check status of MIDI Pipes web service:

    journalctl -u web.service

    systemctl status MIDI Pipes-web

    ps aux | grep "web.py"

etc.

Tail recent everything:

    journalctl -f

Check read/write status of filesystem:

    cat /boot/firmware/cmdline.txt

And look for `overlayroot=tmpfs`
