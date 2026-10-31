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
js = subprocess.run([os.path.join(HERE, "node_modules", ".bin", "esbuild"),
                     os.path.join(HERE, "web", "main.js"), "--bundle", "--format=iife", "--minify",
                     "--target=es2020"], capture_output=True, text=True, check=True,
                    cwd=HERE,
                    env=dict(os.environ, NODE_PATH=os.path.join(HERE, "node_modules"))).stdout
html = open(os.path.join(HERE, "web", "index.tpl.html")).read()
html = html.replace("/*DATA*/", json.dumps(data)).replace("/*APP*/", js.replace("</script", "<\\/script"))
open(out, "w").write(html)
print(out, len(html), "bytes,", len(files), "files")
