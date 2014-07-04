#!/bin/bash

if [ ! -d /etc/specter ]; 
then
    mkdir -p /etc/specter
    cat >/etc/specter/specter.yml <<EOL
ssl-key: /etc/ssl/private/ssl-cert-snakeoil.key
ssl-cert: /etc/ssl/certs/ssl-cert-snakeoil.pem
authcode: REPLACE ME
secret: REPLACE ME
EOL
fi

update-rc.d specter defaults
service specter status >/dev/null 2>&1

if [ "$?" -gt "0" ];
then
    service specter start 2>&1
else
    service specter restart 2>&1
fi 

exit 0
