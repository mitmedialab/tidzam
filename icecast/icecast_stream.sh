#!/bin/sh
ffmpeg  -f jack                     \
        -i $1                       \
        -c:a libvorbis -b:a 320k    \
        -legacy_icecast 1           \
        -content_type audio/ogg     \
        -ice_name $1                \
        -f ogg                      \
        icecast://source:tidzam17@localhost:8000/$1.ogg 
