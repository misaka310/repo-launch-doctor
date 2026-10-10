FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:690445a4d5f14cb2019f221fecf7bec45f62179dcc56314f2e1731c4082823a4

COPY . $SRC/repo-launch-doctor
WORKDIR $SRC/repo-launch-doctor
COPY .clusterfuzzlite/build.sh $SRC/
