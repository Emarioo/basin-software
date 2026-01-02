
# BTB website
Manual workflow to set it up

```bash
sudo su -u btbwebsite
cd /srv/btbwebsite
git clone git@github.com:Emarioo/btb-website btb-website
git clone git@github.com:Emarioo/BetterThanBatch BetterThanBatch

chown -R btbwebsite /srv/btbwebsite
chgrp -R btbwebsite /srv/btbwebsite

sudo systemctl restart btb-website
```

# Manual Workflow to setup things


# Useful commands

```
systemctl start/stop btb-website
systemctl restart btb-website
journalctl -r -u btb-website

ss -lp
ss

iptables -L INPUT
```