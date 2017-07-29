#!/bin/sh
ecasound -i:jack -o:stdout | ices2 /tmp/ices-chan$1.xml
sleep 1
