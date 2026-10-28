"""Shared measurement gate for camera/renderer invariance assertions.

Two suites compare `scene.camera` across an asynchronous transition. The viewport may legitimately
move the camera after that transition: every completed mesh load schedules a 120 ms auto-fit
debounce (`native-scene-view.js` `_scheduleFit`) and OrbitControls damping keeps advancing residual
deltas on each rendered frame. Sampling in the instant a React condition flips therefore measures a
camera that is still in motion.

`settle_view` waits until that machinery is quiescent — nothing loading, no fit pending, and two
consecutive samples with an identical camera, target and viewport — and returns that sample. The
assertions themselves stay exact (no tolerance, no weakened identity comparison); only the moment of
measurement becomes deterministic. `camera_trace` records the immediate sample next to the settled
one so a run can say from evidence whether the earlier failures were a measurement moment or a real
camera change.
"""
import time


async def settle_view(page, timeout_ms=20000):
    await page.wait_for_function(
        'window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 '
        '&& window.__workbenchInspect().scene.fitPending===false '
        '&& window.__workbenchInspect().scene.renderCount>0',
        timeout=timeout_ms)
    deadline = time.monotonic() + timeout_ms / 1000
    previous = None
    while time.monotonic() < deadline:
        current = await page.evaluate('window.__workbenchInspect()')
        if previous is not None and all(
                current['scene'][key] == previous['scene'][key] for key in ('camera', 'cameraTarget', 'viewport')):
            return current
        previous = current
        await page.wait_for_timeout(80)
    raise AssertionError('camera/view never became quiescent for measurement')


def camera_trace(report, case, before, at_flip, after):
    """Record the trigger order and the two measurement moments; never used to relax a comparison."""
    report.setdefault('camera_measurements', []).append({
        'case': case,
        'viewport_before': before['scene']['viewport'], 'viewport_at_flip': at_flip['scene']['viewport'], 'viewport_after': after['scene']['viewport'],
        'camera_before': before['scene']['camera'], 'camera_at_flip': at_flip['scene']['camera'], 'camera_after_settle': after['scene']['camera'],
        'camera_target_before': before['scene']['cameraTarget'], 'camera_target_after': after['scene']['cameraTarget'],
        'fit_pending_at_flip': at_flip['scene'].get('fitPending'), 'auto_fit_suppressed': at_flip['scene'].get('autoFitSuppressed'),
        'pending_loads_at_flip': at_flip['scene']['pendingLoads'],
        'moved_between_flip_and_settle': at_flip['scene']['camera'] != after['scene']['camera'],
        'moved_after_settle': before['scene']['camera'] != after['scene']['camera'],
    })
