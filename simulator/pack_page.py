#!/usr/bin/env python3
"""Pack sim.wasm + theme packages + web/main.js into one self-contained HTML."""
import base64, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
wasm, out, *theme_dirs = sys.argv[1:]
files = {}
def add_tree(src, dst):
    for d, _, fs in os.walk(src):
        for f in fs:
            p = os.path.join(d, f)
            files[dst + "/" + os.path.relpath(p, src).replace(os.sep, "/")] = base64.b64encode(open(p, "rb").read()).decode()
for spec in theme_dirs:            # src=dst pairs
    src, dst = spec.split("=")
    add_tree(src, dst)
data = {"wasm": base64.b64encode(open(wasm, "rb").read()).decode(), "files": files}
# JS fallback: the same wasm translated by wasm2js, plus a bridge module
# whose exports forward to the WASI shim once it exists.
simjs = os.path.abspath(os.path.join(os.path.dirname(wasm), "sim.js"))
subprocess.run([os.path.join(HERE, "node_modules", ".bin", "wasm2js"), wasm, "-O2",
                "--enable-bulk-memory", "--enable-mutable-globals", "--enable-sign-ext",
                "--enable-nontrapping-float-to-int", "-o", simjs], check=True)
import re
names = sorted(set(re.findall(r"wasi_snapshot_preview1\.(\w+)", open(simjs).read())))
bridge = os.path.abspath(os.path.join(os.path.dirname(wasm), "wasi_bridge.js"))
# wasm2js splits every i64 argument into (low, high) i32 halves; the shim
# wants BigInt. These WASI calls take i64s (position in the arg list):
I64 = {"fd_seek": [1], "fd_readdir": [3], "path_open": [5, 6],
       "fd_pread": [3], "fd_pwrite": [3], "fd_filestat_set_size": [1],
       "clock_time_get": [1], "fd_allocate": [1, 2], "fd_advise": [1, 2]}
with open(bridge, "w") as f:
    f.write("export const bridge = { impl: null };\n")
    f.write("const j = (lo, hi) => BigInt.asIntN(64, (BigInt(hi | 0) << 32n) | BigInt(lo >>> 0));\n")
    for n in names:
        if n in I64:
            f.write("export function %s(...a) {\n  const o = []; let i = 0;\n" % n)
            f.write("  for (let k = 0; i < a.length; k++) { if (%s.includes(k)) { o.push(j(a[i], a[i + 1])); i += 2; } else o.push(a[i++]); }\n" % I64[n])
            f.write("  return bridge.impl.%s(...o);\n}\n" % n)
        else:
            f.write("export function %s(...a) { return bridge.impl.%s(...a); }\n" % (n, n))
js = subprocess.run([os.path.join(HERE, "node_modules", ".bin", "esbuild"),
                     os.path.join(HERE, "web", "main.js"), "--bundle", "--format=iife", "--minify",
                     "--target=es2020", "--alias:wasi-bridge=" + bridge,
                     "--alias:wasi_snapshot_preview1=" + bridge, "--alias:sim-fallback=" + simjs], capture_output=True, text=True, check=True,
                    cwd=HERE,
                    env=dict(os.environ, NODE_PATH=os.path.join(HERE, "node_modules"))).stdout
html = open(os.path.join(HERE, "web", "index.tpl.html")).read()
html = html.replace("/*DATA*/", json.dumps(data)).replace("/*APP*/", js.replace("</script", "<\\/script"))
open(out, "w").write(html)
print(out, len(html), "bytes,", len(files), "files")
