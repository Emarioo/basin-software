garbage extra text?

# /home/emarioo/website/README.md

There is btb-website and BetterThanBatch in this directory


```
# Website structure

The website consist of 2 repositories and 3 things.
1. The website repo with the html and web server
2. The btb repo with the documentation (either from dev or the latest release)
3. A auto-update server to detect new pushes to website and btb repo to automatically git pull changes (Auto deployment)


We might add in more sub websites like morsecode which is also auto git pulled and deployed.
```


# /home/emarioo/secure/unzip_cert.sh

```
#!/bin/bash

# unpack certificates from zerossl, run as root

DOMAIN=btb-lang.org

unzip $DOMAIN.zip
cat certificate.crt ca_bundle.crt > fullchain.pem
cp private.key privkey.pem
rm certificate.crt ca_bundle.crt private.key
chown root:emarioo privkey.pem fullchain.pem
chmod 640 privkey.pem fullchain.pem

chown root:root btb-lang.org.zip
chmod 600 btb-lang.org.zip
```

# /home/emarioo/run_web_service.sh

```
#!/bin/bash

# Run minecraft server

TMUX_SESSION=btbweb

cd /home/emarioo/website/btb-website

if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo MC server has tmux session: '$TMUX_SESSION'
else
    echo "Starting MC tmux session"
    tmux new-session -d -s $TMUX_SESSION
fi

sleep 0.4

tmux send-keys -t $TMUX_SESSION "node auto_deploy.js" Enter
```

