#!/bin/sh
# run.sh SCRIPT [fresh]  — runs devsim across power cycles
R=/tmp/devroot_$(basename $1 .txt)
if [ "$2" != "keep" ]; then rm -rf $R; cp -r ${TPL:-./library} $R; fi
mkdir -p shots
[ -n "$UNICORN_SO" ] || export UNICORN_SO=$(python3 -c "import unicorn,os;print(os.path.join(os.path.dirname(unicorn.__file__),'lib','libunicorn.so.2'))")
while :; do
  ./devsim $R "$1"; rc=$?
  [ $rc -eq 77 ] || exit $rc
done
