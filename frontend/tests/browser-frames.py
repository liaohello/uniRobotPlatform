"""frame-link-1 frame browsing acceptance: image ↔ linked robot state ↔ provenance and time.

  --mode real       against a frontend preview whose upstream is the frame-link candidate (18966).
                    Reads the actual COMPLETE and FAILED records, compares every displayed value with
                    a direct GET of the same page, walks pages by next_offset/has_more, opens a frame
                    by sample_id, applies a contract-allowed time window, and exercises the
                    has_more/next_offset pagination gap the backend documents. Only GET requests are
                    issued; the archive itself is never written.
  --mode synthetic  the same product code against isolated page.route fixtures (synthetic data, never
                    the archive): empty selectable_time_bases, absent/refused media, digest mismatch,
                    non-image bytes, a state that is missing, a late frame page after a switch,
                    contract-mismatch payloads, stream-unavailable and invalid sample ids, plus UI
                    cadence wording.

Both modes assert that the browser issues no non-GET request, that the gateway carries the frames GET
as its own exact route (no wildcard under /episodes/{id}/), that the pane never claims 3D replay,
cross-stream sync or a total frame count, and that live polling never rewrites the frame DOM.
"""
import argparse, asyncio, json, re, struct, traceback, zlib
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from playwright.async_api import async_playwright

p = argparse.ArgumentParser()
p.add_argument('url'); p.add_argument('output', type=Path)
p.add_argument('--mode', choices=('real', 'synthetic'), default='real')
p.add_argument('--complete-run', default='run_0104613ff7364ae78cf2f3946bd45f7b')
p.add_argument('--complete-episode', default='episode_27bfed5427684795b361cd2ec21e9aa7')
p.add_argument('--failed-run', default='run_1f6fb34853f94130aadedb8fa486705b')
p.add_argument('--failed-episode', default='episode_879cf70489064a3b83bb15b5395a8341')
a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
report = {'scope': f'{a.mode} frame-link-1 browsing acceptance against {a.url}', 'mode': a.mode,
          'checks': [], 'errors': [], 'requests': [], 'real': {}, 'status': 'failed'}
SOURCE_ID = 'mobilecar-server-history-20261017'
FRAME_SCHEMA = 'unirobot-mobilecar-frame-link-1'
READ_SCHEMA = 'unirobot-mobilecar-episode-read-1'


def tiny_png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\x11\x22\x33')) + chunk(b'IEND', b''))


def check(name, condition, detail=None):
    if not condition: raise AssertionError(name if detail is None else f'{name} :: {detail}')
    report['checks'].append(name)


async def attr(page, selector, name):
    return await page.locator(selector).first.get_attribute(name)


async def attr_all(page, selector, name):
    return await page.locator(selector).evaluate_all(f'els=>els.map(e=>e.getAttribute("{name}"))')


async def count(page, selector):
    return await page.locator(selector).count()


async def open_history(page):
    await page.goto(a.url + '/', wait_until='domcontentloaded')
    await page.wait_for_selector('.side-nav button', timeout=60000)
    await page.get_by_role('button', name='历史 Episode', exact=True).click()
    await page.wait_for_selector('.history-view[data-history-view="true"]', timeout=20000)


async def wait_list(page, state='ready'):
    await page.wait_for_selector(f'.history-list-pane[data-list-state="{state}"]', timeout=40000)


async def wait_frames(page, predicate=None, timeout=60000):
    expr = predicate or "()=>document.querySelector('[data-frame-view=\"true\"][data-frame-bound=\"true\"]')"
    await page.wait_for_function(expr, timeout=timeout)


async def read_direct(page, path, params=None):
    url = a.url + path
    if params: url += '?' + '&'.join(f'{k}={v}' for k, v in params.items())
    return await (await page.request.get(url)).json()


async def wait_asset_settled(page, timeout=40000):
    """Bytes, a refusal or a decode failure are all settled states; 'loading' and 'idle' are not, so
    no assertion ever races the asset request or the image decode."""
    await page.wait_for_function("()=>['bytes','failed','not-loaded'].includes((document.querySelector('[data-frame-asset-status]')?.getAttribute('data-frame-asset-status') ?? ''))", timeout=timeout)


async def wait_asset_uri(page, uri, timeout=40000):
    await page.wait_for_function("(uri)=>(document.querySelector('[data-frame-asset-uri]')?.getAttribute('data-frame-asset-uri') ?? '')===uri", arg=uri, timeout=timeout)


async def open_episode(page, run_id, episode_id, expect='frames'):
    """The frame pane keeps the previous Episode’s page on screen until its own read lands, so every
    step waits for the pane to be bound to *this* identity (or to show this identity’s error)."""
    await page.locator('input[aria-label="run_id 筛选"]').fill(run_id)
    await page.get_by_role('button', name='重新读取首页').click()
    await wait_list(page)
    await page.wait_for_selector(f'[data-episode-open="{episode_id}"]', timeout=30000)
    await page.locator(f'[data-episode-open="{episode_id}"]').click()
    await page.wait_for_selector(f'.history-detail-pane dl[data-detail-run="{run_id}"]', timeout=40000)
    if expect == 'frames':
        await wait_frames(page, f"()=>{{const v=document.querySelector('[data-frame-view]');return !!v && v.getAttribute('data-frame-episode')==='{episode_id}' && v.getAttribute('data-frame-bound')==='true';}}")
    else:
        await wait_frames(page, f"()=>{{const v=document.querySelector('[data-frame-view]');return !!v && v.getAttribute('data-frame-episode')==='{episode_id}' && !!v.querySelector('[data-frame-error]');}}")


def page_attrs(page):
    """Everything the frame pane asserts on, read in one DOM pass so comparisons stay consistent."""
    return page.evaluate("""()=>{const g=(s,n)=>document.querySelector(s)?.getAttribute(n)??null;
      const q=(s,n)=>[...document.querySelectorAll(s)].map(e=>e.getAttribute(n));
      return {bound:g('[data-frame-view]','data-frame-bound'),schema:g('[data-frame-view]','data-frame-schema'),
        episode:g('[data-frame-view]','data-frame-episode'),run:g('[data-frame-view]','data-frame-run'),
        currentSample:g('[data-frame-current-sample]','data-frame-current-sample'),
        returned:g('[data-frame-returned]','data-frame-returned'),offset:g('[data-frame-offset]','data-frame-offset'),
        nextOffset:g('[data-frame-next-offset]','data-frame-next-offset'),hasMore:g('[data-frame-has-more]','data-frame-has-more'),
        scanned:g('[data-frame-scanned]','data-frame-scanned'),pageKind:g('[data-frame-page-kind]','data-frame-page-kind'),
        index:g('[data-frame-index]','data-frame-index'),line:g('[data-frame-line]','data-frame-line'),
        persistSeq:g('[data-frame-persist-seq]','data-frame-persist-seq'),linkage:g('[data-frame-linkage-status]','data-frame-linkage-status'),
        declaredRef:g('[data-frame-declared-ref]','data-frame-declared-ref'),stateStatus:g('[data-frame-state-status]','data-frame-state-status'),
        eventSeq:g('[data-frame-event-seq]','data-frame-event-seq'),recordPosition:g('[data-frame-record-position]','data-frame-record-position'),
        ageMs:g('[data-age-ms]','data-age-ms'),sameClock:g('[data-same-clock-verified]','data-same-clock-verified'),
        selectable:(g('[data-frame-selectable-bases]','data-frame-selectable-bases')||'').split(',').filter(Boolean),
        windowBase:g('[data-frame-window-base]','data-frame-window-base'),windowFrom:g('[data-frame-window-from]','data-frame-window-from'),
        windowTo:g('[data-frame-window-to]','data-frame-window-to'),contextSample:g('[data-frame-context-sample]','data-frame-context-sample'),
        windowGate:g('[data-frame-window-gate]','data-frame-window-gate'),windowReason:g('[data-frame-window-reason]','data-frame-window-reason'),
        notice:document.querySelector('[data-frame-notice]')?.innerText??null,error:document.querySelector('[data-frame-error]')?.innerText??null,
        explanation:g('[data-frame-page-explanation]','data-frame-page-explanation'),
        linkageScope:g('[data-frame-linkage-scope]','data-frame-linkage-scope'),
        assetUri:g('[data-frame-asset-uri]','data-frame-asset-uri'),assetStatus:g('[data-frame-asset-status]','data-frame-asset-status'),
        assetSha:g('[data-frame-asset-sha]','data-frame-asset-sha'),assetDeclared:g('[data-frame-asset-declared]','data-frame-asset-declared'),
        assetMatch:g('[data-frame-asset-digest-match]','data-frame-asset-digest-match'),assetDecoded:g('[data-frame-asset-decoded]','data-frame-asset-decoded'),
        assetField:g('[data-frame-asset-field]','data-frame-asset-field'),assetSample:g('[data-frame-asset-sample]','data-frame-asset-sample'),
        assetMediaType:g('[data-frame-asset-media-type]','data-frame-asset-media-type'),assetBytes:g('[data-frame-asset-bytes]','data-frame-asset-bytes'),
        threeD:g('[data-3d-disabled]','data-3d-disabled'),liveGeometry:g('[data-live-geometry-applied]','data-live-geometry-applied'),
        transformsPose:g('[data-transforms-full-pose]','data-transforms-full-pose'),notProven:g('[data-not-proven]','data-not-proven'),
        rowSamples:q('[data-frame-row]','data-frame-row'),rowStatuses:q('[data-frame-row]','data-row-status'),
        rowDeclaredRefs:q('[data-frame-row]','data-row-declared-ref'),rowLines:q('[data-frame-row]','data-row-line'),
        rowMedia:q('[data-frame-row]','data-row-media'),roles:q('[data-frame-role]','data-frame-role'),
        rolePrimaries:q('[data-frame-role]','data-role-primary'),roleStatuses:q('[data-frame-role]','data-role-status'),
        stateKeys:q('[data-state-row]','data-state-row'),stateUnits:q('[data-state-row]','data-state-unit'),
        deltaLabels:q('[data-delta-row]','data-delta-row'),
        mediaFields:q('[data-frame-media-ref]','data-media-field'),mediaAvailability:q('[data-frame-media-ref]','data-media-availability'),
        provenance:q('[data-provenance-row]','data-provenance-row'),
        text:document.querySelector('[data-frame-view]')?.innerText??''};}""")


def state_of(frame):
    return frame['state']


# ---- real --------------------------------------------------------------------------------------------

async def real_flow(page):
    await wait_list(page)
    await open_episode(page, a.complete_run, a.complete_episode)
    direct = await read_direct(page, f'/api/v1/episodes/{a.complete_episode}/frames', {'run_id': a.complete_run, 'limit': 5, 'offset': 0})
    check('the pane reads frame-link-1 and binds it to the same source/run/episode identity as the detail',
          direct['schema_version'] == FRAME_SCHEMA and direct['read_only'] is True
          and (await page_attrs(page))['schema'] == FRAME_SCHEMA
          and await attr(page, '[data-frame-episode]', 'data-frame-episode') == a.complete_episode
          and await attr(page, '[data-frame-run]', 'data-frame-run') == a.complete_run
          and a.complete_run in await page.locator('[data-provenance-row="identity"]').inner_text()
          and direct['source']['source_id'] == SOURCE_ID and direct['source']['platform_writes'] is False)
    first = direct['frames'][0]
    view = await page_attrs(page)
    check('page counters come from the reader and the pane states no total anywhere',
          [view['returned'], view['offset'], view['nextOffset'], view['hasMore']] == [str(len(direct['frames'])), '0', str(direct['paging']['next_offset']), 'true']
          and view['scanned'] == str(direct['paging']['scanned_anchor_lines'])
          and await attr(page, '[data-frame-no-total]', 'data-frame-no-total') == 'true'
          and not re.search(r'共\s*\d+\s*帧', view['text']), view)
    check('the anchor is one persisted frame per record and the line index is declared not to be a clock',
          view['rowLines'] == [str(f['anchor']['line_index']) for f in direct['frames']]
          and await attr(page, '[data-frame-line-index-clock]', 'data-frame-line-index-clock') == 'true'
          and await attr(page, '[data-frame-persist-counter]', 'data-frame-persist-counter') == 'true'
          and await attr(page, '[data-frame-anchor]', 'data-frame-anchor') == direct['anchor']['relative_path'])
    check('four primary roles matched while the declared feedback reference stays unresolved',
          view['rowStatuses'] == [f['linkage_status'] for f in direct['frames']]
          and all(status == 'matched' for status in view['rowStatuses'])
          and all(ref == 'unresolved_reference' for ref in view['rowDeclaredRefs'])
          and view['rolePrimaries'] == ['true', 'true', 'true', 'true', 'false']
          and view['roleStatuses'] == ['matched', 'matched', 'matched', 'matched', 'unresolved_reference']
          and '不等于完全没有机器人状态' in (await page.locator('[data-frame-role="feedback_observation_row"]').inner_text()), view['roleStatuses'])
    check('the unresolved reference does not empty the state panel: recorded_state is displayed with units',
          set(view['stateKeys']) == set(state_of(first)['recorded_state'].keys()), view['stateKeys'])
    qpos_text = await page.locator('[data-state-row="arm_model_qpos_rad"]').inner_text()
    check('a model joint angle is labelled as a model joint angle, never as a user command or calibration',
          '机械臂模型关节角' in qpos_text and '不是用户控制角' in qpos_text and '不是标定结果' in qpos_text
          and 'radians' in (await attr(page, '[data-state-row="arm_model_qpos_rad"]', 'data-state-unit')), qpos_text[:200])
    base_text = await page.locator('[data-state-row="base_position_world_sim_m"]').inner_text()
    check('chassis pose and gripper/TCP fields keep the reader’s own value wording',
          '底盘位置' in base_text and '10145992864392481' in base_text and '-0.00023473557897040777' in base_text
          and await count(page, '[data-state-row="gripper_width_m"]') == 1
          and await count(page, '[data-state-row="tcp_position_world_m"]') == 1
          and '不是发送过的指令位置' in base_text, base_text[:200])
    check('the state provenance shows join key, event_seq and the record position of the hit',
          view['eventSeq'] == str(first['state']['source']['event_seq'])
          and view['recordPosition'] == f"{first['state']['source']['relative_path']}#{first['state']['source']['line_index']}"
          and first['state']['join_key'] in view['text'] and first['state']['key_value'] in view['text'], (view['eventSeq'], view['recordPosition']))
    age = first['times']['age_of_state_relative_to_frame']
    state_delta = next(delta for delta in first['times']['deltas'] if delta['label'] == 'state_event_minus_frame_capture')
    check('the millisecond value is shown as a linkage time difference, not a sampling latency, with raw values kept',
          view['ageMs'] == str(age['abs_ms']) and view['sameClock'] == 'false'
          and '关联状态事件时间差' in view['text'] and '不是物理状态采样延迟' in view['text']
          and '不是同步证明' in view['text']
          and await attr(page, '[data-delta-row="state_event_minus_frame_capture"]', 'data-delta-capture') == str(state_delta['capture_value'])
          and await attr(page, '[data-delta-row="state_event_minus_frame_capture"]', 'data-delta-other') == str(state_delta['other_value'])
          and set(view['deltaLabels']) == {delta['label'] for delta in first['times']['deltas']}, (view['ageMs'], view['deltaLabels']))
    feedback_time = state_of(first)['recorder_declared_feedback']['feedback_time_s']
    check('the recorder’s raw declared feedback time is listed separately from any difference',
          await attr(page, '[data-feedback-declared-time]', 'data-feedback-declared-time') == str(feedback_time)
          and await attr(page, '[data-feedback-declared-clock]', 'data-feedback-declared-clock') == state_of(first)['recorder_declared_feedback']['feedback_clock']
          and '另列' in (await page.locator('[data-feedback-declared-available]').inner_text()))
    check('clock sameness and cross-stream sync stay declared-not-verified',
          await attr(page, '[data-clock-sameness-verified]', 'data-clock-sameness-verified') == 'false'
          and await attr(page, '[data-frame-sync-streams]', 'data-frame-sync-streams') == 'false'
          and 'naming is not verification' in (await page.locator('[data-clock-sameness-verified]').inner_text()))
    rgb = next(item for item in first['media']['items'] if item['field'] == 'rgb_uri')
    await wait_asset_uri(page, rgb['uri'])
    check('the image is the selected frame’s own rgb reference, served bytes verified against its declaration',
          view['assetUri'] == rgb['uri'] and view['assetField'] == 'rgb_uri' and view['assetStatus'] == 'bytes'
          and view['assetDecoded'] == 'ok' and view['assetMediaType'] == 'image/png'
          and view['assetBytes'] == str(rgb['bytes_on_disk'])
          and (view['assetDeclared'] == 'null' or view['assetDeclared'] in rgb['declared_sha256_by_row'])
          and view['assetMatch'] == str(rgb['declared_sha256_by_row'] is not None).lower()
          and view['assetSample'] == first['sample_id'], (await page_attrs(page))['assetStatus'])
    lines = await page.locator('[data-frame-declared-line]').inner_text(), await page.locator('[data-frame-verified-line]').inner_text(), await page.locator('[data-frame-integrity-line]').inner_text()
    check('declared digest, this-read verification and the integrity conclusion are three separate statements',
          '摘要声明' in lines[0] and '本次读取' in lines[1] and 'sha256' in lines[1] and '完整性结论' in lines[2]
          and '单帧媒体一致不推出整条 Episode 完整' in lines[2], lines[0][:120])
    check('media items are listed exactly as this frame declares them',
          view['mediaFields'] == [item['field'] for item in first['media']['items']]
          and view['mediaAvailability'] == [item['availability'] for item in first['media']['items']])
    prov = view['provenance']
    check('provenance covers source, root boundary, anchor, clocks, profile and per-role positions',
          {'source', 'root', 'identity', 'anchor', 'sample', 'clocks', 'profile', 'state_position', 'role_positions', 'page'} <= set(prov)
          and direct['source']['path_boundary'] in await page.locator('[data-provenance-row="root"]').inner_text()
          and first['anchor']['profile']['profile_id'] in await page.locator('[data-provenance-row="profile"]').inner_text()
          and 'events.jsonl#' in await page.locator('[data-provenance-row="role_positions"]').inner_text())
    check('the 3D and replay boundary is passed through from the response, not softened',
          view['threeD'] == 'true' and view['liveGeometry'] == 'false' and view['transformsPose'] == 'false'
          and 'rendered 3D replay' in view['notProven'] and 'no replay execution' in view['notProven'] + (await attr(page, '[data-capability-limits]', 'data-capability-limits')))

    # Walking pages strictly by next_offset / has_more.
    for _ in range(len(direct['frames']) - 1):
        await page.locator('[data-frame-next]').click()
        await page.wait_for_timeout(120)
    last = direct['frames'][-1]
    check('stepping inside the page moves the cursor and rebinds the image to that frame',
          (await page_attrs(page))['index'] == str(len(direct['frames']) - 1)
          and (await page_attrs(page))['currentSample'] == last['sample_id']
          and (await page_attrs(page))['assetUri'] == next(item for item in last['media']['items'] if item['field'] == 'rgb_uri')['uri'])
    second = await read_direct(page, f'/api/v1/episodes/{a.complete_episode}/frames', {'run_id': a.complete_run, 'limit': 5, 'offset': direct['paging']['next_offset']})
    await page.locator('[data-frame-next]').click()
    await wait_frames(page, f"()=>(document.querySelector('[data-frame-offset]')?.getAttribute('data-frame-offset') ?? '')==='{direct['paging']['next_offset']}'")
    moved = await page_attrs(page)
    check('at the page end the pane advances by the reader’s next_offset and keeps index at the new first frame',
          moved['offset'] == str(second['paging']['offset']) and moved['index'] == '0'
          and moved['currentSample'] == second['frames'][0]['sample_id']
          and moved['rowSamples'] == [f['sample_id'] for f in second['frames']]
          and '行号不是时间轴' in moved['explanation'], (moved['offset'], moved['currentSample']))
    await page.locator('[data-frame-prev]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-offset]')?.getAttribute('data-frame-offset') ?? '')==='0'")
    await wait_asset_uri(page, last['media']['items'][0]['uri'])
    back = await page_attrs(page)
    check('stepping back over a page boundary lands on the previous page’s last frame, not a fabricated one',
          back['offset'] == '0' and back['index'] == str(len(direct['frames']) - 1)
          and back['currentSample'] == last['sample_id'] and back['assetUri'] == last['media']['items'][0]['uri'])

    # Opening by sample_id, then the documented has_more/next_offset gap.
    target = direct['frames'][2]['sample_id']
    await page.locator('input[aria-label="sample_id 精确打开"]').fill(target)
    await page.locator('[data-frame-open-sample]').click()
    await wait_frames(page, f"()=>(document.querySelector('[data-frame-current-sample]')?.getAttribute('data-frame-current-sample') ?? '')==='{target}'")
    await wait_asset_uri(page, direct['frames'][2]['media']['items'][0]['uri'])
    by_sample = await page_attrs(page)
    check('a frame opens by its exact sample_id and the pane says the filter is held by the interface',
          by_sample['returned'] == '1' and by_sample['contextSample'] == target
          and any(f'sample_id={target}' in r['url'] for r in report['requests'])
          and by_sample['assetUri'] == direct['frames'][2]['media']['items'][0]['uri'], by_sample['returned'])
    await page.locator('[data-frame-next]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-returned]')?.getAttribute('data-frame-returned') ?? '')==='0'")
    gap = await page_attrs(page)
    check('the has_more/next_offset gap is reported honestly instead of inventing frames',
          gap['pageKind'] == 'sample-no-match' and gap['returned'] == '0'
          and '混合了候选行计数与锚点原生行号' in gap['notice'] and '不伪造分页结果' in gap['notice']
          and not gap['rowSamples'] and '不声称已遍历全部帧' in gap['notice'], gap['notice'][:200])
    check('an empty page clears the image instead of keeping the previous frame',
          await count(page, '[data-frame-asset-uri]') == 0 and await count(page, '[data-frame-asset-image]') == 0
          and await count(page, '[data-frame-list-empty]') == 1)
    await page.locator('[data-frame-sample-clear]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-returned]')?.getAttribute('data-frame-returned') ?? '')==='5'")

    # A contract-allowed numeric window, then a window that matches nothing.
    capture = direct['frames'][2]['anchor']['clocks']['capture_backend_monotonic_s']
    await page.locator('select[aria-label="帧时间基"]').select_option('capture_backend_monotonic_s')
    await page.locator('input[aria-label="时间窗口起点"]').fill(str(capture - 0.05))
    await page.locator('input[aria-label="时间窗口终点"]').fill(str(capture + 0.05))
    await page.locator('[data-frame-window-apply]').click()
    await wait_frames(page, f"()=>(document.querySelector('[data-frame-window-base]')?.getAttribute('data-frame-window-base') ?? '')==='capture_backend_monotonic_s'")
    windowed = await page_attrs(page)
    direct_window = await read_direct(page, f'/api/v1/episodes/{a.complete_episode}/frames',
                                      {'run_id': a.complete_run, 'limit': 5, 'offset': 0, 'time_base': 'capture_backend_monotonic_s',
                                       'time_from': capture - 0.05, 'time_to': capture + 0.05})
    check('a numeric window is sent as declared seconds and its hits are shown with the exclusion counter',
          windowed['windowBase'] == 'capture_backend_monotonic_s'
          and set(windowed['rowSamples']) <= {f['sample_id'] for f in direct['frames']}
          and windowed['returned'] == str(len(direct_window['frames']))
          and any('time_base=capture_backend_monotonic_s' in r['url'] and 'time_from=' in r['url'] and 'time_to=' in r['url'] for r in report['requests']), windowed['returned'])
    await page.locator('input[aria-label="时间窗口起点"]').fill('1')
    await page.locator('input[aria-label="时间窗口终点"]').fill('2')
    await page.locator('[data-frame-window-apply]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-page-kind]')?.getAttribute('data-frame-page-kind') ?? '')==='window-empty'")
    empty_window = await page_attrs(page)
    check('a window with no frames counts the excluded lines and keeps the window as the active condition',
          empty_window['pageKind'] == 'window-empty' and '空结果页，不是读取错误' in empty_window['explanation']
          and int(re.search(r'excluded_outside_time_window=(\d+)', empty_window['explanation']).group(1)) > 0
          and empty_window['windowBase'] == 'capture_backend_monotonic_s' and await count(page, '[data-frame-asset-uri]') == 0)
    await page.locator('[data-frame-window-clear]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-returned]')?.getAttribute('data-frame-returned') ?? '')==='5'")
    cleared = await page_attrs(page)
    check('clearing the window returns to offset browsing with the reader’s echo dropped',
          cleared['windowBase'] == 'null' and cleared['contextSample'] == 'none'
          and cleared['pageKind'] == 'frames' and len(cleared['rowSamples']) == 5
          and cleared['windowFrom'] == 'null' and cleared['windowTo'] == 'null', cleared['windowBase'])

    # The FAILED / INCOMPLETE record.
    failed = await read_direct(page, f'/api/v1/episodes/{a.failed_episode}/frames', {'run_id': a.failed_run, 'limit': 5, 'offset': 0})
    await open_episode(page, a.failed_run, a.failed_episode)
    await wait_asset_settled(page)
    view = await page_attrs(page)
    check('the incomplete record’s frames are read as the reader returns them',
          failed['paging']['returned'] == len(failed['frames']) and view['returned'] == str(len(failed['frames']))
          and view['rowSamples'] == [f['sample_id'] for f in failed['frames']]
          and 'no-anchor-lines' != view['pageKind'], view['returned'])
    check('every frame of the failed record separates matched primaries from an unresolved reference',
          all(status == 'matched' for status in view['rowStatuses'])
          and all(ref == 'unresolved_reference' for ref in view['rowDeclaredRefs'])
          and f"frames_returned={failed['summary']['frames_returned']}" in view['linkageScope']
          and f"feedback引用未解析={failed['summary']['frames_with_unresolved_feedback_reference']}" in view['linkageScope'].replace(' ', '')
          and state_of(failed['frames'][0])['status'] == view['stateStatus'], view['linkageScope'])
    media = failed['frames'][0]['media']['items']
    check('the failed record’s media is shown with its own availability values, not inferred',
          view['mediaAvailability'] == [item['availability'] for item in media]
          and (view['assetUri'] == media[0]['uri'] if media[0]['availability'] == 'present' else await count(page, '[data-frame-asset-image]') == 0))
    report['real']['complete'] = {'frames': len(direct['frames']), 'sample': first['sample_id'], 'age_ms': age['abs_ms'],
                                  'roles': view['roleStatuses'], 'next_offset': direct['paging']['next_offset']}
    report['real']['failed'] = {'frames': failed['paging']['returned'], 'statuses': view['rowStatuses'], 'declared_refs': view['rowDeclaredRefs']}


# ---- synthetic ---------------------------------------------------------------------------------------

SOURCE_FIXTURE = {'source_id': SOURCE_ID, 'adapter_id': 'mobilecar', 'recording_root': '/fixture', 'access': 'read_only_files', 'platform_writes': False}
SLOW = {'state': 'idle'}


def frame_payload(sample, **patch):
    frame = {
        'sample_id': sample, 'stream_id': 'rgbd',
        'anchor': {'line_index': 0, 'relative_path': 'observations/persist.jsonl', 'persist_sequence': 1,
                   'identity': {'run_id_matches': True, 'episode_id_matches': True, 'declared_run_id': 'run_a', 'declared_episode_id': 'episode_ok'},
                   'clocks': {'capture_backend_monotonic_s': 100.0, 'capture_sim_time_s': 1.0, 'persist_backend_monotonic_s': 100.1},
                   'declared_keys': ['sample_id', 'rgb_uri'], 'reference_keys': {'capture_control_tick_id': 'tick_1', 'feedback_sample_id': 'joint_feedback_1'},
                   'profile': {'profile_id': 'fixture-profile', 'profile_version': '1.0', 'kinds': ['rgb', 'depth']}},
        'linkage_status': 'matched', 'primary_roles_matched': 4, 'declared_reference_status': 'unresolved_reference',
        'media': {'declared_by': 'fixture', 'uri_convention': 'assets/<kind>/<file>',
                  'digest_verification': 'declared only; recomputed when the asset endpoint serves the file',
                  'items': [{'field': 'rgb_uri', 'uri': f'assets/rgb/{sample}_rgb.png', 'availability': 'present', 'row_line_index': 1,
                             'agrees_with_observation_row': True, 'declared_sha256_by_row': 'a' * 64, 'declared_bytes_by_row': 3, 'bytes_on_disk': 3},
                            {'field': 'depth_uri', 'uri': f'assets/depth/{sample}_depth_m.npy', 'availability': 'present', 'row_line_index': 2,
                             'agrees_with_observation_row': True, 'declared_sha256_by_row': 'b' * 64, 'declared_bytes_by_row': 6, 'bytes_on_disk': 6},
                            {'field': 'valid_mask_uri', 'uri': f'assets/masks/{sample}_valid.png', 'availability': 'present', 'row_line_index': 2,
                             'agrees_with_observation_row': True, 'declared_sha256_by_row': None, 'declared_bytes_by_row': None, 'bytes_on_disk': 1}]},
        'state': {'status': 'matched', 'join_key': 'control_tick_id', 'key_value': 'tick_1',
                  'source': {'stream_id': 'events', 'relative_path': 'events.jsonl', 'line_index': 7, 'event_seq': 8, 'event_type': 'feedback'},
                  'recorded_fields': {'event_seq': 8, 'control_tick_id': 'tick_1', 'backend_monotonic_s': 99.997},
                  'recorded_state': {'base_position_world_sim_m': [0.1, 0.2, 0.05], 'arm_model_qpos_rad': [0.0, 0.0, 0.0, -1.57, 0.0],
                                     'gripper_width_m': 0.02, 'tcp_position_world_m': [0.17, 0.0, 0.3], 'mystery_joint_nm': 1.5, 'feedback_time_monotonic': 99.997},
                  'declared_reference': {'feedback_sample_id': 'joint_feedback_1', 'row_status': 'unresolved_reference'},
                  'recorder_declared_feedback': {'available': True, 'feedback_time_s': 99.997, 'feedback_clock': 'backend_monotonic',
                                                 'meaning': 'the recorder’s own declared feedback time'},
                  'units': {'*_rad': 'radians', '*_rad_s': 'radians per second', '*_m': 'metres', '*_nm': 'newton metres', '*_s': 'seconds'},
                  'carried_over_from_another_frame': False, 'interpolated': False,
                  'note': 'the state the recorder placed on the frame’s capture tick'},
        'times': {'deltas': [{'label': 'state_event_minus_frame_capture', 'capture_value': 100.0, 'other_value': 99.997, 'value_s': -0.003, 'abs_value_ms': 3.0,
                              'direction': 'earlier', 'basis': 'fixture basis', 'line_index': 7}],
                  'declared_latency_ms': {'capture_to_persist_ms': 100.0},
                  'age_of_state_relative_to_frame': {'abs_ms': 3.0, 'state_recorded_before_capture': True, 'display_hint': 'show as the age of the state'},
                  'same_clock_verified': False},
        'roles': [{'role': role, 'join_key': 'sample_id', 'key_value': sample, 'status': 'matched', 'expected_records': 1, 'matched_records': 1,
                   'identity_mismatched_records': 0, 'sources': [{'stream_id': 'events', 'relative_path': 'events.jsonl', 'line_index': 7, 'event_seq': 8, 'record_position': 'events.jsonl#7'}]}
                  for role in ['image_observation', 'camera_transform', 'capture_timing_event', 'state_feedback_event']]
                 + [{'role': 'feedback_observation_row', 'join_key': 'sample_id', 'key_value': 'joint_feedback_1', 'status': 'unresolved_reference',
                     'expected_records': 1, 'matched_records': 0, 'identity_mismatched_records': 0}],
    }
    frame.update(patch)
    return frame


def frames_payload(episode, frames, **patch):
    value = {'schema_version': FRAME_SCHEMA, 'read_only': True, 'source': {**SOURCE_FIXTURE, 'path_boundary': 'paths stay inside the episode directory'},
             'retrieved_at': '2026-01-01T00:00:00Z',
             'identity': {'run_id': 'run_a', 'episode_id': episode, 'episode_directory': f'/fixture/run_a/episodes/{episode}',
                          'run_directory_identity': 'the run directory was re-validated as itself before this read', 'native_contract_version': 'mobilecar-1.0'},
             'anchor': {'stream_id': 'observations-persist', 'relative_path': 'observations/persist.jsonl', 'semantics': 'one persisted image frame per record', 'requested_stream': 'rgbd'},
             'paging': {'limit': 5, 'offset': 0, 'returned': len(frames), 'scanned_anchor_lines': 303, 'skipped_before_offset': 0,
                        'excluded_stream_mismatch': 0, 'excluded_without_sample_id': 0, 'excluded_outside_time_window': 0,
                        'excluded_anchor_identity_mismatch': 0, 'records_missing_selected_time_base': 0, 'next_offset': 5 if frames else None, 'has_more': bool(frames)},
             'cursor': {'order': 'native_append_order_of_the_anchor_stream', 'line_index_is_not_a_clock': True, 'persist_sequence_is_the_recorders_own_counter': True,
                        'first_line_index': 0, 'last_line_index': len(frames) - 1, 'first_persist_sequence': 1, 'last_persist_sequence': len(frames)},
             'time': {'selected_time_base': None, 'time_from': None, 'time_to': None,
                      'selectable_time_bases': ['capture_backend_monotonic_s', 'capture_sim_time_s', 'persist_backend_monotonic_s'],
                      'units': {'*_s': 'seconds', '*_ms': 'milliseconds', '*_rad': 'radians', '*_m': 'metres'},
                      'synchronized_across_streams': False,
                      'clock_sameness': {'declared_by_recorder': True, 'verified_by_reader': False, 'note': 'naming is not verification that two writers shared one clock'},
                      'deltas_are_recorded_arithmetic': True, 'browser_arrival_order_is_not_used': True},
             'linkage': {'roles': {role: {'source_stream': 'events', 'join_key': 'sample_id', 'meaning': f'fixture meaning for {role}'}
                                   for role in ['image_observation', 'camera_transform', 'capture_timing_event', 'state_feedback_event', 'feedback_observation_row']},
                         'status_meaning': {'matched': 'every expected record for the role was found by its recorded key',
                                            'unresolved_reference': 'the frame declares a reference whose target record is not in this Episode',
                                            'missing': 'no record for this role carried the key', 'partial': 'some but not all expected records were found',
                                            'stream_absent': 'the source stream is not recorded in this Episode',
                                            'identity_mismatch': 'a candidate record named a different run or Episode and was excluded'},
                         'primary_roles': ['image_observation', 'camera_transform', 'capture_timing_event', 'state_feedback_event'],
                         'selection_rules': {'joins': 'exact equality of the recorded join key', 'state_hold': 'not applied', 'interpolation': 'none'},
                         'role_coverage_on_this_page': {}},
             'summary': {'frames_returned': len(frames), 'frames_with_all_primary_roles_matched': len(frames), 'frames_with_some_primary_roles_missing': 0,
                         'frames_with_no_primary_role_matched': 0, 'frames_without_a_linked_state': 0, 'frames_with_unresolved_feedback_reference': len(frames)},
             'frames': frames,
             'not_proven': ['rendered 3D replay', 'a cross-stream or cross-episode replay cursor', 'no replay execution'],
             'three_d_replay': {'this_slice_does_not_enable_3d_replay': True, 'live_geometry_or_actual_may_be_applied': False, 'transforms_are_full_per_body_pose_sequences': False},
             'capability_limits': ['no replay execution', 'no control, RESET, recording or physics stepping']}
    value.update(patch)
    return value


def detail_payload(episode):
    return {'schema_version': READ_SCHEMA, 'read_only': True, 'source': SOURCE_FIXTURE, 'retrieved_at': '2026-01-01T00:00:00Z',
            'identity': {'source_id': SOURCE_ID, 'adapter_id': 'mobilecar', 'run_id': 'run_a', 'episode_id': episode, 'native_contract_version': 'mobilecar-1.0',
                         'backend_generation': {'available': False, 'reason': 'not present in every record', 'distinct_values': None, 'scope': 'sampled'},
                         'segments': [{'recording_segment_id': 'seg_1', 'previous_recording_segment_id': None, 'status': 'COMPLETE'}],
                         'episode_display_name_is_not_a_key': True},
            'declared': {'recording_status': 'COMPLETE', 'audit_status': 'COMPLETE', 'result': 'unknown', 'complete_tail_file_present': True, 'declared_checksum_entries': 1},
            'integrity': {'status': 'complete', 'scope': 'fixture', 'this_read_evidence': {'files_recomputed_here': ['episode.json']},
                          'checksum_verification': {'declared_entries': 1, 'matched': [], 'mismatched': [], 'verdict': 'none'}, 'not_verified': ['fixture']},
            'streams': [{'stream_id': 'events', 'relative_path': 'events.jsonl', 'format': 'jsonl', 'available': True, 'bytes': 10, 'records': 3},
                        {'stream_id': 'observations-persist', 'relative_path': 'observations/persist.jsonl', 'format': 'jsonl', 'available': True, 'bytes': 10, 'records': 2}],
            'time': {'available_time_bases': {'events': {'available': True, 'time_bases_in_first_record': ['backend_monotonic_s']}},
                     'units': {'*_s': 'seconds'}, 'browser_arrival_order_is_not_used': True, 'synchronized_across_streams': False},
            'three_d_replay': {'status': 'restricted', 'model_match': 'mismatch', 'scene_match': 'mismatch', 'recorded_transforms_available': False,
                               'live_geometry_or_actual_may_be_applied': False, 'reasons': ['recorded model digest differs from the production pin']},
            'platform_association': {'known': False, 'validated_snapshot_ref': None, 'platform_session_id': None, 'reason': 'fixture'},
            'training_qualification': {'training_qualified': False, 'blocks_raw_read': False},
            'media_summary': {'kinds': {}}, 'capability_limits': ['no replay execution']}


def list_payload(rows):
    return {'schema_version': READ_SCHEMA, 'read_only': True, 'source': SOURCE_FIXTURE, 'retrieved_at': '2026-01-01T00:00:00Z',
            'paging': {'limit': 10, 'offset': 0, 'returned': len(rows), 'total_matches': len(rows), 'next_offset': None, 'order': 'run_id_then_episode_id'},
            'filters': {'run_id': None, 'recording_status': None, 'episode_id': None}, 'integrity_scope': 'fixture',
            'episodes': [{'run_id': 'run_a', 'episode_id': row, 'contract_version': 'mobilecar-1.0', 'readable': True, 'read_error': None,
                          'declared': {'recording_status': 'COMPLETE', 'audit_status': 'COMPLETE', 'result': 'unknown'}, 'segment_count': 1} for row in rows]}


def records_payload(episode, stream, records, **patch):
    value = {'schema_version': READ_SCHEMA, 'read_only': True, 'source': SOURCE_FIXTURE, 'retrieved_at': '2026-01-01T00:00:00Z',
             'identity': {'run_id': 'run_a', 'episode_id': episode}, 'stream': {'stream_id': stream, 'relative_path': f'{stream}.jsonl', 'format': 'jsonl'},
             'paging': {'limit': 5, 'offset': 0, 'returned': len(records), 'scanned_lines': len(records), 'skipped_before_offset': 0, 'next_offset': None, 'has_more': False},
             'cursor': {'order': 'native_append_order', 'first_line_index': 0, 'last_line_index': len(records) - 1, 'line_index_is_not_a_clock': True},
             'time': {'selected_time_base': None, 'time_from': None, 'time_to': None, 'units': 'seconds for *_s', 'records_without_the_selected_base': 0,
                      'numeric_time_bases': ['arrival_time_s', 'backend_monotonic_s', 'measurement_time_s', 'sim_time_s'], 'synchronized_across_streams': False},
             'filtering': {'event_seq_range': {'from': None, 'to': None, 'active': False, 'excluded_without_valid_event_seq': 0, 'anomalies': []}},
             'records': [{'line_index': i, 'record': r} for i, r in enumerate(records)],
             'integrity': {'corrupt_lines': [], 'lines_over_read_size_limit': [], 'declared_status': {}, 'scope': 'fixture', 'not_verified': ['fixture']}}
    value.update(patch)
    return value


async def synthetic_handler(route):
    request = route.request
    path = urlsplit(request.url).path
    query = parse_qs(urlsplit(request.url).query)
    # /api/v1/episodes/<id>[/frames|/records|/assets/…]: the identity is segment 4, not segment 3
    # ('episodes'), otherwise every fixture payload answers with episode_id='episodes' and the pane
    # never binds to the Episode the test just opened.
    episode = path.split('/')[4] if len(path.split('/')) > 4 else ''
    if request.method != 'GET':
        await route.fulfill(status=405, content_type='text/html', body='<html>Only allowlisted platform endpoints are exposed</html>'); return
    if path.endswith('/frames'):
        if episode == 'episode_no_frames':
            await route.fulfill(status=404, content_type='application/json',
                                body=json.dumps({'detail': {'code': 'episode_stream_unavailable', 'message': 'this record has no observations/persist.jsonl', 'read_only': True}})); return
        if episode == 'episode_bad_frame_schema':
            await route.fulfill(json={'schema_version': 'unirobot-mobilecar-frame-link-2', 'read_only': True}); return
        if episode == 'episode_bad_sample':
            await route.fulfill(status=400, content_type='application/json',
                                body=json.dumps({'detail': {'code': 'sample_id_invalid', 'message': 'sample id is not a native id token', 'read_only': True}})); return
        if (query.get('sample_id') or [''])[0].startswith('rgbd_slow'):
            SLOW['state'] = 'pending'
            await asyncio.sleep(2.4)
            SLOW['state'] = 'done'
        if (query.get('time_from') or [''])[0] == '1':
            await route.fulfill(json=frames_payload(episode, [], **{
                'paging': {**frames_payload(episode, [])['paging'], 'excluded_outside_time_window': 303, 'next_offset': None, 'has_more': False, 'returned': 0},
                'time': {**frames_payload(episode, [])['time'], 'selected_time_base': (query.get('time_base') or [''])[0], 'time_from': 1.0, 'time_to': 2.0}})); return
        if episode == 'episode_no_time_bases':
            payload = frames_payload(episode, [frame_payload('rgbd_empty_bases')])
            payload['time'] = {**payload['time'], 'selectable_time_bases': []}
            await route.fulfill(json=payload); return
        if episode == 'episode_media_gaps':
            missing = frame_payload('rgbd_media_missing', media={**frame_payload('x')['media'], 'items': [
                {'field': 'rgb_uri', 'uri': 'assets/rgb/gone_rgb.png', 'availability': 'absent', 'declared_sha256_by_row': 'c' * 64, 'declared_bytes_by_row': 9, 'bytes_on_disk': None, 'agrees_with_observation_row': None, 'row_line_index': None},
                {'field': 'depth_uri', 'uri': 'assets/depth/escape.npy', 'availability': 'refused', 'refusal_code': 'episode_asset_escape'},
                {'field': 'valid_mask_uri', 'uri': 'assets/masks/x_valid.png', 'availability': 'not_recorded_on_this_frame'}]})
            unverified = frame_payload('rgbd_digest_bad', media={**frame_payload('x')['media'], 'items': [
                {'field': 'rgb_uri', 'uri': 'assets/rgb/bad_digest_rgb.png', 'availability': 'present', 'declared_sha256_by_row': 'a' * 64, 'declared_bytes_by_row': 3, 'bytes_on_disk': 3, 'agrees_with_observation_row': True, 'row_line_index': 1}]})
            payload = frames_payload(episode, [frame_payload('rgbd_media_ok'), missing, unverified],
                                     paging={**frames_payload(episode, [])['paging'], 'returned': 3, 'next_offset': None, 'has_more': False})
            await route.fulfill(json=payload); return
        if episode == 'episode_state_missing':
            stateless = frame_payload('rgbd_state_missing', linkage_status='partial', primary_roles_matched=3,
                                      state={**frame_payload('x')['state'], 'status': 'missing', 'source': None, 'recorded_state': {}, 'recorded_fields': {}},
                                      roles=[{**role, 'status': 'missing' if role['role'] == 'state_feedback_event' else role['status'],
                                              'sources': [], 'expected_records': 1, 'matched_records': 0} if role['role'] == 'state_feedback_event' else role
                                             for role in frame_payload('x')['roles']])
            await route.fulfill(json=frames_payload(episode, [frame_payload('rgbd_with_state'), stateless])); return
        frames = [frame_payload(f'rgbd_{i}') for i in range(3)]
        offset = int((query.get('offset') or ['0'])[0])
        if offset:
            await route.fulfill(json=frames_payload(episode, [], paging={**frames_payload(episode, [])['paging'], 'offset': offset, 'returned': 0, 'skipped_before_offset': offset, 'next_offset': None, 'has_more': False}))
            return
        await route.fulfill(json=frames_payload(episode, frames)); return
    if '/assets/' in path:
        if 'bad_digest_rgb.png' in path:
            await route.fulfill(status=409, content_type='application/json', body=json.dumps({'detail': {'code': 'episode_asset_digest_mismatch', 'message': 'asset digest does not match the requested sha256', 'expected': 'a' * 64, 'actual': 'b' * 64}})); return
        if 'npy' in path:
            await route.fulfill(status=200, body=b'\x93NUMPY\x01\x00', content_type='application/octet-stream', headers={'X-Episode-Asset-Sha256': 'd' * 64}); return
        await route.fulfill(status=200, body=tiny_png(), content_type='image/png', headers={'X-Episode-Asset-Sha256': 'a' * 64, 'X-Episode-Run-Id': 'run_a'}); return
    if path.endswith('/streams'):
        await route.fulfill(json=detail_payload(episode)); return
    if path.endswith('/records'):
        stream = path.split('/streams/')[1].split('/')[0]
        if stream == 'observations-persist':
            await route.fulfill(json=records_payload(episode, stream, [{'sample_id': 'rgbd_1', 'persist_sequence': 1, 'sim_time_s': 1.0, 'rgb_uri': 'assets/rgb/rgbd_1_rgb.png'}],
                                                    time={**records_payload(episode, stream, [])['time'], 'numeric_time_bases': []}))
            return
        await route.fulfill(json=records_payload(episode, stream, [{'event_seq': 1, 'event_type': 'feedback', 'backend_monotonic_s': 10.0}])); return
    if path == '/api/v1/episodes':
        await route.fulfill(json=list_payload(['episode_ok', 'episode_no_frames', 'episode_bad_frame_schema', 'episode_bad_sample',
                                               'episode_no_time_bases', 'episode_media_gaps', 'episode_state_missing'])); return
    if re.fullmatch(r'/api/v1/episodes/[^/]+', path):
        await route.fulfill(json=detail_payload(episode)); return
    await route.fulfill(status=404, content_type='application/json', body=json.dumps({'detail': {'code': 'episode_not_found', 'message': 'no Episode directory'}}))


async def synthetic_flow(page):
    await wait_list(page)
    await open_episode(page, 'run_a', 'episode_ok')
    view = await page_attrs(page)
    check('the synthetic pane binds frame-link-1 and shows the fixture’s three frames',
          view['schema'] == FRAME_SCHEMA and view['returned'] == '3' and len(view['rowSamples']) == 3)
    check('the selectable time bases come from the page; an empty list is respected, not defaulted',
          view['selectable'] == ['capture_backend_monotonic_s', 'capture_sim_time_s', 'persist_backend_monotonic_s'])
    await open_episode(page, 'run_a', 'episode_no_time_bases')
    empty_bases = await page_attrs(page)
    options = await page.locator('select[aria-label="帧时间基"] option').evaluate_all('els=>els.map(e=>e.value)')
    gate = await page_attrs(page)
    check('an empty selectable_time_bases page offers no numeric base at all instead of a default list',
          empty_bases['selectable'] == [] and empty_bases['episode'] == 'episode_no_time_bases'
          and options == [''] and gate['windowGate'] == 'refused'
          and '未选择时间基' in gate['windowReason']
          and await page.locator('[data-frame-window-apply]').is_disabled()
          and await page.locator('input[aria-label="时间窗口起点"]').is_disabled()
          and 'reader 未声明（空数组就是本页的答案，不回退默认基）' in await page.locator('[data-frame-selectable-bases]').inner_text(),
          (options, gate['windowReason']))
    check('the same page’s empty list is shown as the reader’s answer, not as “undeclared”',
          'reader 未声明（空数组就是本页的答案，不回退默认基）' in await page.locator('[data-frame-selectable-bases]').inner_text())

    await open_episode(page, 'run_a', 'episode_media_gaps')
    await wait_asset_uri(page, 'assets/rgb/rgbd_media_ok_rgb.png')
    await wait_asset_settled(page)
    view = await page_attrs(page)
    check('a present rgb reference is read, decoded and compared with its declared digest',
          view['assetStatus'] == 'bytes' and view['assetDecoded'] == 'ok' and view['assetMatch'] == 'true'
          and view['assetUri'] == 'assets/rgb/rgbd_media_ok_rgb.png')
    await page.locator('[data-frame-pick="rgbd_media_missing"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-frame-asset-status]')?.getAttribute('data-frame-asset-status') ?? '')==='not-loaded'", timeout=30000)
    gap = await page_attrs(page)
    check('an absent or refused reference clears the image instead of keeping the previous frame’s picture',
          gap['assetStatus'] == 'not-loaded' and gap['assetUri'] == 'none'
          and gap['assetSample'] == 'rgbd_media_missing'
          and await count(page, '[data-frame-asset-image]') == 0
          and '不显示任何图像' in await page.locator('[data-frame-asset-unavailable]').inner_text()
          and gap['mediaAvailability'] == ['absent', 'refused', 'not_recorded_on_this_frame'], gap['mediaAvailability'])
    check('each unusable reference says why in the reader’s own terms, per item',
          '不按文件名推测内容' in await page.locator('[data-frame-media-ref="assets/rgb/gone_rgb.png"]').inner_text()
          and 'refusal_code=episode_asset_escape' in await page.locator('[data-frame-media-ref="assets/depth/escape.npy"]').inner_text()
          and '不拿别的帧的图片顶替' in await page.locator('[data-frame-media-ref="assets/masks/x_valid.png"]').inner_text())
    refused = await page.locator('[data-frame-media-ref="assets/depth/escape.npy"]').inner_text()
    check('a refused reference names the reader’s refusal code and stays unpickable',
          'refusal_code=episode_asset_escape' in refused and '界面不绕过' in refused
          and await page.locator('[data-frame-media-pick="depth_uri"]').is_disabled())
    await page.locator('[data-frame-pick="rgbd_digest_bad"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-frame-asset-status]')?.getAttribute('data-frame-asset-status') ?? '')==='failed'", timeout=30000)
    check('a digest the server recomputes differently is shown as the reader’s code, not as a placeholder image',
          await attr(page, '[data-frame-asset-status]', 'data-frame-asset-status') == 'failed'
          and 'episode_asset_digest_mismatch' in await page.locator('[data-frame-asset-error]').inner_text()
          and await count(page, '[data-frame-asset-image]') == 0)
    await page.locator('[data-frame-pick="rgbd_media_ok"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-frame-asset-status]')?.getAttribute('data-frame-asset-status') ?? '')==='bytes'", timeout=30000)
    await page.locator('[data-frame-media-pick="depth_uri"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-frame-asset-media-type]')?.getAttribute('data-frame-asset-media-type') ?? '')==='application/octet-stream'", timeout=30000)
    check('non-image bytes stay bytes: no numpy decoding, no fake image, no point cloud',
          await attr(page, '[data-frame-asset-not-inline]', 'data-frame-asset-not-inline') == 'true'
          and '不做 NumPy 数值解码' in await page.locator('[data-frame-asset-not-inline]').inner_text()
          and await count(page, '[data-frame-asset-image]') == 0
          and await attr(page, '[data-frame-asset-field]', 'data-frame-asset-field') == 'depth_uri')

    await open_episode(page, 'run_a', 'episode_state_missing')
    await page.locator('[data-frame-pick="rgbd_state_missing"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-frame-state-status]')?.getAttribute('data-frame-state-status') ?? '')==='missing'", timeout=30000)
    missing_state = await page_attrs(page)
    check('a frame whose state did not match says so, lists the missing role and never substitutes another frame’s state',
          missing_state['stateStatus'] == 'missing' and await count(page, '[data-state-row]') == 0
          and '状态未命中（status=missing）' in await page.locator('[data-provenance-row="state_position"]').inner_text()
          and 'no record for this role carried the key' in await page.locator('[data-frame-role="state_feedback_event"]').inner_text()
          and 'carried_over_from_another_frame=false' in missing_state['text'])

    await open_episode(page, 'run_a', 'episode_ok')
    no_base = await page_attrs(page)
    check('with no base chosen the pane says it browses by offset/sample only and sends no bound',
          no_base['windowGate'] == 'refused' and '未选择时间基' in no_base['windowReason'])
    await page.locator('select[aria-label="帧时间基"]').select_option('capture_backend_monotonic_s')
    no_bounds = await page_attrs(page)
    check('a base with no bounds is refused locally so the reader’s 400 is never triggered by guesswork',
          no_bounds['windowGate'] == 'refused' and 'time_range_required' in no_bounds['windowReason']
          and await page.locator('[data-frame-window-apply]').is_disabled())
    await page.locator('input[aria-label="时间窗口起点"]').fill('not-a-number')
    await page.locator('[data-frame-window-apply]').click()
    check('a non-numeric bound is refused without sending a request and is not replaced by 0',
          '必须是数值秒' in (await page_attrs(page))['windowReason']
          and not [r for r in report['requests'] if 'time_from=not-a-number' in r['url']])
    await page.locator('input[aria-label="时间窗口起点"]').fill('0')
    await page.locator('input[aria-label="时间窗口终点"]').fill('')
    await page.locator('[data-frame-window-apply]').click()
    await page.wait_for_timeout(400)
    check('an explicit 0 bound is sent while a blank side is omitted',
          any('time_from=0' in r['url'] and 'time_to' not in r['url'] for r in report['requests'] if '/frames' in r['url']))
    await page.locator('input[aria-label="时间窗口起点"]').fill('1')
    await page.locator('input[aria-label="时间窗口终点"]').fill('2')
    await page.locator('[data-frame-window-apply]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-page-kind]')?.getAttribute('data-frame-page-kind') ?? '')==='window-empty'")
    empty = await page_attrs(page)
    check('an empty window page counts the exclusions and clears both image and frame rows',
          empty['pageKind'] == 'window-empty' and '空结果页，不是读取错误' in empty['explanation']
          and await count(page, '[data-frame-asset-uri]') == 0 and not empty['rowSamples'])

    await open_episode(page, 'run_a', 'episode_ok')
    await page.locator('input[aria-label="sample_id 精确打开"]').fill('rgbd_slow_1')
    await page.locator('[data-frame-open-sample]').click()
    await page.wait_for_timeout(200)
    await open_episode(page, 'run_a', 'episode_media_gaps')
    await wait_frames(page, "()=>(document.querySelector('[data-frame-episode]')?.getAttribute('data-frame-episode') ?? '')==='episode_media_gaps' && (document.querySelector('[data-frame-returned]')?.getAttribute('data-frame-returned') ?? '')==='3'")
    await page.wait_for_timeout(2600)
    after_late = await page_attrs(page)
    check('a frame page that arrives after the Episode switch never lands (synthetic delayed response)',
          SLOW['state'] == 'done' and after_late['episode'] == 'episode_media_gaps'
          and after_late['contextSample'] == 'none' and 'rgbd_slow' not in after_late['text']
          and after_late['currentSample'] == 'rgbd_media_ok')

    await open_episode(page, 'run_a', 'episode_no_frames', expect='error')
    missing_stream = await page_attrs(page)
    check('an Episode without a persist stream is shown with the reader’s code and leaves the pane unbound',
          'episode_stream_unavailable' in missing_stream['error'] and '没有对应文件' in missing_stream['error']
          and missing_stream['bound'] == 'false' and await count(page, '[data-frame-row]') == 0)
    await open_episode(page, 'run_a', 'episode_bad_frame_schema', expect='error')
    check('a frame payload that is not frame-link-1 is refused as a contract finding, not rendered',
          'unirobot-mobilecar-frame-link-1' in (await page_attrs(page))['error']
          and (await page_attrs(page))['bound'] == 'false')
    await open_episode(page, 'run_a', 'episode_bad_sample', expect='error')
    check('the reader’s sample_id_invalid refusal is shown with its own hint',
          'sample_id_invalid' in (await page_attrs(page))['error'] and '不是原生 id token' in (await page_attrs(page))['error'])

    await open_episode(page, 'run_a', 'episode_ok')
    await page.locator('[data-stream-option="observations-persist"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-stream-path]')?.getAttribute('data-stream-path') ?? '')==='observations-persist.jsonl'", timeout=30000)
    seek = await attr_all(page, '[data-seek-numeric-bases]', 'data-seek-numeric-bases')
    check('records: an explicit empty numeric_time_bases array keeps seeking refused instead of restoring defaults',
          await attr(page, '[data-seek-gate]', 'data-seek-gate') == 'refused' and seek == ['']
          and 'numeric_time_bases=空' in (await attr(page, '[data-history-seek]', 'title') or '')
          and await page.locator('input[aria-label="定位时间值"]').is_disabled())
    await open_episode(page, 'run_a', 'episode_ok')
    await page.locator('input[aria-label="sample_id 精确打开"]').fill('rgbd_0')
    await page.locator('[data-frame-open-sample]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-context-sample]')?.getAttribute('data-frame-context-sample') ?? '')==='rgbd_0'")
    for _ in range(3):
        await page.locator('[data-frame-next]').click()
        await page.wait_for_timeout(200)
    stop = await page_attrs(page)
    check('the pagination gap stops the walk with the reader’s own counters, keeping the sample condition',
          stop['returned'] == '0' and '混合了候选行计数与锚点原生行号' in stop['notice']
          and stop['contextSample'] == 'rgbd_0' and stop['hasMore'] == 'false', stop['notice'][:180])
    await page.locator('[data-frame-sample-clear]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-returned]')?.getAttribute('data-frame-returned') ?? '')==='3'")
    await page.locator('[data-frame-play]').click()
    playing = await attr(page, '[data-frame-play]', 'data-frame-play')
    await page.wait_for_timeout(1200)
    played = await page_attrs(page)
    await page.locator('[data-frame-play]').click()
    check('play advances on a UI cadence only, and the pane never claims a recorded frame rate',
          playing == 'pause' and int(played['index']) >= 1
          and '节奏只控制界面推进，不是录制帧率' in played['text']
          and '节奏只控制界面推进' in await page.locator('[data-frame-playback-cadence-ui-only]').inner_text()
          and '帧率' not in played['explanation'], (playing, played['index'], played['explanation'][:120]))


async def boundary_checks(page):
    for method, path in (('POST', f'/api/v1/episodes/{a.complete_episode}/frames' if a.mode == 'real' else '/api/v1/episodes/episode_ok/frames'),
                         ('GET', f'/api/v1/episodes/{a.complete_episode}/frames/extra' if a.mode == 'real' else '/api/v1/episodes/episode_ok/frames/extra'),
                         ('POST', '/api/v1/episodes/episode_ok/validate'),
                         ('GET', f'/api/v1/episodes/{a.complete_episode if a.mode == "real" else "episode_ok"}/frames/deeper/still')):
        response = await page.request.fetch(a.url + path, method=method, data='{}' if method == 'POST' else None)
        body = await response.text()
        check(f'the gateway answers {method} {path} with its own refusal, never a forwarded call',
              response.status in (404, 405) and ('allowlisted' in body or 'not allowed' in body.lower()), (response.status, body[:120]))
    if a.mode == 'real':
        response = await page.request.fetch(a.url + f'/api/v1/episodes/{a.complete_episode}/frames?run_id={a.complete_run}&limit=1', method='GET')
        payload = await response.json()
        check('the frames GET is forwarded through the exact route and keeps the frame-link-1 schema',
              response.status == 200 and payload['schema_version'] == FRAME_SCHEMA and payload['read_only'] is True)


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
        page = await browser.new_page(viewport={'width': 1700, 'height': 1000}, device_scale_factor=1)
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        page.on('request', lambda req: report['requests'].append({'method': req.method, 'url': req.url}))
        try:
            if a.mode == 'synthetic': await page.route('**/api/v1/episodes**', synthetic_handler)
            await open_history(page)
            if a.mode == 'real': await real_flow(page)
            else: await synthetic_flow(page)
            await boundary_checks(page)
            episodes = [r for r in report['requests'] if '/api/v1/episodes' in r['url']]
            frames = [r for r in episodes if urlsplit(r['url']).path.endswith('/frames')]
            check('every frame request is a GET on the exact frames route',
                  all(r['method'] == 'GET' for r in episodes) and len(frames) >= (6 if a.mode == 'real' else 8),
                  [r for r in episodes if r['method'] != 'GET'][:3])
            check('the pane never opens a second frames sub-path (no wildcard proxy widening)',
                  {urlsplit(r['url']).path.split('/episodes/')[1].split('/')[1] for r in frames} == {'frames'}, sorted({urlsplit(r['url']).path for r in frames})[:3])
            # The shell's own live monitor keeps reading scene/snapshot in the background by design
            # (browser-history asserts that it does); what must never appear is a control, lifecycle,
            # session or recording request.
            check('no control, session, reset or recording request is issued',
                  not [r for r in report['requests'] if any(token in urlsplit(r['url']).path for token in ('/api/v1/commands', '/api/v1/reset', '/api/v1/runs', '/recording/', '/api/v1/sessions'))],
                  [r['url'] for r in report['requests']][:4])
            check('every request the page issues is a GET',
                  all(r['method'] == 'GET' for r in report['requests']), [r for r in report['requests'] if r['method'] != 'GET'][:3])
            check('the frame pane renders no 3D canvas and no live Target/Ghost control',
                  await page.evaluate("()=>({canvas:document.querySelectorAll('canvas').length, target:document.querySelectorAll('[data-target-readout],[data-ghost-toggle],[data-workbench-tool]').length})") == {'canvas': 0, 'target': 0})
            check('no uncaught browser errors', not report['errors'], report['errors'][:3])
            report['frame_requests'] = len(frames)
            report['status'] = 'passed'
        except Exception as exc:
            report['exception'] = str(exc); report['traceback'] = traceback.format_exc()
            await page.screenshot(path=str(a.output / 'failure.png'), full_page=True)
        finally:
            (a.output / 'browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            await browser.close()

asyncio.run(main())
print(json.dumps({'status': report['status'], 'mode': a.mode, 'checks': len(report['checks']), 'frame_requests': report.get('frame_requests'), 'error': report.get('exception')}, ensure_ascii=False))
raise SystemExit(report['status'] != 'passed')
