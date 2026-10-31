// Echo Mini simulator page: boots sim.wasm (ReChord's real UI) on an in-memory
// filesystem and drives it with on-screen / keyboard buttons.
import { WASI, File, Directory, OpenFile, ConsoleStdout, PreopenDirectory } from "@bjorn3/browser_wasi_shim";
import { bridge } from "wasi-bridge";            // forwards to the shim (JS fallback)
import * as simJs from "sim-fallback";           // same code via wasm2js, for pages that block WebAssembly

// The shim rejects fd_fdstat_set_flags, which wasi-libc uses for fopen("ab").
// Support APPEND (the media index is built with appends).
OpenFile.prototype.fd_fdstat_set_flags = function (flags) { this.append = (flags & 1) !== 0; return 0; };
const _w = OpenFile.prototype.fd_write;
OpenFile.prototype.fd_write = function (data) {
  if (this.append) this.file_pos = BigInt(this.file.data.byteLength);
  return _w.call(this, data);
};

const b64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

function buildFs(files) {
  const root = new Map();
  for (const [path, data] of Object.entries(files)) {
    const parts = path.split("/");
    let dir = root;
    for (const p of parts.slice(0, -1)) {
      if (!dir.has(p)) dir.set(p, new Directory(new Map()));
      dir = dir.get(p).contents;
    }
    dir.set(parts[parts.length - 1], new File(b64(data)));
  }
  // re-link parents (Directory sets them only at construction)
  const fix = (d) => { for (const e of d.contents.values()) if (e instanceof Directory) { e.parent = d; fix(e); } };
  const pre = new PreopenDirectory("/", root);
  fix(pre.dir);
  return pre;
}

const KEY = { UP: 1, DOWN: 2, SEL: 3, BACK: 4, POWER: 5, MENU: 6 };
const K_PRESS = 0, K_LONG = 1, K_REPEAT = 2, K_RELEASE = 3;

const HINTS = {
  "skin": "Home · VOL+/− pick · PLAY open · MENU = quick settings",
  "library": "Library · Search is the first row",
  "library-cat": "List · PLAY opens · <b>hold PLAY for A-Z jump</b>",
  "search": "Search · VOL spins letters · PLAY adds · BACK deletes · <b>hold PLAY</b> (or pick GO&gt;) for results",
  "a-z": "A-Z · VOL moves letter · PLAY jumps · BACK cancels",
  "player": "Now Playing · <b>VOL+/− changes volume — watch the runner</b>",
  "settings": "Settings · try Interface → Theme",
  "menu": "Classic menu (what MENU on the home bar opens)",
  "quick": "Quick settings · MENU or BACK closes",
  "browser": "Files · your folders, PLAY plays a file",
};

async function main() {
  const D = window.SIM_DATA;
  const fs = buildFs(D.files);
  const wasi = new WASI([], [], [
    new OpenFile(new File([])),
    ConsoleStdout.lineBuffered((m) => console.log("[sim]", m)),
    ConsoleStdout.lineBuffered((m) => console.warn("[sim]", m)),
    fs,
  ], { debug: false });
  let X;
  try {
    const { instance } = await WebAssembly.instantiate(b64(D.wasm), { wasi_snapshot_preview1: wasi.wasiImport });
    wasi.initialize(instance);
    X = instance.exports;
  } catch (e) {
    console.warn("WebAssembly unavailable, using the JS build:", e);
    bridge.impl = wasi.wasiImport;
    X = simJs;
    wasi.inst = { exports: { memory: simJs.memory } };
    simJs._initialize && simJs._initialize();
  }
  const n = X.sim_init();
  document.getElementById("tracks").textContent = `${n} demo tracks`;

  const cv = document.getElementById("lcd");
  const ctx = cv.getContext("2d");
  const img = ctx.createImageData(320, 170);
  const t0 = performance.now();
  const now = () => (Math.floor(performance.now() - t0) + 1000) >>> 0;
  const hint = document.getElementById("hint");
  let lastTop = "";

  const topName = () => {
    const p = X.sim_top(); const m = new Uint8Array(X.memory.buffer, p, 32);
    let s = ""; for (const c of m) { if (!c) break; s += String.fromCharCode(c); } return s;
  };

  function frame() {
    X.sim_tick(now());
    const p = X.sim_fb();
    const fb = new Uint16Array(X.memory.buffer, p, 320 * 170);
    const d = img.data;
    for (let i = 0, j = 0; i < fb.length; i++, j += 4) {
      const v = fb[i];
      d[j] = ((v >> 11) & 31) * 8.2258; d[j + 1] = ((v >> 5) & 63) * 4.0476; d[j + 2] = (v & 31) * 8.2258; d[j + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    const top = topName();
    if (top !== lastTop) { lastTop = top; hint.innerHTML = HINTS[top] || top; }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // ---- buttons with the device's hold ladder (input.h) ----------------
  const held = {};
  function down(k) {
    if (held[k]) return;
    const h = held[k] = { long: false, timers: [] };
    X.sim_key(KEY[k], K_PRESS, 0);
    h.timers.push(setTimeout(() => {
      h.long = true;
      X.sim_key(KEY[k], K_LONG, 0);
      if (k === "UP" || k === "DOWN") {
        const t0 = performance.now();
        const rep = () => {
          if (!held[k]) return;
          X.sim_key(KEY[k], K_REPEAT, 0);
          h.timers.push(setTimeout(rep, performance.now() - t0 > 800 ? 50 : 250));
        };
        h.timers.push(setTimeout(rep, 250));
      }
    }, 500));
    document.querySelector(`[data-k="${k}"]`)?.classList.add("on");
  }
  function up(k) {
    const h = held[k];
    if (!h) return;
    h.timers.forEach(clearTimeout);
    delete held[k];
    X.sim_key(KEY[k], K_RELEASE, h.long ? 1 : 0);
    document.querySelector(`[data-k="${k}"]`)?.classList.remove("on");
  }
  for (const b of document.querySelectorAll("[data-k]")) {
    const k = b.dataset.k;
    b.addEventListener("pointerdown", (e) => { e.preventDefault(); b.setPointerCapture(e.pointerId); down(k); });
    b.addEventListener("pointerup", () => up(k));
    b.addEventListener("pointercancel", () => up(k));
    b.addEventListener("contextmenu", (e) => e.preventDefault());
  }
  const KB = { ArrowUp: "UP", ArrowRight: "UP", ArrowDown: "DOWN", ArrowLeft: "DOWN", Enter: "SEL", " ": "SEL",
               Backspace: "BACK", Escape: "BACK", m: "MENU", M: "MENU", p: "POWER", P: "POWER" };
  addEventListener("keydown", (e) => { const k = KB[e.key]; if (k) { e.preventDefault(); if (!e.repeat) down(k); } });
  addEventListener("keyup", (e) => { const k = KB[e.key]; if (k) { e.preventDefault(); up(k); } });
}

main().catch((e) => {
  document.getElementById("hint").textContent = "Simulator failed to start: " + e;
  console.error(e);
});
