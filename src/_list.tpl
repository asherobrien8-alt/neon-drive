# LIST SCREENS (Library / category / Files) — generated from _list.tpl.
# Purple selection bar, red marker, teal selected text, counts on the right
# and a vertical neon word down the right edge.
[bg]
type=fill
x=0
y=0
w=W
h=H
color={navy}

[hbar]
type=fill
x=0
y=18
w=W
h=1
color={pink}

[hmk]
type=fill
x=0
y=4
w=3
h=10
color={red}

[head]
type=text
x=8
y=5
text=@HEAD@
maxc=30
color={cyan}

[bat]
type=text
x=312
y=5
text=(battery < 0 ? "--" : battery + "%")
align=right
color={dim}

[menu]
type=list
axis=vertical
x=14
y=22
height=16
rows=8
source=@SRC@
sel_fg={cyan}
sel_bg={purple}
mark={red}
sel_w=284
val_fg={dim}

@WORD@
[foot]
type=fill
x=0
y=152
w=W
h=1
color={faint}

[hint]
type=text
x=8
y=158
text="VOL MOVE  PLAY OPEN  BACK"
color={dim}

[pos]
type=text
x=312
y=158
text=(n > 0 ? (sel + 1) + "/" + n : "EMPTY")
align=right
color={pink}
