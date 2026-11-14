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
