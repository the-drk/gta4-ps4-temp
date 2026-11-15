# Original-release versus hosted-build regression investigation

## Provenance

The user identifies the earlier roughly 30-minute playable session as the first
`plastikman/gta4-ps4` release, `v0.1.0-ps4`, tagged at
`d6f015fc09cb41e8f68faff2e27c9d64a256fd3a`. They report today's build is barely
10 FPS with severe audio stutter. The delivered hosted-build package is from
`594c1aab5ba79bbb42ab684eda4d7a96f6c9ca82`; its preserved manifest records:

- PKG SHA-256: `6e6d4feb41ff6a6f967efd7b1e76b8fde0e0e6feec6df2521e92613ea31f2dc4`.
- EBOOT SHA-256: `da3f8fcba8c924d8447f5aa3591524a253c7792e9998ea70f7fee9a5fc90d830`.
- Public SDK bundle SHA-256: `b86155980a3f47d48f2dec7b55559afc41dcb6039020358ec001f5a0b6ec5639`.

These identify the delivered artifacts, not an independently read-back installed
EBOOT. The original release's PKG has been removed upstream; its tag and
configuration remain available. A fresh build of the tag is not guaranteed to
reproduce the original binary, particularly with a different SDK/compiler.

The user-supplied console `native.toml` hashes to
`4366b468ee76fb4d7941457461a0f57c3959df1dc4eb0e259fdaa5323156a812`.
This matches the original release asset and today's supplied preset exactly.
Changed config-file contents are therefore not an explanation. Code defaults
and actual configuration loading still require separate consideration.

## Latest runtime evidence

The private `Liberty Recompiled_001.log` contains 412 lines, from
2026-11-14 18:06:45.534 through 18:10:55.350. Raw logs are not committed.

- Excluding the first audio report, whose submission count is cumulative, 16
  ten-second gap reports total **44,305 ms of silence**, averaging 2,769 ms per
  reported interval; the worst is 4,192 ms.
- The arithmetic mean of their reported callback means is **7.442 ms**, maximum
  reported mean 9.16 ms, versus the 5.333 ms budget at 48 kHz / 256 samples.
  This is not a callback-count-weighted mean. The existing 128 ms audio queue
  cannot repair sustained underproduction.
- There are **74 thresholded hitch reports**, average 262.7 ms, maximum 2,323 ms.
  In 44, renderer wait is at least half the reported frame duration; in 23,
  waits on other guest threads meet that threshold. These reports do not
  establish average frame time or average FPS.
- The earlier log 010 had 449 guest-wait-dominated reports among 501 hitches.
  Routes, scene state, warm caches and run durations are not matched, so this
  is a difference in reported stall patterns, not a controlled causal result.
- Memory snapshots show no allocation failures or retries. Later snapshots
  report pressure=false, roughly 177-182 MB of textures against 384 MB, and a
  779 MB largest free direct-memory extent. Raising limits is not justified.
- There are 47 core-count warnings. `XThread::SetActiveCpu` emits them when
  `logical_processor_count()` (libc++ `hardware_concurrency`) returns below six.
  Separately, the affinity report shows process mask `0x7f`, audio core 5,
  renderer/other masks `0x5f`. The query disagreement is real; it does not prove
  that only one/few cores are usable or that this warning caused the regression.

## Source comparison and isolation plan

Changes after the original tag include PS4 renderer spin locks, SSE2 memcmp/bcmp,
FFmpeg NASM/SIMD enablement, additional gated recorder timers, seven-core package
metadata, and build-toolchain changes. None is established as the cause yet.

The branch's shadow-off change applies when shadow interval is zero; the supplied
configuration uses two. The HUD diagnostic change is opt-in. Do not claim that
these gates establish all other build differences are harmless.

1. Preserve the current package, matching symbols, config and original package
   if the user still has it. Never overwrite the only baseline artifact.
2. Prefer an original-tag build using the same hosted toolchain as today's build
   as the first controlled source baseline. Label it a reconstructed baseline,
   not the original release binary. Follow package validation and game-free
   staging rules in AGENTS.md.
3. Compare the same route/save/weather with unchanged configuration. If the
   reconstructed baseline is fast, isolate renderer locks and FFmpeg changes
   independently. If it is also slow, toolchain/SDK and runtime-environment
   differences remain candidates.
4. Do not simultaneously alter audio priorities, affinity, queues, rendering
   settings and memory budgets. No speculative performance fix is validated.

## First recovery candidate: original PS4 renderer lock policy

Restore `std::mutex` for PS4 command capture and queued texture protection,
matching the original release. PS5 retains its spin lock. Keep FFmpeg SIMD,
memcmp, compiler/SDK, package metadata, diagnostics defaults and configuration
unchanged to isolate this candidate. The protection contention instrumentation
uses `try_lock` followed by blocking `lock` on contention and remains compatible.

This removes a plausible source of CPU contention, not a proven culprit. The
historical handoff reported a small improvement from spin locks on another
console, so a regression on this console must be measured rather than assumed.
The resulting package is a recovery test candidate, not a claim of improved FPS.
Compare audio gaps, frame pacing, same-route FPS and stability before accepting
it. If it does not help, do not layer speculative scheduler changes over it;
use the original-tag/toolchain baseline to narrow the remaining differences.

## Recovery-test result: supplied 2026-11-15 capture

The user reports testing yesterday's GitHub Actions build with equally bad
performance and severe audio/FPS stutter. Current source HEAD is `4966d96`
(original PS4 mutex policy). This is user-reported build identification; the
runtime log does not independently identify the installed EBOOT or commit.
Do not confuse this capture with the earlier file with the same basename.

- Private input: `Liberty Recompiled_001.log`, 148,308 bytes, 697 lines,
  2026-11-15 13:09:14.109 through 13:16:20.335.
- SHA-256: `a3509976916d93729ee1237c4729bb195d7ea46f07fa31551084f456b59c0866`.
- Excluding the first two startup audio reports (the second includes 7,495
  submitted frames rather than a normal ten-second count), 36 reports total
  **111,725 ms of silence**: 3,103.5 ms per reported interval, worst 4,997 ms.
  Their callback means average **7.745 ms** (unweighted arithmetic mean), with
  a worst interval mean of 10.66 ms and maximum individual callback 788.8 ms.
  From 13:11:00 onward, 33 reports average 3,295.6 ms silence and 7.960 ms
  callback means. The 5.333 ms production budget is still missed badly.
- **165 thresholded hitch reports** average 170.1 ms, maximum 1,186 ms.
  Guest-thread waits account for at least half the frame in 129 reports;
  renderer waits do so in 23. These are not all frames or average FPS.
  Compared with the earlier hosted-build capture's 44 renderer-dominated
  hitches out of 74, the reported stall mix differs substantially. Different
  duration/route/state prevent attributing that difference to the mutex change.
- Frame 2372 took 1,186 ms, including 1,150 ms renderer wait; the last recorder
  frame was 1,198.7 ms. Other long hitches (832 ms at frame 3338 and 700 ms at
  frame 5034) have essentially no measured renderer or guest wait, so the
  current counters do not explain all stalls.
- Late audio reports show the output worker spending 8.4-9.9 seconds waiting
  on `82191178/Event`, the mixer completion event. The audio-mix thread also
  has idle waits, so this is not a pure computation-time measurement and does
  not distinguish expensive DSP from scheduling/hand-off delays.
- Process affinity remains `0x7f`, audio core 5, other/renderer masks `0x5f`,
  with one failed affinity operation. There are 49 low-core-count warnings;
  as above, they do not prove only a few process cores are usable.
- Final memory sample: 174 MB textures / 384 MB budget, pressure=false,
  zero allocation failures/retries, 166 MB flexible free, 836 MB largest free
  direct-memory extent. No `[PS4 oom]` records. No justification for raising
  memory limits. There are no CPU sampler, capture-split or HUD trace records.

**Conclusion:** the mutex recovery candidate did not resolve the reported
problem. Do not claim that spin locks alone caused the regression or that
this run proves the mutex change had no effect. Keep the next test controlled:
an original-tag source baseline using the same hosted toolchain, package
validation and unchanged console configuration. Preserve its matching ELF and
artifact manifest. If that baseline is also slow, investigate shared toolchain,
SDK and runtime factors rather than layering speculative scheduler changes.

### Hosted reconstructed-baseline recipe

Dispatch `ps4.yml` with `build_package=true` and
`original_release_baseline=true`. The build uses an isolated checkout pinned
to `d6f015fc09cb41e8f68faff2e27c9d64a256fd3a`, retaining that commit's runtime
sources and dependency patches (including original non-NASM FFmpeg policy).
Only the current build/package harness, SDL CMake project-include compatibility
patch and pinned zlib header include are added. Packaging uses the current
seven-core metadata and module stubs to avoid introducing a core-count variable.
The original tag's `native.toml` is included as a reference, not an instruction
to replace the console configuration. The artifact preserves the source commit,
configuration hash, SDK/stub hashes, matching ELF, EBOOT, PKG validation log,
and tracked source diff/status. This is not an exact original-binary rebuild.
