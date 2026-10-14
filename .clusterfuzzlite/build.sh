#!/bin/bash -eu

for fuzzer in fuzzing/*_fuzzer.py; do
  name=$(basename -s .py "$fuzzer")
  pyinstaller --paths "$SRC/repo-launch-doctor" --distpath "$OUT" --onefile --name "${name}.pkg" "$fuzzer"
  cat > "$OUT/$name" <<EOF
#!/bin/sh
# LLVMFuzzerTestOneInput for ClusterFuzzLite fuzzer detection.
this_dir=\$(dirname "\$0")
exec "\$this_dir/${name}.pkg" "\$@"
EOF
  chmod +x "$OUT/$name"
done
