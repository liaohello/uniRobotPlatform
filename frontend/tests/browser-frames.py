"""frame-link-2 browsing and the fixed model reference acceptance.

  --mode real       against a frontend preview whose upstream is the frame-link-2 candidate (18969).
                    Reads the actual COMPLETE and FAILED records, compares every displayed value with a
                    direct GET of the same page, walks pages by next_offset/has_more/next_qualifying,
                    opens a frame by sample_id, applies a contract-allowed time window, then reads the
                    selected frame's robot-state, its nine per-part mapping rows and the frozen
                    bundle's 23 assets, and assembles the fixed model reference from history bytes only.
                    Only GET requests are issued; the archive itself is never written.
  --mode synthetic  the same product code against isolated page.route fixtures (synthetic data, never
                    the archive): the v2 empty selectable_time_bases, absent/refused media, digest
                    mismatch, non-image bytes, ambiguous_kind / ambiguous_candidates with more than one
                    candidate, a state whose recorded_state is null, a late frame page and a late
                    robot-state after a switch, contract-mismatch payloads for both contracts, stream
                    unavailable, invalid sample ids, model identity mismatch, asset digest mismatch,
                    the `verified` joint-driving gate and a 409 history_asset_revision_changed.

Both modes assert that the browser issues no non-GET request, that the gateway carries the three
history GETs as its own exact routes (no wildcard under /episodes/{id}/), that mesh bytes never come
from the live scene asset route, that the pane never claims 3D replay, cross-stream sync or a total
frame count, and that live polling never rewrites the frame DOM.
"""
import argparse, asyncio, hashlib, json, re, struct, traceback, zlib
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

p = argparse.ArgumentParser()
p.add_argument('url'); p.add_argument('output', type=Path)
p.add_argument('--mode', choices=('real', 'synthetic'), default='real')
p.add_argument('--complete-run', default='run_0104613ff7364ae78cf2f3946bd45f7b')
p.add_argument('--complete-episode', default='episode_27bfed5427684795b361cd2ec21e9aa7')
p.add_argument('--failed-run', default='run_1f6fb34853f94130aadedb8fa486705b')
p.add_argument('--failed-episode', default='episode_879cf70489064a3b83bb15b5395a8341')
a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
report = {'scope': f'{a.mode} frame-link-2 + history-pose-1 acceptance against {a.url}', 'mode': a.mode,
          'checks': [], 'errors': [], 'requests': [], 'real': {}, 'status': 'failed'}
SOURCE_ID = 'mobilecar-server-history-20261017'
FRAME_SCHEMA = 'unirobot-mobilecar-frame-link-2'
POSE_SCHEMA = 'unirobot-mobilecar-history-pose-1'
GEOMETRY_SCHEMA = 'unirobot-mobilecar-geometry-2'
READ_SCHEMA = 'unirobot-mobilecar-episode-read-1'
REFUSAL = '<html>Only allowlisted platform endpoints are exposed</html>'


def tiny_png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\x11\x22\x33')) + chunk(b'IEND', b''))


def tiny_stl():
    """One binary STL triangle (normal + 3 vertices + attribute bytes): enough for the mesh loader."""
    return (b'\x00' * 80 + struct.pack('<I', 1)
            + struct.pack('<12f', 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.02, 0.0, 0.0, 0.0, 0.02, 0.0) + b'\x00\x00')


PNG = tiny_png(); STL = tiny_stl(); STL_SHA = hashlib.sha256(STL).hexdigest()


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


async def wait_model(page, status, timeout=60000):
    try:
        await page.wait_for_function(f"()=>(document.querySelector('[data-model-pane]')?.getAttribute('data-model-status') ?? '')==='{status}'", timeout=timeout)
    except PlaywrightTimeoutError:
        actual = await page.evaluate("()=>{const p=document.querySelector('[data-model-pane]');return [p?.getAttribute('data-model-status')??'absent',(p?.querySelector('[data-model-stage]')?.innerText??'').slice(0,300)]}")
        raise AssertionError(f'model pane never reached {status!r}; it stayed {actual[0]!r} · {actual[1]}')


async def read_direct(page, path, params=None):
    url = a.url + path
    if params: url += '?' + '&'.join(f'{k}={v}' for k, v in params.items())
    return await (await page.request.get(url)).json()


async def wait_asset_settled(page, timeout=40000):
    """Bytes, a refusal or a decode failure are all settled states; 'loading' and 'idle' are not, so no
    assertion ever races the asset request or the image decode."""
    await page.wait_for_function("()=>['bytes','failed','not-loaded'].includes((document.querySelector('[data-frame-asset-status]')?.getAttribute('data-frame-asset-status') ?? ''))", timeout=timeout)


async def wait_asset_uri(page, uri, timeout=40000):
    await page.wait_for_function("(uri)=>(document.querySelector('[data-frame-asset-uri]')?.getAttribute('data-frame-asset-uri') ?? '')===uri", arg=uri, timeout=timeout)


async def open_episode(page, run_id, episode_id, expect='frames'):
    """The frame pane keeps the previous Episode's page on screen until its own read lands, so every
    step waits for the pane to be bound to *this* identity (or to show this identity's error)."""
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
    """Everything the pane asserts on, read in one DOM pass so comparisons stay consistent."""
    return page.evaluate("""()=>{const g=(s,n)=>document.querySelector(s)?.getAttribute(n)??null;
      const q=(s,n)=>[...document.querySelectorAll(s)].map(e=>e.getAttribute(n));
      return {bound:g('[data-frame-view]','data-frame-bound'),schema:g('[data-frame-view]','data-frame-schema'),
        episode:g('[data-frame-view]','data-frame-episode'),run:g('[data-frame-view]','data-frame-run'),
        currentSample:g('[data-frame-current-sample]','data-frame-current-sample'),
        returned:g('[data-frame-returned]','data-frame-returned'),offset:g('[data-frame-offset]','data-frame-offset'),
        nextOffset:g('[data-frame-next-offset]','data-frame-next-offset'),hasMore:g('[data-frame-has-more]','data-frame-has-more'),
        nextQualifying:g('[data-frame-next-qualifying]','data-frame-next-qualifying'),
        examined:g('[data-frame-examined]','data-frame-examined'),postExamined:g('[data-frame-post-examined]','data-frame-post-examined'),
        linesRead:g('[data-frame-lines-read]','data-frame-lines-read'),wholeFile:g('[data-frame-whole-file-scanned]','data-frame-whole-file-scanned'),
        excludedBySample:g('[data-frame-excluded-by-sample]','data-frame-excluded-by-sample'),
        migrationFrom:g('[data-frame-migration-from]','data-frame-migration-from'),migrationTo:g('[data-frame-migration-to]','data-frame-migration-to'),
        pageKind:g('[data-frame-page-kind]','data-frame-page-kind'),index:g('[data-frame-index]','data-frame-index'),
        line:g('[data-frame-line]','data-frame-line'),persistSeq:g('[data-frame-persist-seq]','data-frame-persist-seq'),
        linkage:g('[data-frame-linkage-status]','data-frame-linkage-status'),primaryMatched:g('[data-frame-primary-matched]','data-frame-primary-matched'),
        primaryAmbiguous:g('[data-frame-primary-ambiguous]','data-frame-primary-ambiguous'),ambiguousCount:g('[data-frame-ambiguous-count]','data-frame-ambiguous-count'),
        declaredRef:g('[data-frame-declared-ref]','data-frame-declared-ref'),stateStatus:g('[data-frame-state-status]','data-frame-state-status'),
        singleState:g('[data-frame-single-state]','data-frame-single-state'),stateCandidates:g('[data-frame-state-candidates]','data-frame-state-candidates'),
        emptyPayload:g('[data-frame-state-empty-payload]','data-frame-state-empty-payload'),
        eventSeq:g('[data-frame-event-seq]','data-frame-event-seq'),recordPosition:g('[data-frame-record-position]','data-frame-record-position'),
        stateQuantityKeys:g('[data-state-quantity-keys]','data-state-quantity-keys'),
        recorderDeclared:g('[data-recorder-declared]','data-recorder-declared'),recorderAgrees:g('[data-recorder-agrees]','data-recorder-agrees'),
        selectable:(g('[data-frame-selectable-bases]','data-frame-selectable-bases')||'').split(',').filter(Boolean),
        windowBase:g('[data-frame-window-base]','data-frame-window-base'),windowFrom:g('[data-frame-window-from]','data-frame-window-from'),
        windowTo:g('[data-frame-window-to]','data-frame-window-to'),contextSample:g('[data-frame-context-sample]','data-frame-context-sample'),
        windowGate:g('[data-frame-window-gate]','data-frame-window-gate'),windowReason:g('[data-frame-window-reason]','data-frame-window-reason'),
        notice:document.querySelector('[data-frame-notice]')?.innerText??null,error:document.querySelector('[data-frame-error]')?.innerText??null,
        explanation:g('[data-frame-page-explanation]','data-frame-page-explanation'),
        linkageScope:g('[data-frame-linkage-scope]','data-frame-linkage-scope'),roleCoverage:g('[data-frame-role-coverage]','data-frame-role-coverage'),
        statusPrecedence:g('[data-frame-status-precedence]','data-frame-status-precedence'),
        assetUri:g('[data-frame-asset-uri]','data-frame-asset-uri'),assetStatus:g('[data-frame-asset-status]','data-frame-asset-status'),
        assetSha:g('[data-frame-asset-sha]','data-frame-asset-sha'),assetDeclared:g('[data-frame-asset-declared]','data-frame-asset-declared'),
        assetMatch:g('[data-frame-asset-digest-match]','data-frame-asset-digest-match'),assetDecoded:g('[data-frame-asset-decoded]','data-frame-asset-decoded'),
        assetField:g('[data-frame-asset-field]','data-frame-asset-field'),assetSample:g('[data-frame-asset-sample]','data-frame-asset-sample'),
        assetMediaType:g('[data-frame-asset-media-type]','data-frame-asset-media-type'),assetBytes:g('[data-frame-asset-bytes]','data-frame-asset-bytes'),
        threeD:g('[data-3d-disabled]','data-3d-disabled'),liveGeometry:g('[data-live-geometry-applied]','data-live-geometry-applied'),
        transformsPose:g('[data-transforms-full-pose]','data-transforms-full-pose'),poseSlice:g('[data-pose-slice]','data-pose-slice'),
        notProven:g('[data-not-proven]','data-not-proven'),
        rowSamples:q('[data-frame-row]','data-frame-row'),rowStatuses:q('[data-frame-row]','data-row-status'),
        rowDeclaredRefs:q('[data-frame-row]','data-row-declared-ref'),rowLines:q('[data-frame-row]','data-row-line'),
        rowAmbiguous:q('[data-frame-row]','data-row-ambiguous'),rowSingleState:q('[data-frame-row]','data-row-single-state'),
        rowMedia:q('[data-frame-row]','data-row-media'),roles:q('[data-frame-role]','data-frame-role'),
        rolePrimaries:q('[data-frame-role]','data-role-primary'),roleStatuses:q('[data-frame-role]','data-role-status'),
        stateKeys:q('[data-state-row]','data-state-row'),stateUnits:q('[data-state-row]','data-state-unit'),
        candidateLines:q('[data-state-candidate]','data-state-candidate'),
        quantityKeys:q('[data-quantity-row]','data-quantity-row'),quantityAbs:q('[data-quantity-row]','data-quantity-abs-ms'),
        mediaFields:q('[data-frame-media-ref]','data-media-field'),mediaAvailability:q('[data-frame-media-ref]','data-media-availability'),
        mediaRowLines:q('[data-frame-media-ref]','data-media-row-lines'),provenance:q('[data-provenance-row]','data-provenance-row'),
        modelStatus:g('[data-model-pane]','data-model-status'),modelSample:g('[data-model-pane]','data-model-sample'),
        modelEpisode:g('[data-model-pane]','data-model-episode'),modelFramePose:g('[data-model-pane]','data-frame-pose-verified'),
        modelDrive:g('[data-model-drive-summary]','data-model-drive-summary'),modelStage:g('[data-model-stage]','data-model-stage'),
        modelWithheld:g('[data-model-withheld-count]','data-model-withheld-count'),mappingStatuses:q('[data-mapping-row]','data-mapping-status'),
        mappingDrivable:q('[data-mapping-row]','data-mapping-drivable'),mappingTargets:q('[data-mapping-row]','data-mapping-row'),
        comparisonEqual:q('[data-comparison-row]','data-comparison-equal'),assetEqual:q('[data-asset-row]','data-asset-equal'),
        assetReads:q('[data-asset-row]','data-asset-read'),assetIds:q('[data-asset-row]','data-asset-row'),
        canvas:document.querySelectorAll('canvas').length,modelCanvas:document.querySelectorAll('[data-model-canvas-host] canvas').length,
        controlSurface:document.querySelectorAll('[data-target-readout],[data-ghost-toggle],[data-workbench-tool]').length,
        text:document.querySelector('[data-frame-view]')?.innerText??'',
        modelText:document.querySelector('[data-model-pane]')?.innerText??''};}""")


def state_of(frame):
    return frame['state']


# ---- real --------------------------------------------------------------------------------------------

async def real_flow(page):
    await wait_list(page)
    await open_episode(page, a.complete_run, a.complete_episode)
    direct = await read_direct(page, f'/api/v1/episodes/{a.complete_episode}/frames', {'run_id': a.complete_run, 'limit': 5, 'offset': 0})
    view = await page_attrs(page)
    check('the pane reads frame-link-2 and binds it to the same source/run/episode identity as the detail',
          direct['schema_version'] == FRAME_SCHEMA and direct['read_only'] is True and view['schema'] == FRAME_SCHEMA
          and view['episode'] == a.complete_episode and view['run'] == a.complete_run
          and a.complete_run in await page.locator('[data-provenance-row="identity"]').inner_text()
          and direct['source']['source_id'] == SOURCE_ID and direct['source']['platform_writes'] is False, view['schema'])
    check('the response declares its own migration from frame-link-1 and the pane shows it',
          view['migrationFrom'] == 'unirobot-mobilecar-frame-link-1' and view['migrationTo'] == FRAME_SCHEMA
          and 'age_of_state_relative_to_frame' in view['text']
          and 'not the same contract' in await page.locator('[data-frame-version-migration]').inner_text(), view['migrationFrom'])
    first = direct['frames'][0]
    paging = direct['paging']
    check('the corrected pagination is reported with the lines actually read and no total anywhere',
          [view['returned'], view['offset'], view['nextOffset'], view['hasMore']] == [str(len(direct['frames'])), '0', str(paging['next_offset']), 'true']
          and view['linesRead'] == str(paging['anchor_lines']['lines_read'])
          and view['examined'] == str(paging['anchor_records_examined'])
          and view['postExamined'] == str(paging['post_page_records_examined'])
          and view['nextQualifying'] == str(paging['next_qualifying_anchor_line_index'])
          and view['wholeFile'] == str(paging['scan']['whole_file_scanned']).lower()
          and await attr(page, '[data-frame-no-total]', 'data-frame-no-total') == 'true'
          and not re.search(r'共\s*\d+\s*帧', view['text']), (view['linesRead'], view['wholeFile']))
    check('the anchor is one persisted frame per record and the line index is declared not to be a clock',
          view['rowLines'] == [str(f['anchor']['line_index']) for f in direct['frames']]
          and await attr(page, '[data-frame-line-index-clock]', 'data-frame-line-index-clock') == 'true'
          and await attr(page, '[data-frame-persist-counter]', 'data-frame-persist-counter') == 'true'
          and await attr(page, '[data-frame-anchor]', 'data-frame-anchor') == direct['anchor']['relative_path'])
    check('the primaries are listed per frame with no ambiguity in this record',
          view['rowStatuses'] == [f['linkage_status'] for f in direct['frames']]
          and all(status == 'matched' for status in view['rowStatuses'])
          and all(ref == 'unresolved_reference' for ref in view['rowDeclaredRefs'])
          and all(ambiguous == 'none' for ambiguous in view['rowAmbiguous'])
          and view['rolePrimaries'] == ['true', 'true', 'true', 'true', 'false']
          and view['roleStatuses'] == ['matched', 'matched', 'matched', 'matched', 'unresolved_reference'], view['roleStatuses'])
    role_text = await page.locator('[data-frame-role="image_observation"]').inner_text()
    check('role completeness is judged by the required sensor kinds and their candidate lines',
          'required_kinds=rgb/depth ×1' in role_text and 'rgb→[8]' in role_text and 'depth→[9]' in role_text
          and 'one row per required sensor_kind' in role_text
          and 'ambiguous_kind' in view['statusPrecedence'] and 'ambiguous_candidates' in view['statusPrecedence'], role_text[:200])
    check('the unresolved reference does not empty the state panel: recorded_state is displayed with units',
          set(view['stateKeys']) == set(state_of(first)['recorded_state'].keys()), view['stateKeys'])
    qpos_text = await page.locator('[data-state-row="arm_model_qpos_rad"]').inner_text()
    check('a model joint angle is labelled as a model joint angle, never as a user command or calibration',
          '机械臂模型关节角' in qpos_text and '不是用户控制角' in qpos_text
          and 'radians' in (await attr(page, '[data-state-row="arm_model_qpos_rad"]', 'data-state-unit')), qpos_text[:200])
    check('the frame page hands the mapping question to robot-state instead of answering it',
          'robot-state' in qpos_text and await attr(page, '[data-pose-slice]', 'data-pose-slice') == direct['three_d_replay']['robot_pose_readiness_slice'])
    base_text = await page.locator('[data-state-row="base_position_world_sim_m"]').inner_text()
    check('chassis pose and gripper/TCP fields keep the reader’s own value wording',
          '底盘位置' in base_text and '10145992864392481' in base_text and '-0.00023473557897040777' in base_text
          and await count(page, '[data-state-row="gripper_width_m"]') == 1
          and await count(page, '[data-state-row="tcp_position_world_m"]') == 1
          and '不是发送过的指令位置' in base_text, base_text[:200])
    check('the state provenance shows join key, event_seq, candidate count and the record position of the hit',
          view['eventSeq'] == str(first['state']['source']['event_seq'])
          and view['recordPosition'] == f"{first['state']['source']['relative_path']}#{first['state']['source']['line_index']}"
          and view['singleState'] == str(first['state']['single_state_selected']).lower()
          and view['stateCandidates'] == str(first['state']['candidate_records'])
          and view['emptyPayload'] == 'false' and first['state']['key_value'] in view['text'], (view['singleState'], view['stateCandidates']))

    quantities = {q['key']: q for q in first['times']['quantities']}
    check('the removed age field is gone as a payload field and its replacement stamps are separate rows',
          'age_of_state_relative_to_frame' not in first['times']
          and 'age_of_state_relative_to_frame' in json.dumps(first['times'].get('removed_in_this_version'))
          and '本版移除字段' in view['text']
          and all(key in view['quantityKeys'] for key in ('state_event_write_minus_frame_capture', 'state_payload_feedback_time_minus_frame_capture',
                                                           'recorder_declared_feedback_time_minus_frame_capture', 'state_sim_time_minus_frame_capture_sim_time'))
          and abs(float(await attr(page, '[data-quantity-row="state_event_write_minus_frame_capture"]', 'data-quantity-abs-ms')) - quantities['state_event_write_minus_frame_capture']['abs_ms']) < 1e-9
          and abs(float(await attr(page, '[data-quantity-row="state_payload_feedback_time_minus_frame_capture"]', 'data-quantity-abs-ms')) - quantities['state_payload_feedback_time_minus_frame_capture']['abs_ms']) < 1e-9, view['quantityKeys'])
    write_row = await page.locator('[data-quantity-row="state_event_write_minus_frame_capture"]').inner_text()
    payload_row = await page.locator('[data-quantity-row="state_payload_feedback_time_minus_frame_capture"]').inner_text()
    check('the event write stamp and the payload sample stamp are worded as different things',
          '写入' in write_row and '不是状态被采样的瞬间' in write_row and '采样' in payload_row
          and quantities['state_payload_feedback_time_minus_frame_capture']['field'] in payload_row
          and quantities['state_event_write_minus_frame_capture']['source_record'] in write_row, write_row[:200])
    sim_row = await page.locator('[data-quantity-row="state_sim_time_minus_frame_capture_sim_time"]').inner_text()
    check('the sim quantity is named as another clock and never merged with backend_monotonic',
          'sim' in sim_row and quantities['state_sim_time_minus_frame_capture_sim_time']['meaning'] in sim_row)
    persist_row = await page.locator('[data-quantity-row="persist_minus_capture"]').inner_text()
    recorder_text = await page.locator('[data-recorder-declared]').inner_text()
    check('the recorder’s own pipeline latencies are copied, not re-derived into a state age',
          '落盘' in persist_row
          and view['recorderAgrees'] == str(first['times']['recorder_declared']['agrees_with_recomputation']).lower()
          and 'observation_age_ms' in view['recorderDeclared']
          and 'not the difference between a state sample and the capture' in recorder_text, recorder_text[:200])
    check('clock sameness separates what records name from what the reader can verify',
          await attr(page, '[data-clock-sameness-verified]', 'data-clock-sameness-verified') == 'false'
          and await attr(page, '[data-frame-sync-streams]', 'data-frame-sync-streams') == 'false'
          and 'verified_by_reader=false' in view['text'] and 'native build' in view['text']
          and 'synchronized_upgraded_by_numeric_closeness=false' in view['text'])
    feedback = state_of(first)['recorder_declared_feedback']
    check('the recorder’s raw declared feedback time is listed separately from any difference',
          await attr(page, '[data-feedback-declared-time]', 'data-feedback-declared-time') == str(feedback['feedback_time_s'])
          and await attr(page, '[data-feedback-declared-clock]', 'data-feedback-declared-clock') == feedback['feedback_clock']
          and await attr(page, '[data-feedback-timing-status]', 'data-feedback-timing-status') == feedback['timing_event_status'])
    rgb = next(item for item in first['media']['items'] if item['field'] == 'rgb_uri')
    await wait_asset_uri(page, rgb['uri'])
    check('the image is the selected frame’s own rgb reference, served bytes verified against its declaration',
          view['assetUri'] == rgb['uri'] and view['assetField'] == 'rgb_uri' and view['assetStatus'] == 'bytes'
          and view['assetDecoded'] == 'ok' and view['assetMediaType'] == 'image/png'
          and view['assetBytes'] == str(rgb['bytes_on_disk']) and view['assetMatch'] == 'true'
          and view['assetSample'] == first['sample_id'], (await page_attrs(page))['assetStatus'])
    check('media items list every candidate row of their kind, with a declared digest only where recorded',
          view['mediaFields'] == [item['field'] for item in first['media']['items']]
          and view['mediaAvailability'] == [item['availability'] for item in first['media']['items']]
          and view['mediaRowLines'] == [','.join(str(line) for line in item['observation_row_line_indexes']) for item in first['media']['items']]
          and 'every candidate row for the kind is listed' in await page.locator('[data-media-declaration]').inner_text(), view['mediaRowLines'])
    check('provenance covers source, root boundary, anchor, clocks, profile and per-role positions',
          {'source', 'root', 'identity', 'anchor', 'sample', 'clocks', 'profile', 'state_position', 'role_positions', 'page'} <= set(view['provenance'])
          and direct['source']['path_boundary'] in await page.locator('[data-provenance-row="root"]').inner_text()
          and first['anchor']['profile']['profile_id'] in await page.locator('[data-provenance-row="profile"]').inner_text()
          and 'events.jsonl#' in await page.locator('[data-provenance-row="role_positions"]').inner_text())
    check('the 3D and replay boundary is passed through from the response, not softened',
          view['threeD'] == 'true' and view['liveGeometry'] == 'false' and view['transformsPose'] == 'false'
          and 'rendered 3D replay' in view['notProven']
          and 'no replay execution' in (await attr(page, '[data-capability-limits]', 'data-capability-limits')))

    # ---- the fixed model reference on the real selected frame ----
    await wait_model(page, 'ready')
    pose = await read_direct(page, f'/api/v1/episodes/{a.complete_episode}/robot-state', {'run_id': a.complete_run, 'sample_id': first['sample_id']})
    model = await page_attrs(page)
    pose_reads = [r for r in report['requests'] if urlsplit(r['url']).path.endswith('/robot-state')]
    check('the reference view reads robot-state for the selected frame and checks its identity back',
          pose['schema_version'] == POSE_SCHEMA and pose['frame']['sample_id'] == first['sample_id']
          and pose['frame']['linkage_schema'] == FRAME_SCHEMA and model['modelStatus'] == 'ready'
          and model['modelSample'] == first['sample_id']
          and all(first['sample_id'] in r['url'] for r in pose_reads[-1:]), (model['modelStatus'], pose_reads[-1:]))
    check('the nine mapping rows are shown with the reader’s own statuses, and none is fully verified',
          len(model['mappingStatuses']) == 9
          and model['mappingStatuses'].count('partially_verified') == 1 and model['mappingStatuses'].count('unverified') == 4
          and model['mappingStatuses'].count('missing') == 2 and model['mappingStatuses'].count('not_required_for_pose') == 2
          and model['mappingStatuses'].count('verified') == 0
          and pose['pose_readiness']['mapped_targets_partially_or_fully_verified'] in model['modelText'], model['mappingStatuses'])
    arm = model['mappingTargets'].index('arm_joint_positions')
    check('the partially verified arm mapping does not drive the model, so the pose stays the reference pose',
          model['mappingStatuses'][arm] == 'partially_verified' and model['mappingDrivable'][arm] == 'false'
          and '已驱动 0 个关节值' in model['modelDrive'] and '保持固定参考' in model['modelText']
          and model['modelFramePose'] == 'false' and '固定模型参考；所选帧姿态尚未验证' in model['modelText'], model['modelDrive'])
    check('the whole robot is not claimed rebuildable and every missing part keeps its own gap',
          'robot_state_can_be_rebuilt_without_assumptions=false' in model['modelText']
          and 'no attested rule turns the recorded width into jaw joint values' in model['modelText']
          and 'no historical position is recorded for dynamic scene objects' in model['modelText']
          and '不伪造动态物体位姿' in model['modelText'] and 'no live geometry or Actual substitution' in model['modelText'], model['modelText'][-300:])
    check('the run manifest and the frozen bundle agree on all four identity fields',
          model['comparisonEqual'] == ['true'] * 4 and all(row['equal'] for row in pose['model_resource']['comparison'].values()), model['comparisonEqual'])
    check('every mesh asset of the bundle is present in the history manifest with an equal digest',
          model['assetEqual'] == ['true'] * len(pose['model_resource']['assets'])
          and len(model['assetIds']) == len(pose['model_resource']['assets']) == 23
          and await attr(page, '[data-asset-equal-count]', 'data-asset-equal-count') == '23', (len(model['assetIds']), len(pose['model_resource']['assets'])))
    check('the reference canvas belongs to the model pane and carries no live control surface',
          model['canvas'] >= 1 and model['modelCanvas'] == model['canvas'] and model['controlSurface'] == 0
          and await attr(page, '[data-model-pane]', 'data-model-live-poll') == 'off'
          and await attr(page, '[data-model-pane]', 'data-reference-pose') == 'compiled-initial-layout', (model['canvas'], model['modelCanvas']))
    await page.locator('[data-asset-pick="link1"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-asset-row=\"link1\"]')?.getAttribute('data-asset-read') ?? '')==='ok'", timeout=40000)
    read_detail = await attr(page, '[data-asset-row="link1"]', 'data-asset-detail')
    check('a model asset is read only from the history route, with its bytes checked against the bundle digest',
          f"{pose['model_resource']['assets'][next(i for i, item in enumerate(pose['model_resource']['assets']) if item['asset_id'] == 'link1')]['bytes']} 字节" in read_detail
          and 'model/stl' in read_detail and '服务端重算摘要与 bundle 声明一致' in read_detail
          and not [r for r in report['requests'][report['history_from']:] if '/mobilecar/scene/assets/' in urlsplit(r['url']).path], read_detail[:200])

    # Walking pages strictly by next_offset / has_more.
    for _ in range(len(direct['frames']) - 1):
        await page.locator('[data-frame-next]').click()
        await page.wait_for_timeout(150)
    last = direct['frames'][-1]
    moved_last = await page_attrs(page)
    check('stepping inside the page moves the cursor, rebinds the image and re-reads that frame’s state',
          moved_last['index'] == str(len(direct['frames']) - 1) and moved_last['currentSample'] == last['sample_id']
          and moved_last['assetUri'] == next(item for item in last['media']['items'] if item['field'] == 'rgb_uri')['uri']
          and moved_last['modelSample'] == last['sample_id'], (moved_last['index'], moved_last['modelSample']))
    second = await read_direct(page, f'/api/v1/episodes/{a.complete_episode}/frames', {'run_id': a.complete_run, 'limit': 5, 'offset': paging['next_offset']})
    await page.locator('[data-frame-next]').click()
    await wait_frames(page, f"()=>(document.querySelector('[data-frame-offset]')?.getAttribute('data-frame-offset') ?? '')==='{paging['next_offset']}'")
    moved = await page_attrs(page)
    check('at the page end the pane advances by the reader’s next_offset and keeps index at the new first frame',
          moved['offset'] == str(second['paging']['offset']) and moved['index'] == '0'
          and moved['currentSample'] == second['frames'][0]['sample_id']
          and moved['rowSamples'] == [f['sample_id'] for f in second['frames']]
          and 'raw line index' in moved['explanation'], (moved['offset'], moved['currentSample']))
    await page.locator('[data-frame-prev]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-offset]')?.getAttribute('data-frame-offset') ?? '')==='0'")
    await wait_asset_uri(page, last['media']['items'][0]['uri'])
    back = await page_attrs(page)
    check('stepping back over a page boundary lands on the previous page’s last frame, not a fabricated one',
          back['offset'] == '0' and back['index'] == str(len(direct['frames']) - 1)
          and back['currentSample'] == last['sample_id'] and back['assetUri'] == last['media']['items'][0]['uri'])

    # Opening by sample_id: the corrected pagination counts the sample-filtered records itself.
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
    filtered_direct = await read_direct(page, f'/api/v1/episodes/{a.complete_episode}/frames',
                                        {'run_id': a.complete_run, 'limit': 5, 'offset': 0, 'sample_id': target})
    frames_reads_before = sum(1 for r in report['requests'] if '/frames?' in r['url'])
    await page.locator('[data-frame-next]').click()
    await wait_frames(page, "()=>/has_more=false/.test(document.querySelector('[data-frame-notice]')?.innerText??'')")
    gap = await page_attrs(page)
    check('with the reader’s has_more=false the pane stops on the filtered frame and issues no further read',
          filtered_direct['paging']['has_more'] is False and filtered_direct['paging']['next_offset'] is None
          and sum(1 for r in report['requests'] if '/frames?' in r['url']) == frames_reads_before
          and gap['returned'] == '1' and gap['hasMore'] == 'false' and gap['nextOffset'] == 'null'
          and gap['rowSamples'] == [target] and gap['pageKind'] == 'frames'
          and '不声称已遍历全部帧' in gap['notice'] and '不推断录制结束' in gap['notice'], (gap['hasMore'], gap['notice'][:200]))
    check('the filtered page shows the reader’s own census and no v1 paging caveat survives as a fact',
          gap['excludedBySample'] == str(filtered_direct['paging']['excluded_by_sample_id_filter'])
          and gap['examined'] == str(filtered_direct['paging']['anchor_records_examined'])
          and gap['wholeFile'] == str(filtered_direct['paging']['scan']['whole_file_scanned']).lower()
          and '混合了候选行计数与锚点原生行号' not in await page.inner_text('body'),
          (gap['excludedBySample'], gap['examined']))
    await page.locator('[data-frame-sample-clear]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-returned]')?.getAttribute('data-frame-returned') ?? '')==='5'")

    # A contract-allowed numeric window, then a window that matches nothing.
    capture = direct['frames'][2]['anchor']['clocks']['capture_backend_monotonic_s']
    await page.locator('select[aria-label="帧时间基"]').select_option('capture_backend_monotonic_s')
    await page.locator('input[aria-label="时间窗口起点"]').fill(str(capture - 0.05))
    await page.locator('input[aria-label="时间窗口终点"]').fill(str(capture + 0.05))
    await page.locator('[data-frame-window-apply]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-window-base]')?.getAttribute('data-frame-window-base') ?? '')==='capture_backend_monotonic_s'")
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
          and empty_window['windowBase'] == 'capture_backend_monotonic_s'
          and int(re.search(r'窗口外 (\d+)', empty_window['explanation']).group(1)) > 0
          and await count(page, '[data-frame-asset-uri]') == 0 and empty_window['modelStatus'] == 'idle', empty_window['explanation'][:200])
    await page.locator('[data-frame-window-clear]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-returned]')?.getAttribute('data-frame-returned') ?? '')==='5'")
    cleared = await page_attrs(page)
    check('clearing the window returns to offset browsing with the reader’s echo dropped',
          cleared['windowBase'] == 'null' and cleared['contextSample'] == 'none' and cleared['pageKind'] == 'frames'
          and len(cleared['rowSamples']) == 5 and cleared['windowFrom'] == 'null' and cleared['windowTo'] == 'null', cleared['windowBase'])

    # The FAILED / INCOMPLETE record.
    failed = await read_direct(page, f'/api/v1/episodes/{a.failed_episode}/frames', {'run_id': a.failed_run, 'limit': 5, 'offset': 0})
    await open_episode(page, a.failed_run, a.failed_episode)
    await wait_asset_settled(page)
    await wait_model(page, 'ready')
    view = await page_attrs(page)
    check('the incomplete record’s frames are read as the reader returns them',
          failed['paging']['returned'] == len(failed['frames']) and view['returned'] == str(len(failed['frames']))
          and view['rowSamples'] == [f['sample_id'] for f in failed['frames']] and view['pageKind'] != 'no-anchor-lines', view['returned'])
    check('every frame of the failed record separates matched primaries from an unresolved reference',
          all(status == 'matched' for status in view['rowStatuses'])
          and all(ref == 'unresolved_reference' for ref in view['rowDeclaredRefs'])
          and f"frames_returned={failed['summary']['frames_returned']}" in view['linkageScope']
          and f"主角色歧义={failed['summary']['frames_with_ambiguous_primary_role']}" in view['linkageScope']
          and state_of(failed['frames'][0])['status'] == view['stateStatus'], view['linkageScope'])
    check('switching Episodes rebinds the model reference to the new Episode’s history namespace',
          view['modelEpisode'] == a.failed_episode and view['modelStatus'] == 'ready'
          and f'/api/v1/episodes/{a.failed_episode}/model/assets/' in ''.join(r['url'] for r in report['requests']), view['modelEpisode'])
    report['real']['complete'] = {'frames': len(direct['frames']), 'sample': first['sample_id'], 'quantities': len(first['times']['quantities']),
                                  'roles': view['roleStatuses'], 'next_offset': paging['next_offset'],
                                  'mapping': pose['pose_readiness']['mapped_targets_partially_or_fully_verified'],
                                  'assets': len(pose['model_resource']['assets'])}
    report['real']['failed'] = {'frames': failed['paging']['returned'], 'statuses': view['rowStatuses'], 'declared_refs': view['rowDeclaredRefs']}


# ---- synthetic ---------------------------------------------------------------------------------------

SOURCE_FIXTURE = {'source_id': SOURCE_ID, 'adapter_id': 'mobilecar', 'recording_root': '/fixture', 'access': 'read_only_files',
                  'platform_writes': False, 'path_boundary': 'paths stay inside the episode directory'}
QUANTITIES = [
    {'key': 'state_event_write_minus_frame_capture', 'source_record': 'events state feedback envelope', 'field': 'backend_monotonic_s',
     'relative_to': 'persisted frame capture_backend_monotonic_s', 'unit': 's', 'clock': 'named backend_monotonic by the record',
     'meaning': 'when the recorder wrote the state event; it is not the instant the state was sampled', 'capture_value': 100.0, 'other_value': 99.997,
     'value': -0.003, 'abs_ms': 3.0, 'direction': 'earlier', 'line_index': 7},
    {'key': 'state_payload_feedback_time_minus_frame_capture', 'source_record': 'events state feedback payload', 'field': 'feedback_time_monotonic',
     'relative_to': 'persisted frame capture_backend_monotonic_s', 'unit': 's', 'clock': 'named backend_monotonic by feedback_clock',
     'meaning': 'the as-of time the state payload carries for its own sample', 'capture_value': 100.0, 'other_value': 99.996,
     'value': -0.004, 'abs_ms': 4.0, 'direction': 'earlier', 'line_index': 7},
    {'key': 'recorder_declared_feedback_time_minus_frame_capture', 'source_record': 'events rgbd_capture_timing payload', 'field': 'feedback_time_s',
     'relative_to': 'persisted frame capture_backend_monotonic_s', 'unit': 's', 'clock': 'named by payload.feedback_clock',
     'meaning': 'the recorder’s own declared feedback time for this frame', 'capture_value': 100.0, 'other_value': 99.9961,
     'value': -0.0039, 'abs_ms': 3.9, 'direction': 'earlier', 'line_index': 9},
    {'key': 'state_sim_time_minus_frame_capture_sim_time', 'source_record': 'events state feedback payload', 'field': 'sim_time_s',
     'relative_to': 'persisted frame capture_sim_time_s', 'unit': 's', 'clock': 'sim', 'meaning': 'simulator-time separation, a different clock',
     'capture_value': 1.0, 'other_value': 1.0, 'value': 0.0, 'abs_ms': 0.0, 'direction': 'equal', 'line_index': 7},
    {'key': 'persist_minus_capture', 'source_record': 'persisted frame', 'field': 'persist_backend_monotonic_s', 'relative_to': 'its own capture clock',
     'unit': 's', 'clock': 'named backend_monotonic by the record', 'meaning': 'the recorder’s own capture-to-disk latency',
     'capture_value': 100.0, 'other_value': 100.1, 'value': 0.1, 'abs_ms': 100.0, 'direction': 'later', 'line_index': 0},
    {'key': 'observation_arrival_minus_frame_capture', 'source_record': 'observations index row', 'field': 'arrival_time_s',
     'relative_to': 'persisted frame capture_backend_monotonic_s', 'unit': 's', 'clock': 'row clock_id', 'meaning': 'when the bridge says it arrived',
     'capture_value': 100.0, 'other_value': 100.03, 'value': 0.03, 'abs_ms': 30.0, 'direction': 'later', 'line_index': 1, 'sensor_kind': 'rgb'},
]
STATUS_MEANING = {'matched': 'every record the role requires was found by its recorded key, once',
                  'partial': 'some but not all records the role requires were found',
                  'missing': 'no record for this role carried the key',
                  'unresolved_reference': 'the frame declares a reference whose target record is not in this Episode',
                  'identity_mismatch': 'a candidate record named a different run or Episode and was excluded',
                  'stream_absent': 'the source stream is not recorded in this Episode',
                  'ambiguous_kind': 'a sensor_kind the role requires was recorded more than once for the same frame key',
                  'ambiguous_candidates': 'more than one record claimed this role’s key, so no single record can be reported'}
ROLE_KEYS = ['image_observation', 'camera_transform', 'capture_timing_event', 'state_feedback_event', 'feedback_observation_row']
ARM_RAD = [0.01, 0.02, 0.03, -1.57, 0.05]


def role_fixture(sample, role, **patch):
    value = {'role': role, 'join_key': 'sample_id', 'key_value': sample, 'status': 'matched', 'meaning': f'fixture meaning for {role}',
             'requirement': {'exact_records': 1, 'rule': 'exactly one record for this key'},
             'candidate_records': 1, 'matched_records': 1, 'identity_mismatched_records': 0,
             'missing_kinds': [], 'duplicate_kinds': [], 'unexpected_kinds': [], 'kind_inventory': None,
             'candidate_line_indexes': [7], 'ambiguous_records': None, 'reason': None,
             'sources': [{'stream_id': 'events', 'relative_path': 'events.jsonl', 'line_index': 7, 'record_position': 'events.jsonl#7'}]}
    value.update(patch)
    return value


def frame_payload(sample, **patch):
    frame = {
        'sample_id': sample, 'stream_id': 'rgbd',
        'anchor': {'line_index': 0, 'relative_path': 'observations/persist.jsonl', 'persist_sequence': 1,
                   'identity': {'run_id_matches': True, 'episode_id_matches': True, 'declared_run_id': 'run_a', 'declared_episode_id': 'episode_ok'},
                   'clocks': {'capture_backend_monotonic_s': 100.0, 'capture_sim_time_s': 1.0, 'persist_backend_monotonic_s': 100.1},
                   'declared_keys': ['sample_id', 'rgb_uri'], 'reference_keys': {'capture_control_tick_id': 'tick_1', 'feedback_sample_id': 'joint_feedback_1'},
                   'profile': {'profile_id': 'fixture-profile', 'profile_version': '1.0', 'kinds': ['rgb', 'depth']}},
        'linkage_status': 'matched', 'primary_roles_matched': ROLE_KEYS[:4], 'primary_roles_ambiguous': [],
        'declared_reference_status': 'unresolved_reference',
        'media': {'declared_by': 'fixture', 'uri_convention': 'assets/<kind>/<file>',
                  'digest_verification': 'declared only; recomputed when the asset endpoint serves the file',
                  'duplicate_row_rule': 'every candidate row for the kind is listed; none is silently chosen',
                  'items': [{'field': 'rgb_uri', 'uri': f'assets/rgb/{sample}_rgb.png', 'availability': 'present', 'observation_row_line_indexes': [1],
                             'observation_row_candidates': 1, 'agrees_with_observation_row': True, 'declared_sha256_by_row': hashlib.sha256(PNG).hexdigest(),
                             'declared_bytes_by_row': len(PNG), 'bytes_on_disk': len(PNG)},
                            {'field': 'depth_uri', 'uri': f'assets/depth/{sample}_depth_m.npy', 'availability': 'present', 'observation_row_line_indexes': [2],
                             'observation_row_candidates': 1, 'agrees_with_observation_row': True, 'declared_sha256_by_row': 'b' * 64, 'declared_bytes_by_row': 6, 'bytes_on_disk': 6},
                            {'field': 'valid_mask_uri', 'uri': f'assets/masks/{sample}_valid.png', 'availability': 'present', 'observation_row_line_indexes': [2],
                             'observation_row_candidates': 1, 'agrees_with_observation_row': True, 'declared_sha256_by_row': None, 'declared_bytes_by_row': None, 'bytes_on_disk': 1}]},
        'state': {'status': 'matched', 'join_key': 'control_tick_id', 'key_value': 'tick_1', 'candidate_records': 1, 'single_state_selected': True,
                  'source': {'stream_id': 'events', 'relative_path': 'events.jsonl', 'line_index': 7, 'event_seq': 8, 'event_type': 'feedback'},
                  'recorded_fields': {'event_seq': 8, 'control_tick_id': 'tick_1', 'backend_monotonic_s': 99.997},
                  'recorded_state': {'base_position_world_sim_m': [0.1, 0.2, 0.05], 'arm_model_qpos_rad': ARM_RAD, 'gripper_width_m': 0.02,
                                     'tcp_position_world_m': [0.17, 0.0, 0.3], 'mystery_joint_nm': 1.5, 'feedback_time_monotonic': 99.997},
                  'candidates': [{'line_index': 7, 'record_position': 'events.jsonl#7', 'event_seq': 8, 'backend_monotonic_s': 99.997, 'sim_time_s': 1.0, 'payload': {}}],
                  'multiple_candidates_note': None,
                  'declared_reference': {'feedback_sample_id': 'joint_feedback_1', 'row_status': 'unresolved_reference'},
                  'recorder_declared_feedback': {'available': True, 'timing_event_status': 'matched', 'feedback_time_s': 99.9961, 'feedback_clock': 'backend_monotonic',
                                                 'meaning': 'the recorder’s own declared feedback time'},
                  'units': {'*_rad': 'radians', '*_rad_s': 'radians per second', '*_m': 'metres', '*_nm': 'newton metres', '*_s': 'seconds'},
                  'carried_over_from_another_frame': False, 'interpolated': False,
                  'note': 'the state the recorder placed on the frame’s capture tick'},
        'times': {'quantities': QUANTITIES, 'semantics_rule': 'each quantity is one named subtraction of two recorded fields',
                  'state_time_quantity_keys': ['state_event_write_minus_frame_capture', 'state_payload_feedback_time_minus_frame_capture', 'recorder_declared_feedback_time_minus_frame_capture'],
                  'recorder_declared': {'fields': {'observation_age_ms': 30.0, 'capture_to_persist_ms': 100.0},
                                        'observation_age_ms_note': 'observation_age_ms is capture-to-arrival, not the difference between a state sample and the capture',
                                        'recomputed_arrival_minus_capture_ms': 30.0, 'agrees_with_recomputation': True},
                  'removed_in_this_version': {'times.age_of_state_relative_to_frame': 'read times.quantities instead'},
                  'same_clock_verified': False},
        'roles': [role_fixture(sample, 'image_observation', requirement={'required_kinds': ['rgb', 'depth'], 'kind_cardinality': 1, 'rule': 'one row per required sensor_kind'},
                               candidate_records=2, matched_records=2, required_kinds=['rgb', 'depth'], matched_kinds=['rgb', 'depth'],
                               kind_inventory={'rgb': [1], 'depth': [2]}, candidate_line_indexes=[1, 2],
                               sources=[{'stream_id': 'observations-index', 'relative_path': 'observations/index.jsonl', 'line_index': 1, 'record_position': 'observations/index.jsonl#1'}])]
                 + [role_fixture(sample, role) for role in ROLE_KEYS[1:4]]
                 + [role_fixture(sample, 'feedback_observation_row', key_value='joint_feedback_1', status='unresolved_reference', candidate_records=0,
                                 matched_records=0, candidate_line_indexes=[], sources=[],
                                 requirement={'exact_records': 1, 'rule': 'one observation row equal to the declared feedback id'})],
    }
    frame.update(patch)
    return frame


def paging_fixture(frames, **patch):
    value = {'limit': 5, 'offset': 0, 'returned': len(frames), 'has_more': bool(frames), 'next_offset': 5 if frames else None,
             'next_qualifying_anchor_line_index': 5 if frames else None, 'offset_semantics': 'raw line index after the last returned anchor',
             'skipped_before_offset': 0, 'excluded_anchor_identity_mismatch': 0, 'excluded_stream_mismatch': 0, 'excluded_without_sample_id': 0,
             'excluded_by_sample_id_filter': 0, 'excluded_outside_time_window': 0, 'records_missing_selected_time_base': 0,
             'anchor_records_examined': 303 if frames else 6, 'post_page_records_examined': 1 if frames else 0,
             'anchor_lines': {'lines_read': 303 if frames else 6, 'blank_lines_skipped': 0, 'oversize_lines_skipped': 0,
                              'unparseable_lines_skipped': 0, 'non_object_lines_skipped': 0, 'prefiltered_lines_skipped': 0},
             'scan': {'whole_file_scanned': not frames, 'stopped_after_full_page_at_line_index': 5 if frames else None,
                      'note': 'a full page stops at the first further qualifying anchor'}}
    value.update(patch)
    return value


def frames_payload(episode, frames, **patch):
    base = {'schema_version': FRAME_SCHEMA, 'read_only': True, 'source': SOURCE_FIXTURE, 'retrieved_at': '2026-01-01T00:00:00Z',
            'identity': {'run_id': 'run_a', 'episode_id': episode, 'episode_directory': f'/fixture/run_a/episodes/{episode}',
                         'run_directory_identity': 'the run directory was re-validated as itself before this read', 'native_contract_version': 'mobilecar-1.0'},
            'anchor': {'stream_id': 'observations-persist', 'relative_path': 'observations/persist.jsonl', 'semantics': 'one persisted image frame per record', 'requested_stream': 'rgbd'},
            'paging': paging_fixture(frames),
            'cursor': {'order': 'native_append_order_of_the_anchor_stream', 'line_index_is_not_a_clock': True, 'persist_sequence_is_the_recorders_own_counter': True,
                       'first_line_index': 0, 'last_line_index': len(frames) - 1, 'first_persist_sequence': 1, 'last_persist_sequence': len(frames)},
            'time': {'selected_time_base': None, 'time_from': None, 'time_to': None,
                     'selectable_time_bases': ['capture_backend_monotonic_s', 'capture_sim_time_s', 'persist_backend_monotonic_s'],
                     'units': {'*_s': 'seconds', '*_ms': 'milliseconds', '*_rad': 'radians', '*_m': 'metres'},
                     'synchronized_across_streams': False, 'same_clock_verified': False,
                     'clock_sameness': {'fields_that_name_a_shared_base': ['persisted frame clock', 'state event backend_monotonic_s'],
                                        'declared_by_recorder': True, 'verified_by_reader': False,
                                        'verified_claim': 'naming one clock base is not proof that two writers stamped it at one instant',
                                        'writer_version_binding': {'recorded': ['run manifest contract_version'],
                                                                   'not_recorded': ['the native build or release that wrote the archive'],
                                                                   'consequence': 'cannot be cited as proof', 'synchronized_upgraded_by_numeric_closeness': False}},
                     'deltas_are_recorded_arithmetic': True, 'browser_arrival_order_is_not_used': True},
            'linkage': {'roles': {role: {'source_stream': 'events', 'join_key': 'sample_id', 'meaning': f'fixture meaning for {role}'} for role in ROLE_KEYS},
                        'status_meaning': STATUS_MEANING,
                        'status_precedence': ['stream_absent', 'identity_mismatch', 'ambiguous_kind', 'ambiguous_candidates', 'partial', 'missing', 'unresolved_reference', 'matched'],
                        'primary_roles': ROLE_KEYS[:4],
                        'selection_rules': {'joins': 'exact equality of the recorded join key', 'when_nothing_matches': 'missing / unresolved_reference / stream_absent',
                                            'when_several_match': 'ambiguous_kind or ambiguous_candidates with every candidate line index listed; the first line in the file is not chosen',
                                            'completeness': 'judged by the required sensor_kind set and per-kind cardinality, never by a record count alone',
                                            'state_hold': 'not applied: a frame never inherits another frame’s state', 'interpolation': 'none',
                                            'nearest_in_time': 'not used; numeric closeness is not treated as identity or as simultaneity'},
                        'role_coverage_on_this_page': {role: {'matched': len(frames)} for role in ROLE_KEYS[:4]}},
            'summary': {'frames_returned': len(frames), 'frames_with_all_primary_roles_matched': len(frames), 'frames_with_some_primary_roles_missing': 0,
                        'frames_with_no_primary_role_matched': 0, 'frames_with_ambiguous_primary_role': 0, 'frames_without_a_linked_state': 0,
                        'frames_with_unresolved_feedback_reference': len(frames)},
            'frames': frames,
            'not_proven': ['rendered 3D replay', 'a cross-stream or cross-episode replay cursor', 'that two records naming the same clock base were stamped by one writer'],
            'version_migration': {'from_schema': 'unirobot-mobilecar-frame-link-1', 'to_schema': FRAME_SCHEMA,
                                  'changed': ['paging.has_more is decided by finding the next qualifying anchor line'],
                                  'removed_fields': {'times.age_of_state_relative_to_frame': 'it merged the state event’s write stamp with the state sample stamps'},
                                  'compatibility_note': 'consumers must read schema_version: frame-link-1 and frame-link-2 pages are not the same contract'},
            'three_d_replay': {'this_slice_does_not_enable_3d_replay': True, 'live_geometry_or_actual_may_be_applied': False,
                               'transforms_are_full_per_body_pose_sequences': False, 'robot_pose_readiness_slice': 'GET /api/v1/episodes/{episode_id}/robot-state'},
            'capability_limits': ['no replay execution', 'no control, RESET, recording or physics stepping']}
    base.update(patch)
    return base


def geometry_payload():
    return {'schema_version': GEOMETRY_SCHEMA, 'read_only': True, 'data_source': 'live_native_http_with_verified_compiled_geometry',
            'world_pose_semantics': 'compiled_initial_layout_not_live_object_state', 'retrieved_at': '2026-01-01T00:00:00Z',
            'resource_identity': {'contract_version': 'mobilecar-1.0', 'model_id': 'fixture_model', 'model_sha256': 'm' * 64, 'scene_id': 'fixture_scene'},
            'runtime_identity': {'run_id': 'run_fixture', 'backend_generation': 1, 'episode_id': 'episode_fixture'},
            'data': {'contract_version': 'mobilecar-1.0', 'model_id': 'fixture_model', 'model_sha256': 'm' * 64, 'scene_id': 'fixture_scene',
                     'camera_ids': ['rgbd'], 'tcp_site': 'grasp_tcp', 'source': 'fixture',
                     'links': [{'name': 'base_link', 'parent_name': None, 'joint_name': 'base_free', 'joint_type': 'free', 'joint_axis': [0.0, 0.0, 1.0],
                                'local_transform': {'position_m': [0.0, 0.0, 0.055], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                                'geoms': [{'name': 'base_vis', 'geom_type': 'box', 'size_m': [0.09, 0.05, 0.02],
                                           'local_transform': {'position_m': [0.0, 0.0, 0.0], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                                           'rgba': [0.3, 0.4, 0.5, 1.0], 'mesh_asset_id': None, 'collision': False, 'group': 0}]},
                               {'name': 'link1', 'parent_name': 'base_link', 'joint_name': 'joint1', 'joint_type': 'hinge', 'joint_axis': [0.0, 0.0, 1.0],
                                'local_transform': {'position_m': [0.0, 0.0, 0.1], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                                'geoms': [{'name': 'link1_mesh', 'geom_type': 'mesh', 'size_m': [1.0, 1.0, 1.0],
                                           'local_transform': {'position_m': [0.0, 0.0, 0.0], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                                           'rgba': [0.6, 0.2, 0.2, 1.0], 'mesh_asset_id': 'link1', 'collision': False, 'group': 0}]}],
                     'world_links': [{'name': 'target_cube', 'parent_name': None, 'joint_name': None, 'joint_type': 'fixed', 'joint_axis': [0.0, 0.0, 1.0],
                                      'local_transform': {'position_m': [0.4, 0.0, 0.03], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                                      'geoms': [{'name': 'cube_vis', 'geom_type': 'box', 'size_m': [0.03, 0.03, 0.03],
                                                 'local_transform': {'position_m': [0.0, 0.0, 0.0], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                                                 'rgba': [0.9, 0.8, 0.1, 1.0], 'mesh_asset_id': None, 'collision': False, 'group': 0}]}],
                     'mesh_assets': [{'asset_id': 'link1', 'uri': f'/api/v1/mobilecar/scene/assets/link1?sha256={STL_SHA}', 'sha256': STL_SHA,
                                      'media_type': 'model/stl', 'coordinate_space': 'mujoco_compiled_mesh', 'units': 'm',
                                      'mesh_preprocessing_applied': True, 'source_sha256': 's' * 64, 'source_mesh_name': 'link1.stl'}]}}


def mapping_fixture(arm_status='partially_verified'):
    return [{'target': 'arm_joint_positions', 'recorded_field': 'arm_model_qpos_rad', 'recorded_unit': 'rad', 'recorded_length': 5,
             'target_field': 'bundle hinge joints joint1, joint2, joint3, joint4, joint5', 'status': arm_status,
             'evidence': {'bundle_arm_hinge_joints_in_document_order': ['joint1', 'joint2', 'joint3', 'joint4', 'joint5'], 'positions_are_model_radians_not_user_radians': True},
             'model_to_user_formula': {'q_model': 'zero_model_rad + user_direction * q_user', 'zero_model_rad': [0.0, 0.0, 0.0, -1.5707963267948966, 0.0],
                                       'user_direction': [1, 1, 1, 1, 1], 'authority': 'platform_reference_not_native_attested'},
             'no_default_applied': True, 'gap': 'joint positions for indexes 0, 1, 2 and 4 are mapped by array order without a per-index attestation'},
            {'target': 'base_position', 'recorded_field': 'base_position_world_sim_m', 'recorded_unit': 'm', 'recorded_length': 3,
             'target_field': 'bundle root link base_link free joint base_free', 'status': 'unverified', 'evidence': {}, 'no_default_applied': True,
             'gap': 'the body origin, frame and z convention for the recorded base position is not attested'},
            {'target': 'base_orientation', 'recorded_field': 'base_quaternion_xyzw', 'recorded_unit': 'unit quaternion', 'recorded_length': 4,
             'target_field': 'bundle transforms declare orientation as xyzw', 'status': 'unverified', 'evidence': {}, 'no_default_applied': True,
             'gap': 'the body and frame it rotates are not attested'},
            {'target': 'gripper_joints', 'recorded_field': 'gripper_width_m', 'recorded_unit': 'm', 'recorded_length': 1,
             'target_field': 'bundle slide joints left_jaw_joint, right_jaw_joint', 'status': 'unverified', 'evidence': {}, 'no_default_applied': True,
             'gap': 'no attested rule turns the recorded width into jaw joint values; a half-width or sign guess would have to be invented'},
            {'target': 'tcp_site_position', 'recorded_field': 'tcp_position_world_m', 'recorded_unit': 'm', 'recorded_length': 3,
             'target_field': 'bundle tcp_site grasp_tcp', 'status': 'unverified', 'evidence': {}, 'no_default_applied': True,
             'gap': 'whether the recorded position is the named site’s world position is not attested'},
            {'target': 'camera_extrinsics', 'recorded_field': None, 'recorded_unit': None, 'recorded_length': None,
             'target_field': 'bundle camera link chain depth_cam_link', 'status': 'missing', 'evidence': {}, 'no_default_applied': True,
             'gap': 'no recorded camera calibration, so the optical frame’s relation to the model link is unverified'},
            {'target': 'wheel_joint_velocities', 'recorded_field': 'wheel_velocity_rad_s', 'recorded_unit': 'rad/s', 'recorded_length': 4,
             'target_field': 'bundle wheel hinges', 'status': 'not_required_for_pose', 'evidence': {}, 'no_default_applied': True,
             'gap': 'the four wheel values carry no per-wheel identity; a static pose does not need them'},
            {'target': 'base_twist', 'recorded_field': 'base_twist_body_m_s', 'recorded_unit': 'm/s or rad/s per component', 'recorded_length': 3,
             'target_field': None, 'status': 'not_required_for_pose', 'evidence': {}, 'no_default_applied': True, 'gap': 'component meaning is not recorded'},
            {'target': 'dynamic_scene_objects', 'recorded_field': None, 'recorded_unit': None, 'recorded_length': None,
             'target_field': 'bundle world links world_static, target_cube', 'status': 'missing', 'evidence': {}, 'no_default_applied': True,
             'gap': 'no historical position is recorded for dynamic scene objects, so they cannot be placed from the record'}]


def pose_payload(episode, sample, **patch):
    value = {'schema_version': POSE_SCHEMA, 'read_only': True, 'source': SOURCE_FIXTURE, 'retrieved_at': '2026-01-01T00:00:00Z',
             'identity': {'run_id': 'run_a', 'episode_id': episode, 'recorded_run_manifest': {'contract_version': 'mobilecar-1.0', 'model_sha256': 'm' * 64},
                          'identity_source': 'the run manifest the recorder itself wrote, copied verbatim'},
             'frame': {'sample_id': sample, 'linkage_schema': FRAME_SCHEMA, 'linkage_status': 'matched',
                       'anchor': {'relative_path': 'observations/persist.jsonl', 'line_index': 0, 'persist_sequence': 1},
                       'media': {'items': [{'field': 'rgb_uri', 'uri': f'assets/rgb/{sample}_rgb.png', 'availability': 'present'}]}},
             'state': {'linkage_status': 'matched', 'source': {'stream_id': 'events', 'relative_path': 'events.jsonl', 'line_index': 7, 'event_seq': 8, 'event_type': 'feedback'},
                       'candidate_records': 1, 'single_state_selected': True,
                       'recorded_payload': {'arm_model_qpos_rad': ARM_RAD, 'base_position_world_sim_m': [0.1, 0.2, 0.05], 'gripper_width_m': 0.02,
                                            'tcp_position_world_m': [0.17, 0.0, 0.3], 'wheel_velocity_rad_s': [0.1, 0.1, 0.1, 0.1],
                                            'base_quaternion_xyzw': [0.0, 0.0, 0.0, 1.0], 'base_twist_body_m_s': [0.0, 0.0, 0.0]},
                       'declared_reference': {'feedback_sample_id': 'joint_feedback_1', 'row_status': 'unresolved_reference'}, 'units': {'*_rad': 'radians'}},
             'time': {'quantities': QUANTITIES, 'state_time_quantity_keys': ['state_event_write_minus_frame_capture']},
             'mapping': mapping_fixture(),
             'status_meaning': {'verified': 'the record and the fixed bundle agree on this mapping, and nothing had to be assumed',
                                'partially_verified': 'some parts of the mapping are attested; the attested indexes or fields are named here',
                                'unverified': 'the value is recorded, but its frame, order, sign or convention is not attested by the record or the bundle',
                                'missing': 'the value a renderer would need is not recorded at all',
                                'not_required_for_pose': 'recorded data that this slice does not need to place the robot'},
             'pose_readiness': {'model_identity': 'match', 'mapping_valid_for_this_episode': True, 'mapped_targets_partially_or_fully_verified': '1/9',
                                'robot_state_can_be_rebuilt_without_assumptions': False,
                                'blocking_fields': ['base_position', 'base_orientation', 'gripper_joints', 'tcp_site_position', 'camera_extrinsics', 'dynamic_scene_objects'],
                                'next_round_owner': 'frontend assembly plus an attested base/gripper mapping source',
                                'note': 'resource identity, digests and joint-length checks pass; the remaining gaps are attestation gaps'},
             'model_resource': {'status': 'match', 'comparison': {'contract_version': {'recorded': 'mobilecar-1.0', 'bundle': 'mobilecar-1.0', 'equal': True},
                                                                  'model_id': {'recorded': 'fixture_model', 'bundle': 'fixture_model', 'equal': True},
                                                                  'model_sha256': {'recorded': 'm' * 64, 'bundle': 'm' * 64, 'equal': True},
                                                                  'scene_id': {'recorded': 'fixture_scene', 'bundle': 'fixture_scene', 'equal': True}},
                                'bundle_sha256': '2' * 64, 'content_identity_sha256': 'c' * 64, 'compiler': {'name': 'MuJoCo', 'version': '3.1.6'},
                                'link_count': 2, 'tcp_site': 'grasp_tcp', 'camera_ids': ['rgbd'],
                                'arm_hinge_joints': ['joint1', 'joint2', 'joint3', 'joint4', 'joint5'], 'gripper_slide_joints': ['left_jaw_joint', 'right_jaw_joint'],
                                'wheel_hinge_joints': ['front_left_joint'], 'assets': [{'asset_id': 'link1', 'sha256': STL_SHA, 'media_type': 'model/stl',
                                                                                        'coordinate_space': 'mujoco_compiled_mesh', 'units': 'm', 'bytes': len(STL)}],
                                'asset_integrity': 're-verified per request before bytes leave the process', 'live_native_scene_proxied': False,
                                'served_via': 'GET /api/v1/episodes/{episode_id}/model/assets/{asset_id} (frozen bundle only)'},
             'rendering': {'verified': False, 'frontend_assembly_done': False, 'note': 'this slice prepares and reports the mapping; it does not render'},
             'not_proven': [{'target': 'base_position', 'status': 'unverified', 'gap': 'the body origin, frame and z convention is not attested'},
                            {'target': 'dynamic_scene_objects', 'status': 'missing', 'gap': 'no historical position is recorded for dynamic scene objects'}],
             'capability_limits': ['no replay execution', 'no live geometry or Actual substitution', 'no fabricated dynamic object pose',
                                   'no control, RESET, recording or physics stepping']}
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
            'paging': {'limit': 20, 'offset': 0, 'returned': len(rows), 'total_matches': len(rows), 'next_offset': None, 'order': 'run_id_then_episode_id'},
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


SLOW = {'frame': 'idle', 'pose': 'idle'}
SYNTH_EPISODES = ['episode_ok', 'episode_no_frames', 'episode_bad_frame_schema', 'episode_bad_sample', 'episode_no_time_bases',
                  'episode_media_gaps', 'episode_state_missing', 'episode_ambiguous', 'episode_state_ambiguous',
                  'episode_pose_verified', 'episode_pose_identity_mismatch', 'episode_pose_asset_mismatch',
                  'episode_pose_missing', 'episode_pose_bad_schema', 'episode_pose_late', 'episode_asset_conflict']


def ambiguous_frame(sample='rgbd_ambiguous'):
    frame = frame_payload(sample)
    roles = [dict(role) for role in frame['roles']]
    roles[0] = {**roles[0], 'status': 'ambiguous_kind', 'candidate_records': 3, 'matched_records': 1, 'duplicate_kinds': ['rgb'],
                'kind_inventory': {'rgb': [1, 4], 'depth': [2]}, 'candidate_line_indexes': [1, 2, 4],
                'ambiguous_records': [{'stream_id': 'observations-index', 'relative_path': 'observations/index.jsonl', 'line_index': 1,
                                       'record_position': 'observations/index.jsonl#1', 'projection': {'sensor_kind': 'rgb'}},
                                      {'stream_id': 'observations-index', 'relative_path': 'observations/index.jsonl', 'line_index': 4,
                                       'record_position': 'observations/index.jsonl#4', 'projection': {'sensor_kind': 'rgb'}}]}
    media = [dict(item) for item in frame['media']['items']]
    media[0] = {**media[0], 'observation_row_line_indexes': [1, 4], 'observation_row_candidates': 2, 'observation_rows_conflict': True}
    return {**frame, 'roles': roles, 'media': {**frame['media'], 'items': media},
            'primary_roles_matched': ROLE_KEYS[1:4], 'primary_roles_ambiguous': ['image_observation'], 'linkage_status': 'ambiguous_kind'}


def state_ambiguous_frame(sample='rgbd_state_ambiguous'):
    frame = frame_payload(sample)
    roles = [dict(role) for role in frame['roles']]
    roles[3] = {**roles[3], 'status': 'ambiguous_candidates', 'candidate_records': 2, 'matched_records': 0, 'candidate_line_indexes': [7, 8],
                'ambiguous_records': [{'stream_id': 'events', 'relative_path': 'events.jsonl', 'line_index': 7, 'record_position': 'events.jsonl#7', 'event_seq': 8},
                                      {'stream_id': 'events', 'relative_path': 'events.jsonl', 'line_index': 8, 'record_position': 'events.jsonl#8', 'event_seq': 9}]}
    return {**frame, 'roles': roles, 'linkage_status': 'ambiguous_candidates', 'primary_roles_matched': ROLE_KEYS[:3],
            'primary_roles_ambiguous': ['state_feedback_event'],
            'state': {**frame['state'], 'status': 'ambiguous_candidates', 'candidate_records': 2, 'single_state_selected': False, 'recorded_state': None,
                      'source': None, 'recorded_fields': {},
                      'candidates': [{'line_index': 7, 'record_position': 'events.jsonl#7', 'event_seq': 8, 'backend_monotonic_s': 99.997, 'sim_time_s': 1.0, 'payload': {}},
                                     {'line_index': 8, 'record_position': 'events.jsonl#8', 'event_seq': 9, 'backend_monotonic_s': 99.998, 'sim_time_s': 1.0, 'payload': {}}],
                      'multiple_candidates_note': 'two events carried this control_tick_id; the first line in the file is not chosen'}}


async def synthetic_handler(route):
    request = route.request
    path = urlsplit(request.url).path
    query = parse_qs(urlsplit(request.url).query)
    segments = path.split('/')
    # /api/v1/episodes/<id>[/frames|/robot-state|/model/assets/…|/records|/assets/…]: the identity is
    # segment 4, not segment 3 ('episodes'), otherwise every fixture answers with episode_id='episodes'.
    episode = segments[4] if len(segments) > 4 else ''
    if request.method != 'GET':
        await route.fulfill(status=405, content_type='text/html', body=REFUSAL); return
    if path.endswith('/robot-state'):
        if episode == 'episode_pose_missing':
            await route.fulfill(status=404, content_type='application/json', body=json.dumps({'detail': {
                'code': 'frame_not_found', 'message': 'this Episode has no persisted frame matching the request', 'read_only': True,
                'episode_id': episode, 'sample_id': (query.get('sample_id') or [''])[0]}})); return
        if episode == 'episode_pose_bad_schema':
            await route.fulfill(json={'schema_version': 'unirobot-mobilecar-history-pose-2', 'read_only': True}); return
        if episode == 'episode_pose_late':
            SLOW['pose'] = 'pending'
            await asyncio.sleep(2.4)
            SLOW['pose'] = 'done'
        sample = (query.get('sample_id') or [''])[0]
        if episode == 'episode_pose_verified':
            await route.fulfill(json=pose_payload(episode, sample, mapping=mapping_fixture('verified'))); return
        if episode == 'episode_pose_identity_mismatch':
            payload = pose_payload(episode, sample)
            payload['model_resource']['comparison']['model_sha256'] = {'recorded': 'm' * 64, 'bundle': 'other', 'equal': False}
            payload['pose_readiness']['model_identity'] = 'mismatch'
            await route.fulfill(json=payload); return
        if episode in ('episode_pose_asset_mismatch', 'episode_asset_conflict'):
            payload = pose_payload(episode, sample)
            payload['model_resource']['assets'][0]['sha256'] = 'f' * 64
            await route.fulfill(json=payload); return
        await route.fulfill(json=pose_payload(episode, sample)); return
    if '/model/assets/' in path:
        asset = segments[-1]
        declared = (query.get('sha256') or [''])[0]
        if episode == 'episode_asset_conflict' and asset == 'link1':
            await route.fulfill(status=409, content_type='application/json', body=json.dumps({'detail': {
                'code': 'history_asset_revision_changed', 'message': 'asset digest differs from the frozen bundle', 'read_only': True,
                'asset_id': asset, 'bundle_sha256': 'f' * 64, 'requested_sha256': declared}})); return
        if declared and declared != STL_SHA:
            await route.fulfill(status=409, content_type='application/json', body=json.dumps({'detail': {
                'code': 'history_asset_revision_changed', 'message': 'asset digest differs from the frozen bundle', 'read_only': True,
                'asset_id': asset, 'bundle_sha256': STL_SHA, 'requested_sha256': declared}})); return
        await route.fulfill(status=200, body=STL, content_type='model/stl', headers={'ETag': f'"sha256:{STL_SHA}"', 'Cache-Control': 'no-store'}); return
    if path.endswith('/frames'):
        if episode == 'episode_no_frames':
            await route.fulfill(status=404, content_type='application/json', body=json.dumps({'detail': {
                'code': 'episode_stream_unavailable', 'message': 'this record has no observations/persist.jsonl', 'read_only': True}})); return
        if episode == 'episode_bad_frame_schema':
            await route.fulfill(json={'schema_version': 'unirobot-mobilecar-frame-link-1', 'read_only': True}); return
        if episode == 'episode_bad_sample':
            await route.fulfill(status=400, content_type='application/json', body=json.dumps({'detail': {
                'code': 'sample_id_invalid', 'message': 'sample id is not a native id token', 'read_only': True}})); return
        if (query.get('sample_id') or [''])[0].startswith('rgbd_slow'):
            SLOW['frame'] = 'pending'
            await asyncio.sleep(2.4)
            SLOW['frame'] = 'done'
        if (query.get('time_from') or [''])[0] == '1':
            empty = frames_payload(episode, [])
            await route.fulfill(json={**empty, 'paging': paging_fixture([], returned=0, has_more=False, next_offset=None, next_qualifying_anchor_line_index=None,
                                                                         excluded_outside_time_window=303, anchor_records_examined=303, post_page_records_examined=0,
                                                                         scan={'whole_file_scanned': True, 'stopped_after_full_page_at_line_index': None,
                                                                               'note': 'the file was read past the last qualifying anchor'}),
                                          'time': {**empty['time'], 'selected_time_base': (query.get('time_base') or [''])[0], 'time_from': 1.0, 'time_to': 2.0}}); return
        if episode == 'episode_no_time_bases':
            payload = frames_payload(episode, [frame_payload('rgbd_empty_bases')])
            payload['time'] = {**payload['time'], 'selectable_time_bases': []}
            await route.fulfill(json=payload); return
        if episode == 'episode_media_gaps':
            missing = frame_payload('rgbd_media_missing', media={**frame_payload('x')['media'], 'items': [
                {'field': 'rgb_uri', 'uri': 'assets/rgb/gone_rgb.png', 'availability': 'absent', 'declared_sha256_by_row': 'c' * 64, 'declared_bytes_by_row': 9,
                 'bytes_on_disk': None, 'agrees_with_observation_row': None, 'observation_row_line_indexes': [], 'observation_row_candidates': 0},
                {'field': 'depth_uri', 'uri': 'assets/depth/escape.npy', 'availability': 'refused', 'refusal_code': 'episode_asset_escape'},
                {'field': 'valid_mask_uri', 'uri': 'assets/masks/x_valid.png', 'availability': 'not_recorded_on_this_frame'}]})
            unverified = frame_payload('rgbd_digest_bad', media={**frame_payload('x')['media'], 'items': [
                {'field': 'rgb_uri', 'uri': 'assets/rgb/bad_digest_rgb.png', 'availability': 'present', 'declared_sha256_by_row': 'a' * 64, 'declared_bytes_by_row': 3,
                 'bytes_on_disk': 3, 'agrees_with_observation_row': True, 'observation_row_line_indexes': [1], 'observation_row_candidates': 1}]})
            await route.fulfill(json=frames_payload(episode, [frame_payload('rgbd_media_ok'), missing, unverified],
                                                   paging=paging_fixture([1, 2, 3], returned=3, next_offset=None, next_qualifying_anchor_line_index=None, has_more=False))); return
        if episode == 'episode_state_missing':
            stateless = frame_payload('rgbd_state_missing', linkage_status='missing', primary_roles_matched=[],
                                      state={**frame_payload('x')['state'], 'status': 'missing', 'source': None, 'recorded_state': None, 'recorded_fields': {},
                                             'candidate_records': 0, 'single_state_selected': None, 'candidates': []},
                                      roles=[{**role, 'status': 'missing', 'sources': [], 'candidate_records': 0, 'matched_records': 0, 'candidate_line_indexes': []}
                                             if role['role'] == 'state_feedback_event' else role for role in frame_payload('x')['roles']])
            payload = frames_payload(episode, [frame_payload('rgbd_with_state'), stateless],
                                     paging=paging_fixture([1, 2], returned=2, next_offset=None, next_qualifying_anchor_line_index=None, has_more=False))
            payload['summary'] = {**payload['summary'], 'frames_returned': 2, 'frames_with_all_primary_roles_matched': 1,
                                  'frames_with_some_primary_roles_missing': 1, 'frames_without_a_linked_state': 1, 'frames_with_unresolved_feedback_reference': 2}
            await route.fulfill(json=payload); return
        if episode == 'episode_ambiguous':
            payload = frames_payload(episode, [frame_payload('rgbd_clean'), ambiguous_frame()],
                                     paging=paging_fixture([1, 2], returned=2, next_offset=None, next_qualifying_anchor_line_index=None, has_more=False))
            payload['summary'] = {**payload['summary'], 'frames_returned': 2, 'frames_with_all_primary_roles_matched': 1, 'frames_with_ambiguous_primary_role': 1}
            payload['linkage'] = {**payload['linkage'], 'role_coverage_on_this_page': {**payload['linkage']['role_coverage_on_this_page'],
                                                                                       'image_observation': {'matched': 1, 'ambiguous_kind': 1}}}
            await route.fulfill(json=payload); return
        if episode == 'episode_state_ambiguous':
            payload = frames_payload(episode, [frame_payload('rgbd_with_state'), state_ambiguous_frame()],
                                     paging=paging_fixture([1, 2], returned=2, next_offset=None, next_qualifying_anchor_line_index=None, has_more=False))
            payload['summary'] = {**payload['summary'], 'frames_returned': 2, 'frames_with_all_primary_roles_matched': 1, 'frames_with_ambiguous_primary_role': 1}
            await route.fulfill(json=payload); return
        frames = [frame_payload(f'rgbd_{i}') for i in range(3)]
        offset = int((query.get('offset') or ['0'])[0])
        if offset:
            filtered = 3 if (query.get('sample_id') or [''])[0] else 0
            await route.fulfill(json=frames_payload(episode, [], paging=paging_fixture([], offset=offset, returned=0, has_more=False, next_offset=None,
                                                                                       next_qualifying_anchor_line_index=None, skipped_before_offset=offset,
                                                                                       excluded_by_sample_id_filter=filtered, anchor_records_examined=6,
                                                                                       post_page_records_examined=6,
                                                                                       scan={'whole_file_scanned': True, 'stopped_after_full_page_at_line_index': None,
                                                                                             'note': 'no further qualifying anchor exists after this offset'}))); return
        await route.fulfill(json=frames_payload(episode, frames)); return
    if '/assets/' in path:
        if 'bad_digest_rgb.png' in path:
            await route.fulfill(status=409, content_type='application/json', body=json.dumps({'detail': {'code': 'episode_asset_digest_mismatch',
                                                                                                          'message': 'asset digest does not match the requested sha256',
                                                                                                          'expected': 'a' * 64, 'actual': 'b' * 64}})); return
        if 'npy' in path:
            await route.fulfill(status=200, body=b'\x93NUMPY\x01\x00', content_type='application/octet-stream', headers={'X-Episode-Asset-Sha256': 'd' * 64}); return
        await route.fulfill(status=200, body=PNG, content_type='image/png', headers={'X-Episode-Asset-Sha256': hashlib.sha256(PNG).hexdigest(), 'X-Episode-Run-Id': 'run_a'}); return
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
        await route.fulfill(json=list_payload(SYNTH_EPISODES)); return
    if re.fullmatch(r'/api/v1/episodes/[^/]+', path):
        await route.fulfill(json=detail_payload(episode)); return
    # Anything deeper is not one of the exact history routes: answer the way the read-only gateway does,
    # so the suite proves the pane never reaches a widened episode path.
    await route.fulfill(status=404, content_type='text/html', body=REFUSAL)


async def scene_handler(route):
    """The placement tree is a platform-side read; in synthetic mode it is a fixture too, so this suite
    never needs a live robot to exercise the reference assembly."""
    await route.fulfill(json=geometry_payload())


async def synthetic_flow(page):
    await wait_list(page)
    await open_episode(page, 'run_a', 'episode_ok')
    view = await page_attrs(page)
    check('the synthetic pane binds frame-link-2 and shows the fixture’s three frames',
          view['schema'] == FRAME_SCHEMA and view['returned'] == '3' and len(view['rowSamples']) == 3
          and view['migrationTo'] == FRAME_SCHEMA and view['primaryMatched'] == '|'.join(ROLE_KEYS[:4]))
    check('the three state stamps stay separate rows and the removed age is named as removed',
          {'state_event_write_minus_frame_capture', 'state_payload_feedback_time_minus_frame_capture', 'recorder_declared_feedback_time_minus_frame_capture',
           'state_sim_time_minus_frame_capture_sim_time', 'persist_minus_capture', 'observation_arrival_minus_frame_capture'} == set(view['quantityKeys'])
          and 'age_of_state_relative_to_frame' in await page.locator('[data-time-semantics]').inner_text()
          # String(3.0) in JS is '3': the fixture values are shown in the reader's own numeric form.
          and '3' in view['quantityAbs'] and '4' in view['quantityAbs'], view['quantityKeys'])
    await wait_model(page, 'ready')
    model = await page_attrs(page)
    check('the fixed reference assembles from the bundle tree with history bytes and an unverified pose',
          model['modelStatus'] == 'ready' and model['modelCanvas'] == 1
          and '固定模型参考；所选帧姿态尚未验证' in model['modelText'] and model['modelFramePose'] == 'false'
          and model['comparisonEqual'] == ['true'] * 4, model['modelStatus'])
    check('a partially verified mapping drives nothing and keeps the reference pose',
          '已驱动 0 个关节值' in model['modelDrive'] and model['mappingDrivable'] == ['false'] * 9
          and model['mappingStatuses'] == ['partially_verified'] + ['unverified'] * 4 + ['missing'] + ['not_required_for_pose'] * 2 + ['missing']
          and int(model['modelWithheld']) == 9, (model['mappingStatuses'], model['modelWithheld']))
    check('the reference surface carries no live control affordance and declares itself non-polling',
          model['controlSurface'] == 0 and await attr(page, '[data-model-pane]', 'data-model-live-poll') == 'off'
          and await attr(page, '[data-model-pane]', 'data-reference-pose') == 'compiled-initial-layout',
          (model['controlSurface'], model['modelStatus']))

    await open_episode(page, 'run_a', 'episode_pose_verified')
    await wait_model(page, 'ready')
    verified = await page_attrs(page)
    arm = verified['mappingTargets'].index('arm_joint_positions')
    check('a verified mapping drives exactly the recorded model radians (synthetic gate, not a real archive claim)',
          verified['mappingDrivable'][arm] == 'true' and verified['mappingStatuses'][arm] == 'verified'
          and '已驱动 5 个关节值' in verified['modelDrive'], verified['modelDrive'])
    await page.locator('[data-model-inspect]').click()
    driven = json.loads(await attr(page, '[data-model-inspected]', 'data-model-inspected'))
    check('the driven values are the model angles themselves, not user-zero converted ones',
          driven['selectedJointDriven']['joint4'] == ARM_RAD[3] and driven['selectedJointDriven']['joint1'] == ARM_RAD[0]
          and abs(driven['selectedJointDriven']['joint4'] - (ARM_RAD[3] - (-1.5707963267948966))) > 1.0, driven['selectedJointDriven'])

    await open_episode(page, 'run_a', 'episode_pose_identity_mismatch')
    await wait_model(page, 'blocked')
    mismatch = await page_attrs(page)
    check('a model identity that does not match the record blocks the assembly instead of substituting geometry',
          mismatch['modelStatus'] == 'blocked' and '模型身份不符' in mismatch['modelStage']
          and mismatch['canvas'] == 0 and 'false' in mismatch['comparisonEqual'], mismatch['modelStage'][:160])
    await open_episode(page, 'run_a', 'episode_pose_asset_mismatch')
    await wait_model(page, 'blocked')
    asset_mismatch = await page_attrs(page)
    check('an asset digest that differs from the frozen bundle blocks the assembly and names the asset',
          asset_mismatch['modelStatus'] == 'blocked' and '资产摘要不一致' in asset_mismatch['modelStage']
          and 'link1' in asset_mismatch['modelStage'] and asset_mismatch['assetEqual'] == ['false'] and asset_mismatch['canvas'] == 0,
          asset_mismatch['modelStage'][:160])

    await open_episode(page, 'run_a', 'episode_asset_conflict')
    await wait_model(page, 'blocked')
    await page.locator('[data-asset-pick="link1"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-asset-row=\"link1\"]')?.getAttribute('data-asset-read') ?? '')==='failed'", timeout=30000)
    conflict = await attr(page, '[data-asset-row="link1"]', 'data-asset-detail')
    check('a content change on the asset route is shown as the reader’s own 409 code with no bytes claimed',
          'history_asset_revision_changed' in conflict and '字节未返回' in conflict and 'link1' in conflict, conflict[:200])

    await open_episode(page, 'run_a', 'episode_pose_missing')
    await wait_model(page, 'failed')
    missing_pose = await page_attrs(page)
    check('a robot-state the reader cannot find is reported with its own code and leaves the frame panels intact',
          missing_pose['modelStatus'] == 'failed' and 'frame_not_found' in missing_pose['modelStage']
          and '该 Episode 没有符合请求的持久化帧' in missing_pose['modelStage']
          and missing_pose['canvas'] == 0 and len(missing_pose['rowSamples']) == 3, missing_pose['modelStage'][:200])
    await open_episode(page, 'run_a', 'episode_pose_bad_schema')
    await wait_model(page, 'failed')
    check('a pose payload that is not history-pose-1 is refused as a contract finding, not rendered',
          '响应不是 unirobot-mobilecar-history-pose-1' in (await page_attrs(page))['modelStage']
          and 'unirobot-mobilecar-history-pose-2' in (await page_attrs(page))['modelStage'], (await page_attrs(page))['modelStage'][:200])

    await open_episode(page, 'run_a', 'episode_ambiguous')
    await page.locator('[data-frame-pick="rgbd_ambiguous"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-frame-ambiguous-count]')?.getAttribute('data-frame-ambiguous-count') ?? '')==='1'", timeout=30000)
    ambiguous = await page_attrs(page)
    role_text = await page.locator('[data-frame-role="image_observation"]').inner_text()
    check('an ambiguous_kind role lists every candidate line and the frame records the ambiguity',
          ambiguous['ambiguousCount'] == '1' and ambiguous['primaryAmbiguous'] == 'image_observation'
          and ambiguous['roleStatuses'][0] == 'ambiguous_kind' and 'recorded more than once' in role_text
          and 'rgb→[1,4]' in role_text and '2 条候选记录冲突' in role_text
          and '1,4' in ambiguous['mediaRowLines'][0] and ambiguous['rowAmbiguous'][1] == 'image_observation',
          (ambiguous['roleStatuses'], ambiguous['mediaRowLines']))
    await open_episode(page, 'run_a', 'episode_state_ambiguous')
    await page.locator('[data-frame-pick="rgbd_state_ambiguous"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-frame-single-state]')?.getAttribute('data-frame-single-state') ?? '')==='false'", timeout=30000)
    no_state = await page_attrs(page)
    check('no single selected state means no values at all: nothing is picked, zero-filled or carried over',
          no_state['singleState'] == 'false' and no_state['stateCandidates'] == '2' and no_state['emptyPayload'] == 'true'
          and not no_state['stateKeys'] and '不挑第一条' in no_state['text'] and '不补 0' in no_state['text']
          and 'the first line in the file is not chosen' in no_state['text']
          and no_state['candidateLines'] == ['events.jsonl#7', 'events.jsonl#8'], (no_state['singleState'], no_state['stateKeys']))
    await wait_model(page, 'ready')
    after_ambiguous = await page_attrs(page)
    check('the model reference follows the frame whose state is ambiguous without inventing a pose',
          after_ambiguous['modelStatus'] == 'ready' and '已驱动 0 个关节值' in after_ambiguous['modelDrive']
          and after_ambiguous['modelSample'] == 'rgbd_state_ambiguous', after_ambiguous['modelDrive'])

    await open_episode(page, 'run_a', 'episode_no_time_bases')
    empty_bases = await page_attrs(page)
    options = await page.locator('select[aria-label="帧时间基"] option').evaluate_all('els=>els.map(e=>e.value)')
    check('an empty selectable_time_bases page offers no numeric base at all instead of a default list',
          empty_bases['selectable'] == [] and options == [''] and empty_bases['windowGate'] == 'refused'
          and '未选择时间基' in empty_bases['windowReason'] and await page.locator('[data-frame-window-apply]').is_disabled()
          and 'reader 未声明（空数组就是本页的答案，不回退默认基）' in await page.locator('[data-frame-selectable-bases]').inner_text(),
          (options, empty_bases['windowReason']))

    await open_episode(page, 'run_a', 'episode_media_gaps')
    await wait_asset_uri(page, 'assets/rgb/rgbd_media_ok_rgb.png')
    await wait_asset_settled(page)
    check('a present rgb reference is read, decoded and compared with its declared digest',
          (await page_attrs(page))['assetStatus'] == 'bytes' and (await page_attrs(page))['assetDecoded'] == 'ok'
          and (await page_attrs(page))['assetMatch'] == 'true')
    await page.locator('[data-frame-pick="rgbd_media_missing"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-frame-asset-status]')?.getAttribute('data-frame-asset-status') ?? '')==='not-loaded'", timeout=30000)
    gap = await page_attrs(page)
    check('an absent or refused reference clears the image instead of keeping the previous frame’s picture',
          gap['assetStatus'] == 'not-loaded' and gap['assetUri'] == 'none' and gap['assetSample'] == 'rgbd_media_missing'
          and await count(page, '[data-frame-asset-image]') == 0 and '不显示任何图像' in await page.locator('[data-frame-asset-unavailable]').inner_text()
          and gap['mediaAvailability'] == ['absent', 'refused', 'not_recorded_on_this_frame'], gap['mediaAvailability'])
    check('each unusable reference says why in the reader’s own terms, per item',
          '不按文件名推测内容' in await page.locator('[data-frame-media-ref="assets/rgb/gone_rgb.png"]').inner_text()
          and 'refusal_code=episode_asset_escape' in await page.locator('[data-frame-media-ref="assets/depth/escape.npy"]').inner_text()
          and '不拿别的帧的图片顶替' in await page.locator('[data-frame-media-ref="assets/masks/x_valid.png"]').inner_text()
          and 'none is silently chosen' in await page.locator('[data-media-declaration]').inner_text())
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
          and await count(page, '[data-frame-asset-image]') == 0)

    await open_episode(page, 'run_a', 'episode_state_missing')
    await page.locator('[data-frame-pick="rgbd_state_missing"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-frame-state-status]')?.getAttribute('data-frame-state-status') ?? '')==='missing'", timeout=30000)
    missing_state = await page_attrs(page)
    check('a frame whose state did not match says so and never substitutes another frame’s state',
          missing_state['stateStatus'] == 'missing' and await count(page, '[data-state-row]') == 0
          and '状态未命中（status=missing）' in await page.locator('[data-provenance-row="state_position"]').inner_text()
          and 'no record for this role carried the key' in await page.locator('[data-frame-role="state_feedback_event"]').inner_text()
          and 'carried_over_from_another_frame=false' in missing_state['text'])

    await open_episode(page, 'run_a', 'episode_ok')
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
    await page.locator('input[aria-label="时间窗口起点"]').fill('1')
    await page.locator('input[aria-label="时间窗口终点"]').fill('2')
    await page.locator('[data-frame-window-apply]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-page-kind]')?.getAttribute('data-frame-page-kind') ?? '')==='window-empty'")
    empty = await page_attrs(page)
    check('an empty window page counts the exclusions, clears rows and releases the model surface',
          empty['pageKind'] == 'window-empty' and '空结果页，不是读取错误' in empty['explanation']
          and await count(page, '[data-frame-asset-uri]') == 0 and not empty['rowSamples']
          and empty['modelStatus'] == 'idle' and empty['canvas'] == 0, empty['modelStatus'])

    await open_episode(page, 'run_a', 'episode_pose_late')
    await page.locator('input[aria-label="sample_id 精确打开"]').fill('rgbd_slow_1')
    await page.locator('[data-frame-open-sample]').click()
    await page.wait_for_timeout(200)
    await open_episode(page, 'run_a', 'episode_ambiguous')
    await wait_frames(page, "()=>(document.querySelector('[data-frame-episode]')?.getAttribute('data-frame-episode') ?? '')==='episode_ambiguous'")
    await wait_model(page, 'ready')
    await page.wait_for_timeout(2600)
    after_late = await page_attrs(page)
    check('a frame page and a robot-state that arrive after the switch never land (synthetic delayed responses)',
          SLOW['frame'] == 'done' and SLOW['pose'] == 'done' and after_late['episode'] == 'episode_ambiguous'
          and after_late['modelEpisode'] == 'episode_ambiguous' and after_late['contextSample'] == 'none'
          and 'rgbd_slow' not in after_late['text'] and after_late['currentSample'] == 'rgbd_clean'
          and 'rgbd_slow' not in after_late['modelText'], (after_late['modelEpisode'], after_late['currentSample']))

    await open_episode(page, 'run_a', 'episode_no_frames', expect='error')
    missing_stream = await page_attrs(page)
    check('an Episode without a persist stream is shown with the reader’s code and leaves the pane unbound',
          'episode_stream_unavailable' in missing_stream['error'] and '没有对应文件' in missing_stream['error']
          and missing_stream['bound'] == 'false' and await count(page, '[data-frame-row]') == 0)
    await open_episode(page, 'run_a', 'episode_bad_frame_schema', expect='error')
    check('a frame payload that is not frame-link-2 is refused as a contract finding, not rendered',
          'unirobot-mobilecar-frame-link-1' in (await page_attrs(page))['error'] and (await page_attrs(page))['bound'] == 'false')
    await open_episode(page, 'run_a', 'episode_bad_sample', expect='error')
    check('the reader’s sample_id_invalid refusal is shown with its own hint',
          'sample_id_invalid' in (await page_attrs(page))['error'] and '不是原生 id token' in (await page_attrs(page))['error'])

    await open_episode(page, 'run_a', 'episode_ok')
    await page.locator('[data-stream-option="observations-persist"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-stream-path]')?.getAttribute('data-stream-path') ?? '')==='observations-persist.jsonl'", timeout=30000)
    check('records: an explicit empty numeric_time_bases array keeps seeking refused instead of restoring defaults',
          await attr(page, '[data-seek-gate]', 'data-seek-gate') == 'refused'
          and await attr_all(page, '[data-seek-numeric-bases]', 'data-seek-numeric-bases') == ['']
          and await page.locator('input[aria-label="定位时间值"]').is_disabled())
    await open_episode(page, 'run_a', 'episode_ok')
    await page.locator('input[aria-label="sample_id 精确打开"]').fill('rgbd_0')
    await page.locator('[data-frame-open-sample]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-context-sample]')?.getAttribute('data-frame-context-sample') ?? '')==='rgbd_0'")
    for _ in range(3):
        await page.locator('[data-frame-next]').click()
        await page.wait_for_timeout(200)
    stop = await page_attrs(page)
    check('the corrected pagination stops the walk with the reader’s counters and keeps the sample condition',
          stop['returned'] == '0' and '不伪造分页结果' in stop['notice'] and '混合了候选行计数与锚点原生行号' not in stop['notice']
          and stop['contextSample'] == 'rgbd_0' and stop['hasMore'] == 'false' and stop['wholeFile'] == 'true', stop['notice'][:200])
    await page.locator('[data-frame-sample-clear]').click()
    await wait_frames(page, "()=>(document.querySelector('[data-frame-returned]')?.getAttribute('data-frame-returned') ?? '')==='3'")
    await page.locator('[data-frame-play]').click()
    playing = await attr(page, '[data-frame-play]', 'data-frame-play')
    await page.wait_for_timeout(1200)
    played = await page_attrs(page)
    await page.locator('[data-frame-play]').click()
    check('play advances on a UI cadence only, re-reading the state of each frame it lands on',
          playing == 'pause' and int(played['index']) >= 1 and played['modelSample'] == played['currentSample']
          and '节奏只控制界面推进，不是录制帧率' in played['text'] and '帧率' not in played['explanation'], (playing, played['index']))


async def boundary_checks(page):
    episode = a.complete_episode if a.mode == 'real' else 'episode_ok'
    for method, path in (('POST', f'/api/v1/episodes/{episode}/frames'),
                         ('GET', f'/api/v1/episodes/{episode}/frames/extra'),
                         ('POST', f'/api/v1/episodes/{episode}/robot-state'),
                         ('GET', f'/api/v1/episodes/{episode}/robot-state/extra'),
                         ('POST', f'/api/v1/episodes/{episode}/model/assets/link1'),
                         ('GET', f'/api/v1/episodes/{episode}/model/assets/link1/deeper'),
                         ('GET', f'/api/v1/episodes/{episode}/model/assets'),
                         ('POST', '/api/v1/episodes/episode_ok/validate'),
                         ('GET', f'/api/v1/episodes/{episode}/frames/deeper/still')):
        response = await page.request.fetch(a.url + path, method=method, data='{}' if method == 'POST' else None)
        body = await response.text()
        check(f'the gateway answers {method} {path} with its own refusal, never a forwarded call',
              response.status in (404, 405) and ('allowlisted' in body or 'not allowed' in body.lower()), (response.status, body[:120]))
    if a.mode == 'real':
        sample = report['real']['complete']['sample']
        for path, params in ((f'/api/v1/episodes/{episode}/frames', {'run_id': a.complete_run, 'limit': 1}),
                             (f'/api/v1/episodes/{episode}/robot-state', {'run_id': a.complete_run, 'sample_id': sample}),
                             (f'/api/v1/episodes/{episode}/model/assets/link1', {'run_id': a.complete_run})):
            response = await page.request.get(a.url + path + '?' + '&'.join(f'{k}={v}' for k, v in params.items()))
            content_type = response.headers.get('content-type') or ''
            check(f'the gateway forwards the exact GET {urlsplit(path).path} and nothing else',
                  response.status == 200 and content_type.startswith(('application/json', 'model/stl')), (response.status, content_type))
        unknown = await page.request.get(a.url + f'/api/v1/episodes/{episode}/robot-state?run_id={a.complete_run}&sample_id=rgbd_does_not_exist')
        refused = await unknown.json()
        check('an unknown sample_id reaches the reader’s own 404 frame_not_found through the exact route',
              unknown.status == 404 and refused['detail']['code'] == 'frame_not_found', (unknown.status, refused))


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
        page = await browser.new_page(viewport={'width': 1700, 'height': 1000}, device_scale_factor=1)
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        page.on('request', lambda req: report['requests'].append({'method': req.method, 'url': req.url}))
        try:
            if a.mode == 'synthetic':
                await page.route('**/api/v1/episodes**', synthetic_handler)
                await page.route('**/api/v1/mobilecar/scene', scene_handler)
            await open_history(page)
            # The app's own live viewport may load scene meshes while the shell boots; the isolation
            # claim below is about the history pane, so it is measured from the moment it opens.
            report['history_from'] = len(report['requests'])
            if a.mode == 'real': await real_flow(page)
            else: await synthetic_flow(page)
            await boundary_checks(page)
            episodes = [r for r in report['requests'] if '/api/v1/episodes' in r['url']]
            sub_paths = {urlsplit(r['url']).path.split('/episodes/')[1].split('/')[1] for r in episodes
                         if '/episodes/' in urlsplit(r['url']).path and len(urlsplit(r['url']).path.split('/episodes/')[1].split('/')) > 1}
            frames = [r for r in episodes if urlsplit(r['url']).path.endswith('/frames')]
            poses = [r for r in episodes if urlsplit(r['url']).path.endswith('/robot-state')]
            assets = [r for r in episodes if '/model/assets/' in urlsplit(r['url']).path]
            check('every episode request is a GET on the three exact history routes',
                  all(r['method'] == 'GET' for r in episodes) and len(frames) >= (6 if a.mode == 'real' else 8) and len(poses) >= 1 and len(assets) >= 1,
                  [r for r in episodes if r['method'] != 'GET'][:3])
            check('the pane only ever opens the declared episode sub-paths (no wildcard proxy widening)',
                  sub_paths <= {'frames', 'robot-state', 'model', 'assets', 'streams', 'record'}, sorted(sub_paths))
            check('every model mesh byte came from the history asset route, never the live scene asset route',
                  not [r for r in report['requests'][report['history_from']:] if '/mobilecar/scene/assets/' in urlsplit(r['url']).path] and len(assets) >= (2 if a.mode == 'real' else 1),
                  sorted({urlsplit(r['url']).path for r in report['requests'][report['history_from']:] if 'assets' in r['url']})[:4])
            check('no control, session, reset or recording request is issued',
                  not [r for r in report['requests'] if any(token in urlsplit(r['url']).path for token in ('/api/v1/commands', '/api/v1/reset', '/api/v1/runs', '/recording/', '/api/v1/sessions'))],
                  [r['url'] for r in report['requests']][:4])
            check('every request the page issues is a GET',
                  all(r['method'] == 'GET' for r in report['requests']), [r for r in report['requests'] if r['method'] != 'GET'][:3])
            canvas_state = await page.evaluate("()=>({canvas:document.querySelectorAll('canvas').length,inPane:document.querySelectorAll('[data-model-canvas-host] canvas').length,target:document.querySelectorAll('[data-target-readout],[data-ghost-toggle],[data-workbench-tool]').length})")
            check('the only canvas on the page is the fixed model reference, with no live control surface',
                  canvas_state == {'canvas': 1, 'inPane': 1, 'target': 0}, canvas_state)
            check('no uncaught browser errors', not report['errors'], report['errors'][:3])
            report['frame_requests'] = len(frames); report['pose_requests'] = len(poses); report['asset_requests'] = len(assets)
            report['status'] = 'passed'
        except Exception as exc:
            report['exception'] = str(exc); report['traceback'] = traceback.format_exc()
            await page.screenshot(path=str(a.output / 'failure.png'), full_page=True)
        finally:
            (a.output / 'browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            await browser.close()

asyncio.run(main())
print(json.dumps({'status': report['status'], 'mode': a.mode, 'checks': len(report['checks']), 'frame_requests': report.get('frame_requests'),
                  'pose_requests': report.get('pose_requests'), 'asset_requests': report.get('asset_requests'), 'error': report.get('exception')}, ensure_ascii=False))
raise SystemExit(report['status'] != 'passed')
