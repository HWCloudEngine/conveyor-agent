#!/usr/bin/env bash

for ((i=0;i<=59;i++));
do
    if  ! pgrep -f  "python $(type -P conveyoragent)" >/dev/null ;
    then
        (/usr/bin/python /usr/local/bin/conveyoragent --config-file /etc/conveyoragent/hybrid-v2v.conf > /dev/null 2>&1 &)
        echo "restart conveyoragent...  $(date)"
    fi
    sleep 1s
done