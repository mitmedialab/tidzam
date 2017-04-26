#!/bin/bash
echo "TidZam Installer \n================"

echo "System dependencies packages"
apt-get install redis-server python3-tk jack-mixer qjackctl mpv icecast2 ices2 ecasound

echo "Python package installation"
pip3 install tflearn matplotlib scipy soundfile sounddevice python-socketio aiohttp chainclient aioredis JACK-Client sklearn

# dpkg -i mpv/mpv_0.14.0-1build1_amd64.deb
# apt-mark hold package_name
