#!/bin/sh
ecasound -i:jack,mpv:out_$1 -o:stdout | ices2 /tmp/ices-chan$1.xml
sleep 1
