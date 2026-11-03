#!/bin/sh
# Test library for devsim: 8 s sine tones, one pitch per song (freqs.txt), in
# every format/rate the player meets (MP3 22k mono .. FLAC 24/96, WAV, an
# uppercase .MP3 without a Xing header, cover art, SD-card folders, an .m3u8
# with a BOM and mixed path styles). The pitch identifies the song in the
# audio devsim "hears". Also library_long/ with two 60 s songs for seeking.
set -e
H=$(cd "$(dirname "$0")" && pwd)
L=$H/library
rm -rf "$L" "$H/library_long"
mkdir -p "$L/Internal" "$L/SD"
cp -r "$H/../../STEP-2-THEME/.rechord" "$L/Internal/.rechord"
ff() { ffmpeg -loglevel error -y "$@"; }
ffmpeg -loglevel error -y -f lavfi -i "color=c=0xff2a6d:s=500x500" -frames:v 1 /tmp/devsim_cover.jpg
tone() { # freq secs out [ffmpeg options...]
  f=$1; d=$2; o=$3; shift 3; mkdir -p "$(dirname "$o")"
  ff -f lavfi -i "sine=frequency=$f:duration=$d" "$@" "$o"
}
art() { # add the cover to an mp3
  ff -i "$1" -i /tmp/devsim_cover.jpg -map 0:a -map 1:v -c copy -id3v2_version 3 "$1.tmp.mp3" && mv "$1.tmp.mp3" "$1"
}
M=$L/Internal/Music
tone 900 8 "$M/Gunship/Gunship/01 Tech Noir.wav" -ac 2 -ar 44100 -c:a pcm_s16le -metadata title="Tech Noir" -metadata artist=Gunship -metadata album=Gunship -metadata track=1
tone 1000 8 "$M/Gunship/Gunship/02 Dark All Day.mp3" -ac 1 -ar 22050 -b:a 64k -metadata title="Dark All Day" -metadata artist=Gunship -metadata album=Gunship -metadata track=2
tone 300 8 "$M/Kavinsky/OutRun/01 Nightcall.mp3" -ac 2 -ar 44100 -b:a 128k -metadata title=Nightcall -metadata artist=Kavinsky -metadata album=OutRun -metadata track=1
art "$M/Kavinsky/OutRun/01 Nightcall.mp3"
tone 400 8 "$M/Kavinsky/OutRun/02 Roadgame.mp3" -ac 2 -ar 44100 -q:a 9 -metadata title=Roadgame -metadata artist=Kavinsky -metadata album=OutRun -metadata track=2
tone 500 8 "$M/Kavinsky/OutRun/03 ProtoVision.MP3" -ac 2 -ar 44100 -b:a 320k -write_xing 0 -f mp3 -metadata title=ProtoVision -metadata artist=Kavinsky -metadata album=OutRun -metadata track=3
tone 600 8 "$M/The Midnight/Endless Summer/01 Sunset.flac" -ac 2 -ar 44100 -sample_fmt s32 -bits_per_raw_sample 24 -metadata title=Sunset -metadata artist="The Midnight" -metadata album="Endless Summer" -metadata track=1
tone 700 8 "$M/The Midnight/Endless Summer/02 Gloria.flac" -ac 2 -ar 96000 -sample_fmt s32 -bits_per_raw_sample 24 -metadata title=Gloria -metadata artist="The Midnight" -metadata album="Endless Summer" -metadata track=2
tone 800 8 "$M/The Midnight/Endless Summer/03 Jason.mp3" -ac 2 -ar 48000 -b:a 192k -metadata title=Jason -metadata artist="The Midnight" -metadata album="Endless Summer" -metadata track=3
art "$M/The Midnight/Endless Summer/03 Jason.mp3"
S=$L/SD
tone 1100 8 "$S/Night Drive/01 Midnight City.mp3" -ac 2 -ar 44100 -b:a 256k -metadata title="Midnight City" -metadata artist=M83 -metadata album="Hurry Up" -metadata track=1
art "$S/Night Drive/01 Midnight City.mp3"
tone 1200 8 "$S/Night Drive/02 Turbo Killer.mp3" -ac 2 -ar 44100 -b:a 160k -metadata title="Turbo Killer" -metadata artist="Carpenter Brut" -metadata album=Trilogy -metadata track=2
tone 1300 8 "$S/Night Drive/03 Tech Noir Remix.flac" -ac 2 -ar 44100 -sample_fmt s32 -bits_per_raw_sample 24 -metadata title="Tech Noir Remix" -metadata artist=Gunship -metadata album=Remixes -metadata track=3
tone 1400 8 "$S/Gym/01 Rampage.mp3" -ac 2 -ar 44100 -b:a 128k -metadata title=Rampage -metadata artist=Kavinsky -metadata album=OutRun -metadata track=4
mkdir -p "$S/Playlists"
printf '\357\273\277#EXTM3U\r\n#EXTINF:8,Carpenter Brut - Turbo Killer\r\n../Night Drive/02 Turbo Killer.mp3\r\n/Internal/Music/Kavinsky/OutRun/01 Nightcall.mp3\r\nInternal\\Music\\The Midnight\\Endless Summer\\02 Gloria.flac\r\n/Internal/Music/Missing/nope.mp3\r\n\\Internal\\Music\\Kavinsky\\OutRun\\03 ProtoVision.MP3\r\n' > "$S/Playlists/Road Trip.m3u8"
printf '\357\273\277../Gym/01 Rampage.mp3\r\n../Night Drive/01 Midnight City.mp3\r\n' > "$S/Playlists/Gym Mix.m3u"
# long songs for the seek scenario
LL=$H/library_long
mkdir -p "$LL/Internal" "$LL/SD"
cp -r "$L/Internal/.rechord" "$LL/Internal/.rechord"
tone 1500 60 "$LL/Internal/Music/Test/01 Long Ride.mp3" -ac 2 -ar 44100 -b:a 192k -metadata title="Long Ride" -metadata artist=Tester
tone 1700 60 "$LL/Internal/Music/Test/02 Long Flac.flac" -ac 2 -ar 44100 -metadata title="Long Flac" -metadata artist=Tester
echo "library ready"
