#!/bin/bash
rsync -av --exclude-from=.gitignore --exclude .git ./ web@nuke:/web/vestaboard-pattern-server/
scp config/prod.json web@nuke:/web/vestaboard-pattern-server/config/prod.json
ssh web@nuke "sudo /usr/bin/systemctl reload vestaboard-pattern-server.service"