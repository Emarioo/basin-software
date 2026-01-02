# Update cert for btb-lang.org

# TODO: We shouldn't run server as root...

iptables -t nat -I PREROUTING 1 -j ACCEPT
python3 -m http_server
iptables -t nat -D PREROUTING 1
echo "Restored iptables"

#FROM=/etc/letsencrypt/live/btb-lang.org 
#TO=/home/emarioo/secure
#cp $FROM/fullchain.pem $TO/fullchain.pem
#cp $FROM/privkey.pem $TO/privkey.pem

#chgrp emarioo $TO/fullchain.pem
#chgrp emarioo $TO/privkey.pem
#chmod g+r $TO/fullchain.pem
#chmod g+r $TO/privkey.pem