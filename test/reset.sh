#!/usr/bin/env bash
rm -Rf ~/.gridtogo
cd ~/GridToGo
rm -f gridtogoserver.db bin/gridtogoserver.db
mysql -uroot -pburrtango -e"\. test/reset.sql"
