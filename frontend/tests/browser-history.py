"""History Episode browsing and single-stream read-only playback acceptance.

  --mode real       against a frontend preview whose upstream is the fixed history candidate
                    (episode-read-1). Verifies pagination, composite identity, stream reads,
                    media bytes, missing-media wording and the layered integrity wording against
                    the actual COMPLETE and FAILED records. Only GET requests are issued; the
                    archive itself is never written.
  --mode synthetic  the same product code against isolated page.route fixtures: unsupported and
                    missing streams, corrupt/over-size lines, digest mismatch, unsupported asset
                    type, unknown time base, ambiguous episode id, records without the selected
                    time base, contract-mismatch payloads and late responses after a switch. The
                    real archive is not touched by this mode at all.

Both modes assert that the browser issues no non-GET request, that the gateway refuses native
episode validate/assessment, control and run-stop paths locally, that no 3D canvas or live
Target/Ghost is mounted in the history view, and that live polling never rewrites history DOM.
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
a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
report = {'scope': f'{a.mode} history episode acceptance against {a.url}', 'mode': a.mode,
          'checks': [], 'errors': [], 'requests': [], 'real': {}, 'status': 'failed'}
SOURCE_ID = 'mobilecar-server-history-20261017'


def tiny_png():
    """A real 1x1 PNG built here, so a decode assertion means the browser decoded served bytes."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\x11\x22\x33')) + chunk(b'IEND', b''))


def check(name, condition, detail=None):
    if not condition: raise AssertionError(name if detail is None else f'{name} :: {detail}')
    report['checks'].append(name)


async def attr(page, selector, name):
    return await page.locator(selector).first.get_attribute(name)


async def attr_or_none(page, selector, name):
    return await page.locator(selector).first.get_attribute(name) if await page.locator(selector).count() else None


async def attr_all(page, selector, name):
    return await page.locator(selector).evaluate_all(f'els=>els.map(e=>e.getAttribute("{name}"))')


async def open_history(page):
    await page.goto(a.url + '/', wait_until='domcontentloaded')
    await page.wait_for_selector('.side-nav button', timeout=60000)
    await page.get_by_role('button', name='历史 Episode', exact=True).click()
    await page.wait_for_selector('.history-view[data-history-view="true"]', timeout=20000)


async def wait_list(page, state='ready'):
    await page.wait_for_selector(f'.history-list-pane[data-list-state="{state}"]', timeout=40000)


async def wait_records(page, predicate="()=>document.querySelector('.history-stream-pane[data-stream-bound=\"true\"]')", timeout=40000):
    await page.wait_for_function(predicate, timeout=timeout)


async def read_direct(page, path, params=None):
    url = a.url + path
    if params: url += '?' + '&'.join(f'{k}={v}' for k, v in params.items())
    return await (await page.request.get(url)).json()


async def filter_run(page, run_id):
    await page.locator('input[aria-label="run_id 筛选"]').fill(run_id)
    await page.get_by_role('button', name='重新读取首页').click()
    await wait_list(page)


async def open_episode(page, run_id, episode_id):
    await filter_run(page, run_id)
    await page.wait_for_selector(f'[data-episode-open="{episode_id}"]', timeout=30000)
    await page.locator(f'[data-episode-open="{episode_id}"]').click()
    await page.wait_for_selector(f'.history-detail-pane dl[data-detail-run="{run_id}"]', timeout=40000)


async def cursor_index(page):
    return int(await attr(page, '[data-cursor-index]', 'data-cursor-index'))


async def goto_index(page, target):
    for _ in range(60):
        current = await cursor_index(page)
        if current == target: return current
        await page.locator('[data-history-next]' if current < target else '[data-history-prev]').click()
        await page.wait_for_timeout(120)
    raise AssertionError(f'could not reach cursor index {target}')


def fingerprint_script():
    return """()=>{const v=document.querySelector('.history-view');
      return v?v.innerText.length+'|'+((document.querySelector('[data-detail-episode]')?.getAttribute('data-detail-episode') ?? ''))+
        '|'+((document.querySelector('[data-cursor-line]')?.getAttribute('data-cursor-line') ?? ''))+
        '|'+(document.querySelector('[data-integrity-layers]')?.innerText.length??0):'';}"""


# ---- real --------------------------------------------------------------------------------------------

async def real_flow(page):
    await wait_list(page)
    total = int(await attr(page, '[data-paging-total]', 'data-paging-total'))
    first_page = await read_direct(page, '/api/v1/episodes', {'limit': 10, 'offset': 0})
    check('the platform list agrees with the reader on the declared scale', first_page['paging']['total_matches'] == total and total > 0, (total, first_page['paging']))
    check('the list is served from the pinned history source and declares read_only',
          first_page['read_only'] is True and first_page['source']['source_id'] == SOURCE_ID
          and first_page['source']['platform_writes'] is False and await attr(page, '[data-history-source]', 'data-history-source') == SOURCE_ID)
    check('list integrity scope and capability limits are shown as the reader words them',
          'opened episode.json only' in (await attr(page, '[data-integrity-scope]', 'data-integrity-scope'))
          and 'no replay execution' in (await attr(page, '.history-list-pane [data-capability-limits]', 'data-capability-limits')))
    ui_ids = await attr_all(page, '[data-episode-open]', 'data-episode-open')
    check('page one rows are exactly the reader page', ui_ids == [item['episode_id'] for item in first_page['episodes']], (ui_ids[:3],))
    rows_meta = await page.locator('[data-episode-row]').evaluate_all('els=>els.map(e=>[e.getAttribute("data-row-run"),e.getAttribute("data-row-source"),e.getAttribute("data-episode-row")])')
    check('every row identity carries source, run and episode together',
          all(len(meta) == 3 and meta[0] and meta[1] == SOURCE_ID and meta[2] for meta in rows_meta), rows_meta[:2])
    await page.locator('select[aria-label="分页大小"]').select_option('10')
    await wait_list(page)
    page_two = await read_direct(page, '/api/v1/episodes', {'limit': 10, 'offset': 10})
    await page.get_by_role('button', name=re.compile('^下一页')).click()
    await wait_list(page)
    second_ids = await attr_all(page, '[data-episode-open]', 'data-episode-open')
    check('the next page is the reader page at next_offset and does not overlap',
          second_ids == [item['episode_id'] for item in page_two['episodes']] and not set(second_ids) & set(ui_ids)
          and int(await attr(page, '[data-paging-offset]', 'data-paging-offset')) == 10, (second_ids[:2],))
    await page.locator('select[aria-label="录制状态筛选"]').select_option('FAILED')
    await wait_list(page)
    failed_ids = await attr_all(page, '[data-episode-open]', 'data-episode-open')
    check('the status filter keeps only FAILED declarations in the DOM',
          all(status == 'FAILED' for status in await attr_all(page, '[data-episode-row]', 'data-row-status')), failed_ids[:3])
    failed_total = int(await attr(page, '[data-paging-total]', 'data-paging-total'))
    check('FAILED count is the reader’s own filtered total, not a client recount',
          failed_total == (await read_direct(page, '/api/v1/episodes', {'limit': 1, 'recording_status': 'FAILED'}))['paging']['total_matches'] and failed_total > 0, failed_total)
    failed_ref = (await read_direct(page, '/api/v1/episodes', {'limit': 1, 'recording_status': 'FAILED'}))['episodes'][0]
    complete_ref = {'run_id': a.complete_run, 'episode_id': a.complete_episode} if a.complete_run else \
        (await read_direct(page, '/api/v1/episodes', {'limit': 1, 'recording_status': 'COMPLETE'}))['episodes'][0]
    report['real']['complete_ref'] = [complete_ref['run_id'], complete_ref['episode_id']]
    report['real']['failed_ref'] = [failed_ref['run_id'], failed_ref['episode_id']]

    await page.locator('select[aria-label="录制状态筛选"]').select_option('')
    await wait_list(page)
    await open_episode(page, complete_ref['run_id'], complete_ref['episode_id'])
    detail = await read_direct(page, f"/api/v1/episodes/{complete_ref['episode_id']}", {'run_id': complete_ref['run_id']})
    requests_by_page = [r for r in report['requests'] if '/api/v1/episodes/' in r['url'] and '/records' not in r['url'] and '/assets' not in r['url'] and '/streams' not in r['url']]
    check('the detail read carries run_id explicitly',
          all('run_id=' in r['url'] for r in requests_by_page[-1:]), requests_by_page[-1:][0]['url'] if requests_by_page else 'none')
    check('detail identity is the composite triple and the display name is not a key',
          await attr(page, '[data-detail-run]', 'data-detail-run') == complete_ref['run_id']
          and await attr(page, '[data-detail-episode]', 'data-detail-episode') == complete_ref['episode_id']
          and await attr(page, '[data-detail-source]', 'data-detail-source') == SOURCE_ID
          and await attr(page, '[data-display-name-not-key]', 'data-display-name-not-key') == 'true')
    check('segments are shown as segments of this episode',
          int(await attr(page, '[data-segment-count]', 'data-segment-count')) == len(detail['identity'].get('segments', [])) >= 1
          and detail['identity']['segments'][0]['recording_segment_id'] in (await page.locator('[data-segment-count]').inner_text()))
    check('available streams come from the reader and are all listed',
          int(await attr(page, '[data-stream-count]', 'data-stream-count')) == len(detail['streams'])
          and await attr_all(page, '[data-stream-option]', 'data-stream-option') == [s['stream_id'] for s in detail['streams']])
    check('legacy configuration association is shown as unknown, not invented',
          await attr(page, '[data-association-known]', 'data-association-known') == 'false'
          and 'legacy_native_record_without_platform_sidecar' in await attr(page, '[data-association-reason]', 'data-association-reason')
          and 'validated_snapshot_ref=null' in (await page.locator('[data-association-known]').inner_text()))
    check('training qualification is displayed separately and never blocks the raw read',
          'blocks_raw_read=false' in (await page.locator('[data-training-blocks-read]').inner_text())
          and await attr(page, '[data-training-blocks-read]', 'data-training-blocks-read') == 'false')
    check('model identity inside the record is the recorded digest',
          await attr(page, '[data-recorded-model]', 'data-recorded-model') == detail['recorded_model_identity']['model_sha256'])
    check('time declaration keeps named bases, units and the unsynchronised flag',
          'backend_monotonic' in await attr(page, '[data-clocks]', 'data-clocks')
          and '*_s' in await attr(page, '[data-units]', 'data-units')
          and 'synchronized_across_streams=false' in (await page.locator('[data-units]').inner_text()))
    check('action semantics classes stay separate and are not promoted',
          'recorded_target:actuator_reference' in await attr(page, '[data-action-classes]', 'data-action-classes')
          and 'execution_feedback:feedback' in await attr(page, '[data-action-classes]', 'data-action-classes'))
    check('media declaration states the counts and declared-digest coverage the reader reports',
          await attr(page, '[data-media-kinds]', 'data-media-kinds') == ','.join(f'{k}:{v["count"]}' for k, v in detail['media_summary']['kinds'].items())
          and await attr(page, '[data-media-sha-coverage]', 'data-media-sha-coverage') == ','.join(f'{k}:{v["declared_sha256_coverage"]}' for k, v in detail['media_summary']['kinds'].items()),
          (await attr(page, '[data-media-kinds]', 'data-media-kinds'), await attr(page, '[data-media-sha-coverage]', 'data-media-sha-coverage')))
    check('source identity and archive baseline are shown as a change-detection reference',
          await attr(page, '[data-archive-sha]', 'data-archive-sha') == detail['source']['archive_baseline']['aggregate_sha256']
          and 'change-detection' in (await page.locator('[data-archive-sha]').inner_text()))
    check('the resolved root and the path boundary rule are shown as the reader reports them',
          await attr(page, '[data-source-root-resolved]', 'data-source-root-resolved') == detail['source']['recording_root_resolved']
          and await attr(page, '[data-source-path-boundary]', 'data-source-path-boundary') == detail['source']['path_boundary'],
          (await attr(page, '[data-source-path-boundary]', 'data-source-path-boundary'), detail['source'].get('path_boundary')))
    check('the media summary declares its own truncation and asset exclusions',
          await attr(page, '[data-media-excluded-count]', 'data-media-excluded-count') == str(detail['media_summary'].get('excluded_count'))
          and '截断' in (await page.locator('[data-media-kinds]').inner_text()),
          (await attr(page, '[data-media-excluded-count]', 'data-media-excluded-count'), detail['media_summary'].get('excluded_count')))
    check('history 3D limitation is stated before anything else and live geometry is refused',
          await attr(page, '[data-live-geometry-applied]', 'data-live-geometry-applied') == 'false'
          and await attr(page, '[data-three-d-status]', 'data-three-d-status') == detail['three_d_replay']['status']
          and '不等于渲染正确性已验证' in (await page.locator('.history-3d-notice').inner_text()))

    layers = await attr_all(page, '[data-integrity-layer]', 'data-integrity-layer')
    check('integrity is rendered as five separate layers',
          layers == ['declared', 'lifecycle', 'tail', 'checksum', 'uncovered'], layers)
    verification = detail['integrity']['checksum_verification']
    mismatch_present = bool(verification.get('mismatched'))
    tone = await page.locator('[data-integrity-layer="checksum"] [data-layer-tone]').get_attribute('data-layer-tone')
    layer_text = await page.locator('[data-integrity-layer="checksum"]').inner_text()
    check('the checksum layer tone follows the reader verdict and a mismatch is never displayed as complete',
          (tone == 'bad' and '不得读作' in layer_text and '已验证完整' not in layer_text) == mismatch_present,
          (tone, verification.get('verdict'), layer_text[:220]))
    check('the known stale self-check is explained only where the evidence confines it',
          (await attr(page, '[data-checksum-pattern]', 'data-checksum-pattern') == 'known_stale_self_check')
          == (detail['declared']['recording_status'] == 'COMPLETE'
              and all(item['relative_path'] in ('episode.json', 'episode_complete.json') for item in detail['integrity']['checksum_verification']['mismatched'])),
          (await attr(page, '[data-checksum-pattern]', 'data-checksum-pattern'), detail['integrity']['checksum_verification']['verdict']))
    check('uncovered scope is named, so absence is not read as verification',
          'files not opened by this request' in (await page.locator('[data-integrity-layer="uncovered"]').inner_text()))
    check('the interface never claims an all-complete verdict',
          await attr(page, '[data-all-complete-forbidden]', 'data-all-complete-forbidden') == 'true')

    await wait_records(page)
    check('the first stream is read as a bounded page with its own cursor',
          await attr(page, '[data-stream-path]', 'data-stream-path') == 'events.jsonl'
          and await page.locator('[data-record-row]').count() > 0
          and await attr(page, '[data-cursor-line-index-clock]', 'data-cursor-line-index-clock') == 'true'
          and await attr(page, '[data-selected-time-base]', 'data-selected-time-base') == 'none')
    check('cross-stream unsynchronised stays visible while browsing one stream',
          await attr(page, '[data-cross-stream]', 'data-cross-stream') == 'unsynchronised'
          and '跨流未同步' in (await page.locator('[data-cross-stream]').inner_text()))
    check('the display time base is the one this stream declares',
          await attr(page, '[data-display-time-base]', 'data-display-time-base') in detail['time']['available_time_bases']['events']['time_bases_in_first_record'])
    base_line = await attr(page, '[data-cursor-line]', 'data-cursor-line')
    await page.locator('[data-history-next]').click()
    await page.wait_for_function('(before)=>document.querySelector("[data-cursor-line]").getAttribute("data-cursor-line")!==before', arg=base_line, timeout=20000)
    check('next record advances the cursor by one record of this page',
          await cursor_index(page) == 1 and await attr(page, '[data-cursor-line]', 'data-cursor-line') != base_line)
    await page.locator('[data-history-prev]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-cursor-index]')?.getAttribute('data-cursor-index') ?? '')==='0'", timeout=20000)
    check('previous record returns to the first record', await cursor_index(page) == 0)
    await page.locator('[data-history-play]').click()
    await page.wait_for_function("()=>Number((document.querySelector('[data-cursor-index]')?.getAttribute('data-cursor-index') ?? ''))>=2", timeout=20000)
    playing_index = await cursor_index(page)
    await page.locator('[data-history-play]').click()
    await page.wait_for_timeout(900)
    check('pause stops the cursor where it was', await cursor_index(page) == playing_index)
    check('playback is labelled as a UI cadence, never as the recorded frame rate',
          await attr(page, '[data-playback-cadence-ui-only]', 'data-playback-cadence-ui-only') == 'true'
          and '不是录制帧率' in (await page.locator('[data-playback-cadence-ui-only]').inner_text()))
    cursor_time = await attr(page, '[data-cursor-time]', 'data-cursor-time')
    check('the cursor time comes from the record with its declared unit, and a clock is shown only when the record carries one',
          re.fullmatch(r'\d+\.\d{6}', cursor_time or '') is not None
          and await attr(page, '[data-cursor-time-unit]', 'data-cursor-time-unit') == '秒'
          and await attr(page, '[data-cursor-clock]', 'data-cursor-clock') in ('null', 'backend_monotonic', 'sim', 'device'),
          (cursor_time, await attr(page, '[data-cursor-clock]', 'data-cursor-clock')))

    await page.locator('select[aria-label="时间基"]').select_option('sim_time_s')
    await wait_records(page, "()=>(document.querySelector('[data-display-time-base]')?.getAttribute('data-display-time-base') ?? '')==='sim_time_s'")
    seek_value = float(await attr(page, '[data-cursor-time]', 'data-cursor-time'))
    checked = await read_direct(page, '/api/v1/episodes/%s/streams/events/records' % complete_ref['episode_id'],
                                {'run_id': complete_ref['run_id'], 'limit': 5, 'offset': 0, 'time_base': 'sim_time_s', 'time_from': seek_value})
    await page.locator('input[aria-label="定位时间值"]').fill(str(seek_value))
    await page.locator('[data-history-seek]').click()
    await wait_records(page, f"()=>document.querySelector('[data-records-error]')===null && (document.querySelector('[data-cursor-index]')?.getAttribute('data-cursor-index') ?? '')==='0' && (document.querySelector('[data-selected-time-base]')?.getAttribute('data-selected-time-base') ?? '')==='sim_time_s'")
    check('seek uses the declared base with a range and reports the server result',
          await attr(page, '[data-selected-time-base]', 'data-selected-time-base') == 'sim_time_s'
          and float(await attr(page, '[data-cursor-time]', 'data-cursor-time')) >= seek_value)
    check('records lacking the selected base are counted exactly as the reader reports them',
          await attr(page, '[data-records-without-base]', 'data-records-without-base') == str(checked['time']['records_without_the_selected_base']),
          (await attr(page, '[data-records-without-base]', 'data-records-without-base'), checked['time']['records_without_the_selected_base']))
    check('the seek page keeps line_index and event_seq as position, never as a clock',
          await attr(page, '[data-cursor-line-index-clock]', 'data-cursor-line-index-clock') == 'true'
          and 'line_index_is_not_a_clock=true' in (await page.locator('[data-cursor-line-index-clock]').inner_text()))

    numeric = await read_direct(page, '/api/v1/episodes/%s/streams/events/records' % complete_ref['episode_id'], {'run_id': complete_ref['run_id'], 'limit': 1})
    check('numeric seeking is gated by the numeric_time_bases the reader itself declares',
          await attr(page, '[data-numeric-time-bases]', 'data-numeric-time-bases') == ','.join(numeric['time']['numeric_time_bases'])
          and 'wall_utc' not in numeric['time']['numeric_time_bases']
          and await attr(page, '[data-seek-gate]', 'data-seek-gate') == 'numeric',
          (await attr(page, '[data-numeric-time-bases]', 'data-numeric-time-bases'), numeric['time']['numeric_time_bases']))
    time_calls = lambda: len([r for r in report['requests'] if 'time_from' in r['url']])
    requests_before = time_calls()
    await page.locator('input[aria-label="定位时间值"]').fill('   ')
    await page.locator('[data-history-seek]').click()
    await page.wait_for_selector('[data-seek-error]', timeout=15000)
    check('a whitespace-only seek box is refused instead of becoming time_from=0',
          time_calls() == requests_before and '不发送请求' in (await page.locator('[data-seek-error]').inner_text()),
          (await page.locator('[data-seek-error]').inner_text())[:120])
    await page.locator('input[aria-label="定位时间值"]').fill('0')
    await page.locator('[data-history-seek]').click()
    await wait_records(page, "()=>(document.querySelector('[data-selected-time-base]')?.getAttribute('data-selected-time-base') ?? '')==='sim_time_s'")
    zero_calls = [r['url'] for r in report['requests'] if 'time_from=0' in r['url']]
    check('an explicit 0 is a legal seek value and is sent as time_from=0',
          bool(zero_calls) and await attr(page, '[data-page-returned]', 'data-page-returned') != '0', zero_calls[-1:])
    await page.locator('select[aria-label="时间基"]').select_option('wall_utc')
    await wait_records(page, "()=>(document.querySelector('[data-display-time-base]')?.getAttribute('data-display-time-base') ?? '')==='wall_utc'")
    check('wall_utc is refused for numeric seeking instead of guessing a calendar format',
          await attr(page, '[data-seek-gate]', 'data-seek-gate') == 'refused'
          and await page.locator('input[aria-label="定位时间值"]').is_disabled()
          and await page.locator('[data-history-seek]').is_disabled()
          and '日历' in (await attr(page, '[data-history-seek]', 'title') or ''))
    await page.locator('select[aria-label="时间基"]').select_option('sim_time_s')
    await wait_records(page, "()=>(document.querySelector('[data-display-time-base]')?.getAttribute('data-display-time-base') ?? '')==='sim_time_s'")
    check('switching the time base drops the previous seek value, error and notice',
          await page.locator('input[aria-label="定位时间值"]').input_value() == ''
          and await attr_or_none(page, '[data-seek-error]', 'data-seek-error') is None
          and await attr_or_none(page, '[data-history-notice]', 'data-history-notice') is None)
    await page.locator('input[aria-label="定位时间值"]').fill('1.5')
    await page.locator('[data-stream-option="control"]').click()
    await wait_records(page, "()=>(document.querySelector('[data-stream-path]')?.getAttribute('data-stream-path') ?? '')==='control.jsonl'")
    check('switching the stream drops the previous seek value and result notice',
          await page.locator('input[aria-label="定位时间值"]').input_value() == ''
          and await attr_or_none(page, '[data-history-notice]', 'data-history-notice') is None)
    await open_episode(page, complete_ref['run_id'], complete_ref['episode_id'])
    await page.locator('input[aria-label="定位时间值"]').fill('')
    check('reopening the episode leaves no carry-over seek text, error or notice',
          await page.locator('input[aria-label="定位时间值"]').input_value() == ''
          and await attr_or_none(page, '[data-seek-error]', 'data-seek-error') is None
          and await attr_or_none(page, '[data-history-notice]', 'data-history-notice') is None)

    await open_episode(page, failed_ref['run_id'], failed_ref['episode_id'])
    failed_detail = await read_direct(page, f"/api/v1/episodes/{failed_ref['episode_id']}", {'run_id': failed_ref['run_id']})
    expected_tail_tone = 'ok' if failed_detail['declared']['complete_tail_file_present'] else 'bad'
    check('a FAILED record reads with its declared status, its own tail state and its own lifecycle verdict',
          failed_detail['declared']['recording_status'] == 'FAILED'
          and 'FAILED' in (await page.locator('[data-integrity-layer="declared"]').inner_text())
          and failed_detail['integrity']['status'] in (await page.locator('[data-integrity-layer="lifecycle"]').inner_text())
          and await attr(page, '[data-integrity-layer="tail"] [data-layer-tone]', 'data-layer-tone') == expected_tail_tone
          and failed_detail['integrity']['status'] != 'complete',
          (failed_detail['integrity']['status'], failed_detail['declared']['complete_tail_file_present'],
           await attr(page, '[data-integrity-layer="tail"] [data-layer-tone]', 'data-layer-tone')))
    check('the FAILED record is not attributed to the known stale self-check when its declaration is not COMPLETE',
          await attr(page, '[data-checksum-pattern]', 'data-checksum-pattern') == 'unexplained'
          and '不归因于同一历史问题' in (await page.locator('[data-integrity-layer="checksum"]').inner_text()))
    check('opening another episode drops the previous cursor and stream context',
          await attr(page, '[data-detail-run]', 'data-detail-run') == failed_ref['run_id']
          and await cursor_index(page) == 0 and await attr(page, '[data-display-time-base]', 'data-display-time-base') != '')

    await page.locator('select[aria-label="记录分页大小"]').select_option('50')
    await page.locator('[data-stream-option="observations-index"]').click()
    await wait_records(page, "()=>(document.querySelector('[data-stream-path]')?.getAttribute('data-stream-path') ?? '')==='observations/index.jsonl'")
    rows_text = await page.locator('.history-record-table tbody').inner_text()
    check('the observation index page shows sample ids', 'rgbd_' in rows_text or 'laser_' in rows_text, rows_text[:120])
    media_cells = await page.locator('.history-record-table tbody tr').evaluate_all('rows=>rows.map(r=>r.children[4].textContent)')
    rgb_row = next((i for i, text in enumerate(media_cells) if '_rgb.png' in text), None)
    depth_row = next((i for i, text in enumerate(media_cells) if '_depth_m.npy' in text), None)
    check('rgb media is referenced by the record itself, not by a guessed filename', rgb_row is not None, media_cells[:4])
    await goto_index(page, rgb_row)
    await page.wait_for_function("()=>(document.querySelector('[data-asset-status]')?.getAttribute('data-asset-status') ?? '')==='bytes'", timeout=40000)
    asset = page.locator('[data-asset-uri]')
    media_ref = await attr(page, '[data-media-ref]', 'data-media-ref')
    check('the served asset is exactly the record reference with the server digest',
          await attr(page, '[data-asset-uri]', 'data-asset-uri') == media_ref
          and await attr(page, '[data-asset-media-type]', 'data-asset-media-type') == 'image/png'
          and re.fullmatch(r'[0-9a-f]{64}', await attr(page, '[data-asset-sha]', 'data-asset-sha') or '') is not None)
    declared = await attr(page, '[data-asset-declared]', 'data-asset-declared')
    asset_calls = [r['url'] for r in report['requests'] if '/assets/assets/rgb/' in r['url']]
    check('the declared digest is only claimed when the reader actually carried it, and is then verified server-side',
          (declared == 'null' and await attr(page, '[data-asset-digest-match]', 'data-asset-digest-match') == 'unknown')
          or (declared != 'null' and await attr(page, '[data-asset-digest-match]', 'data-asset-digest-match') == 'true'
              and f'sha256={declared}' in asset_calls[-1]), (declared, asset_calls[-1:]))
    await page.wait_for_function("()=>(document.querySelector('[data-asset-decoded]')?.getAttribute('data-asset-decoded') ?? '')==='ok'", timeout=30000)
    natural = await page.locator('[data-asset-image]').evaluate('el=>el.naturalWidth+"x"+el.naturalHeight')
    check('the rgb bytes actually decode in the browser', int(natural.split('x')[0]) > 0 and int(natural.split('x')[1]) > 0, natural)
    if depth_row is not None:
        await goto_index(page, depth_row)
        await page.wait_for_function("()=>(document.querySelector('[data-asset-status]')?.getAttribute('data-asset-status') ?? '')==='bytes'", timeout=40000)
        check('a non-image asset is reported as bytes, never faked as a picture',
              await attr(page, '[data-asset-not-inline]', 'data-asset-not-inline') == 'true'
              and 'application/octet-stream' in (await asset.inner_text()))
    await goto_index(page, 0)
    check('a record without a media reference says so instead of showing another sample',
          await attr(page, '[data-media-bound]', 'data-media-bound') == 'false'
          or 'asset_uri' in (await page.locator('[data-media-none]').inner_text()),
          await attr(page, '[data-media-bound]', 'data-media-bound'))
    report['real']['streams'] = [s['stream_id'] for s in failed_detail['streams']]
    report['real']['integrity'] = {'complete': detail['integrity']['status'], 'failed': failed_detail['integrity']['status'],
                                   'complete_pattern': await attr(page, '[data-checksum-pattern]', 'data-checksum-pattern')}

    missing = await page.request.get(a.url + '/api/v1/episodes/%s/streams/nope/records?run_id=%s' % (complete_ref['episode_id'], complete_ref['run_id']))
    body = await missing.json()
    check('the reader refuses an unsupported stream with its own code and supported list',
          missing.status == 404 and body['detail']['code'] == 'episode_stream_unsupported' and 'events' in body['detail']['supported'], body)
    unavailable = await attr_all(page, '[data-stream-option]', 'data-stream-available')
    check('stream availability is taken from the reader and rendered per stream', unavailable[0] == 'true' and len(unavailable) == len(failed_detail['streams']))

    # The m1p candidate distinguishes "this stream legitimately has no event_seq" from a load
    # failure; verify that against the record whose assets the probe already resolved.
    await open_episode(page, complete_ref['run_id'], complete_ref['episode_id'])
    await page.locator('select[aria-label="记录分页大小"]').select_option('50')
    await page.locator('[data-stream-option="observations-index"]').click()
    await wait_records(page, "()=>(document.querySelector('[data-stream-path]')?.getAttribute('data-stream-path') ?? '')==='observations/index.jsonl'")
    range_page = await read_direct(page, '/api/v1/episodes/%s/streams/observations-index/records' % complete_ref['episode_id'],
                                   {'run_id': complete_ref['run_id'], 'limit': 5, 'event_seq_from': 1, 'event_seq_to': 5})
    await page.locator('input[aria-label="event_seq 起点"]').fill('1')
    await page.locator('input[aria-label="event_seq 终点"]').fill('5')
    await page.locator('[data-history-filter]').click()
    await wait_records(page, "()=>(document.querySelector('[data-page-kind]')?.getAttribute('data-page-kind') ?? '')==='filtered-out-without-event-seq'")
    excluded = range_page['filtering']['event_seq_range']['excluded_without_valid_event_seq']
    check('an empty interval page is the reader’s exclusion count, not a failed load',
          range_page['records'] == [] and range_page['filtering']['event_seq_range']['active'] is True and excluded > 0
          and await attr(page, '[data-page-returned]', 'data-page-returned') == '0'
          and await attr(page, '[data-filtering-excluded]', 'data-filtering-excluded') == str(excluded)
          and await attr_or_none(page, '[data-records-error]', 'data-records-error') is None, (excluded,))
    check('the explanation names the legitimate absence and refuses to invent a sequence number',
          '合法地没有 event_seq' in await attr(page, '[data-page-explanation]', 'data-page-explanation')
          and '不补造序号' in await attr(page, '[data-page-explanation]', 'data-page-explanation'))
    check('excluded lines carry the reader’s own anomaly reasons and value types',
          (await attr(page, '[data-filtering-anomaly-reasons]', 'data-filtering-anomaly-reasons')) == ','.join(a['reason'] for a in range_page['filtering']['event_seq_range']['anomalies'])
          and int(await attr(page, '[data-filtering-anomalies]', 'data-filtering-anomalies')) == len(range_page['filtering']['event_seq_range']['anomalies']),
          (await attr(page, '[data-filtering-anomalies]', 'data-filtering-anomalies'), len(range_page['filtering']['event_seq_range']['anomalies'])))
    check('an empty page keeps the cursor unpositioned and playback unavailable',
          await attr(page, '[data-cursor-line]', 'data-cursor-line') == 'null'
          and await page.locator('[data-history-play]').is_disabled())
    await page.locator('[data-history-filter-clear]').click()
    await wait_records(page, "()=>(document.querySelector('[data-page-kind]')?.getAttribute('data-page-kind') ?? '')==='records'")
    check('clearing the interval reads records again on the same stream',
          await attr(page, '[data-filtering-active]', 'data-filtering-active') == 'false'
          and int(await attr(page, '[data-page-returned]', 'data-page-returned')) > 0)
    range_calls = len([r for r in report['requests'] if 'event_seq_from' in r['url']])
    await page.locator('input[aria-label="event_seq 起点"]').fill('2.5')
    await page.locator('[data-history-filter]').click()
    await page.wait_for_selector('[data-filter-error]', timeout=15000)
    check('a non-integer interval bound is refused locally and no request is sent',
          len([r for r in report['requests'] if 'event_seq_from' in r['url']]) == range_calls
          and '整数' in (await page.locator('[data-filter-error]').inner_text()))
    await page.locator('input[aria-label="event_seq 起点"]').fill('')
    await page.locator('[data-history-filter]').click()
    await wait_records(page, "()=>(document.querySelector('[data-page-kind]')?.getAttribute('data-page-kind') ?? '')==='records'")

    # observations-persist declares its media as rgb_uri / depth_uri / valid_mask_uri and has no
    # asset_uri at all, so the viewer must follow those fields instead of guessing a filename.
    persist_page = await read_direct(page, '/api/v1/episodes/%s/streams/observations-persist/records' % complete_ref['episode_id'],
                                     {'run_id': complete_ref['run_id'], 'limit': 3})
    first_persist = persist_page['records'][0]['record']
    await page.locator('[data-stream-option="observations-persist"]').click()
    await wait_records(page, "()=>(document.querySelector('[data-stream-path]')?.getAttribute('data-stream-path') ?? '')==='observations/persist.jsonl'")
    check('persist media comes from the record’s own rgb/depth/mask fields, with no asset_uri invented',
          all(first_persist.get(key) for key in ('rgb_uri', 'depth_uri', 'valid_mask_uri'))
          and 'asset_uri' not in first_persist
          and (await attr_all(page, '[data-record-row]', 'data-record-media-fields'))[0] == 'rgb_uri|depth_uri|valid_mask_uri'
          and await attr_all(page, '[data-media-ref]', 'data-media-field') == ['rgb_uri', 'depth_uri', 'valid_mask_uri'],
          await attr_all(page, '[data-media-ref]', 'data-media-field'))
    check('persist declares no named numeric time base, so seeking stays refused instead of invented',
          await attr(page, '[data-cursor-time-base]', 'data-cursor-time-base') == 'none'
          and await attr(page, '[data-seek-gate]', 'data-seek-gate') == 'refused'
          and await page.locator('input[aria-label="定位时间值"]').is_disabled()
          and '无该时间字段' in (await page.locator('.history-record-table tbody tr').first.inner_text()))
    await page.wait_for_function("()=>(document.querySelector('[data-asset-status]')?.getAttribute('data-asset-status') ?? '')==='bytes'", timeout=40000)
    check('the rgb reference the record declares is what is read and decoded',
          await attr(page, '[data-asset-uri]', 'data-asset-uri') == first_persist['rgb_uri']
          and await attr(page, '[data-asset-field]', 'data-asset-field') == 'rgb_uri'
          and await attr(page, '[data-asset-media-type]', 'data-asset-media-type') == 'image/png'
          and await attr(page, '[data-asset-decoded]', 'data-asset-decoded') == 'ok',
          (await attr(page, '[data-asset-field]', 'data-asset-field'), await attr(page, '[data-asset-decoded]', 'data-asset-decoded')))
    asset_lines = [await attr_or_none(page, f'[data-asset-{name}-line]', f'data-asset-{name}-line') for name in ('declared', 'verified', 'integrity')]
    check('declared digest, this-read verification and the integrity conclusion stay three separate statements',
          all(line is not None for line in asset_lines)
          and '完整性结论' in (await page.locator('[data-asset-integrity-line]').inner_text())
          and '本次读取' in (await page.locator('[data-asset-verified-line]').inner_text())
          and re.fullmatch(r'[0-9a-f]{64}', await attr(page, '[data-asset-sha]', 'data-asset-sha') or '') is not None)
    await page.locator('[data-media-pick="%s"]' % first_persist['depth_uri']).click()
    await page.wait_for_function("(uri)=>{const el=document.querySelector('[data-asset-uri]');return !!el && el.getAttribute('data-asset-uri')===uri && (document.querySelector('[data-asset-status]')?.getAttribute('data-asset-status') ?? '')==='bytes';}",
                                 arg=first_persist['depth_uri'], timeout=40000)
    check('the numpy depth asset is read as bytes and stated as not inline-displayable',
          await attr(page, '[data-asset-field]', 'data-asset-field') == 'depth_uri'
          and await attr(page, '[data-asset-media-type]', 'data-asset-media-type') == 'application/octet-stream'
          and await attr(page, '[data-asset-not-inline]', 'data-asset-not-inline') == 'true'
          and int(await attr(page, '[data-asset-bytes]', 'data-asset-bytes')) > 0)
    await page.locator('[data-media-pick="%s"]' % first_persist['valid_mask_uri']).click()
    await page.wait_for_function("(uri)=>{const el=document.querySelector('[data-asset-uri]');return !!el && el.getAttribute('data-asset-uri')===uri && (document.querySelector('[data-asset-decoded]')?.getAttribute('data-asset-decoded') ?? '')==='ok';}",
                                 arg=first_persist['valid_mask_uri'], timeout=40000)
    check('the valid-mask reference is read as its own asset, never reused from the rgb image',
          await attr(page, '[data-asset-field]', 'data-asset-field') == 'valid_mask_uri'
          and await attr(page, '[data-asset-uri]', 'data-asset-uri') == first_persist['valid_mask_uri'])
    report['real']['persist_refs'] = [first_persist['rgb_uri'], first_persist['depth_uri'], first_persist['valid_mask_uri']]
    report['real']['event_seq_filter'] = {'excluded': excluded, 'anomalies': len(range_page['filtering']['event_seq_range']['anomalies'])}


# ---- synthetic ---------------------------------------------------------------------------------------

def list_payload(rows, total=2, filters=None):
    return {'schema_version': 'unirobot-mobilecar-episode-read-1', 'read_only': True,
            'source': {'source_id': SOURCE_ID, 'adapter_id': 'mobilecar', 'recording_root': '/fixture', 'access': 'read_only_files', 'platform_writes': False},
            'retrieved_at': '2026-10-25T00:00:00Z',
            'paging': {'limit': 10, 'offset': 0, 'returned': len(rows), 'total_matches': total, 'next_offset': None, 'order': 'run_id_then_episode_id', 'declared_total_from_native_list': total},
            'filters': filters or {'run_id': None, 'recording_status': None, 'episode_id': None},
            'episodes': rows, 'integrity_scope': 'statuses are as declared by the native record files',
            'capability_limits': ['no replay execution']}


def row(run, episode, status='COMPLETE', readable=True, read_error=None):
    return {'run_id': run, 'episode_id': episode, 'contract_version': 'mobilecar-1.0', 'readable': readable, 'read_error': read_error,
            'task_language': 'fixture display name', 'operator_id': 'op', 'operator_kind': 'agent_ui', 'view_source': 'third_person_3d',
            'map_mode': 'unavailable', 'created_wall_utc': '2026-01-01T00:00:00Z', 'ended_wall_utc': '2026-01-01T00:01:00Z', 'segment_count': 1,
            'declared': {'recording_status': status, 'audit_status': 'COMPLETE' if status == 'COMPLETE' else 'INCOMPLETE', 'result': 'unknown', 'termination_reason': 'X', 'require_recording': True},
            'declaration_only': True}


def detail_payload(episode, **patch):
    value = {'schema_version': 'unirobot-mobilecar-episode-read-1', 'read_only': True,
             'source': {'source_id': SOURCE_ID, 'adapter_id': 'mobilecar', 'recording_root': '/fixture', 'access': 'read_only_files', 'platform_writes': False,
                        'archive_baseline': {'files_hashed': 696, 'aggregate_sha256': '6' * 64, 'meaning': 'change-detection reference'}},
             'retrieved_at': '2026-01-01T00:00:00Z',
             'identity': {'source_id': SOURCE_ID, 'adapter_id': 'mobilecar', 'run_id': 'run_a', 'episode_id': episode, 'native_contract_version': 'mobilecar-1.0',
                          'backend_generation': {'available': False, 'reason': 'not present in every record', 'distinct_values': None, 'scope': 'sampled'},
                          'segments': [{'recording_segment_id': 'seg_1', 'previous_recording_segment_id': None, 'status': 'COMPLETE', 'started_wall_utc': 'a', 'ended_wall_utc': 'b', 'termination_reason': 'X'}],
                          'episode_display_name_is_not_a_key': True},
             'declared': {'recording_status': 'COMPLETE', 'audit_status': 'COMPLETE', 'result': 'unknown', 'termination_reason': 'X', 'require_recording': True,
                          'complete_tail_file_present': True, 'declared_checksum_entries': 924, 'episode_json_readable': True, 'tail_json_readable': True},
             'integrity': {'status': 'complete', 'scope': 'this episode, as read by this request',
                           'this_read_evidence': {'episode_json_parsed': True, 'tail_json_parsed': True, 'episode_json_sha256': '0d' * 32, 'tail_json_sha256': 'b2' * 32, 'files_recomputed_here': ['episode.json']},
                           'checksum_verification': {'declared_entries': 924, 'matched': [], 'mismatched': [{'relative_path': 'episode.json', 'declared_sha256': '5e' * 32, 'actual_sha256': '0d' * 32}], 'verdict': 'mismatch_present', 'meaning': 'declared, not verified'},
                           'not_verified': ['files not opened by this request'], 'declaration_is_not_verification': True},
             'streams': [{'stream_id': 'events', 'relative_path': 'events.jsonl', 'format': 'jsonl', 'available': True, 'bytes': 10, 'records': 3, 'records_over_read_size_limit': 0},
                         {'stream_id': 'commands', 'relative_path': 'commands.jsonl', 'format': 'jsonl', 'available': False, 'bytes': None, 'records': None},
                         {'stream_id': 'observations-index', 'relative_path': 'observations/index.jsonl', 'format': 'jsonl', 'available': True, 'bytes': 10, 'records': 2},
                         {'stream_id': 'nope', 'relative_path': 'nope.jsonl', 'format': 'jsonl', 'available': True, 'bytes': 5, 'records': 3}],
             'time': {'record_order_is_native_append_order': True, 'clocks_declared_by_run_manifest': ['sim', 'backend_monotonic'],
                      'available_time_bases': {'events': {'available': True, 'time_bases_in_first_record': ['backend_monotonic_s', 'sim_time_s', 'wall_utc']}},
                      'units': {'*_s': 'seconds'}, 'browser_arrival_order_is_not_used': True, 'synchronized_across_streams': False},
             'action_semantics': {'recorded_target': ['actuator_reference'], 'command_intent': ['requested'], 'execution_feedback': ['feedback'], 'recorded_state': ['feedback_initial'], 'lifecycle': ['recording_start']},
             'recorded_model_identity': {'model_id': 'm', 'model_sha256': '3' * 64, 'scene_id': 's'},
             'three_d_replay': {'status': 'restricted', 'model_match': 'mismatch', 'scene_match': 'mismatch', 'recorded_transforms_available': False,
                                'live_geometry_or_actual_may_be_applied': False, 'reasons': ['recorded model digest differs from the production pin'], 'still_available': ['metadata']},
             'platform_association': {'known': False, 'validated_snapshot_ref': None, 'platform_session_id': None, 'reason': 'legacy_native_record_without_platform_sidecar'},
             'training_qualification': {'declared_eligibility_present': False, 'training_qualified': False, 'export_valid': None, 'quality_report_present': False, 'blocks_raw_read': False},
             'media_summary': {'uri_convention': 'assets/<kind>/<file>', 'declared_sha256_source': 'episode_complete.json', 'verification': 'only served assets',
                               'kinds': {'rgb': {'count': 1, 'sample': [{'relative_path': 'assets/rgb/good_rgb.png', 'bytes': 3, 'declared_sha256': 'a' * 64}], 'declared_sha256_coverage': '1/1'}}},
             'capability_limits': ['no replay execution', 'no native validate proxy']}
    value.update(patch)
    return value


def records_payload(episode, stream, records, **patch):
    value = {'schema_version': 'unirobot-mobilecar-episode-read-1', 'read_only': True,
             'source': {'source_id': SOURCE_ID, 'adapter_id': 'mobilecar', 'recording_root': '/fixture', 'access': 'read_only_files', 'platform_writes': False},
             'retrieved_at': '2026-01-01T00:00:00Z', 'identity': {'run_id': 'run_a', 'episode_id': episode, 'native_contract_version': 'mobilecar-1.0'},
             'stream': {'stream_id': stream, 'relative_path': f'{stream}.jsonl', 'format': 'jsonl', 'file_bytes': 10},
             'paging': {'limit': 5, 'offset': 0, 'returned': len(records), 'scanned_lines': len(records) + 1, 'skipped_before_offset': 0, 'next_offset': None, 'has_more': False},
             'cursor': {'order': 'native_append_order', 'first_line_index': 0, 'last_line_index': len(records) - 1, 'first_event_seq': 1, 'last_event_seq': len(records), 'line_index_is_not_a_clock': True},
             'time': {'selected_time_base': None, 'time_from': None, 'time_to': None, 'units': 'seconds for *_s', 'records_without_the_selected_base': 0,
                      'numeric_time_bases': ['arrival_time_s', 'backend_monotonic_s', 'measurement_time_s', 'sim_time_s'], 'synchronized_across_streams': False},
             'filtering': {'event_seq_range': {'from': None, 'to': None, 'active': False, 'excluded_without_valid_event_seq': 0, 'anomalies': []},
                           'note': 'when a range is active, records whose event_seq is missing, non-integer or boolean are excluded and counted'},
             'records': [{'line_index': i, 'record': r} for i, r in enumerate(records)],
             'integrity': {'corrupt_lines': [], 'lines_over_read_size_limit': [], 'declared_status': {'recording_status': 'COMPLETE', 'audit_status': 'COMPLETE', 'declaration_only': True}, 'scope': 'records returned by this page only', 'not_verified': ['records outside this page']}}
    value.update(patch)
    return value


EVENTS = [{'event_seq': 1, 'event_type': 'recording_start', 'backend_monotonic_s': 10.0, 'wall_utc': '2026-01-01T00:00:00Z'},
          {'event_seq': 2, 'event_type': 'actuator_reference', 'backend_monotonic_s': 10.5},
          {'event_seq': 3, 'event_type': 'feedback'}]
OBS = [{'sample_id': 'laser_1', 'sensor_kind': 'lidar', 'arrival_time_s': 1.0},
       {'sample_id': 'rgbd_1', 'sensor_kind': 'rgb', 'arrival_time_s': 2.0, 'asset_uri': 'assets/rgb/good_rgb.png', 'valid_mask_uri': 'assets/masks/none_valid.png'},
       {'sample_id': 'rgbd_2', 'sensor_kind': 'rgb', 'asset_uri': 'assets/rgb/bad_digest_rgb.png'},
       {'sample_id': 'rgbd_3', 'sensor_kind': 'rgb', 'asset_uri': 'assets/rgb/missing_rgb.png'},
       {'sample_id': 'rgbd_4', 'sensor_kind': 'rgb', 'asset_uri': 'assets/rgb/weird_rgb.zzz'},
       {'sample_id': 'rgbd_5', 'sensor_kind': 'depth', 'asset_uri': 'assets/depth/x_depth_m.npy'},
       {'sample_id': 'rgbd_6', 'sensor_kind': 'rgb', 'asset_uri': 'assets/rgb/slow_rgb.png'}]
SLOW = {'state': 'idle'}


async def synthetic_handler(route):
    request = route.request
    path = urlsplit(request.url).path
    query = parse_qs(urlsplit(request.url).query)
    if request.method != 'GET':
        await route.fulfill(status=405, content_type='text/html', body='<html>Method not allowed</html>'); return
    if '/assets/' in path:
        if request.url.endswith('bad_digest_rgb.png?run_id=run_a'):
            await route.fulfill(status=409, content_type='application/json', body=json.dumps({'detail': {'code': 'episode_asset_digest_mismatch', 'message': 'asset digest does not match the requested sha256', 'expected': 'a' * 64, 'actual': 'b' * 64}})); return
        if 'missing_rgb.png' in path:
            await route.fulfill(status=404, content_type='application/json', body=json.dumps({'detail': {'code': 'episode_asset_missing', 'message': 'asset is not present in the record', 'read_only': True}})); return
        if 'weird_rgb.zzz' in path:
            await route.fulfill(status=415, content_type='application/json', body=json.dumps({'detail': {'code': 'episode_asset_type_unsupported', 'message': 'unsupported asset type', 'suffix': '.zzz'}})); return
        if 'npy' in path:
            await route.fulfill(status=200, body=b'\x93NUMPY\x01\x00', content_type='application/octet-stream', headers={'X-Episode-Asset-Sha256': 'd' * 64}); return
        if 'slow_rgb.png' in path:
            await asyncio.sleep(2.2)
            await route.fulfill(status=200, body=tiny_png(), content_type='image/png', headers={'X-Episode-Asset-Sha256': 'e' * 64}); return
        await route.fulfill(status=200, body=tiny_png(), content_type='image/png', headers={'X-Episode-Asset-Sha256': 'a' * 64, 'X-Episode-Run-Id': 'run_a'}); return
    if path.endswith('/records'):
        stream = path.split('/streams/')[1].split('/')[0]
        if stream == 'nope':
            await route.fulfill(status=404, content_type='application/json', body=json.dumps({'detail': {'code': 'episode_stream_unsupported', 'message': 'unknown stream id: nope', 'read_only': True, 'supported': ['events', 'control', 'tail']}})); return
        if stream == 'broken':
            await route.fulfill(status=500, content_type='application/json', body=json.dumps({'detail': {'code': 'episode_record_read_failed', 'message': 'reader failed'}})); return
        if 'time_base' in query and 'time_from' not in query and 'time_to' not in query:
            await route.fulfill(status=400, content_type='application/json', body=json.dumps({'detail': {'code': 'time_range_required', 'message': 'time_base needs time_from or time_to in that base', 'read_only': True}})); return
        if query.get('time_base', [None])[0] == 'browser_arrival':
            await route.fulfill(status=400, content_type='application/json', body=json.dumps({'detail': {'code': 'time_base_unsupported', 'message': 'unknown time base: browser_arrival', 'read_only': True, 'supported': ['arrival_time_s', 'backend_monotonic_s', 'sim_time_s', 'wall_utc']}})); return
        if stream == 'events':
            if SLOW['state'] == 'pending':
                await asyncio.sleep(1.8)
                SLOW['state'] = 'done'
            base = query.get('time_base', [None])[0]
            rows = EVENTS
            filtering = records_payload('', '', [])['filtering']
            if 'event_seq_from' in query:
                low, high = int(query['event_seq_from'][0]), int((query.get('event_seq_to') or ['999999'])[0])
                rows = [item for item in EVENTS if low <= item['event_seq'] <= high]
                filtering = {'event_seq_range': {'from': low, 'to': high, 'active': True, 'excluded_without_valid_event_seq': 0, 'anomalies': []}, 'note': filtering['note']}
            page = records_payload(path.split('/episodes/')[1].split('/')[0], 'events', rows,
                                   time={**records_payload('', '', [])['time'], 'selected_time_base': base, 'records_without_the_selected_base': 1 if base else 0},
                                   filtering=filtering)
            await route.fulfill(json=page); return
        if 'event_seq_from' in query and stream == 'observations-index':
            # The reader answers 200 with an empty page and the exclusion count for a stream whose
            # native records legitimately carry no event_seq at all.
            low, high = int(query['event_seq_from'][0]), int((query.get('event_seq_to') or ['999999'])[0])
            episode = path.split('/episodes/')[1].split('/')[0]
            page = records_payload(episode, 'observations-index', [],
                                   paging={'limit': 5, 'offset': 0, 'returned': 0, 'scanned_lines': len(OBS), 'skipped_before_offset': 0, 'next_offset': None, 'has_more': False},
                                   cursor={'order': 'native_append_order', 'first_line_index': None, 'last_line_index': None, 'first_event_seq': None, 'last_event_seq': None, 'line_index_is_not_a_clock': True},
                                   filtering={'event_seq_range': {'from': low, 'to': high, 'active': True, 'excluded_without_valid_event_seq': len(OBS),
                                                                   'anomalies': [{'line_index': i, 'reason': 'event_seq_missing_or_not_integer', 'value_type': 'NoneType'} for i in range(len(OBS))]},
                                              'note': 'no sequence number is invented'})
            page['stream']['relative_path'] = 'observations/index.jsonl'
            await route.fulfill(json=page); return
        if stream == 'observations-index':
            page = records_payload(path.split('/episodes/')[1].split('/')[0], 'observations-index', OBS)
            page['stream']['relative_path'] = 'observations/index.jsonl'
            page['integrity'] = {**page['integrity'], 'corrupt_lines': [{'line_index': 1, 'error': 'json_invalid', 'column': 7}],
                                 'lines_over_read_size_limit': [7, 9], 'not_verified': ['records outside this page', 'asset payloads referenced by these records']}
            await route.fulfill(json=page); return
        await route.fulfill(json=records_payload(path.split('/episodes/')[1].split('/')[0], stream, [])); return
    if path.endswith('/streams'):
        await route.fulfill(json=detail_payload(path.split('/episodes/')[1])); return
    if path == '/api/v1/episodes':
        rows = [row('run_a', 'episode_ok'), row('run_a', 'episode_unreadable', readable=False, read_error='episode.json unreadable'),
                row('run_a', 'episode_ambiguous'), row('run_a', 'episode_other_mismatch'), row('run_a', 'episode_bad_schema'),
                row('run_b', 'episode_failed', status='FAILED')]
        status = (query.get('recording_status') or [None])[0]
        run = (query.get('run_id') or [None])[0]
        if status:
            rows = [item for item in rows if item['declared']['recording_status'] == status]
        if run:
            rows = [item for item in rows if item['run_id'] == run]
        await route.fulfill(json=list_payload(rows, total=len(rows),
                                             filters={'run_id': run, 'recording_status': status, 'episode_id': None})); return
    if re.fullmatch(r'/api/v1/episodes/[^/]+', path):
        episode = path.split('/')[-1]
        if episode == 'episode_ambiguous' and not query.get('run_id'):
            await route.fulfill(status=409, content_type='application/json', body=json.dumps({'detail': {'code': 'episode_id_ambiguous', 'message': 'episode id exists under multiple runs; run_id is required', 'episode_id': episode, 'runs': ['run_a', 'run_b']}})); return
        if episode == 'episode_bad_schema':
            await route.fulfill(json={'schema_version': 'unirobot-mobilecar-episode-read-2', 'read_only': True}); return
        payload = detail_payload(episode)
        payload['identity']['run_id'] = (query.get('run_id') or ['run_a'])[0]
        if episode == 'episode_other_mismatch':
            payload['integrity']['checksum_verification']['mismatched'] = [{'relative_path': 'events.jsonl', 'declared_sha256': '1' * 64, 'actual_sha256': '2' * 64}]
            payload['integrity']['checksum_verification']['verdict'] = 'mismatch_present'
        if episode == 'episode_unreadable':
            payload['declared'] = {**payload['declared'], 'recording_status': 'FAILED', 'audit_status': 'INCOMPLETE', 'complete_tail_file_present': False}
            payload['integrity'] = {**payload['integrity'], 'status': 'finalize_failed_missing_tail',
                                    'checksum_verification': {'declared_entries': 0, 'matched': [], 'mismatched': [], 'verdict': 'none'},
                                    'this_read_evidence': {**payload['integrity']['this_read_evidence'], 'files_recomputed_here': ['episode.json']}}
        await route.fulfill(json=payload); return
    await route.fulfill(status=404, content_type='application/json', body=json.dumps({'detail': {'code': 'episode_not_found', 'message': 'no Episode directory with that identity in this source'}}))


async def synthetic_flow(page):
    await wait_list(page)
    check('a readable=false row is listed with its reader-provided reason',
          await attr(page, '[data-episode-row="episode_unreadable"]', 'data-row-readable') == 'false'
          and 'episode.json unreadable' in (await page.locator('[data-episode-row="episode_unreadable"] [data-row-read-error]').inner_text()))
    check('no-results and no-recordings are distinguished by whether a filter was applied',
          not await page.locator('[data-list-empty]').count())
    await page.locator('select[aria-label="录制状态筛选"]').select_option('FAILED')
    await wait_list(page)
    check('the FAILED filter keeps only FAILED declarations in the DOM',
          await attr(page, '[data-episode-row="episode_failed"]', 'data-row-status') == 'FAILED')
    await page.locator('select[aria-label="录制状态筛选"]').select_option('RECORDING')
    await wait_list(page)
    check('an empty filtered page reads as “no match”, not as an archive with nothing recorded',
          await attr(page, '[data-list-empty]', 'data-list-empty') == 'no-match'
          and '筛选无匹配' in (await page.locator('[data-list-empty]').inner_text())
          and 'status=RECORDING' in (await page.locator('[data-list-empty]').inner_text()),
          (await page.locator('[data-list-empty]').inner_text())[:180])
    await page.locator('select[aria-label="录制状态筛选"]').select_option('')
    await wait_list(page)

    await page.locator('[data-episode-open="episode_ok"]').click()
    await page.wait_for_selector('[data-detail-episode="episode_ok"]', timeout=30000)
    check('an unknown backend_generation is shown as unknown instead of a value',
          await attr(page, '[data-generation-available]', 'data-generation-available') == 'false'
          and 'not present in every record' in (await page.locator('[data-generation-available]').inner_text()))
    check('a restricted 3D state refuses live geometry',
          await attr(page, '[data-three-d-status]', 'data-three-d-status') == 'restricted'
          and await attr(page, '[data-live-geometry-applied]', 'data-live-geometry-applied') == 'false'
          and 'differs from the production pin' in (await page.locator('.history-3d-notice').inner_text()))
    check('training_qualified=false is displayed but does not block the read',
          'training_qualified=false' in (await page.locator('[data-training-blocks-read]').inner_text())
          and await attr(page, '[data-training-blocks-read]', 'data-training-blocks-read') == 'false')
    await wait_records(page)
    check('an unavailable stream is listed as unavailable and cannot be opened',
          await attr(page, '[data-stream-option="commands"]', 'data-stream-available') == 'false'
          and await page.locator('[data-stream-option="commands"]').is_disabled()
          and await attr(page, '[data-missing-stream]', 'data-missing-stream') == 'true')
    await page.locator('[data-stream-option="nope"]').click()
    await page.wait_for_selector('[data-records-error]', timeout=20000)
    check('an unsupported stream is refused with the server code and its supported list',
          'episode_stream_unsupported' in (await page.locator('[data-records-error]').inner_text())
          and 'supported=events,control,tail' in (await page.locator('[data-records-error]').inner_text())
          and await attr(page, '[data-stream-bound]', 'data-stream-bound') == 'false')
    await page.locator('[data-stream-option="events"]').click()
    await wait_records(page)
    rows = await attr_all(page, '[data-record-row]', 'data-record-row')
    check('the page is bounded to the reader records', rows == ['0', '1', '2'], rows)
    missing_time = await attr_all(page, '[data-record-row]', 'data-record-time-present')
    check('a record without the selected time base is never shown as zero',
          'false' in missing_time
          and '无该时间字段' in await page.locator('[data-record-row="2"]').inner_text()
          and ' 0 ' not in await page.locator('[data-record-row="2"]').inner_text(), missing_time)
    await page.locator('[data-history-next]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-cursor-index]')?.getAttribute('data-cursor-index') ?? '')==='1'", timeout=15000)
    await page.locator('[data-history-next]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-cursor-index]')?.getAttribute('data-cursor-index') ?? '')==='2'", timeout=15000)
    await page.locator('[data-history-next]').click()
    check('the end of a page with has_more=false stops instead of inventing records',
          await cursor_index(page) == 2 and 'has_more=false' in (await page.locator('[data-history-notice]').inner_text()))

    await page.locator('[data-stream-option="observations-index"]').click()
    await wait_records(page, "()=>(document.querySelector('[data-stream-path]')?.getAttribute('data-stream-path') ?? '')==='observations/index.jsonl'")
    scope_text = await page.locator('[data-page-scope]').evaluate('e=>e.parentElement.innerText')
    check('corrupt and over-size lines are surfaced per page with the reader’s own line numbers',
          await attr(page, '[data-corrupt-lines]', 'data-corrupt-lines') == '1'
          and await attr(page, '[data-over-size-lines]', 'data-over-size-lines') == '2'
          and '超限行 7,9' in scope_text and '@列 7' in scope_text
          and 'asset payloads referenced by these records' in scope_text, scope_text[:220])
    check('a record without a media reference is stated, not filled with another sample',
          await attr(page, '[data-media-bound]', 'data-media-bound') == 'false'
          and 'asset_uri' in (await page.locator('[data-media-none]').inner_text()))
    await goto_index(page, 1)
    await page.wait_for_function("()=>(document.querySelector('[data-asset-status]')?.getAttribute('data-asset-status') ?? '')==='bytes'", timeout=20000)
    check('media comes from the record’s own asset_uri and both references are listed',
          await attr(page, '[data-asset-uri]', 'data-asset-uri') == 'assets/rgb/good_rgb.png'
          and sorted(await attr_all(page, '[data-media-ref]', 'data-media-ref')) == sorted(['assets/rgb/good_rgb.png', 'assets/masks/none_valid.png']),
          await attr_all(page, '[data-media-ref]', 'data-media-ref'))
    check('the declared digest is sent to the server and the served digest matches it',
          await attr(page, '[data-asset-digest-match]', 'data-asset-digest-match') == 'true'
          and f'sha256={"a" * 64}' in [r['url'] for r in report['requests'] if '/assets/assets/rgb/good_rgb.png' in r['url']][-1])
    await page.wait_for_function("()=>(document.querySelector('[data-asset-decoded]')?.getAttribute('data-asset-decoded') ?? '')==='ok'", timeout=20000)
    check('the served bytes really decode as an image',
          await page.locator('[data-asset-image]').evaluate('el=>el.naturalWidth+"x"+el.naturalHeight') == '1x1')
    for position, code, note in ((2, 'episode_asset_digest_mismatch', '实际摘要'), (3, 'episode_asset_missing', '该媒体在记录中不存在'),
                                 (4, 'episode_asset_type_unsupported', '后缀'), (5, '', '不能内联显示')):
        await goto_index(page, position)
        await page.wait_for_function("()=>['bytes','failed'].includes((document.querySelector('[data-asset-status]')?.getAttribute('data-asset-status') ?? ''))", timeout=20000)
        text = await page.locator('[data-asset-uri]').inner_text()
        if code:
            check(f'the reader’s {code} is shown verbatim instead of a placeholder image',
                  await attr(page, '[data-asset-status]', 'data-asset-status') == 'failed'
                  and code in (await page.locator('[data-asset-error]').inner_text()) and note in text, text[:200])
        else:
            check('a non-image asset is reported as bytes with its real content type',
                  await attr(page, '[data-asset-status]', 'data-asset-status') == 'bytes'
                  and await attr(page, '[data-asset-not-inline]', 'data-asset-not-inline') == 'true'
                  and 'application/octet-stream' in text, text[:200])

    await page.locator('[data-episode-open="episode_ok"]').click()
    await page.wait_for_selector('[data-detail-episode="episode_ok"]', timeout=30000)
    await wait_records(page)
    await page.locator('select[aria-label="时间基"]').select_option('sim_time_s')
    await page.wait_for_function("()=>(document.querySelector('[data-display-time-base]')?.getAttribute('data-display-time-base') ?? '')==='sim_time_s'", timeout=20000)
    await page.locator('select[aria-label="时间基"]').select_option('wall_utc')
    await page.wait_for_function("()=>(document.querySelector('[data-display-time-base]')?.getAttribute('data-display-time-base') ?? '')==='wall_utc'", timeout=20000)
    check('a text time base is not offered for numeric seeking instead of guessing a format',
          await page.locator('[data-history-seek]').is_disabled()
          and await page.locator('input[aria-label="定位时间值"]').is_disabled()
          and '需要数值时间基' in (await page.locator('input[aria-label="定位时间值"]').get_attribute('placeholder') or ''))
    check('the refusal lists the numeric bases the reader accepts instead of assuming one',
          await attr(page, '[data-seek-gate]', 'data-seek-gate') == 'refused'
          and 'numeric_time_bases=' in (await attr(page, '[data-history-seek]', 'title') or '')
          and 'wall_utc' not in (await attr(page, '[data-numeric-time-bases]', 'data-numeric-time-bases') or ''))
    await page.locator('select[aria-label="时间基"]').select_option('backend_monotonic_s')
    await wait_records(page, "()=>(document.querySelector('[data-display-time-base]')?.getAttribute('data-display-time-base') ?? '')==='backend_monotonic_s'")
    check('a numeric base re-enables the seek box that the calendar base disabled',
          await attr(page, '[data-seek-gate]', 'data-seek-gate') == 'numeric'
          and await page.locator('input[aria-label="定位时间值"]').is_enabled())
    time_calls = len([r for r in report['requests'] if 'time_from' in r['url']])
    await page.locator('input[aria-label="定位时间值"]').fill('   ')
    await page.locator('[data-history-seek]').click()
    await page.wait_for_selector('[data-seek-error]', timeout=15000)
    check('a whitespace-only seek box sends no request and is not turned into 0',
          len([r for r in report['requests'] if 'time_from' in r['url']]) == time_calls
          and '不发送请求' in (await page.locator('[data-seek-error]').inner_text()))
    await page.locator('input[aria-label="定位时间值"]').fill('0')
    await page.locator('[data-history-seek]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-selected-time-base]')?.getAttribute('data-selected-time-base') ?? '')==='backend_monotonic_s'", timeout=20000)
    check('an explicit 0 is a legal value and is sent as time_base + time_from=0',
          any('time_base=backend_monotonic_s' in r['url'] and 'time_from=0' in r['url'] for r in report['requests']))
    await page.locator('select[aria-label="时间基"]').select_option('sim_time_s')
    await wait_records(page, "()=>(document.querySelector('[data-display-time-base]')?.getAttribute('data-display-time-base') ?? '')==='sim_time_s'")
    check('changing the time base drops both the previous value and the previous refusal',
          await page.locator('input[aria-label="定位时间值"]').input_value() == ''
          and await attr_or_none(page, '[data-seek-error]', 'data-seek-error') is None)

    # An empty result page must not keep the previous record's media on screen.
    await page.locator('[data-stream-option="observations-index"]').click()
    await wait_records(page, "()=>(document.querySelector('[data-stream-path]')?.getAttribute('data-stream-path') ?? '')==='observations/index.jsonl'")
    await goto_index(page, 1)
    await page.wait_for_function("()=>(document.querySelector('[data-asset-status]')?.getAttribute('data-asset-status') ?? '')==='bytes'", timeout=20000)
    await page.locator('input[aria-label="event_seq 起点"]').fill('1')
    await page.locator('input[aria-label="event_seq 终点"]').fill('2')
    await page.locator('[data-history-filter]').click()
    await wait_records(page, "()=>(document.querySelector('[data-page-kind]')?.getAttribute('data-page-kind') ?? '')==='filtered-out-without-event-seq'")
    check('an empty page clears the media slot instead of keeping the previous record’s image',
          await page.locator('[data-asset-uri]').count() == 0
          and await attr(page, '[data-media-bound]', 'data-media-bound') == 'false'
          and int(await attr(page, '[data-filtering-excluded]', 'data-filtering-excluded')) == len(OBS)
          and await attr(page, '[data-cursor-line]', 'data-cursor-line') == 'null')
    await page.locator('[data-history-filter-clear]').click()
    await wait_records(page, "()=>(document.querySelector('[data-page-kind]')?.getAttribute('data-page-kind') ?? '')==='records'")
    await page.locator('[data-stream-option="events"]').click()
    await wait_records(page, "()=>(document.querySelector('[data-stream-path]')?.getAttribute('data-stream-path') ?? '')==='events.jsonl'")

    await page.locator('[data-episode-open="episode_ok"]').click()
    await page.wait_for_selector('[data-detail-episode="episode_ok"]', timeout=30000)
    await wait_records(page)
    await page.locator('input[aria-label="按 episode_id 打开"]').fill('episode_ambiguous')
    await page.locator('[data-history-open]').click()
    await page.wait_for_selector('[data-ambiguous-runs]', timeout=30000)
    check('a bare episode_id is refused as ambiguous and the candidate runs are shown verbatim',
          await attr(page, '[data-ambiguous-runs]', 'data-ambiguous-runs') == 'run_a,run_b'
          and 'episode_id_ambiguous' in (await page.locator('[data-detail-error]').inner_text())
          and await attr(page, '[data-detail-bound]', 'data-detail-bound') == 'false')
    await page.locator('[data-ambiguous-pick="run_b"]').click()
    await page.wait_for_selector('[data-detail-run="run_b"]', timeout=30000)
    check('picking a candidate run re-reads with that run_id instead of cross-reading',
          await attr(page, '[data-detail-episode]', 'data-detail-episode') == 'episode_ambiguous'
          and 'run_id=run_b' in [r['url'] for r in report['requests'] if r['url'].count('/api/v1/episodes/episode_ambiguous') and 'run_id' in r['url']][-1])

    await page.locator('[data-episode-open="episode_other_mismatch"]').click()
    await page.wait_for_selector('[data-detail-episode="episode_other_mismatch"]', timeout=30000)
    check('a mismatch outside the known stale self-check scope is reported without a cause',
          await attr(page, '[data-checksum-pattern]', 'data-checksum-pattern') == 'unexplained'
          and '不归因于同一历史问题' in (await page.locator('[data-integrity-layer="checksum"]').inner_text())
          and 'events.jsonl' in (await page.locator('[data-integrity-layer="checksum"]').inner_text()))

    await page.locator('[data-episode-open="episode_unreadable"]').click()
    await page.wait_for_selector('[data-detail-episode="episode_unreadable"]', timeout=30000)
    check('a missing tail reads as finalize_failed_missing_tail with the tail layer failing',
          'finalize_failed_missing_tail' in (await page.locator('[data-integrity-layer="lifecycle"]').inner_text())
          and await attr(page, '[data-integrity-layer="tail"] [data-layer-tone]', 'data-layer-tone') == 'bad')

    await page.locator('[data-episode-open="episode_bad_schema"]').click()
    await page.wait_for_selector('[data-detail-error]', timeout=30000)
    check('a payload that is not the declared read contract is refused, not rendered',
          'unirobot-mobilecar-episode-read-1' in (await page.locator('[data-detail-error]').inner_text())
          and await attr(page, '[data-detail-bound]', 'data-detail-bound') == 'false')

    # Late responses must never overwrite the newer context: a slow records page and a slow asset
    # response both arrive after the selection has already moved on.
    await page.locator('[data-episode-open="episode_ok"]').click()
    await page.wait_for_selector('[data-detail-episode="episode_ok"]', timeout=30000)
    await wait_records(page)
    SLOW['state'] = 'pending'
    await page.locator('[data-stream-option="events"]').click()
    await page.wait_for_timeout(200)
    await page.locator('[data-stream-option="observations-index"]').click()
    await wait_records(page, "()=>(document.querySelector('[data-stream-path]')?.getAttribute('data-stream-path') ?? '')==='observations/index.jsonl'")
    await goto_index(page, 1)
    await page.wait_for_function("()=>(document.querySelector('[data-asset-status]')?.getAttribute('data-asset-status') ?? '')==='bytes'", timeout=20000)
    await goto_index(page, 6)
    await page.wait_for_function("()=>(document.querySelector('[data-asset-status]')?.getAttribute('data-asset-status') ?? '')==='loading'", timeout=20000)
    await goto_index(page, 0)
    await asyncio.sleep(3.0)
    late_current = await attr(page, '[data-current-stream]', 'data-current-stream')
    late_path = await attr(page, '[data-stream-path]', 'data-stream-path')
    check('a late records page cannot overwrite the stream selected meanwhile',
          late_current == 'observations-index' and late_path == 'observations/index.jsonl', (late_current, late_path))
    check('a late asset response cannot paint a sample the cursor has left behind',
          await attr(page, '[data-media-bound]', 'data-media-bound') == 'false'
          and await attr_or_none(page, '[data-asset-uri]', 'data-asset-uri') is None,
          await attr_or_none(page, '[data-asset-uri]', 'data-asset-uri'))
    await page.screenshot(path=str(a.output / 'synthetic.png'), full_page=True)



async def boundary_checks(page):
    probes = [('POST', '/api/v1/episodes/episode_x/validate'), ('POST', '/api/v1/episodes/episode_x'),
              ('GET', '/api/v1/episodes/episode_x/assessment'), ('POST', '/api/v1/episodes/episode_x/records'),
              ('POST', '/api/v1/runs/run_x/stop'), ('POST', '/api/v1/commands'), ('POST', '/api/v1/reset'),
              ('GET', '/api/v1/episodes/../secrets'), ('DELETE', '/api/v1/episodes/episode_x'),
              ('PUT', '/api/v1/episodes/episode_x/streams/events/records')]
    refused = []
    for method, path in probes:
        response = await page.request.fetch(a.url + path, method=method, data=b'{}' if method != 'GET' else None, fail_on_status_code=False)
        body = await response.text()
        refused.append({'method': method, 'path': path, 'status': response.status,
                        'gateway': 'allowlisted' in body or 'not allowed' in body.lower(),
                        'html_error_page': 'text/html' in (response.headers.get('content-type') or '')})
    report['gateway_boundary'] = refused
    check('the gateway refuses episode validate/assessment and every control or native path with its own error page',
          all(item['status'] in (404, 405) and item['gateway'] and item['html_error_page'] for item in refused),
          [item for item in refused if not (item['status'] in (404, 405) and item['gateway'] and item['html_error_page'])])
    check('the history view never renders a 3D canvas or a Target/Ghost control',
          await page.evaluate("()=>({canvas:document.querySelectorAll('canvas').length, target:document.querySelectorAll('[data-target-readout],[data-ghost-toggle],[data-workbench-tool]').length})") == {'canvas': 0, 'target': 0})


async def live_isolation(page):
    chip = page.locator('.monitor-chip')
    before = await chip.inner_text()
    history_before = await page.evaluate(fingerprint_script())
    await page.wait_for_timeout(3200)
    after = await chip.inner_text()
    check('the live source keeps polling in the background while history is open', before != after, (before, after))
    check('live polling never rewrites the history view',
          await page.evaluate(fingerprint_script()) == history_before, (history_before, await page.evaluate(fingerprint_script())))


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
            if a.mode == 'real': await live_isolation(page)
            episodes = [r for r in report['requests'] if '/api/v1/episodes' in r['url']]
            check('every history request is a GET on an allowlisted read path',
                  all(r['method'] == 'GET' for r in episodes) and len(episodes) > 0, [r for r in episodes if r['method'] != 'GET'][:3])
            check('the history view issues no mobilecar snapshot, session, control or reset request',
                  not [r for r in report['requests'] if any(token in urlsplit(r['url']).path for token in ('/api/v1/commands', '/api/v1/reset', '/api/v1/runs', '/recording/', '/api/v1/sessions'))],
                  [r['url'] for r in report['requests']][:4])
            await page.get_by_role('button', name='返回实时视图', exact=True).click()
            await page.wait_for_selector('.history-view', state='detached', timeout=30000)
            footer = await page.locator('.status-bar').inner_text()
            check('leaving history states the explicit source restore and that nothing was backfilled',
                  '已从历史浏览返回' in footer and '没有回填任何本地 Target' in footer, footer[:200])
            check('no uncaught browser errors', not report['errors'], report['errors'][:3])
            report['real']['history_requests'] = len(episodes)
            report['status'] = 'passed'
        except Exception as exc:
            report['exception'] = str(exc); report['traceback'] = traceback.format_exc()
            await page.screenshot(path=str(a.output / 'failure.png'), full_page=True)
        finally:
            (a.output / 'browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            await browser.close()

asyncio.run(main())
print(json.dumps({'status': report['status'], 'mode': a.mode, 'checks': len(report['checks']), 'error': report.get('exception')}, ensure_ascii=False))
raise SystemExit(report['status'] != 'passed')
