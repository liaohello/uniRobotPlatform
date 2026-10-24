"""Server-only usability verification for the 3D workbench.

Covers real wheel zoom, camera/handle framing, Dockview sash drag, in-app
maximize, browser fullscreen enter/exit, layout presets, panel collapse and a
continuous TCP drag across live Actual refreshes. It does NOT certify robot
control, Session readiness, recording or M1 integration.
"""
import argparse, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

p = argparse.ArgumentParser()
p.add_argument('url')
p.add_argument('output', type=Path)
p.add_argument('--release', default='')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)

checks = []
errors = []
requests = []
report = {'scope': '3D workbench viewport/layout usability; no motion/session/recording acceptance',
          'release': a.release, 'checks': checks, 'errors': errors, 'sizes': {}}


def brief(target):
    return None if target is None else {key: target[key] for key in ('mode', 'revision', 'tcpWorldM')}


def check(name, condition, detail=None):
    if not condition:
        raise AssertionError(name if detail is None else f'{name} :: {detail}')
    checks.append(name)


def state(page):
    return page.evaluate('window.__workbenchInspect()')


def loaded(page):
    page.wait_for_function(
        'window.__workbenchInspect && window.__workbenchInspect().scene.pendingLoads===0 '
        '&& window.__workbenchInspect().scene.renderCount>0', timeout=90000)


def canvas_box(page):
    return page.locator('.canvas-host canvas').bounding_box()


def distance(page):
    return state(page)['scene']['cameraDistance']


def camera_vector(page):
    s = state(page)['scene']
    return [s['camera'][i] - s['cameraTarget'][i] for i in range(3)]


def inside(point, box, margin=2):
    return (box['x'] - margin <= point['x'] <= box['x'] + box['width'] + margin
            and box['y'] - margin <= point['y'] <= box['y'] + box['height'] + margin)


def wait_size(page, key, minimum, timeout=8000):
    page.wait_for_function(
        f'window.__workbenchInspect().scene.viewport.{key} >= {minimum}', timeout=timeout)


def visible_button(page, name):
    button = page.get_by_role('button', name=name, exact=True)
    button.wait_for(state='visible')
    box = button.bounding_box()
    return box is not None and box['width'] > 8 and box['height'] > 8


def enter_fullscreen(page):
    page.get_by_role('button', name='浏览器全屏', exact=True).click()
    page.wait_for_timeout(700)
    return page.evaluate('()=>({active:!!document.fullscreenElement,enabled:document.fullscreenEnabled,tag:document.fullscreenElement?.tagName||null})')


def exit_fullscreen(page):
    button = page.get_by_role('button', name='退出全屏', exact=True)
    if button.count() and button.is_visible():
        button.click()
    else:
        page.evaluate('()=>document.exitFullscreen&&document.exitFullscreen()')
    page.wait_for_timeout(600)


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=[
        '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
        '--disable-dev-shm-usage'])
    page = browser.new_page(viewport={'width': 1366, 'height': 768}, device_scale_factor=1,
                            timezone_id='America/Los_Angeles')
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda req: requests.append({'method': req.method, 'url': req.url}))
    try:
        page.goto(a.url + '/?inspect=1', wait_until='networkidle')
        loaded(page)
        page.wait_for_timeout(600)
        initial = state(page)
        base_instance = initial['scene']['instanceId']

        # ---- 1366x768: space budget and reachable controls ----
        metrics = page.evaluate("""()=>{
          const rect=s=>{const e=document.querySelector(s);return e?e.getBoundingClientRect():null};
          const v=rect('.viewport-panel'), c=rect('.canvas-host canvas');
          return {header:rect('.global-header')?.height,control:rect('.control-strip')?.height,
            layout:rect('.layout-bar')?.height,status:rect('.status-bar')?.height,
            nav:rect('.side-nav')?.width,viewport:v&&{x:v.x,y:v.y,w:v.width,h:v.height},
            canvas:c&&{x:c.x,y:c.y,w:c.width,h:c.height},
            scrollH:document.documentElement.scrollHeight,innerH:window.innerHeight,
            dpr:window.devicePixelRatio};}""")
        report['sizes']['1366x768'] = metrics
        fixed = sum(metrics[k] for k in ('header', 'control', 'layout', 'status'))
        check('1366x768 fixed chrome stays under 150px', fixed <= 150, fixed)
        check('1366x768 canvas is usable (>=300px tall)', metrics['canvas']['h'] >= 300, metrics['canvas']['h'])
        check('1366x768 document does not scroll', metrics['scrollH'] <= metrics['innerH'] + 1,
              (metrics['scrollH'], metrics['innerH']))
        check('only one renderer instance', initial['scene']['lifecycle']['active'] == 1)
        page.screenshot(path=str(a.output / 'usability-1366.png'), full_page=True)
        for name in ('放大', '缩小', '适配模型', '恢复全景', '聚焦选中对象', '车头', '车侧', '顶视', '图层选项'):
            check(f'viewport toolbar exposes {name}', visible_button(page, name))
        for name in ('最大化视口', '浏览器全屏', '保存', '恢复', '重置', '标准工作台', '3D 专注'):
            check(f'layout bar exposes {name}', visible_button(page, name))

        # ---- navigation rail and inspector diagnostics stay operable ----
        page.get_by_role('button', name='收起导航', exact=True).click()
        page.wait_for_timeout(300)
        collapsed_nav = page.evaluate("()=>document.querySelector('.side-nav').getBoundingClientRect().width")
        page.get_by_role('button', name='展开导航', exact=True).click()
        page.wait_for_timeout(300)
        expanded_nav = page.evaluate("()=>document.querySelector('.side-nav').getBoundingClientRect().width")
        report['nav'] = {'collapsed': collapsed_nav, 'expanded': expanded_nav}
        check('navigation rail can be collapsed and restored', collapsed_nav <= 60 and expanded_nav >= 100)
        page.locator('.inspector details.diag summary').first.click()
        page.wait_for_timeout(200)
        check('Inspector diagnostics expand on demand',
              page.locator('.inspector details.diag').first.evaluate('(e)=>e.open') is True)
        check('Inspector target actions stay reachable next to scrolling diagnostics',
              page.locator('.inspector-actions').is_visible())
        check('Inspector keeps a local scroll region',
              page.locator('.inspector-scroll').evaluate('(e)=>e.scrollHeight>=e.clientHeight'))
        # ---- Session preparation surface: honest states only ----
        page.get_by_role('button', name='Session 准备', exact=True).click()
        page.wait_for_timeout(300)
        drawer = page.locator('.session-drawer')
        check('Session 准备 opens a draft/validation/prepared surface', drawer.is_visible())
        drawer_text = drawer.inner_text()
        report['session_drawer'] = drawer_text[:900]
        check('Session drawer separates draft, validation and prepared steps',
              all(token in drawer_text for token in ('草案 Draft', '校验 Validation', 'prepared Session')))
        check('Session drawer reports the real blocked reason instead of Ready',
              '未就绪' in drawer_text and 'session_ready=false' in drawer_text)
        check('Session drawer keeps Start disabled',
              page.get_by_role('button', name='Start', exact=True).is_disabled())
        page.screenshot(path=str(a.output / 'usability-session.png'), full_page=True)
        page.get_by_role('button', name='关闭 Session 准备', exact=True).click()
        page.wait_for_timeout(200)

        # ---- real wheel zoom over the canvas ----
        box = canvas_box(page)
        cx, cy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        page.mouse.move(cx, cy)
        before = distance(page)
        page.mouse.wheel(0, -420)
        page.wait_for_timeout(260)
        after_in = distance(page)
        page.mouse.wheel(0, 420)
        page.wait_for_timeout(260)
        after_out = distance(page)
        report['wheel'] = {'before': before, 'in': after_in, 'out': after_out}
        check('mouse wheel zooms the camera in', after_in < before * 0.95, (before, after_in))
        check('mouse wheel zooms the camera back out', after_out > after_in * 1.03, (after_in, after_out))
        # The legend and hint overlays must not swallow wheel input.
        legend = page.locator('.viewport-legend').bounding_box()
        if legend:
            page.mouse.move(legend['x'] + 6, legend['y'] + 4)
            before_legend = distance(page)
            page.mouse.wheel(0, -320)
            page.wait_for_timeout(240)
            check('wheel over the legend overlay still zooms', distance(page) < before_legend * 0.97,
                  (before_legend, distance(page)))
            page.mouse.wheel(0, 320)
            page.wait_for_timeout(240)

        # ---- zoom buttons and model framing ----
        page.get_by_role('button', name='放大', exact=True).click()
        page.wait_for_timeout(220)
        plus = distance(page)
        check('zoom-in button dollies closer', plus < after_out, (after_out, plus))
        page.get_by_role('button', name='缩小', exact=True).click()
        page.wait_for_timeout(220)
        minus = distance(page)
        check('zoom-out button dollies further', minus > plus, (plus, minus))
        page.get_by_role('button', name='适配模型', exact=True).click()
        page.wait_for_timeout(400)
        framed = state(page)['scene']
        report['fit_model'] = {'distance': framed['cameraDistance'], 'viewport': framed['viewport'],
                               'links': list(framed['linkPoints'].values())}
        box = canvas_box(page)
        check('适配模型 frames the robot, not a floor-sized box', framed['cameraDistance'] < 3.5,
              framed['cameraDistance'])
        check('适配模型 keeps every robot link on screen',
              all(inside(point, box) for point in framed['linkPoints'].values()))

        # ---- 恢复全景 includes visible scene objects ----
        layer_button = page.get_by_role('button', name='图层选项', exact=True)
        layer_button.click()
        check('layer menu lists scene object toggle', page.get_by_role('checkbox', name='显示场景对象').is_checked())
        page.get_by_role('button', name='恢复全景', exact=True).click()
        page.wait_for_timeout(400)
        scene_view = state(page)['scene']
        box = canvas_box(page)
        check('恢复全景 keeps the robot on screen',
              all(inside(point, box) for point in scene_view['linkPoints'].values()))
        check('恢复全景 includes scene objects',
              'target_cube' in scene_view['worldPoints'] and inside(scene_view['worldPoints']['target_cube'], box))
        layer_button.click()

        # ---- focus selection ----
        page.locator('[data-object="link4"]').click()
        page.wait_for_timeout(120)
        target_before = state(page)['scene']['cameraTarget']
        page.get_by_role('button', name='聚焦选中对象', exact=True).click()
        page.wait_for_timeout(350)
        focused = state(page)['scene']
        check('聚焦选中对象 moves the orbit pivot', focused['cameraTarget'] != target_before)
        check('聚焦选中对象 keeps the same renderer and selection',
              focused['instanceId'] == base_instance and focused['selected'] == 'link4')

        # ---- camera naming follows the chassis axes ----
        page.get_by_role('button', name='车头', exact=True).click()
        page.wait_for_timeout(250)
        front = camera_vector(page)
        page.get_by_role('button', name='车侧', exact=True).click()
        page.wait_for_timeout(250)
        side = camera_vector(page)
        page.get_by_role('button', name='顶视', exact=True).click()
        page.wait_for_timeout(250)
        top = camera_vector(page)
        norm = lambda v: [round(x / (sum(y * y for y in v) ** 0.5), 3) for x in v]
        report['camera_axes'] = {'front': norm(front), 'side': norm(side), 'top': norm(top)}
        check('车头 looks along world_sim +X', abs(norm(front)[0]) > 0.95)
        check('车侧 looks along world_sim -Y', abs(norm(side)[2]) > 0.95)
        check('顶视 looks down world_sim +Z', abs(norm(top)[1]) > 0.95)
        page.get_by_role('button', name='恢复全景', exact=True).click()
        page.wait_for_timeout(300)

        # ---- Dockview sash drag: sizes, aspect, same renderer ----
        sash_info = page.evaluate("""()=>{
          return [...document.querySelectorAll('.dv-sash')].map(e=>{const r=e.getBoundingClientRect();
            return {x:r.x,y:r.y,w:r.width,h:r.height,cx:r.x+r.width/2,cy:r.y+r.height/2}});}""")
        hierarchy_width = state(page)['ui']['panels']['hierarchy']['width']
        vertical = [row for row in sash_info if row['h'] > 120 and row['w'] <= 8]
        check('vertical sash is present for the left column', len(vertical) > 0)
        viewport_before = state(page)['scene']['viewport']
        # leftmost vertical sash separates the hierarchy column from the viewport
        chosen = min(vertical, key=lambda row: row['cx'])
        page.mouse.move(chosen['cx'], chosen['cy'])
        page.mouse.down()
        page.mouse.move(chosen['cx'] + 60, chosen['cy'], steps=12)
        page.mouse.up()
        page.wait_for_timeout(350)
        dragged = state(page)
        report['sash'] = {'hierarchy_before': hierarchy_width,
                          'hierarchy_after': dragged['ui']['panels']['hierarchy']['width'],
                          'viewport_before': viewport_before, 'viewport_after': dragged['scene']['viewport']}
        check('sash drag widens the left column',
              dragged['ui']['panels']['hierarchy']['width'] >= hierarchy_width + 25,
              (hierarchy_width, dragged['ui']['panels']['hierarchy']['width']))
        check('sash drag resizes the viewport without a new renderer',
              dragged['scene']['instanceId'] == base_instance)
        aspect_ok = abs(dragged['scene']['cameraAspect'] - dragged['scene']['viewport']['width'] / dragged['scene']['viewport']['height']) < 0.02
        check('camera aspect follows the sash-dragged viewport', aspect_ok,
              (dragged['scene']['cameraAspect'], dragged['scene']['viewport']))

        # ---- horizontal sash: sensor strip height is adjustable ----
        horizontal = [row for row in page.evaluate(
            "()=>[...document.querySelectorAll('.dv-sash')].map(e=>{const r=e.getBoundingClientRect();"
            "return {cx:r.x+r.width/2,cy:r.y+r.height/2,w:r.width,h:r.height}})") if row['w'] > 120 and row['h'] <= 8]
        check('horizontal sash is present above the sensor strip', len(horizontal) > 0)
        if horizontal:
            sensor_row = min(horizontal, key=lambda row: row['cy'])
            sensors_before = state(page)['ui']['panels']['sensors']['height']
            page.mouse.move(sensor_row['cx'], sensor_row['cy'])
            page.mouse.down()
            page.mouse.move(sensor_row['cx'], sensor_row['cy'] - 30, steps=10)
            page.mouse.up()
            page.wait_for_timeout(350)
            sensors_after = state(page)['ui']['panels']['sensors']['height']
            report['sash_horizontal'] = {'before': sensors_before, 'after': sensors_after}
            check('horizontal sash changes the sensor strip height',
                  sensors_after is not None and sensors_after >= sensors_before + 15,
                  (sensors_before, sensors_after))
            check('horizontal sash keeps the renderer and aspect',
                  state(page)['scene']['instanceId'] == base_instance
                  and abs(state(page)['scene']['cameraAspect']
                          - state(page)['scene']['viewport']['width'] / state(page)['scene']['viewport']['height']) < 0.02)

        # ---- in-app maximize / restore ----
        before_max = state(page)
        page.get_by_role('button', name='最大化视口', exact=True).click()
        page.wait_for_timeout(600)
        maximized = state(page)
        report['maximize'] = {'before': before_max['scene']['viewport'], 'after': maximized['scene']['viewport'],
                              'aspect': maximized['scene']['cameraAspect'], 'distance': maximized['scene']['cameraDistance']}
        check('应用内最大化 grows the 3D viewport',
              maximized['scene']['viewport']['height'] >= before_max['scene']['viewport']['height'] + 80)
        check('应用内最大化 keeps the same renderer and camera',
              maximized['scene']['instanceId'] == base_instance
              and abs(maximized['scene']['cameraDistance'] - before_max['scene']['cameraDistance']) < 1e-6)
        check('应用内最大化 keeps selection and target state',
              maximized['selected'] == before_max['selected'] and maximized['target'] == before_max['target'])
        check('应用内最大化 updates the camera aspect',
              abs(maximized['scene']['cameraAspect'] - maximized['scene']['viewport']['width'] / maximized['scene']['viewport']['height']) < 0.02)
        check('应用内最大化 is reflected by the button state',
              page.get_by_role('button', name='还原视口', exact=True).is_visible())
        # Same renderer must keep receiving Actual and answering handle picks.
        snapshots_at_max = maximized['monitor']['snapshots']
        page.wait_for_function(
            f'window.__workbenchInspect().monitor.snapshots >= {snapshots_at_max + 1}', timeout=8000)
        check('应用内最大化 keeps the Actual subscription alive',
              state(page)['monitor']['snapshots'] > snapshots_at_max
              and state(page)['scene']['instanceId'] == base_instance)
        page.get_by_role('button', name='TCP', exact=True).click()
        page.wait_for_timeout(200)
        maximized_handle = state(page)['scene']['handles'].get('x')
        check('应用内最大化 keeps TCP handles projected', maximized_handle is not None)
        if maximized_handle:
            page.mouse.move(maximized_handle['x'], maximized_handle['y'])
            page.mouse.down()
            page.wait_for_timeout(150)
            check('应用内最大化 keeps handle picking aligned',
                  state(page)['scene']['dragging'] is True)
            page.mouse.up()
            page.wait_for_timeout(120)
        page.get_by_role('button', name='选择', exact=True).click()
        page.get_by_role('button', name='还原视口', exact=True).click()
        page.wait_for_timeout(500)
        restored = state(page)
        check('还原视口 returns to the docked size and same renderer',
              restored['scene']['instanceId'] == base_instance
              and abs(restored['scene']['viewport']['height'] - before_max['scene']['viewport']['height']) < 24)

        # ---- local target survives layout transitions ----
        page.get_by_role('button', name='TCP', exact=True).click()
        position = state(page)['actual']['tcp']['position_m']
        x_input = page.get_by_role('spinbutton', name='TCP X', exact=True)
        x_input.fill(str(round(position[0] + 0.02, 5)))
        x_input.press('Tab')
        page.wait_for_function('window.__workbenchInspect().target && window.__workbenchInspect().target.mode==="tcp"')
        revision = state(page)['target']['revision']

        # ---- browser fullscreen ----
        fs = enter_fullscreen(page)
        report['fullscreen'] = {'doc': fs}
        if fs['active']:
            fs_state = state(page)
            report['fullscreen']['viewport'] = fs_state['scene']['viewport']
            report['fullscreen']['aspect'] = fs_state['scene']['cameraAspect']
            check('全屏 keeps the same renderer and local target',
                  fs_state['scene']['instanceId'] == base_instance and fs_state['target']['revision'] == revision)
            check('全屏 grows the viewport and updates aspect',
                  fs_state['scene']['viewport']['height'] > restored['scene']['viewport']['height']
                  and abs(fs_state['scene']['cameraAspect'] - fs_state['scene']['viewport']['width'] / fs_state['scene']['viewport']['height']) < 0.02)
            check('全屏 keeps source, status and target entry points visible',
                  page.locator('.viewport-hud .hud-chip.target').is_visible()
                  and page.get_by_role('button', name='取消本地目标').is_visible())
            page.get_by_role('button', name='图层选项', exact=True).click()
            menu = page.locator('.layer-menu').bounding_box()
            check('全屏 keeps popovers inside the fullscreen viewport',
                  menu is not None and menu['y'] >= 0 and menu['y'] + menu['height'] <= fs_state['scene']['viewport']['height'] + 60)
            page.get_by_role('button', name='图层选项', exact=True).click()
            # Esc is the browser's own fullscreen exit; it must not delete the draft.
            canvas_size = canvas_box(page)
            page.locator('.canvas-host canvas').click(position={'x': canvas_size['width'] - 30, 'y': canvas_size['height'] - 80})
            page.keyboard.press('Escape')
            page.wait_for_timeout(600)
            after_esc = page.evaluate('()=>!!document.fullscreenElement')
            post_esc = state(page)
            report['fullscreen']['esc_exit'] = {'fullscreen': after_esc, 'target': brief(post_esc['target']),
                                               'orbit': post_esc['scene']['orbitEnabled']}
            check('Esc while fullscreen does not clear the local target',
                  post_esc['target'] is not None and post_esc['target']['revision'] == revision)
            check('Esc leaves Orbit usable', post_esc['scene']['orbitEnabled'] is True)
            if after_esc:
                exit_fullscreen(page)
            check('exit fullscreen restores the docked viewport',
                  state(page)['scene']['viewport']['height'] < fs_state['scene']['viewport']['height'])
            check('exit fullscreen keeps the local target',
                  state(page)['target'] is not None and state(page)['target']['revision'] == revision)
        else:
            reason = page.locator('.layout-warning')
            report['fullscreen']['reason'] = reason.inner_text() if reason.count() else ''
            check('unsupported fullscreen states a real reason', bool(report['fullscreen']['reason'].strip()))
            check('unsupported fullscreen does not fake success', state(page)['ui']['fullscreen'] is False)

        # ---- layout presets ----
        page.get_by_role('button', name='3D 专注', exact=True).click()
        page.wait_for_timeout(700)
        focus = state(page)
        report['preset_focus'] = {'panels': focus['ui']['panels'], 'viewport': focus['scene']['viewport'],
                                  'nav': page.evaluate("()=>document.querySelector('.side-nav').getBoundingClientRect().width")}
        check('3D 专注 closes media and timeline panels',
              focus['ui']['panels']['sensors']['open'] is False and focus['ui']['panels']['timeline']['open'] is False)
        check('3D 专注 maximizes the 3D viewport',
              focus['ui']['maximized'] is True and focus['scene']['viewport']['height'] > restored['scene']['viewport']['height'])
        check('3D 专注 collapses the navigation rail', report['preset_focus']['nav'] <= 60)
        page.screenshot(path=str(a.output / 'usability-focus3d.png'), full_page=True)
        check('3D 专注 keeps one renderer and the local target',
              focus['scene']['instanceId'] == base_instance and focus['target']['revision'] == revision)
        page.get_by_role('button', name='标准工作台', exact=True).click()
        page.wait_for_timeout(700)
        standard = state(page)
        check('标准工作台 restores every panel',
              all(standard['ui']['panels'][key]['open'] for key in ('hierarchy', 'inspector', 'sensors', 'timeline')))
        check('标准工作台 leaves maximize mode',
              standard['ui']['maximized'] is False and standard['scene']['viewport']['height'] < focus['scene']['viewport']['height'])
        check('layout preset switches keep the renderer and target',
              standard['scene']['instanceId'] == base_instance and standard['target']['revision'] == revision)

        # ---- panel collapse / restore ----
        page.get_by_role('button', name='传感器视图', exact=True).click()
        page.wait_for_timeout(500)
        collapsed = state(page)
        check('传感器面板 can be collapsed', collapsed['ui']['panels']['sensors']['open'] is False)
        check('collapsing a panel grows the viewport without a new renderer',
              collapsed['scene']['viewport']['height'] > standard['scene']['viewport']['height']
              and collapsed['scene']['instanceId'] == base_instance)
        page.get_by_role('button', name='传感器视图', exact=True).click()
        page.wait_for_timeout(500)
        check('传感器面板 can be restored', state(page)['ui']['panels']['sensors']['open'] is True)

        # ---- save / restore layout does not change runtime state ----
        page.get_by_role('button', name='保存', exact=True).click()
        page.get_by_role('button', name='Inspector', exact=True).click()
        page.wait_for_timeout(400)
        check('Inspector can be collapsed before restore', state(page)['ui']['panels']['inspector']['open'] is False)
        page.get_by_role('button', name='恢复', exact=True).click()
        page.wait_for_timeout(600)
        after_restore = state(page)
        report['layout_restore'] = {'target': brief(after_restore['target']), 'camera': after_restore['scene']['camera'],
                                    'instance': after_restore['scene']['instanceId'],
                                    'standard_camera': standard['scene']['camera'],
                                    'standard_target': brief(standard['target'])}
        check('布局恢复 reopens the saved panels', after_restore['ui']['panels']['inspector']['open'] is True)
        check('布局恢复 keeps renderer, camera and target',
              after_restore['scene']['instanceId'] == base_instance
              and after_restore['target']['revision'] == revision
              and max(abs(now - before) for now, before in zip(after_restore['scene']['camera'], standard['scene']['camera'])) < 1e-6,
              (after_restore['scene']['instanceId'], after_restore['target']['revision'], revision,
               after_restore['scene']['camera'], standard['scene']['camera']))

        # ---- continuous TCP drag across two live Actual refreshes ----
        page.get_by_role('button', name='恢复全景', exact=True).click()
        page.wait_for_timeout(300)
        fresh = state(page)
        handle = fresh['scene']['handles']['x']
        start_x = fresh['target']['tcpWorldM'][0]
        snapshots_before = fresh['monitor']['snapshots']
        camera_before = fresh['scene']['camera']
        panels_before = json.dumps(fresh['ui']['panels'], sort_keys=True)
        page.mouse.move(handle['x'], handle['y'])
        page.mouse.down()
        dragged_samples = []
        for step in range(1, 9):
            page.mouse.move(handle['x'] + step * 4, handle['y'], steps=2)
            page.wait_for_timeout(280)
            dragged_samples.append(state(page))
        still_dragging = state(page)['scene']['dragging']
        page.mouse.up()
        page.wait_for_timeout(300)
        final = state(page)
        actual_delta = max(abs(now - before) for now, before in zip(
            final['actual']['tcp']['position_m'], fresh['actual']['tcp']['position_m']))
        report['tcp_continuous_drag'] = {
            'snapshots_before': snapshots_before, 'snapshots_after': final['monitor']['snapshots'],
            'dragging_throughout': still_dragging, 'target_x': [sample['target']['tcpWorldM'][0] for sample in dragged_samples],
            'camera_stable': final['scene']['camera'] == camera_before, 'actual_delta_m': actual_delta}
        check('TCP drag stays active across live Actual refreshes',
              still_dragging and final['monitor']['snapshots'] >= snapshots_before + 2,
              (still_dragging, snapshots_before, final['monitor']['snapshots']))
        check('TCP drag moves the local target only',
              final['target']['tcpWorldM'][0] > start_x + 0.002 and actual_delta < 1e-4,
              (start_x, final['target']['tcpWorldM'][0], actual_delta))
        check('TCP drag during polling does not orbit the camera', final['scene']['camera'] == camera_before)
        check('TCP drag does not reflow the panel layout',
              json.dumps(final['ui']['panels'], sort_keys=True) == panels_before)

        # ---- 1920x1080 ----
        page.set_viewport_size({'width': 1920, 'height': 1080})
        page.wait_for_timeout(700)
        big = state(page)
        big_metrics = page.evaluate("""()=>{const c=document.querySelector('.canvas-host canvas').getBoundingClientRect();
          return {w:c.width,h:c.height,scrollH:document.documentElement.scrollHeight,innerH:window.innerHeight}}""")
        report['sizes']['1920x1080'] = big_metrics
        page.screenshot(path=str(a.output / 'usability-1920.png'), full_page=True)
        check('1920x1080 canvas is large (>=500px tall)', big_metrics['h'] >= 500, big_metrics['h'])
        check('1920x1080 keeps aspect and renderer',
              abs(big['scene']['cameraAspect'] - big['scene']['viewport']['width'] / big['scene']['viewport']['height']) < 0.02
              and big['scene']['instanceId'] == base_instance)
        box = canvas_box(page)
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        d0 = distance(page)
        page.mouse.wheel(0, -300)
        page.wait_for_timeout(250)
        check('1920x1080 wheel zoom works', distance(page) < d0 * 0.97, (d0, distance(page)))
        page.get_by_role('button', name='最大化视口', exact=True).click()
        page.wait_for_timeout(600)
        check('1920x1080 in-app maximize works',
              state(page)['scene']['viewport']['height'] > big['scene']['viewport']['height'])
        page.get_by_role('button', name='还原视口', exact=True).click()
        page.wait_for_timeout(400)

        # ---- 125% page zoom (CSS viewport 1093x614, DPR 1.25) ----
        zoom_context = browser.new_context(viewport={'width': 1093, 'height': 614}, device_scale_factor=1.25)
        zoom_page = zoom_context.new_page()
        zoom_page.on('pageerror', lambda error: errors.append('zoom:' + str(error)))
        zoom_page.goto(a.url + '/?inspect=1', wait_until='networkidle')
        loaded(zoom_page)
        zoom_page.wait_for_timeout(600)
        # Short CSS viewports start in 3D focus; measure the standard layout.
        if zoom_page.get_by_role('button', name='还原视口', exact=True).count():
            zoom_page.get_by_role('button', name='标准工作台', exact=True).click()
            zoom_page.wait_for_timeout(600)
        zoom_metrics = zoom_page.evaluate("""()=>{const c=document.querySelector('.canvas-host canvas').getBoundingClientRect();
          const s=document.querySelector('.status-bar').getBoundingClientRect();
          return {w:c.width,h:c.height,statusBottom:s.bottom,innerH:window.innerHeight,
            scrollH:document.documentElement.scrollHeight,dpr:window.devicePixelRatio,
            preset:document.querySelector('.application').className}}""")
        report['sizes']['125_percent'] = zoom_metrics
        check('125% zoom keeps the page inside the viewport',
              zoom_metrics['statusBottom'] <= zoom_metrics['innerH'] + 1 and zoom_metrics['scrollH'] <= zoom_metrics['innerH'] + 1,
              zoom_metrics)
        check('125% zoom keeps a usable 3D canvas', zoom_metrics['h'] >= 150, zoom_metrics['h'])
        for name in ('放大', '最大化视口', '浏览器全屏', '标准工作台', '3D 专注'):
            check(f'125% zoom keeps {name} reachable', visible_button(zoom_page, name))
        zoom_page.get_by_role('button', name='最大化视口', exact=True).click()
        zoom_page.wait_for_timeout(600)
        zoom_state = state(zoom_page)
        check('125% zoom in-app maximize works and updates aspect',
              zoom_state['scene']['viewport']['height'] > zoom_metrics['h']
              and abs(zoom_state['scene']['cameraAspect'] - zoom_state['scene']['viewport']['width'] / zoom_state['scene']['viewport']['height']) < 0.02)
        zoom_page.screenshot(path=str(a.output / 'usability-125.png'), full_page=True)
        zoom_context.close()

        # ---- network and error boundary ----
        bad = [r for r in requests if r['method'] != 'GET']
        check('browser issued GET requests only', not bad, bad[:3])
        external = [r for r in requests if '/api/v1/' in r['url'] and not r['url'].split('?')[0].endswith(
            ('/mobilecar/scene', '/mobilecar/capabilities', '/mobilecar/snapshot')) and '/scene/assets/' not in r['url']]
        check('no motion/RESET/recording endpoints were called', not external, external[:3])
        check('no uncaught browser errors', not errors, errors[:3])

        report['status'] = 'passed'
        report['request_count'] = len(requests)
        report['base_instance'] = base_instance
    except Exception as exc:
        import traceback
        report['status'] = 'failed'
        report['exception'] = str(exc)
        report['traceback'] = traceback.format_exc()
        try:
            page.screenshot(path=str(a.output / 'failure.png'), full_page=True)
        except Exception:
            pass
    finally:
        (a.output / 'usability.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        browser.close()

print(json.dumps({'status': report['status'], 'checks': len(checks), 'error': report.get('exception')}, ensure_ascii=False))
raise SystemExit(report['status'] != 'passed')
