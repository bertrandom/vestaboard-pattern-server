#!/bin/bash
rsync -av \
  --include='/config/prod.json5' \
  --include='**/.gitignore' \
  --exclude='/.git' \
  --filter=':- .gitignore' \
  --delete-after \
  ./ web@nuke:/web/vestaboard-pattern-server/
ssh web@nuke "sudo /usr/bin/systemctl reload vestaboard-pattern-server.service"