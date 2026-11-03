# devsim — the player, on a PC, with ears

devsim runs the **real Neon Drive firmware** on Linux: the AP code (UI, player,
library, playlists, settings, power handling) is compiled for x86-64 from the
exact patched ReChord tree that `firmware/build.sh` builds, and the **real
Core B image** (`bb_core.bin`, the MP3/FLAC/WAV decoder core) runs instruction
by instruction in unicorn on the same shared memory the device uses.

Only the hardware is modelled: 1 ms ticks, the I2S FIFO and its interrupt,
the DAC (volume, mute, amp), keys (ADC ladder + POWER), headphone jack, USB
cable, panel and storage timing. A scenario script presses keys like a person
would, and every second devsim reports what you would **hear**: player state,
song, how much of the second was audible, and the measured pitch. Each test
song is a different sine tone, so "the right song is playing" is checked from
the audio itself.

```
sh build.sh                 # needs: cc make gcc-arm-none-eabi ffmpeg, pip install unicorn
sh regress.sh               # every scenario, summary at the end (about 10 min)
./mk.sh s3 && sh run.sh s3.txt          # one scenario
DEVSIM_PCM=/tmp/out.raw sh run.sh s3.txt  # also capture the audio (s16 mono)
```

Scenario lines: `wait MS`, `press KEY [MS]`, `hold KEY MS` (UP DOWN SEL BACK
MENU POWER), `listen MS`, `shot NAME` (screen to shots/NAME.ppm), `mark TEXT`,
`jack out|in`, `usb on|off`. A power-off restarts devsim, which boots and
continues the script. Report line:

```
t=  42.1s + PLAY  Gloria   list  3/12  audio 100%  tone 700/700 Hz  96000Hz v-23/a 46 p  2.1 [player]
          | state  song        queue        audible   heard/expected   rate  volume/DAC  pos  screen
          + = right song, fully audible      ! = transition or problem
```

| Scenario | What it proves |
|---|---|
| s1 | library rebuild, All Songs, plays and keeps going across MP3/FLAC/WAV and rate changes |
| s2 | next ×3, previous, pause, resume |
| s3 | shuffle, skips, queue view |
| s4 | repeat one, repeat all wraps, repeat off stops at the end |
| s5 | volume steps, both ends, presses during song changes |
| s6 | power off mid-song, power on, Now Playing, PLAY resumes where it was |
| s7 | Search: type, results, play |
| s8 | long pause, idle power save (DAC + Core B off) then play again |
| s9 / s9b | MUSIC SETUP: Playback, Interface, Controls, Bluetooth, EQ, System, file browser |
| s10 | playlist files (BOM, CRLF, mixed path styles, a missing song), folder playlists, favorites |
| s11 | first boot without a library builds it; manual rebuild |
| s12 | headphones pulled, hold-VOL seek mode, sleep timer power-off and resume after it |
| s13 | seeking forwards/backwards in MP3 and FLAC (`library_long`) |
| s14 | queue: pick a song, overlay closes, it plays |
