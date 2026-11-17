#!/usr/bin/env python3
"""Host-side regression checks for the PS4 shadow-off and HUD diagnostic gates.

These checks model the capture policy and assert that the corresponding source
guards remain present. They do not compile the Orbis target or validate GPU
behaviour on hardware.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "glue/rexglue-sdk-main/gta4-recomp/src/gta4_native_hooks.cpp"
GRAPHICS = ROOT / "glue/rexglue-sdk-main/src/graphics/gta4_native/graphics_system.cpp"


def should_drop(interval: int, frame: int, has_device: bool,
                minimum: int, index_count: int) -> bool:
    """Mirror the PS4 hook's decision before depth-surface classification."""
    shadow_rest = (
        interval == 0
        or (
            interval > 1
            and has_device
            and (frame + 1) % interval != 0
        )
    )
    return has_device and (
        shadow_rest or (minimum != 0 and index_count < minimum)
    )


def extract_function(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        raise AssertionError(f"Missing function signature: {signature}")
    opening = source.find("{", start)
    if opening < 0:
        raise AssertionError(f"Missing function body: {signature}")
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening:index + 1]
    raise AssertionError(f"Unterminated function body: {signature}")


hooks = HOOKS.read_text(encoding="utf-8")
graphics = GRAPHICS.read_text(encoding="utf-8")

shadow = extract_function(
    hooks, "bool DropSmallShadowDraw(uint8_t* base, uint32_t device, uint32_t index_count)"
)
assert "#if REX_PLATFORM_PS4" in shadow
assert re.search(r"interval\s*==\s*0\s*\|\|", shadow)
assert re.search(
    r"if\s*\(!device\s*\|\|\s*\(!shadow_rest\s*&&\s*"
    r"\(!minimum\s*\|\|\s*index_count\s*>=\s*minimum\)\)\)\s*return false",
    shadow,
), "PS4 shadow-off capture guard changed; review the truth table"

cases = 0
for interval in range(5):
    for frame in range(13):
        for has_device in (False, True):
            for minimum in (0, 1000):
                for count in (0, 999, 1000, 2000):
                    actual = should_drop(interval, frame, has_device, minimum, count)
                    if interval == 0:
                        expected = has_device
                    else:
                        old_rest = (
                            interval > 1
                            and has_device
                            and (frame + 1) % interval != 0
                        )
                        expected = old_rest or (
                            minimum != 0 and count < minimum and has_device
                        )
                    assert actual == expected, (
                        f"policy mismatch: interval={interval}, frame={frame}, "
                        f"device={has_device}, minimum={minimum}, count={count}"
                    )
                    cases += 1

diagnostics = extract_function(
    graphics,
    "uint64_t NextNativeTraceDiagnosticCount(std::atomic<uint64_t>& counter)",
)
assert "REX_PLATFORM_PS4" in diagnostics
assert "REXCVAR_GET(ps5_hud_trace)" in diagnostics
assert "REX_PLATFORM_PS5 || REX_PLATFORM_PS4" in diagnostics

print(f"PASS: {cases} shadow-policy cases and PS4 HUD diagnostic source guards.")
print("NOTE: host-side checks only; an Orbis build and console A/B remain required.")
