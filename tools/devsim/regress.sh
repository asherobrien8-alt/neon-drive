#!/bin/sh
# regress.sh : run every scenario in parallel, write /tmp/r_NAME.txt
for n in s1 s2 s3 s4 s5 s6 s7 s8 s9b s10 s11 s12 s13 s14; do
  if [ -f scenarios/body_$n.txt ]; then ./mk.sh $n; else cp scenarios/$n.txt .; fi
  T=./library; [ $n = s13 ] && T=./library_long
  ( TPL=$T timeout 2400 ./run.sh $n.txt > /tmp/r_$n.txt 2>&1; echo "rc $?" >> /tmp/r_$n.txt ) &
done
wait
for n in s1 s2 s3 s4 s5 s6 s7 s8 s9b s10 s11 s12 s13 s14; do
  echo "=== $n $(tail -1 /tmp/r_$n.txt)  faults: $(grep -o 'faults [0-9]*' /tmp/r_$n.txt | tail -1)"
  grep -E "^  t=|^##" /tmp/r_$n.txt | sed -n '/^##/,$p' | awk '
    /^##/ {print; next}
    { st=$3; ti=substr($0,index($0,$4),16); li=$0; sub(/.*list +/,"",li); li=substr(li,1,5);
      k=st" "ti" "li; if (k!=last) { printf "    %s %s  %s %s\n", $2, st, ti, li; last=k } }'
done
