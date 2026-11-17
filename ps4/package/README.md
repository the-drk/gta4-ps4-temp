# Reproducing the PS4 package

`pkg.gp4` and `param.sfo` are the exact package metadata staged for CXIV.
The GP4 lists 27 entries, all game-free. The script copies those entries from
tracked source files, the freshly built EBOOT, and two OpenOrbis stub modules.
It verifies the GP4 against the staged files, builds the PKG, validates it, and
keeps the matching ELF for crash symbolization.

```sh
ps4/build-clean.sh
PS4_PKGTOOL_OPENSSL_LIB="$HOME/codex_scratch/libssl1.1/usr/lib/x86_64-linux-gnu" \
  ps4/package/build-package.sh
```

The default build directory is
`~/codex_scratch/gta4-ps4-clean/build`; the default package directory is
`~/codex_scratch/gta4-ps4-clean/package`. Set `PS4_BUILD_DIR` and
`PS4_PACKAGE_DIR` to select others. The package script refuses to overwrite an
existing stage, so choose a new `PS4_PACKAGE_DIR` for each package run. It
writes `out/GTA4.pkg` as a link to the validated content-ID PKG.

The same validated PkgTool output is also copied to a uniquely named
`out/<version>.fpkg` file. The extension is a distribution label; the bytes
are identical to the validated `.pkg` output, and the package is built as a
PS4 application package from the GP4 (it is not re-signed or transformed by the
copy). The script writes `FPKG-VERSION.txt` and `SHA256SUMS` with the version,
core profile, workflow run/attempt, source commit, SFO/EBOOT/package hashes,
and UTC build time. GitHub Actions publishes the versioned fPKG as an
individual Release asset for direct download; the small Actions artifact keeps
its manifests and diagnostics without wrapping the 140+ MB package in a ZIP.
For the six/seven-core A/B, both packages reuse the same baseline EBOOT and
only differ in the SFO `ATTRIBUTE` seven-core bit. This isolates the metadata
setting; it is not a rebuilt six-core executable and must be validated on the
console before drawing performance conclusions.

External inputs that Git does not contain:

- `PS4_SDK_BUNDLE` defaults to `~/ps4-gladius/sdk/orbis-sdk-v1` and provides
  the Orbis toolchain, Mesa RADV, and `PkgTool.Core`. This bundle identifies
  itself in `BUNDLE.txt` and carries `SHA256SUMS` plus `verify.sh`. Treat it as
  read-only. The scripts require the CXIV bundle fingerprint
  `b86155980a3f47d48f2dec7b55559afc41dcb6039020358ec001f5a0b6ec5639`
  for `BUNDLE.txt`.
- `PS4_STUBS_DIR` defaults to
  `~/codex_scratch/gta4-ps4-deps/openorbis-stubs`. Its `libc.prx` and
  `libSceFios2.prx` are the source-built OpenOrbis stubs used by CXIV. The
  script checks their SHA-256 values before packaging. `PS4_EXPECTED_LIBC_SHA256`
  and `PS4_EXPECTED_FIOS2_SHA256` can override those pins for a separately
  recorded build provenance, as the CI job does for its pinned Orbis-Win runner
  toolchain. The stubs can be built from the OpenOrbis sources using orbis-win's
  `scripts/build-openorbis-module-stubs.sh`.
- `PS4_DXC_ROOT` defaults to `~/codex_scratch/gta4-ps4-deps/dxc` for the
  host shader compiler used by the clean build. The build script checks hashes
  of `bin/dxc`, `lib/libdxcompiler.so`, and `lib/libdxil.so` before configuring.
- The Linux `PkgTool.Core` needs OpenSSL 1.1. Set
  `PS4_PKGTOOL_OPENSSL_LIB` to the directory containing `libssl.so.1.1`
  and `libcrypto.so.1.1`. It is already cached at the path in the command
  above on this machine.

The Xbox 360 game files are never staged; they remain on the console under
`/data/LibertyRecomp/game`. A fresh detached checkout built and packaged
successfully on 2026-11-08. The package passed all 28 validator checks.
The clean EBOOT differs from the old CXIV EBOOT, so byte-for-byte reproduction
of that historical build is not established. The older CMake cache had repeated
compile flags and a different source path.
