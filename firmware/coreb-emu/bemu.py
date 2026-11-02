#!/usr/bin/env python3
"""Run the real Core B image (bb_core.bin) in unicorn and drive it like the AP:
file rings, OPEN/NEXT/SEEK/CLOSE commands, PCM ring consumption."""
import struct, sys, os
from unicorn import *
from unicorn.arm_const import *

SH = 0x01020000
FILE0, FILE0_N = 0x01021000, 32 * 1024
FILE1, FILE1_N = 0x01029000, 16 * 1024
PCM, PCM_N = 0x01030000, 64 * 1024
W = dict(MAGIC=0, STATE=1, RD=2, WR=3, FRAMES=4, CMD=18, ARG=19, ACK=20, BSTATE=21,
         BEOF=22, BERR=23, RG=24, GD=25, GP=26, GT=27, SEQ=28, RING=38, PREV=39, BSTALL=43)
F = [dict(OPEN=9, SIZE=10, BASE=11, RD=12, WR=13, EOF=14, TO=15, SSEQ=16, SACK=17),
     dict(OPEN=29, SIZE=30, BASE=31, RD=32, WR=33, EOF=34, TO=35, SSEQ=36, SACK=37)]
RINGS = [(FILE0, FILE0_N), (FILE1, FILE1_N)]


class CoreB:
    def __init__(self, blob):
        self.mu = mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        mu.mem_map(0x01000000, 0x60000)
        mu.mem_map(0x40030000, 0x1000)
        mu.mem_write(0x01000000, blob)
        sp, pc = struct.unpack('<II', blob[:8])
        mu.reg_write(UC_ARM_REG_SP, sp)
        self.pc = pc
        self.insns = 0
        self.files = [None, None]      # (data, pos)
        self.pcm = bytearray()
        self.seq = 0

    def r(self, i): return struct.unpack('<I', self.mu.mem_read(SH + 4 * i, 4))[0]
    def w(self, i, v): self.mu.mem_write(SH + 4 * i, struct.pack('<I', v & 0xFFFFFFFF))

    def run(self, n=300_000):
        try:
            self.mu.emu_start(self.pc | 1, 0x0FFFFFFF, count=n)
        except UcError as e:
            raise RuntimeError('B fault %s at %x' % (e, self.mu.reg_read(UC_ARM_REG_PC)))
        self.pc = self.mu.reg_read(UC_ARM_REG_PC)
        self.insns += n
        self.service()

    # ---- AP side: bfs_poll + I2S consumer
    def publish(self, slot, data):
        f = F[slot]
        for k in ('BASE', 'RD', 'WR', 'EOF', 'TO'):
            self.w(f[k], 0)
        self.w(f['SIZE'], len(data))
        self.w(f['SACK'], self.r(f['SSEQ']))
        self.files[slot] = [data, 0]
        self.w(f['OPEN'], 1)

    def close_ring(self, slot):
        self.files[slot] = None
        self.w(F[slot]['OPEN'], 0)

    def service(self):
        for slot in (0, 1):
            fl = self.files[slot]
            if fl is None:
                continue
            f = F[slot]; base, n = RINGS[slot]
            if self.r(f['SSEQ']) != self.r(f['SACK']):
                to = self.r(f['TO'])
                fl[1] = to
                self.w(f['BASE'], to); self.w(f['RD'], 0); self.w(f['WR'], 0); self.w(f['EOF'], 0)
                self.w(f['SACK'], self.r(f['SSEQ']))
            if self.r(f['EOF']):
                continue
            rd, wr = self.r(f['RD']), self.r(f['WR'])
            free = n - ((wr - rd) & 0xFFFFFFFF)
            while free > 0:
                pos = wr % n
                k = min(free, n - pos, 4096)
                chunk = fl[0][fl[1]:fl[1] + k]
                if chunk:
                    self.mu.mem_write(base + pos, bytes(chunk))
                fl[1] += len(chunk)
                wr += len(chunk); free -= len(chunk)
                self.w(f['WR'], wr)
                if len(chunk) < k:
                    self.w(f['EOF'], 1)
                    break
        # PCM consumer (only while RUN)
        if self.r(W['STATE']) == 1:
            rd, wr = self.r(W['RD']), self.r(W['WR'])
            while rd != wr:
                pos = rd % PCM_N
                k = min(wr - rd, PCM_N - pos)
                self.pcm += self.mu.mem_read(PCM + pos, k)
                rd += k
            self.w(W['RD'], rd)

    def cmd(self, c, arg=0, ring=0, budget=60_000_000):
        self.w(W['RING'], ring); self.w(W['ARG'], arg); self.w(W['PREV'], 0)
        self.seq += 1
        self.w(W['CMD'], c); self.w(W['SEQ'], self.seq)
        used = 0
        while self.r(W['ACK']) != self.seq:
            self.run(); used += 300_000
            if used > budget:
                raise RuntimeError('no ack for cmd %d (bstate %d bstall %d)' % (c, self.r(W['BSTATE']), self.r(W['BSTALL'])))
        return used

    def boot(self):
        self.w(W['RG'], 32768)
        while self.r(W['MAGIC']) != 0x42524459:
            self.run()

    def open(self, data, codec):
        self.w(W['STATE'], 0); self.w(W['RD'], 0); self.w(W['WR'], 0)
        self.w(W['GD'], 0); self.w(W['GP'], 0); self.w(W['GT'], 0)
        self.publish(0, data)
        cost = self.cmd(1, codec, 0)
        ok = self.r(W['BSTATE']) == 1
        return ok, cost

    def play(self, seconds, rate=44100):
        self.w(W['STATE'], 1)
        start = len(self.pcm)
        need = int(seconds * rate) * 8
        guard = 0
        while len(self.pcm) - start < need and not self.r(W['BEOF']):
            self.run(); guard += 1
            if guard > 20000:
                raise RuntimeError('no PCM progress (bstate %d berr %d)' % (self.r(W['BSTATE']), self.r(W['BERR'])))
        self.service()
        return self.pcm[start:]

    def stop(self):
        self.cmd(3)
        self.w(W['STATE'], 0)
        self.close_ring(0); self.close_ring(1)
