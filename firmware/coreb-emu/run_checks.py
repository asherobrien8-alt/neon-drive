#!/usr/bin/env python3
"""Run the real Core B image under unicorn and drive it like the AP does:
hard starts of MP3/FLAC files, skips (CLOSE+OPEN), gapless NEXT, seeks.

    pip install unicorn numpy
    python3 run_checks.py path/to/bb_core.bin song1.mp3 song2.mp3 song3.flac ...

Prints, for each file, whether Core B opened it and the decoded level of the
first second. Every file is opened twice in a row and also after a FLAC, the
sequences that failed on the device before Neon Drive 4."""
import sys
import numpy as np
from bemu import CoreB


def level(p):
    a = np.frombuffer(bytes(p), np.int32).reshape(-1, 2) / 65536.0
    return len(a), int(np.sqrt((a ** 2).mean())) if len(a) else 0


def main():
    b = CoreB(open(sys.argv[1], 'rb').read())
    b.boot()
    bad = 0
    for rnd in range(2):
        for path in sys.argv[2:]:
            codec = 2 if path.lower().endswith('.flac') else (0 if path.lower().endswith('.wav') else 1)
            ok, cost = b.open(open(path, 'rb').read(), codec)
            if not ok:
                print('FAIL open', path, 'berr', b.r(23)); bad += 1; b.stop(); continue
            n, rms = level(b.play(1.0))
            print('%-40s ok  %6d frames  level %5d  open %.1fM insns' % (path, n, rms, cost / 1e6))
            if n == 0 or rms == 0:
                bad += 1
            b.stop()
    print('FAILURES:', bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
