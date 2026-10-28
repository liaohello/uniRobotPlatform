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
# A second episode of the SAME run (2026-10-28 18970): the static bundle identity matches the driving
# archive, but its own per-part contract is unusable — arm blocked, base/TCP/gripper conditional, no
# single state record. Measured through GET only; it is the real-data counterpart of the synthetic
# "no readiness / conditional stays off" cases.
p.add_argument('--partial-run', default='run_0104613ff7364ae78cf2f3946bd45f7b')
p.add_argument('--partial-episode', default='episode_9285f8146bf44f99a3a4e796c7e20359')
a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
report = {'scope': f'{a.mode} frame-link-2 + history-pose-1 acceptance against {a.url}', 'mode': a.mode,
          'checks': [], 'errors': [], 'requests': [], 'real': {}, 'synthetic': {}, 'status': 'failed'}
SOURCE_ID = 'mobilecar-server-history-20261017'
FRAME_SCHEMA = 'unirobot-mobilecar-frame-link-2'
POSE_SCHEMA = 'unirobot-mobilecar-history-pose-1'
GEOMETRY_SCHEMA = 'unirobot-mobilecar-geometry-2'
# The identity fields the assembled tree is bound to: the record and the bundle agree on all four, and
# a synthetic case can break exactly one of them to prove the binding is what stops the assembly.
BUNDLE_ID = '2' * 64
CONTENT_ID = 'c' * 64
MODEL_INPUTS_ID = 'i' * 64
COMPILED_ID = 's' * 64
WORLD_LINK_NAMES = ['world_static', 'target_cube']
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


async def wait_model_quiet(page, attempts=15):
    """Sample the surface until the last mesh has landed and the camera stopped moving: the deferred
    fit-to-extents is allowed once, at assembly, and must not be confused with a frame step."""
    previous = None
    for _ in range(attempts):
        await page.locator('[data-model-inspect]').click()
        state = json.loads(await attr(page, '[data-model-inspected]', 'data-model-inspected'))
        current = (json.dumps(state['camera'], sort_keys=True), state['pendingLoads'], state['assetFailures'])
        if state['pendingLoads'] == 0 and state['assetFailures'] == [] and current == previous:
            return state
        previous = current
        await page.wait_for_timeout(400)
    raise AssertionError(f'the reference view never settled on loads {previous[1]} / failures {previous[2]}')


async def pick_model_link(page):
    """Click-to-select on the reference surface: sweep a few points until a link is picked, and report
    what the surface says afterwards. A pick is read-only — it must list link/geom and never create a
    Target/Ghost/tool affordance or a write request."""
    box = await page.locator('[data-model-canvas-host]').bounding_box()
    before = len(report['requests'])
    picked = 'none'
    for fy in (0.45, 0.55, 0.62, 0.7, 0.76):
        for fx in (0.4, 0.45, 0.5, 0.55, 0.6):
            await page.mouse.click(box['x'] + box['width'] * fx, box['y'] + box['height'] * fy)
            await page.wait_for_timeout(90)
            picked = await attr(page, '[data-model-selection-link]', 'data-model-selection-link')
            if picked != 'none':
                break
        if picked != 'none':
            break
    return {'link': picked, 'geoms': await attr_all(page, '[data-model-geom]', 'data-model-geom'),
            'meshes': await attr_all(page, '[data-model-geom]', 'data-geom-mesh'),
            'selection': await attr(page, '[data-model-selection]', 'data-model-selection'),
            'controls': await count(page, '[data-target-readout],[data-ghost-toggle],[data-workbench-tool]'),
            'new_requests': report['requests'][before:]}


def static_tree_reads(mark):
    """Placement-tree reads in the window since `mark`. The tree is a property of the Episode's content
    identity, so frame steps, view switches and picker clicks must not add a single one."""
    return [urlsplit(r['url']).path for r in report['requests'][mark:] if urlsplit(r['url']).path == '/api/v1/mobilecar/scene']


def frame_reads_of(mark):
    """robot-state reads in the same window and the distinct frames they were asked for: the other side
    of the census, so "one tree read" can not be trivially true because no frame was ever read."""
    urls = [r['url'] for r in report['requests'][mark:] if urlsplit(r['url']).path.endswith('/robot-state')]
    samples = {value for u in urls for value in parse_qs(urlsplit(u).query).get('sample_id', [])}
    return {'poses': len(urls), 'samples': sorted(samples)}


def history_asset_reads(mark):
    return [urlsplit(r['url']).path for r in report['requests'][mark:] if '/model/assets/' in urlsplit(r['url']).path]


async def open_episode_tree_reads(page, run_id, episode_id, expect='frames'):
    """Open an Episode and report the placement-tree reads the switch caused: only an Episode identity
    change is allowed to re-read the static tree, and then exactly once."""
    mark = len(report['requests'])
    await open_episode(page, run_id, episode_id, expect)
    return static_tree_reads(mark)


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
        modelStatus:g('[data-model-pane]','data-model-status'),modelRequested:g('[data-model-pane]','data-model-requested-sample'),
        modelDisplayed:g('[data-model-pane]','data-model-displayed-sample'),modelAttribution:g('[data-model-pane]','data-model-attribution'),
        modelEpisode:g('[data-model-pane]','data-model-episode'),modelFramePose:g('[data-model-pane]','data-frame-pose-verified'),
        modelBase:g('[data-model-pane]','data-model-base-applied'),modelTcp:g('[data-model-pane]','data-model-tcp-applied'),
        modelJoints:g('[data-model-pane]','data-model-joints-applied'),modelRootHeight:g('[data-model-pane]','data-model-root-height'),
        modelCompiledRoot:g('[data-model-pane]','data-model-compiled-root-height'),
        modelTreeReads:g('[data-model-pane]','data-model-tree-reads'),
        modelTreeReadEpisode:g('[data-model-pane]','data-model-tree-read-episode'),
        modelTreeSource:g('[data-model-pane]','data-model-tree-source'),
        modelDrive:g('[data-model-drive-summary]','data-model-drive-summary'),modelStage:g('[data-model-stage]','data-model-stage'),
        modelWithheld:g('[data-model-withheld-count]','data-model-withheld-count'),mappingStatuses:q('[data-mapping-row]','data-mapping-status'),
        valueNames:q('[data-model-value]','data-model-value'),valueKinds:q('[data-model-value]','data-value-kind'),
        valueModels:q('[data-model-value]','data-value-model'),valueDisplays:q('[data-model-value]','data-value-display'),
        valueSources:q('[data-model-value]','data-value-source'),valuesTable:g('[data-model-values-table]','data-model-values-table'),
        valueNoneRow:document.querySelectorAll('[data-model-value-none]').length,
        motionVisited:g('[data-model-pane]','data-motion-visited-frames'),
        motionKey:g('[data-model-pane]','data-motion-visited-key'),
        motionNames:q('[data-motion-row]','data-motion-row'),
        motionDistinct:q('[data-motion-row]','data-motion-distinct'),
        motionVisits:q('[data-motion-row]','data-motion-visits'),
        motionSamples:q('[data-motion-row]','data-motion-samples'),
        motionNoneRow:document.querySelectorAll('[data-motion-none]').length,
        partCaps:q('[data-part-row]','data-part-row'),partStatuses:q('[data-part-row]','data-part-status'),partDrivable:q('[data-part-row]','data-part-drivable'),
        fkVerdicts:q('[data-fk-row]','data-fk-verdict'),fkCheck:g('[data-fk-check]','data-fk-check'),
        treeFields:q('[data-tree-binding-row]','data-tree-binding-row'),treeEqual:q('[data-tree-binding-row]','data-tree-binding-equal'),
        simKeys:g('[data-sim-quantity-keys]','data-sim-quantity-keys'),
        corrections:[...document.querySelectorAll('[data-frame-correction]')].map(e=>e.innerText),
        displayedSamples:q('[data-frame-displayed-sample]','data-frame-displayed-sample'),
        mappingTargets:q('[data-mapping-row]','data-mapping-row'),
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
    episode_mark = len(report['requests'])
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
    check('the M1.5e time-source split and its recorded corrections are shown as the reader states them',
          'state_sim_time_minus_frame_capture_sim_time' in view['simKeys']
          and 'state_event_envelope_sim_time_minus_frame_capture_sim_time' in view['simKeys']
          and '负载量与信封量各一条，缺就是缺，不互相回填' in view['simKeys']
          and len(view['corrections']) == len(direct['version_migration']['corrections']) >= 1
          and any('PAYLOAD' in line for line in view['corrections'])
          and set(direct['frames'][0]['times']['sim_time_quantity_keys']) == set(SIM_KEYS), (view['simKeys'], view['corrections']))
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
    # One placement-tree read for this Episode's content identity; everything after must be pose-only traffic.
    assembly_reads = len(static_tree_reads(episode_mark))
    frame_mark = len(report['requests'])
    pose = await read_direct(page, f'/api/v1/episodes/{a.complete_episode}/robot-state', {'run_id': a.complete_run, 'sample_id': first['sample_id']})
    model = await page_attrs(page)
    pose_reads = [r for r in report['requests'] if urlsplit(r['url']).path.endswith('/robot-state')]
    check('the reference view reads robot-state for the selected frame and checks its identity back',
          pose['schema_version'] == POSE_SCHEMA and pose['frame']['sample_id'] == first['sample_id']
          and pose['frame']['linkage_schema'] == FRAME_SCHEMA and model['modelStatus'] == 'ready'
          and model['modelDisplayed'] == first['sample_id'] and model['modelRequested'] == first['sample_id']
          and model['modelAttribution'] == 'matched'
          and all(first['sample_id'] in r['url'] for r in pose_reads[-1:]), (model['modelAttribution'], pose_reads[-1:]))
    check('the ten mapping rows carry the reader’s own statuses and four of them are verified',
          len(model['mappingStatuses']) == 10 and model['mappingStatuses'].count('verified') == 4
          and model['mappingStatuses'].count('unverified') == 1 and model['mappingStatuses'].count('missing') == 3
          and model['mappingStatuses'].count('not_required_for_pose') == 2
          and pose['pose_readiness']['mapped_targets_partially_or_fully_verified'] in model['modelText'], model['mappingStatuses'])
    check('the readiness gate drives the arm, the chassis and the TCP point on the real record',
          model['partCaps'] == PART_CAPS and model['partStatuses'] == ['ready', 'ready_with_caveats', 'ready_with_caveats', 'conditional', 'ready_with_caveats', 'blocked', 'blocked', 'blocked', 'not_required']
          and model['modelJoints'] == '5' and model['modelBase'] == 'true' and model['modelTcp'] == 'true'
          and int(model['modelWithheld']) == 5 and model['modelFramePose'] == 'true'
          and '本帧历史姿态（按部件门控）' in model['modelText'], (model['partStatuses'], model['modelDrive']))
    await page.locator('[data-model-inspect]').click()
    posed = json.loads(await attr(page, '[data-model-inspected]', 'data-model-inspected'))
    recorded = pose['state']['recorded_payload']
    check('the driven joint values are the recorded model radians verbatim, with no user-zero step',
          posed['selectedJointDriven'] == {name: value for name, value in zip(pose['model_resource']['arm_hinge_joints'], recorded['arm_model_qpos_rad'])}
          and posed['selectedJointDriven']['joint4'] == recorded['arm_model_qpos_rad'][3]
          and abs(posed['selectedJointDriven']['joint4'] - (recorded['arm_model_qpos_rad'][3] - (-1.5707963267948966))) > 1.0
          and pose['model_vs_user_angles']['conversion_is_required_for_drawing'] is False, posed['selectedJointDriven'])
    readout_names = pose['model_resource']['arm_hinge_joints'] + ['base_link', pose['model_resource']['tcp_site']]
    report['real']['driven_value_readout'] = {'table': model['valuesTable'], 'names': model['valueNames'],
                                              'models': model['valueModels'], 'displays': model['valueDisplays']}
    check('the pane prints one row per driven value, named by the frame it belongs to and taken verbatim from the record',
          model['valuesTable'] == pose['frame']['sample_id'] and model['valueNames'] == readout_names
          and model['valueKinds'] == ['arm'] * 5 + ['base', 'tcp'] and model['valueNoneRow'] == 0
          and [float(value) for value in model['valueModels'][:5]] == recorded['arm_model_qpos_rad']
          and json.loads(model['valueModels'][5].split(' / ')[0]) == recorded['base_position_world_sim_m']
          and json.loads(model['valueModels'][6]) == recorded['tcp_position_world_m']
          and model['valueSources'][5].startswith('base_position_world_sim_m')
          and 'local_position_m' in model['valueDisplays'][5] and '未再叠加' in model['valueDisplays'][5]
          and '不合成朝向' in model['valueDisplays'][6], (model['valueNames'], model['valueModels']))
    check('the user angle shown beside each joint is the reader’s formula, and it is not what was drawn',
          all('未参与绘制' in cell for cell in model['valueDisplays'][:5])
          and abs(float(model['valueDisplays'][3].split('（')[0]) - recorded['arm_model_qpos_rad'][3]) > 1.0
          and abs(float(model['valueDisplays'][3].split('（')[0]) - (recorded['arm_model_qpos_rad'][3] - (-1.5707963267948966))) < 1e-12
          and float(model['valueDisplays'][0].split('（')[0]) == float(model['valueModels'][0])
          and all(f'arm_model_qpos_rad[{index}]' == source.split(' ·')[0]
                  for index, source in enumerate(model['valueSources'][:5])), (model['valueDisplays'][:5], model['valueSources'][:5]))
    check('the chassis is placed at the recorded world pose and the compiled root offset is not re-added',
          abs(float(model['modelRootHeight']) - recorded['base_position_world_sim_m'][2]) < 1e-12
          and abs(float(model['modelRootHeight']) - (recorded['base_position_world_sim_m'][2] + pose['model_resource']['root_joint']['local_position_m'][2])) > 0.05
          and abs(float(model['modelCompiledRoot']) - float(model['modelRootHeight'])) > 1e-9, (model['modelRootHeight'], model['modelCompiledRoot']))
    fk = pose['tcp_kinematic_cross_check']
    check('the TCP point is the recorded position and the reader’s same-frame FK error is shown with its tolerance owner',
          fk['verdict'] == 'consistent' and fk['abs_error_m'] < fk['consistency_tolerance_m']
          and f"abs_error_m={fk['abs_error_m']}" in model['fkCheck'] and f"容差={fk['consistency_tolerance_m']}" in model['fkCheck']
          and 'not a calibration limit' in model['fkCheck']
          and json.loads(model['fkCheck'].split('记录 TCP=')[1].split(' ·')[0]) == recorded['tcp_position_world_m']
          and 'inconsistent' in model['fkVerdicts'], (model['fkCheck'][:200], fk['abs_error_m']))
    check('the withheld parts keep their own limits and never claim a whole-robot rebuild',
          'robot_state_can_be_rebuilt_without_assumptions=false' in model['modelText']
          and 'whole_robot_pose_rebuildable=false' in model['modelText']
          and 'nothing in the record or bundle attests them' in model['modelText']
          and 'no historical position is recorded for dynamic scene objects' in model['modelText']
          and 'no TCP orientation is recorded and the reference declares none' in model['modelText']
          and 'writer_identified=false' in model['modelText'] and 'uncalibrated' in model['modelText']
          and '不伪造动态物体位姿' in model['modelText'] and 'no live geometry or Actual substitution' in model['modelText']
          # The reader separates "kinematics agree" from "hardware is calibrated": the second is a limit, not a result.
          and 'no calibration claim' in model['modelText']
          and fk['verdict'] == 'consistent' and 'consistent' in model['modelText'], model['modelText'][-400:])
    check('the assembled tree is bound to the record by content identity, not only by mesh digests',
          set(model['treeEqual']) == {'true'} and {'bundle_sha256', 'content_identity_sha256', 'model_inputs_sha256', 'compiled_scene_sha256',
                                                  'link_count', 'arm_hinge_joints'} <= set(model['treeFields'])
          and model['comparisonEqual'] == ['true'] * 4
          and model['assetEqual'] == ['true'] * len(pose['model_resource']['assets']), model['treeFields'])
    # What the placement route says about itself is shown as stated: the bundle content is identity-bound to
    # the record, but the route is still the live-native one, because no Episode-scoped manifest exists yet.
    scene_envelope = await read_direct(page, '/api/v1/mobilecar/scene')
    report['real']['tree_source'] = {'data_source': scene_envelope.get('data_source'), 'world_pose_semantics': scene_envelope.get('world_pose_semantics'),
                                     'runtime_identity': scene_envelope.get('runtime_identity'), 'shown_on_pane': model['modelTreeSource']}
    check('the pane states the placement route in that route’s own words instead of claiming an Episode-scoped manifest',
          model['modelTreeSource'] == scene_envelope['data_source']
          and f"data_source={scene_envelope['data_source']}" in model['modelStage']
          and 'Episode 作用域的静态 manifest 尚未发布' in model['modelStage']
          and scene_envelope['world_pose_semantics'] == 'compiled_initial_layout_not_live_object_state'
          and (scene_envelope.get('runtime_identity') or {}).get('episode_id') != a.complete_episode, report['real']['tree_source'])

    # ---- real multi-frame pose linkage: the picture must follow the record, frame by frame ----
    distinct, seen_values = [], set()
    for candidate in direct['frames']:
        state = (candidate.get('state') or {}).get('recorded_state') or {}
        signature = (tuple(round(value, 6) for value in state.get('arm_model_qpos_rad') or []),
                     tuple(round(value, 6) for value in state.get('base_position_world_sim_m') or []))
        if signature in seen_values:
            continue
        seen_values.add(signature)
        distinct.append(candidate)
    check('the page really carries several frames with different chassis and joint values',
          len(distinct) >= 3, [len(distinct), len(direct['frames'])])
    observations = []
    for position, candidate in enumerate(distinct[:3]):
        await page.locator(f'[data-frame-pick="{candidate["sample_id"]}"]').click()
        await wait_model(page, 'ready')
        await page.wait_for_function(f"()=>(document.querySelector('[data-model-pane]')?.getAttribute('data-model-displayed-sample') ?? '')==='{candidate['sample_id']}'", timeout=60000)
        await page.locator('[data-model-inspect]').click()
        state = (candidate.get('state') or {}).get('recorded_state') or {}
        shown = json.loads(await attr(page, '[data-model-inspected]', 'data-model-inspected'))
        attrs = await page_attrs(page)
        # That frame's own answer from the reader: the recorded site, the reader's same-frame FK of it, and
        # the tolerance it declares for that agreement, all compared against what actually rendered.
        frame_pose = await read_direct(page, f'/api/v1/episodes/{a.complete_episode}/robot-state',
                                       {'run_id': a.complete_run, 'sample_id': candidate['sample_id']})
        fk_of_frame = frame_pose['tcp_kinematic_cross_check']
        payload_of_frame = frame_pose['state']['recorded_payload']
        observations.append({'sample': candidate['sample_id'], 'camera': shown['camera'], 'links': shown['links'],
                             'joints': shown['selectedJointDriven'], 'base': shown['attribution']['rootHeightWorldSimM'],
                             'baseVector': tuple(state['base_position_world_sim_m']), 'armVector': tuple(state['arm_model_qpos_rad']),
                             'tip': shown['worldPositions'].get('gripper_link') or shown['worldPositions'].get('link5') or [],
                             'baseSim': shown['worldPositionsSim'].get('base_link'), 'tcpSim': shown['tcpPositionSim'],
                             'tipSim': shown['worldPositionsSim'].get('gripper_link') or shown['worldPositionsSim'].get('link5'),
                             'recordedTcp': fk_of_frame['recorded_tcp_position_m'], 'computedTcp': fk_of_frame['computed_tcp_position_m'],
                             'fkAbs': fk_of_frame['abs_error_m'], 'fkTolerance': fk_of_frame['consistency_tolerance_m'],
                             'fkToleranceAuthority': fk_of_frame['tolerance_authority'], 'attrs': attrs,
                             'readout': attrs['valueModels'][:5], 'readoutBase': attrs['valueModels'][5], 'readoutTcp': attrs['valueModels'][6]})
        check(f'frame {position + 1}’s own value rows carry that frame’s numbers, not the previous frame’s',
              attrs['valuesTable'] == candidate['sample_id'] and attrs['valueNames'] == readout_names
              and [float(value) for value in attrs['valueModels'][:5]] == payload_of_frame['arm_model_qpos_rad']
              and json.loads(attrs['valueModels'][5].split(' / ')[0]) == payload_of_frame['base_position_world_sim_m']
              and json.loads(attrs['valueModels'][6]) == payload_of_frame['tcp_position_world_m'],
              (attrs['valuesTable'], attrs['valueModels'][:5]))
        check(f'frame {position + 1} binds the pose, the numbers and the image to its own sample',
              shown['attribution']['displayedSample'] == candidate['sample_id']
              and shown['selectedJointDriven'] == {name: value for name, value in zip(pose['model_resource']['arm_hinge_joints'], state['arm_model_qpos_rad'])}
              and abs(float(attrs['modelRootHeight']) - state['base_position_world_sim_m'][2]) < 1e-12
              and attrs['currentSample'] == candidate['sample_id'] and attrs['assetUri'] == candidate['media']['items'][0]['uri']
              and candidate['sample_id'] in attrs['displayedSamples'][0], (shown['attribution'], attrs['modelRootHeight']))
        await page.screenshot(path=str(a.output / f'pose-{candidate["sample_id"][:12]}.png'), full_page=False)
    # Movement is judged from what the record actually varies: these frames differ in the chassis by
    # microns, so the claim is "distinct recorded values render as distinct", not "moved by > X mm".
    arm_variants = {item['armVector'] for item in observations}
    base_variants = {item['baseVector'] for item in observations}
    moved = [(x, y) for x in range(len(observations)) for y in range(x + 1, len(observations))
             if observations[x]['armVector'] != observations[y]['armVector']]
    tip_gap = lambda p, q: sum((a - b) ** 2 for a, b in zip(p, q)) ** 0.5
    check('the rendered picture follows the record: distinct chassis values render at distinct heights and a distinct arm value moves the tip',
          len(base_variants) == len(observations) and len({item['base'] for item in observations}) == len(observations)
          and all(observations[0]['base'] != item['base'] for item in observations[1:])
          and all(tip_gap(observations[x]['tip'], observations[y]['tip']) > 1e-12 for x, y in moved)
          and all(item['links'] == observations[0]['links'] for item in observations)
          and all(len(item['tip']) == 3 for item in observations),
          {'bases': [item['base'] for item in observations], 'arm_variants': len(arm_variants), 'moved_pairs': len(moved)})
    report['real']['driven_value_readout_per_frame'] = [{'sample': item['sample'], 'arm': item['readout'], 'base': item['readoutBase'], 'tcp': item['readoutTcp']} for item in observations]
    check('the printed rows move exactly where the record moves: distinct recorded values give distinct printed values',
          len({tuple(item['readout']) for item in observations}) == len(arm_variants)
          and len({item['readoutBase'] for item in observations}) == len(base_variants)
          and len({item['readoutTcp'] for item in observations}) == len({tuple(item['recordedTcp']) for item in observations})
          and all(item['attrs']['valueNoneRow'] == 0 for item in observations), report['real']['driven_value_readout_per_frame'])
    last_attrs = observations[-1]['attrs']
    visited_over_time = [int(item['attrs']['motionVisited']) for item in observations]
    episode_samples = {c['sample_id'] for c in direct['frames']} | {item['sample'] for item in observations}
    contributing = {s for cell in last_attrs['motionSamples'] for s in cell.split(',') if s}
    arm_distinct_printed = [int(value) for value in last_attrs['motionDistinct'][:5]]
    report['real']['motion_coverage'] = {'visited_frames': last_attrs['motionVisited'], 'key': last_attrs['motionKey'],
                                         'names': last_attrs['motionNames'], 'distinct': last_attrs['motionDistinct'],
                                         'visits': last_attrs['motionVisits'], 'contributing_samples': sorted(contributing),
                                         'visited_counts_during_loop': visited_over_time,
                                         'arm_variants_in_loop_frames': len(arm_variants)}
    check('运动覆盖只统计本会话真归属过的帧：帧数逐次增长、来源帧属于本 Episode、记录里变化的轴如实显出多个值',
          last_attrs['motionNames'] == readout_names and last_attrs['motionNoneRow'] == 0
          and visited_over_time == sorted(visited_over_time) and visited_over_time[-1] > visited_over_time[0]
          and visited_over_time[-1] >= len(observations)
          and contributing <= episode_samples and last_attrs['motionKey'].startswith(a.complete_episode)
          and max(arm_distinct_printed) >= len(arm_variants)
          and len(set(last_attrs['motionVisits'][:5])) == 1
          and int(last_attrs['motionVisits'][0]) <= visited_over_time[-1], report['real']['motion_coverage'])
    check('stepping frames never resets the camera or rebuilds the tree',
          all(abs(item['camera']['distance'] - observations[0]['camera']['distance']) < 1e-6
              and abs(item['camera']['azimuthDeg'] - observations[0]['camera']['azimuthDeg']) < 1e-6
              and abs(item['camera']['polarDeg'] - observations[0]['camera']['polarDeg']) < 1e-6 for item in observations)
          and all(item['links'] == observations[0]['links'] for item in observations), [item['camera'] for item in observations])
    # What actually rendered, converted back into the record's own axes, must land where the record says —
    # this is the numeric half of the acceptance, not a re-reading of the DOM attribute.
    base_residuals = [max(abs(a - b) for a, b in zip(item['baseSim'], item['baseVector'])) for item in observations]
    tcp_vs_record = [tip_gap(item['tcpSim'], item['recordedTcp']) for item in observations]
    tcp_vs_backend_fk = [tip_gap(item['tcpSim'], item['computedTcp']) for item in observations]
    site_offsets = [tip_gap(item['tcpSim'], item['tipSim']) for item in observations]
    report['real']['rendered_geometry_vs_record'] = {
        'frames': [item['sample'] for item in observations],
        'rendered_base_vs_record_max_component_error_m': base_residuals,
        'rendered_tcp_vs_recorded_m': tcp_vs_record, 'rendered_tcp_vs_backend_fk_m': tcp_vs_backend_fk,
        'reader_abs_error_m_per_frame': [item['fkAbs'] for item in observations],
        'tolerance_m': observations[0]['fkTolerance'], 'tolerance_authority': observations[0]['fkToleranceAuthority'],
        'rendered_tcp_to_gripper_link_m': site_offsets}
    check('the rendered tree lands on the record’s world_sim vectors and re-derives the backend’s same-frame FK agreement',
          all(v < 1e-9 for v in base_residuals) and all(v < 1e-9 for v in tcp_vs_record)
          and all(v <= observations[0]['fkTolerance'] for v in tcp_vs_backend_fk)
          and all(abs(ours - theirs) < 1e-12 for ours, theirs in zip(tcp_vs_backend_fk, [item['fkAbs'] for item in observations]))
          and all(len(item['baseSim']) == 3 and len(item['tcpSim']) == 3 and len(item['tipSim']) == 3 for item in observations)
          # The site rides on the same rigid chain as the gripper origin, so that distance may not change
          # between frames: it is the one arm-geometry invariant both the record and the render can agree on.
          and max(site_offsets) - min(site_offsets) < 1e-12, report['real']['rendered_geometry_vs_record'])
    report['real']['pose_linkage'] = {'frames': [item['sample'] for item in observations],
                                      'root_heights': [item['base'] for item in observations],
                                      'recorded_base_vectors': [list(item['baseVector']) for item in observations],
                                      'joint_sets': [item['joints'] for item in observations],
                                      'arm_value_variants': len(arm_variants), 'chassis_variants': len(base_variants),
                                      'arm_moved_pairs': len(moved),
                                      'tip_positions': [item['tip'] for item in observations],
                                      'fk_abs_error_m': fk['abs_error_m'], 'fk_tolerance_m': fk['consistency_tolerance_m'],
                                      'fk_tolerance_authority': fk['tolerance_authority'],
                                      'camera_kept': observations[0]['camera']}
    # The two things a person uses the surface for besides stepping: knowing which way the axes go, and
    # clicking a part to inspect it. Both must hold without producing any control.
    axes = await attr(page, '[data-model-axis-convention]', 'data-model-axis-convention')
    check('the reference surface states the world_sim axis convention and that the TCP has no orientation frame',
          'world_sim' in axes and '+X=车头' in axes and 'joint_axis' in axes and '不画朝向帧' in axes
          and 'mujocoRoot' in axes, axes[:180])
    picked = await pick_model_link(page)
    after_pick = await page_attrs(page)
    report['real']['picking'] = picked
    check('click-to-select on the real reference model lists link and geom, and stays read-only',
          picked['link'] not in ('none', None) and len(picked['geoms']) >= 1 and picked['controls'] == 0
          and all(row['method'] == 'GET' for row in picked['new_requests'])
          and after_pick['modelDisplayed'] == after_pick['modelRequested'] and after_pick['modelJoints'] == '5'
          and after_pick['modelRootHeight'] != 'null', picked)
    await page.screenshot(path=str(a.output / 'pose-inspector-pick.png'), full_page=False)
    # The three standard views on the real record: only the camera may move, the posed tree stays put.
    views = {}
    for name in ('side', 'front', 'top'):
        await page.locator(f'[data-model-view="{name}"]').click()
        await page.locator('[data-model-inspect]').click()
        views[name] = json.loads(await attr(page, '[data-model-inspected]', 'data-model-inspected'))
    report['real']['standard_views'] = {name: item['camera'] for name, item in views.items()}
    check('front/side/top on the real model move only the camera and keep the posed frame and tree',
          abs(views['side']['camera']['azimuthDeg'] - views['front']['camera']['azimuthDeg']) > 20
          and views['top']['camera']['polarDeg'] < 20
          and all(abs(item['camera']['distance'] - views['front']['camera']['distance']) < 1e-6 for item in views.values())
          and all(item['attribution']['displayedSample'] == observations[-1]['sample'] for item in views.values())
          and all(item['links'] == views['front']['links'] and item['worldPositions'] == views['front']['worldPositions'] for item in views.values())
          and all(item['pendingLoads'] == 0 and item['assetFailures'] == [] for item in views.values()),
          {name: item['camera'] for name, item in views.items()})
    await page.locator('[data-frame-pick]').first.click()
    await wait_model(page, 'ready')
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
          and moved_last['modelDisplayed'] == last['sample_id'], (moved_last['index'], moved_last['modelDisplayed']))
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

    # The census of the whole stepping session: the tree belongs to the Episode's content identity, so
    # all these frame changes must arrive as pose traffic only — no second placement read.
    stepping = await page_attrs(page)
    census = {'tree_reads_since_stepping': static_tree_reads(frame_mark),
              'tree_reads_for_this_episode': assembly_reads,
              'pane_tree_reads': stepping['modelTreeReads'], 'pane_tree_read_episode': stepping['modelTreeReadEpisode'],
              'frames': frame_reads_of(frame_mark),
              'history_asset_bytes': len(history_asset_reads(frame_mark)),
              'live_scene_asset_bytes': len([r for r in report['requests'][frame_mark:] if '/mobilecar/scene/assets/' in urlsplit(r['url']).path])}
    report['real']['static_tree_census'] = census
    check('the fixed tree is read once for the Episode identity and never again per frame',
          census['tree_reads_since_stepping'] == [] and assembly_reads == 1
          and stepping['modelTreeReads'] == '1' and stepping['modelTreeReadEpisode'] == a.complete_episode
          and len(census['frames']['samples']) >= 5 and census['frames']['poses'] >= 5
          and census['history_asset_bytes'] >= 1 and census['live_scene_asset_bytes'] == 0, census)

    # The FAILED / INCOMPLETE record.
    failed = await read_direct(page, f'/api/v1/episodes/{a.failed_episode}/frames', {'run_id': a.failed_run, 'limit': 5, 'offset': 0})
    switch_mark = len(report['requests'])
    await open_episode(page, a.failed_run, a.failed_episode)
    await wait_asset_settled(page)
    await wait_model(page, 'ready')
    switched = await page_attrs(page)
    check('a different Episode re-reads the placement tree exactly once, not once per frame of it',
          static_tree_reads(switch_mark) == ['/api/v1/mobilecar/scene']
          and switched['modelEpisode'] == a.failed_episode
          and switched['modelTreeReads'] == '1' and switched['modelTreeReadEpisode'] == a.failed_episode,
          {'reads': static_tree_reads(switch_mark), 'pane': [switched['modelTreeReads'], switched['modelTreeReadEpisode']],
           'poses': frame_reads_of(switch_mark)['poses']})
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

    # ---- a second real archive of the same run: identical static bundle, unusable per-part contract ----
    partial = await read_direct(page, f'/api/v1/episodes/{a.partial_episode}/frames', {'run_id': a.partial_run, 'limit': 3, 'offset': 0})
    partial_first = partial['frames'][0]['sample_id']
    partial_pose = await read_direct(page, f'/api/v1/episodes/{a.partial_episode}/robot-state', {'run_id': a.partial_run, 'sample_id': partial_first})
    partial_mark = len(report['requests'])
    await open_episode(page, a.partial_run, a.partial_episode)
    await wait_asset_settled(page)
    await wait_model(page, 'ready')
    pmodel = await page_attrs(page)
    partial_parts = [(row['capability'], row['status']) for row in (partial_pose.get('part_readiness') or [])]
    report['real']['partial_archive'] = {
        'episode': a.partial_episode, 'run': a.partial_run, 'frames_read': len(partial['frames']), 'sample': partial_first,
        'linkage_status': partial_pose['frame']['linkage_status'],
        'recorded_payload': partial_pose['state']['recorded_payload'],
        'single_state_selected': partial_pose['state'].get('single_state_selected'),
        'mapping': [(row['target'], row['status']) for row in partial_pose['mapping']],
        'parts': partial_parts,
        'fk_verdict': (partial_pose.get('tcp_kinematic_cross_check') or {}).get('verdict'),
        'bundle_sha256': (partial_pose.get('model_resource') or {}).get('bundle_sha256'),
        'content_identity_sha256': (partial_pose.get('model_resource') or {}).get('content_identity_sha256'),
        'tree_reads_on_switch': static_tree_reads(partial_mark), 'pane_tree_reads': pmodel['modelTreeReads'],
        'driven_joints': pmodel['modelJoints'], 'base_applied': pmodel['modelBase'], 'tcp_applied': pmodel['modelTcp'],
        'withheld': int(pmodel['modelWithheld']), 'value_rows': pmodel['valueNames'], 'motion_rows': pmodel['motionNames'],
        'tree_binding_equal': pmodel['treeEqual'],
    }
    check('真实第二档：同一条 run 的另一 Episode 按自己的分部契约判定——固定模型装配成立，但一个记录部件都不驱动',
          pmodel['modelEpisode'] == a.partial_episode and pmodel['modelStatus'] == 'ready'
          and pmodel['modelJoints'] == '0' and pmodel['modelBase'] == 'false' and pmodel['modelTcp'] == 'false'
          and pmodel['modelFramePose'] == 'false' and pmodel['valueNames'] == [] and pmodel['valueNoneRow'] == 1
          and pmodel['motionNames'] == [] and pmodel['motionNoneRow'] == 1
          and pmodel['partStatuses'] == [status for _, status in partial_parts]
          and int(pmodel['modelWithheld']) == len(partial_parts) - 1
          and len(pmodel['partCaps']) == len(partial_parts) and pmodel['partDrivable'].count('true') == 1
          and '界面没有该能力的处理规则' not in pmodel['modelText'], report['real']['partial_archive'])
    check('真实第二档：conditional/blocked 都留在未驱动一侧，本帧缺状态被原样写成缺而不是 0',
          'conditional' in pmodel['modelText'] and 'blocked' in pmodel['modelText'] and '不驱动' in pmodel['modelText']
          and 'recorded_payload=null' in pmodel['modelText']
          and '本帧没有可归属的历史姿态' in pmodel['modelText']
          and partial_pose['state']['recorded_payload'] is None
          and all(status != 'verified' for _, status in report['real']['partial_archive']['mapping'][:5]),
          (pmodel['modelDrive'], pmodel['modelStage']))
    check('真实第二档：这份档案的静态树同样按内容身份绑定，并按自己的 Episode 身份恰好重读一次',
          static_tree_reads(partial_mark) == ['/api/v1/mobilecar/scene']
          and pmodel['modelTreeReads'] == '1' and pmodel['modelTreeReadEpisode'] == a.partial_episode
          and set(pmodel['treeEqual']) == {'true'} and pmodel['modelCanvas'] == 1
          and pmodel['modelTreeSource'] == 'live_native_http_with_verified_compiled_geometry',
          {'reads': static_tree_reads(partial_mark), 'equal': pmodel['treeEqual'], 'canvas': pmodel['modelCanvas']})
    await page.screenshot(path=str(a.output / 'pose-second-archive-no-drive.png'), full_page=False)


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
    {'key': 'state_event_envelope_sim_time_minus_frame_capture_sim_time', 'source_record': 'events state feedback envelope', 'field': 'sim_time_s',
     'relative_to': 'persisted frame capture_sim_time_s', 'unit': 's', 'clock': 'sim', 'meaning': "the envelope's own simulator time, a separate record from the payload stamp",
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
# M1.5e splits the simulator-time quantity in two and records the labelling fix as `corrections`.
SIM_KEYS = ['state_sim_time_minus_frame_capture_sim_time', 'state_event_envelope_sim_time_minus_frame_capture_sim_time']
CORRECTIONS = ['state_sim_time_minus_frame_capture_sim_time now names only the state feedback PAYLOAD stamp and is absent when the payload carries no numeric sim_time_s; earlier builds of this version silently filled it from the event envelope while still labelling the payload as the source',
               'the envelope’s own simulator time is a separate quantity, state_event_envelope_sim_time_minus_frame_capture_sim_time',
               'no quantity is ever filled from another record: absence is reported as absence']
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
                  'sim_time_quantity_keys': SIM_KEYS,
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
                                  'corrections': CORRECTIONS,
                                  'changed': ['paging.has_more is decided by finding the next qualifying anchor line'],
                                  'removed_fields': {'times.age_of_state_relative_to_frame': 'it merged the state event’s write stamp with the state sample stamps'},
                                  'compatibility_note': 'consumers must read schema_version: frame-link-1 and frame-link-2 pages are not the same contract'},
            'three_d_replay': {'this_slice_does_not_enable_3d_replay': True, 'live_geometry_or_actual_may_be_applied': False,
                               'transforms_are_full_per_body_pose_sequences': False, 'robot_pose_readiness_slice': 'GET /api/v1/episodes/{episode_id}/robot-state'},
            'capability_limits': ['no replay execution', 'no control, RESET, recording or physics stepping']}
    base.update(patch)
    return base


def geometry_payload(content_identity=CONTENT_ID, bundle_sha=BUNDLE_ID, arm_order=None, world_link_count=1):
    """The frozen placement tree the pane assembles from, with the identity fields the record is bound by.

    `arm_order` and `content_identity` let a synthetic case keep every mesh digest identical while the
    tree itself differs — the case mesh digests alone cannot catch."""
    order = arm_order or ['joint1', 'joint2', 'joint3', 'joint4', 'joint5']
    links = [{'name': 'base_link', 'parent_name': None, 'joint_name': 'base_free', 'joint_type': 'free', 'joint_axis': [0.0, 0.0, 1.0],
              'local_transform': {'position_m': [0.0, 0.0, 0.055], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
              'geoms': [{'name': 'base_vis', 'geom_type': 'box', 'size_m': [0.3, 0.2, 0.08],
                         'local_transform': {'position_m': [0.0, 0.0, 0.0], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                         'rgba': [0.3, 0.4, 0.5, 1.0], 'mesh_asset_id': None, 'collision': False, 'group': 0}]}]
    parent = 'base_link'
    for index, joint in enumerate(order):
        links.append({'name': f'{joint}_link', 'parent_name': parent, 'joint_name': joint, 'joint_type': 'hinge', 'joint_axis': [0.0, 0.0, 1.0],
                      'local_transform': {'position_m': [0.0, 0.0, 0.1], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                      'geoms': [{'name': f'{joint}_mesh', 'geom_type': 'mesh', 'size_m': [1.0, 1.0, 1.0],
                                 'local_transform': {'position_m': [0.0, 0.0, 0.0], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                                 'rgba': [0.6, 0.2, 0.2, 1.0], 'mesh_asset_id': 'link1', 'collision': False, 'group': 0}]})
        parent = f'{joint}_link'
    world_links = [{'name': name, 'parent_name': None, 'joint_name': None, 'joint_type': 'fixed', 'joint_axis': [0.0, 0.0, 1.0],
                    'local_transform': {'position_m': [0.4, 0.0, 0.03], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                    'geoms': [{'name': f'{name}_vis', 'geom_type': 'box', 'size_m': [0.03, 0.03, 0.03],
                               'local_transform': {'position_m': [0.0, 0.0, 0.0], 'orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                               'rgba': [0.9, 0.8, 0.1, 1.0], 'mesh_asset_id': None, 'collision': False, 'group': 0}]}
                   for name in WORLD_LINK_NAMES[:world_link_count]]
    return {'schema_version': GEOMETRY_SCHEMA, 'read_only': True, 'data_source': 'live_native_http_with_verified_compiled_geometry',
            'world_pose_semantics': 'compiled_initial_layout_not_live_object_state', 'retrieved_at': '2026-01-01T00:00:00Z',
            'resource_identity': {'contract_version': 'mobilecar-1.0', 'model_id': 'fixture_model', 'model_sha256': 'm' * 64, 'scene_id': 'fixture_scene'},
            'runtime_identity': {'run_id': 'run_fixture', 'backend_generation': 1, 'episode_id': 'episode_fixture'},
            'geometry_binding': {'bundle_sha256': bundle_sha, 'content_identity_sha256': content_identity,
                                 'exported_runtime_identity': {'run_id': 'run_fixture', 'backend_generation': 1, 'episode_id': 'episode_fixture'}},
            'geometry_provenance': {'model_inputs_sha256': MODEL_INPUTS_ID, 'compiled_scene_sha256': COMPILED_ID, 'compiler': 'MuJoCo', 'compiler_version': '3.1.6'},
            'data': {'contract_version': 'mobilecar-1.0', 'model_id': 'fixture_model', 'model_sha256': 'm' * 64, 'scene_id': 'fixture_scene',
                     'camera_ids': ['rgbd'], 'tcp_site': 'grasp_tcp', 'source': 'fixture', 'links': links, 'world_links': world_links,
                     'mesh_assets': [{'asset_id': 'link1', 'uri': f'/api/v1/mobilecar/scene/assets/link1?sha256={STL_SHA}', 'sha256': STL_SHA,
                                      'media_type': 'model/stl', 'coordinate_space': 'mujoco_compiled_mesh', 'units': 'm',
                                      'mesh_preprocessing_applied': True, 'source_sha256': 's' * 64, 'source_mesh_name': 'link1.stl'}]}}


def mapping_fixture(arm_status='partially_verified', mode='legacy'):
    """`legacy` copies the 18969 answer (nothing verified); `m15e` copies the 18970 answer, where the
    arm joints, the base pose and the TCP site are verified with their own stated basis."""
    if mode == 'm15e':
        return [
            {'target': 'arm_joint_positions', 'recorded_field': 'arm_model_qpos_rad', 'recorded_unit': 'rad', 'recorded_length': 5,
             'target_field': 'bundle hinge joints joint1, joint2, joint3, joint4, joint5', 'status': 'verified',
             'verified_basis': ['the recorded TCP position is reproduced from these five values through the frozen tree', 'the source chain addresses the joints by name'],
             'draw_source': 'model radians, applied directly to the hinge joints', 'requires_user_angle_conversion': False,
             'evidence': {'bundle_arm_hinge_joints_in_document_order': ['joint1', 'joint2', 'joint3', 'joint4', 'joint5'], 'positions_are_model_radians_not_user_radians': True},
             'no_default_applied': True, 'gap': 'index 0, 1, 2 and 4 are mapped through the source order chain; a per-index record attestation exists only at index 3'},
            {'target': 'base_position', 'recorded_field': 'base_position_world_sim_m', 'recorded_unit': 'm', 'recorded_length': 3,
             'target_field': 'bundle root link base_link free joint base_free', 'status': 'verified',
             'verified_basis': ['reproducing the recorded TCP position requires the base pose to be the base body’s world pose; the alternative convention is off by exactly the base body offset'],
             'evidence': {'bundle_root_joint': {'name': 'base_link', 'joint_name': 'base_free', 'joint_type': 'free', 'local_position_m': [0.0, 0.0, 0.055]}},
             'no_default_applied': True, 'gap': 'the MuJoCo quantity behind the field is declared in native source that cannot be tied to a single writer build; the kinematic cross-check is reported separately'},
            {'target': 'base_orientation', 'recorded_field': 'base_quaternion_xyzw', 'recorded_unit': 'unit quaternion', 'recorded_length': 4,
             'target_field': 'bundle transforms declare orientation as xyzw', 'status': 'verified',
             'verified_basis': ['the recorded TCP position is reproduced with this quaternion read in xyzw order'], 'evidence': {}, 'no_default_applied': True,
             'gap': 'the component order is labelled consistently and declared in native source, but no record-side attestation ties this archive to that writer'},
            {'target': 'gripper_joints', 'recorded_field': 'gripper_width_m', 'recorded_unit': 'm', 'recorded_length': 1,
             'target_field': 'bundle slide joints left_jaw_joint, right_jaw_joint', 'status': 'unverified', 'evidence': {}, 'no_default_applied': True,
             'gap': 'turning the recorded width into jaw and drive joint values needs the platform\'s declared gripper constants accepted as authoritative; nothing in the record or bundle attests them'},
            {'target': 'tcp_site_position', 'recorded_field': 'tcp_position_world_m', 'recorded_unit': 'm', 'recorded_length': 3,
             'target_field': 'bundle tcp_site grasp_tcp on body guide_rod_link', 'status': 'verified',
             'verified_basis': ['the recomputed site position matches the recorded one within the stated tolerance'], 'evidence': {'the_site_is_not_a_link_in_the_bundle': True},
             'no_default_applied': True, 'gap': 'the site offset lives in the platform reference config, not in the frozen bundle or the record; the cross-check reports how well that attachment reproduces the recorded position'},
            {'target': 'tcp_site_orientation', 'recorded_field': None, 'recorded_unit': None, 'recorded_length': None, 'target_field': None,
             'status': 'missing', 'evidence': {}, 'no_default_applied': True, 'gap': 'no TCP orientation is recorded and the reference declares none'},
            {'target': 'camera_extrinsics', 'recorded_field': None, 'recorded_unit': None, 'recorded_length': None,
             'target_field': 'bundle camera link chain depth_cam_link', 'status': 'missing', 'evidence': {}, 'no_default_applied': True,
             'gap': 'no recorded camera calibration, and the declared mount body is not rigid to the TCP'},
            {'target': 'wheel_joint_velocities', 'recorded_field': 'wheel_velocity_rad_s', 'recorded_unit': 'rad/s', 'recorded_length': 4,
             'target_field': None, 'status': 'not_required_for_pose', 'evidence': {}, 'no_default_applied': True,
             'gap': 'the four wheel values carry no per-wheel identity; a static pose does not need them'},
            {'target': 'base_twist', 'recorded_field': 'base_twist_body_m_s', 'recorded_unit': 'm/s or rad/s', 'recorded_length': 3,
             'target_field': None, 'status': 'not_required_for_pose', 'evidence': {}, 'no_default_applied': True,
             'gap': 'component meaning is not recorded and a static pose does not need it'},
            {'target': 'dynamic_scene_objects', 'recorded_field': None, 'recorded_unit': None, 'recorded_length': None,
             'target_field': 'bundle world links world_static, target_cube', 'status': 'missing', 'evidence': {}, 'no_default_applied': True,
             'gap': 'no historical position is recorded for dynamic scene objects, so they cannot be placed from the record'},
        ]
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


def part_readiness_fixture(tcp_position, arm_count=5):
    """The nine capabilities exactly as the 18970 candidate reports them — rules and gaps verbatim, with
    only the counts scaled to this fixture's six-link tree."""
    part = lambda capability, status, **extra: {'capability': capability, 'status': status, 'requires': ['fixture requirement'],
                                                'pose_input_required': True, 'frontend_rule': f'rule for {capability}', 'gaps': [], **extra}
    return {'part_readiness': [
        part('fixed_model_reference_assembly', 'ready', pose_input_required=False,
             inputs_available={'identity': 'match', 'asset_count': 1, 'link_count': 6,
                               'asset_routes': 'GET /api/v1/episodes/{episode_id}/model/assets/{asset_id}'},
             frontend_rule='the frozen model may be assembled and shown for any frame of this Episode once the identity matches; a whole-robot pose gap never blocks this assembly'),
        part('arm_local_pose', 'ready_with_caveats',
             inputs_available={'recorded_length': arm_count, 'bundle_joints': ['joint1', 'joint2', 'joint3', 'joint4', 'joint5'], 'draw_in_model_radians': True},
             frontend_rule='apply the recorded five values directly to the five arm hinges in model radians; do not convert through user angles to draw, and do not claim an axis is exercised unless the samples actually move it',
             gaps=['the writer is narrowed to the 2026-10-17 release family but not identified', 'per-index record attestation exists only at index 3']),
        part('base_pose_placement', 'ready_with_caveats', inputs_available={'position_length': 3, 'quaternion_length': 4},
             frontend_rule='the base may be placed only with the caveat shown beside it: the field\'s meaning comes from native source that is not bound to an identified writer build; if the kinematic cross-check disagrees, do not place the base',
             gaps=['the MuJoCo quantity behind the field is declared in native source that cannot be tied to a single writer build; the kinematic cross-check is reported separately']),
        part('gripper_visual_appearance', 'conditional',
             inputs_available={'recorded_scalar': True, 'platform_constants': {'min_width_m': 0.012000038000000005, 'max_width_m': 0.05,
                                                                              'zero_width_m': 0.025, 'zero_model_rad': -1.077632656580025,
                                                                              'width_per_drive_rad_m': 0.023199}},
             frontend_rule='the jaws may be posed only from the platform reference constants, which declare themselves not native-attested; otherwise keep the jaws at the bundle\'s own layout and label the gripper as not-from-record',
             gaps=['turning the recorded width into jaw and drive joint values needs the platform\'s declared gripper constants accepted as authoritative; nothing in the record or bundle attests them']),
        part('tcp_position_marker', 'ready_with_caveats',
             inputs_available={'recorded_position': 3, 'computed_position': [value + 1e-14 for value in tcp_position], 'abs_error_m': 1.6454e-14},
             frontend_rule='a point marker is allowed; it must not be drawn as an oriented frame because no TCP orientation is recorded',
             gaps=['the site offset lives in the platform reference config, not in the frozen bundle or the record; the cross-check reports how well that attachment reproduces the recorded position']),
        part('tcp_orientation_frame', 'blocked', inputs_available={'recorded': False},
             frontend_rule='do not synthesise an oriented TCP frame',
             gaps=['no TCP orientation is recorded and the reference declares none']),
        part('camera_view_from_record', 'blocked',
             inputs_available={'recorded_calibration': False, 'declared_mount': {'parent_body': 'link4', 'status': 'source_topology_not_rigid_to_tcp'}},
             frontend_rule='an image plane or a viewer-placed camera is allowed; a record-derived camera pose is not',
             gaps=['no recorded camera calibration, and the declared mount body is not rigid to the TCP']),
        part('dynamic_scene_objects_from_record', 'blocked', inputs_available={'recorded': False},
             frontend_rule='keep world objects at the bundle’s compiled initial layout and label that layout as not the historical state',
             gaps=['no historical position is recorded for dynamic scene objects, so they cannot be placed from the record']),
        part('wheel_pose_from_record', 'not_required', inputs_available={'unlabelled_velocity_count': 4},
             frontend_rule='wheel angles are not needed to place the robot for this slice',
             gaps=['the four wheel values carry no per-wheel identity; a static pose does not need them'])],
        'part_status_meaning': {'ready': 'the inputs, the fixed resources and the mapping rule are all present and consistent',
                                'ready_with_caveats': 'usable now, with the named limits stated beside it',
                                'conditional': 'usable only if the consumer accepts the named unattested assumption and shows it',
                                'blocked': 'a required input or attestation is absent, so this part must not be drawn from the record',
                                'not_required': 'this part is not needed to place the robot'}}


def fk_fixture(tcp_position, supported=('recorded_pose_is_base_body_world_pose',)):
    """The reader's own same-frame forward-kinematics answer, including the convention it excluded."""
    return {'status': 'computed', 'method': 'pure forward kinematics over the frozen bundle tree',
            'recorded_tcp_position_m': tcp_position, 'computed_tcp_position_m': [value + 1e-14 for value in tcp_position],
            'abs_error_m': 1.6454e-14, 'verdict': 'consistent', 'consistency_tolerance_m': 0.005,
            'tolerance_authority': 'stated by this slice to judge kinematic agreement; it is not a calibration limit and not a contract threshold',
            'supported_hypotheses': list(supported), 'chain_links': ['base_link', 'joint1_link'],
            'hypotheses': [{'hypothesis': 'recorded_pose_is_base_body_world_pose', 'status': 'computed',
                            'computed_tcp_position_m': [value + 1e-14 for value in tcp_position], 'abs_error_m': 1.6454e-14, 'verdict': 'consistent'},
                           {'hypothesis': 'recorded_pose_needs_the_bundle_base_offset', 'status': 'computed',
                            'computed_tcp_position_m': [tcp_position[0], tcp_position[1], tcp_position[2] + 0.055], 'abs_error_m': 0.0556, 'verdict': 'inconsistent'}]}


def pose_payload(episode, sample, mode='m15e', **patch):
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
             'mapping': mapping_fixture(mode='legacy' if mode == 'legacy' else 'm15e'),
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
                                'bundle_sha256': BUNDLE_ID, 'content_identity_sha256': CONTENT_ID, 'compiler': {'name': 'MuJoCo', 'version': '3.1.6'},
                                'model_inputs_sha256': MODEL_INPUTS_ID, 'compiled_scene_sha256': COMPILED_ID,
                                'link_count': 6, 'tcp_site': 'grasp_tcp', 'camera_ids': ['rgbd'],
                                'root_joint': {'name': 'base_link', 'parent_name': None, 'joint_name': 'base_free', 'joint_type': 'free',
                                               'joint_axis': [0.0, 0.0, 1.0], 'local_position_m': [0.0, 0.0, 0.055], 'local_orientation_xyzw': [0.0, 0.0, 0.0, 1.0]},
                                'tcp_parent_body_view': {'name': 'joint5_link', 'joint_type': 'fixed'},
                                'world_links': [{'name': name, 'geom_types': ['box']} for name in WORLD_LINK_NAMES],
                                'link_frames': "each link's local_transform is the model body offset relative to its parent body",
                                'arm_hinge_joints': ['joint1', 'joint2', 'joint3', 'joint4', 'joint5'], 'gripper_slide_joints': ['left_jaw_joint', 'right_jaw_joint'],
                                'wheel_hinge_joints': ['front_left_joint'], 'assets': [{'asset_id': 'link1', 'sha256': STL_SHA, 'media_type': 'model/stl',
                                                                                        'coordinate_space': 'mujoco_compiled_mesh', 'units': 'm', 'bytes': len(STL)}],
                                'asset_integrity': 're-verified per request before bytes leave the process', 'live_native_scene_proxied': False,
                                'served_via': 'GET /api/v1/episodes/{episode_id}/model/assets/{asset_id} (frozen bundle only)'},
             'rendering': {'verified': False, 'frontend_assembly_done': False, 'note': 'this slice prepares and reports the mapping; it does not render'},
             'not_proven': [{'target': 'base_position', 'status': 'unverified', 'gap': 'the body origin, frame and z convention is not attested'},
                            {'target': 'dynamic_scene_objects', 'status': 'missing', 'gap': 'no historical position is recorded for dynamic scene objects'}],
             'capability_limits': ['no replay execution', 'no live geometry or Actual substitution', 'no fabricated dynamic object pose',
                                   'no calibration claim', 'no control, RESET, recording or physics stepping']}
    if mode != 'legacy':
        tcp = value['state']['recorded_payload']['tcp_position_world_m']
        value['not_proven'] = [
            {'target': 'gripper_joints', 'status': 'unverified',
             'gap': 'turning the recorded width into jaw and drive joint values needs the platform\'s declared gripper constants accepted as authoritative; nothing in the record or bundle attests them'},
            {'target': 'tcp_site_orientation', 'status': 'missing', 'gap': 'no TCP orientation is recorded and the reference declares none'},
            {'target': 'camera_extrinsics', 'status': 'missing', 'gap': 'no recorded camera calibration, and the declared mount body is not rigid to the TCP'},
            {'target': 'dynamic_scene_objects', 'status': 'missing', 'gap': 'no historical position is recorded for dynamic scene objects, so they cannot be placed from the record'}]
        value['pose_readiness']['blocking_fields'] = ['gripper_joints', 'tcp_site_orientation', 'camera_extrinsics', 'dynamic_scene_objects']
        value.update(part_readiness_fixture(tcp))
        value.update({'capability_summary': {'usable_now': ['fixed_model_reference_assembly', 'arm_local_pose', 'base_pose_placement', 'tcp_position_marker'],
                                             'usable_only_with_the_named_caveat': ['gripper_visual_appearance'],
                                             'blocked': ['tcp_orientation_frame', 'camera_view_from_record', 'dynamic_scene_objects_from_record'],
                                             'fixed_model_assembly_available': True, 'whole_robot_pose_rebuildable': False,
                                             'escalation_forbidden': 'a usable part never upgrades into whole-robot rebuild, rendering or synchronised replay',
                                             'defaults_forbidden': 'no part may be filled with an assumed value',
                                             'kinematic_agreement': 'consistent', 'abs_tcp_error_m': 1.6454e-14},
                      'tcp_kinematic_cross_check': fk_fixture(tcp),
                      'version_binding': {'reference_source': 'native working tree at commit a5cef52 (dirty)', 'chain_verified_in_reference_source': True,
                                          'writer_identified': False, 'record_carries_no': ['native release id', 'build id', 'git commit'],
                                          'conclusion': 'narrows the writer to that release family; it does not identify a single build'},
                      'model_vs_user_angles': {'render_source': 'arm_model_qpos_rad applied to the bundle hinge joints, in model radians, with no conversion step',
                                               'conversion_is_required_for_drawing': False,
                                               'user_angle_formula': {'q_user': 'q_user = (q_model - zero_model_rad) / user_direction',
                                                                      'zero_model_rad': [0.0, 0.0, 0.0, -1.5707963267948966, 0.0],
                                                                      'user_direction': [1, 1, 1, 1, 1], 'used_for': 'user-facing display and limit comparison only'},
                                               'zero_pose_authority': {'zero_status': 'user_defined_photo_pose_not_hardware_500', 'calibration_session': 'uncalibrated',
                                                                       'authority': 'platform_reference_not_native_attested'}},
                      'pose_readiness': {**value['pose_readiness'], 'mapped_targets_partially_or_fully_verified': '4/10',
                                         'parts_ready': ['fixed_model_reference_assembly'], 'parts_conditional': ['gripper_visual_appearance'],
                                         'parts_blocked': ['tcp_orientation_frame', 'camera_view_from_record', 'dynamic_scene_objects_from_record'],
                                         'kinematic_agreement': 'consistent'}})
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
                  'episode_pose_missing', 'episode_pose_bad_schema', 'episode_pose_late', 'episode_asset_conflict',
                  'episode_no_part_readiness', 'episode_zero_angles', 'episode_no_world_pose_convention',
                  'episode_tree_identity', 'episode_link_order_swap', 'episode_pose_order_swap', 'episode_no_sim_keys']
# The placement tree is one read per Episode and carries no episode in its URL, so a case that needs a
# different tree sets this explicitly before it switches Episodes — no ordering race inside the fixture.
SCENE = {'content_identity': CONTENT_ID, 'arm_order': None, 'mode': 'ok'}
# The nine capabilities, in the order the reader lists them on 18970.
PART_CAPS = ['fixed_model_reference_assembly', 'arm_local_pose', 'base_pose_placement', 'gripper_visual_appearance', 'tcp_position_marker',
             'tcp_orientation_frame', 'camera_view_from_record', 'dynamic_scene_objects_from_record', 'wheel_pose_from_record']


def set_scene_variant(content_identity=CONTENT_ID, arm_order=None, mode='ok'):
    """`mode` drives how the placement-tree route answers: 'ok' serves the frozen bundle, 'unavailable'
    refuses it the way a candidate without a loaded bundle does, 'live' answers with a live-object tree
    that must never be drawn as history."""
    SCENE['content_identity'] = content_identity
    SCENE['arm_order'] = arm_order
    SCENE['mode'] = mode


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
        if episode == 'episode_ok' and sample == 'rgbd_2':
            # A deliberately slow answer for the frame the attribution check switches to, so "the old
            # pose is hidden while this frame is in flight" is an observable window, not a race.
            await asyncio.sleep(1.2)
        if episode == 'episode_no_part_readiness':
            # The 18969 answer: a verified-looking mapping with no per-capability readiness at all.
            await route.fulfill(json=pose_payload(episode, sample, mode='legacy')); return
        if episode == 'episode_pose_verified':
            await route.fulfill(json=pose_payload(episode, sample, mode='legacy', mapping=mapping_fixture('verified'))); return
        if episode == 'episode_zero_angles':
            payload = pose_payload(episode, sample)
            payload['state']['recorded_payload']['arm_model_qpos_rad'] = [0.0, 0.0, 0.0, 0.0, 0.0]
            await route.fulfill(json=payload); return
        if episode == 'episode_no_world_pose_convention':
            payload = pose_payload(episode, sample)
            payload['tcp_kinematic_cross_check']['supported_hypotheses'] = []
            await route.fulfill(json=payload); return
        if episode == 'episode_state_ambiguous':
            # The same frame the frame page calls ambiguous: two state records claim its key, so the
            # reader selects none — the tree still assembles, but no recorded value may pose it.
            payload = pose_payload(episode, sample)
            payload['state'] = {**payload['state'], 'linkage_status': 'ambiguous_candidates', 'recorded_payload': None,
                                'single_state_selected': False, 'candidate_records': 2,
                                'multiple_candidates_note': 'two records claim this frame’s key, so no single record can be reported',
                                'candidates': [{'line_index': 7, 'record_position': 'events.jsonl#7', 'payload': {}},
                                               {'line_index': 8, 'record_position': 'events.jsonl#8', 'payload': {}}]}
            await route.fulfill(json=payload); return
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
        if episode == 'episode_no_sim_keys':
            # The 18969 answer: only the payload's own sim quantity existed, the split key list and the
            # corrections list did not exist at all.
            legacy_page = frames_payload(episode, [frame_payload('rgbd_legacy_time')])
            frame = legacy_page['frames'][0]
            legacy_rows = [row for row in frame['times']['quantities'] if row['key'] != SIM_KEYS[1]]
            legacy_page['version_migration'] = {key: value for key, value in legacy_page['version_migration'].items() if key != 'corrections'}
            await route.fulfill(json={**legacy_page, 'frames': [{**frame, 'times': {key: (legacy_rows if key == 'quantities' else value)
                                                                                   for key, value in frame['times'].items() if key != 'sim_time_quantity_keys'}}]}); return
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
    never needs a live robot to exercise the assembly, the identity binding and the pose drive. The mode
    also lets a case refuse the route or answer it with a live-object tree."""
    if SCENE['mode'] == 'unavailable':
        await route.fulfill(status=503, content_type='application/json',
                            json={'detail': {'code': 'geometry_bundle_unavailable',
                                             'message': '该候选没有加载冻结 geometry bundle：没有历史模型资产可读'}})
        return
    envelope = geometry_payload(content_identity=SCENE['content_identity'], arm_order=SCENE['arm_order'],
                                world_link_count=len(WORLD_LINK_NAMES))
    if SCENE['mode'] == 'live':
        envelope['world_pose_semantics'] = 'live_native_object_state_not_compiled_layout'
    await route.fulfill(json=envelope)


async def synthetic_flow(page):
    await wait_list(page)
    episode_mark = len(report['requests'])
    await open_episode(page, 'run_a', 'episode_ok')
    view = await page_attrs(page)
    check('the synthetic pane binds frame-link-2 and shows the fixture’s three frames',
          view['schema'] == FRAME_SCHEMA and view['returned'] == '3' and len(view['rowSamples']) == 3
          and view['migrationTo'] == FRAME_SCHEMA and view['primaryMatched'] == '|'.join(ROLE_KEYS[:4]))
    check('the three state stamps stay separate rows and the removed age is named as removed',
          {'state_event_write_minus_frame_capture', 'state_payload_feedback_time_minus_frame_capture', 'recorder_declared_feedback_time_minus_frame_capture',
           'state_sim_time_minus_frame_capture_sim_time', 'state_event_envelope_sim_time_minus_frame_capture_sim_time', 'persist_minus_capture', 'observation_arrival_minus_frame_capture'} == set(view['quantityKeys'])
          and 'age_of_state_relative_to_frame' in await page.locator('[data-time-semantics]').inner_text()
          # String(3.0) in JS is '3': the fixture values are shown in the reader's own numeric form.
          and '3' in view['quantityAbs'] and '4' in view['quantityAbs'], view['quantityKeys'])
    # The split sim keys and the recorded labelling fix are the reader's own words, not the interface's.
    check('the M1.5e sim-time split and the recorded corrections are shown from the reader’s own keys',
          all(key in view['simKeys'] for key in SIM_KEYS) and '负载量与信封量各一条，缺就是缺，不互相回填' in view['simKeys']
          and len(view['corrections']) == len(CORRECTIONS)
          and all(line in ' '.join(view['corrections']) for line in CORRECTIONS), (view['simKeys'], view['corrections'][:1]))
    await wait_model(page, 'ready')
    assembly_reads = len(static_tree_reads(episode_mark))
    frame_mark = len(report['requests'])
    model = await page_attrs(page)
    check('the tree assembles from the frozen bundle with history bytes and a pose attributable to the frame',
          model['modelStatus'] == 'ready' and model['modelCanvas'] == 1 and model['modelAttribution'] == 'matched'
          and model['modelDisplayed'] == model['modelRequested'] and model['modelFramePose'] == 'true'
          and model['comparisonEqual'] == ['true'] * 4 and set(model['treeEqual']) == {'true'}
          and '本帧历史姿态（按部件门控）' in model['modelText'], (model['modelAttribution'], model['treeFields']))
    check('the pane names the placement route’s own data_source rather than an Episode-scoped manifest',
          model['modelTreeSource'] == 'live_native_http_with_verified_compiled_geometry'
          and 'data_source=live_native_http_with_verified_compiled_geometry' in model['modelStage']
          and 'Episode 作用域的静态 manifest 尚未发布' in model['modelStage'], (model['modelTreeSource'], model['modelStage'][:200]))
    check('the readiness gate drives the arm, the chassis and the TCP point and withholds the rest by name',
          model['partCaps'] == PART_CAPS and model['partDrivable'] == ['true', 'true', 'true', 'false', 'true', 'false', 'false', 'false', 'false']
          and model['partStatuses'] == ['ready', 'ready_with_caveats', 'ready_with_caveats', 'conditional', 'ready_with_caveats', 'blocked', 'blocked', 'blocked', 'not_required']
          and model['modelJoints'] == '5' and model['modelBase'] == 'true' and model['modelTcp'] == 'true'
          and int(model['modelWithheld']) == 5 and '不默认开启' in model['modelText'], (model['partStatuses'], model['modelWithheld']))
    check('the same-frame kinematic answer is shown with both tested conventions and its tolerance owner',
          model['fkVerdicts'] == ['consistent', 'inconsistent'] and '0.0556' in model['modelText']
          and 'not a calibration limit' in model['fkCheck'] and 'abs_error_m=1.6454e-14' in model['fkCheck']
          and 'verdict=consistent' in model['fkCheck'], (model['fkVerdicts'], model['fkCheck'][:200]))
    check('the version binding and the uncalibrated zero stay on screen next to the driven pose',
          'writer_identified=false' in model['modelText'] and 'uncalibrated' in model['modelText']
          and 'conversion_is_required_for_drawing=false' in model['modelText'], model['modelText'][-300:])
    check('the reference surface carries no live control affordance and declares itself non-polling',
          model['controlSurface'] == 0 and await attr(page, '[data-model-pane]', 'data-model-live-poll') == 'off'
          and await attr(page, '[data-model-pane]', 'data-reference-pose') == 'compiled-initial-layout',
          (model['controlSurface'], model['modelStatus']))

    # Stepping frames must rebind the pose, not the viewport: camera, layout and tree stay.
    before = await wait_model_quiet(page)
    await page.locator('[data-frame-next]').click()
    await wait_model(page, 'ready')
    after = await wait_model_quiet(page)
    check('a frame step re-poses the same tree without rebuilding the viewport or moving the camera',
          after['camera'] == before['camera'] and after['links'] == before['links'] and after['worldLinks'] == before['worldLinks']
          and after['lifecycle']['renders'] > before['lifecycle']['renders'] and after['attribution']['displayedSample'] != before['attribution']['displayedSample']
          and after['pendingLoads'] == 0 and after['assetFailures'] == [], (after['camera'], before['camera']))
    await page.locator('[data-model-view="top"]').click()
    await page.locator('[data-model-inspect]').click()
    top = json.loads(await attr(page, '[data-model-inspected]', 'data-model-inspected'))
    await page.locator('[data-model-view="front"]').click()
    await page.locator('[data-model-inspect]').click()
    front = json.loads(await attr(page, '[data-model-inspected]', 'data-model-inspected'))
    check('the standard views move only the camera and survive a frame step',
          abs(top['camera']['polarDeg'] - front['camera']['polarDeg']) > 20 and abs(top['camera']['distance'] - front['camera']['distance']) < 1e-6
          and front['attribution']['displayedSample'] == after['attribution']['displayedSample'], (top['camera'], front['camera']))
    axes = await attr(page, '[data-model-axis-convention]', 'data-model-axis-convention')
    picked = await pick_model_link(page)
    picked_state = await page_attrs(page)
    check('the axis statement and a real click-to-select work on the reference surface without any control',
          'world_sim' in axes and '+X=车头' in axes and '不画朝向帧' in axes
          and picked['link'] in ('base_link', 'joint1_link', 'joint2_link', 'joint3_link', 'joint4_link', 'joint5_link')
          and len(picked['geoms']) >= 1 and picked['controls'] == 0
          and all(row['method'] == 'GET' for row in picked['new_requests'])
          and picked_state['modelDisplayed'] == picked_state['modelRequested'] and picked_state['modelJoints'] == '5',
          (picked['link'], picked['geoms'], axes[:80]))

    # A read still in flight may never show the previous frame's pose under the new frame's title.
    await page.locator('[data-frame-pick="rgbd_1"]').click()
    await wait_model(page, 'ready')
    await page.locator('[data-frame-pick="rgbd_2"]').click()
    await page.wait_for_function("()=>(document.querySelector('[data-model-pane]')?.getAttribute('data-model-attribution') ?? '')==='pending'", timeout=30000)
    pending = await page_attrs(page)
    check('while the next frame is being read the dynamic pose is hidden, not relabelled',
          pending['modelAttribution'] == 'pending' and pending['modelDisplayed'] == 'none' and pending['modelRequested'] == 'rgbd_2'
          and pending['modelFramePose'] == 'false' and pending['modelBase'] == 'false' and pending['modelTcp'] == 'false' and pending['modelJoints'] == '0'
          and pending['valueNames'] == [] and pending['valuesTable'] == 'no-frame' and pending['valueNoneRow'] == 1
          and '回到编译初始布局' in pending['modelStage'], (pending['modelAttribution'], pending['valueNames'], pending['modelStage'][:160]))
    await wait_model(page, 'ready')
    landed = await page_attrs(page)
    check('once it lands the pose belongs to that frame and only that frame',
          landed['modelAttribution'] == 'matched' and landed['modelDisplayed'] == 'rgbd_2' and landed['modelRequested'] == 'rgbd_2'
          and landed['modelFramePose'] == 'true' and landed['modelJoints'] == '5'
          and landed['valuesTable'] == 'rgbd_2' and landed['valueNames'] == ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'base_link', 'grasp_tcp']
          and [float(value) for value in landed['valueModels'][:5]] == ARM_RAD
          and json.loads(landed['valueModels'][5].split(' / ')[0]) == [0.1, 0.2, 0.05]
          and json.loads(landed['valueModels'][6]) == [0.17, 0.0, 0.3]
          and abs(float(landed['valueDisplays'][3].split('（')[0]) - (-1.57 - (-1.5707963267948966))) < 1e-12,
          (landed['valuesTable'], landed['valueModels']))

    check('驱动成立不等于运动被验证：两个归属帧值相同时运动覆盖明说“没有跨帧运动覆盖证据”',
          int(landed['motionVisited']) >= 2 and landed['motionNoneRow'] == 0
          and landed['motionNames'] == ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'base_link', 'grasp_tcp']
          and landed['motionDistinct'] == ['1'] * 7 and landed['motionVisits'] == [landed['motionVisited']] * 7
          and '没有跨帧运动覆盖证据' in landed['modelText'] and '不推断整条记录' in landed['modelText'],
          (landed['motionVisited'], landed['motionDistinct']))

    # Census across frame steps, view switches, picks and a late-response switch. The fixture refuses the
    # live workbench's own native read, so that path retries on this same route: the pane's own counter is
    # the attributed measurement and the route window is only recorded.
    stepping = await page_attrs(page)
    census = {'pane_tree_reads': stepping['modelTreeReads'], 'pane_tree_read_episode': stepping['modelTreeReadEpisode'],
              'route_tree_reads_before_stepping': assembly_reads,
              'route_tree_reads_since_stepping': len(static_tree_reads(frame_mark)),
              'frames': frame_reads_of(frame_mark),
              'live_scene_asset_bytes': len([r for r in report['requests'][frame_mark:] if '/mobilecar/scene/assets/' in urlsplit(r['url']).path])}
    report['synthetic']['static_tree_census'] = census
    check('the pane downloads the fixed tree once for its Episode identity and never again per frame',
          stepping['modelTreeReads'] == '1' and stepping['modelTreeReadEpisode'] == 'episode_ok'
          and census['frames']['poses'] >= 2 and len(census['frames']['samples']) >= 2
          and census['live_scene_asset_bytes'] == 0, census)

    switch_reads = await open_episode_tree_reads(page, 'run_a', 'episode_pose_verified')
    report['synthetic']['episode_switch_tree_reads'] = switch_reads
    await wait_model(page, 'ready')
    switched = await page_attrs(page)
    check('switching Episodes re-reads the placement tree once, under the new Episode identity',
          switched['modelTreeReads'] == '1' and switched['modelTreeReadEpisode'] == 'episode_pose_verified'
          and switched['modelEpisode'] == 'episode_pose_verified',
          {'pane': [switched['modelTreeReads'], switched['modelTreeReadEpisode']], 'route': switch_reads})
    check('换 Episode 会把运动覆盖观测重新起算，不混入上一个 Episode 的帧',
          switched['motionKey'].startswith('episode_pose_verified|') and switched['motionVisited'] == '1'
          and switched['motionNames'] == [] and switched['motionNoneRow'] == 1,
          (switched['motionKey'], switched['motionVisited'], switched['motionNames']))
    legacy = await page_attrs(page)
    arm = legacy['mappingTargets'].index('arm_joint_positions')
    check('a verified mapping without any part_readiness still drives nothing (the gate is the readiness)',
          legacy['mappingStatuses'][arm] == 'verified' and legacy['modelJoints'] == '0' and legacy['modelBase'] == 'false'
          and legacy['modelFramePose'] == 'false' and 'reader 未返回该能力的就绪状态' in legacy['modelText']
          and legacy['valueNames'] == [] and legacy['valueNoneRow'] == 1
          and legacy['motionNames'] == [] and legacy['motionNoneRow'] == 1, legacy['modelDrive'])

    await open_episode(page, 'run_a', 'episode_zero_angles')
    await wait_model(page, 'ready')
    await page.locator('[data-model-inspect]').click()
    zeros = json.loads(await attr(page, '[data-model-inspected]', 'data-model-inspected'))
    zero_attrs = await page_attrs(page)
    check('zero angles are legal values and are driven as recorded, not treated as missing',
          all(value == 0.0 for value in zeros['selectedJointDriven'].values()) and len(zeros['selectedJointDriven']) == 5
          and '0 是合法数值' in zero_attrs['modelText']
          and zero_attrs['valueModels'][:5] == ['0', '0', '0', '0', '0'] and zero_attrs['valueNoneRow'] == 0
          and abs(float(zero_attrs['valueDisplays'][3].split('（')[0]) - 1.5707963267948966) < 1e-12,
          (zeros['selectedJointDriven'], zero_attrs['valueModels'][:5]))

    await open_episode(page, 'run_a', 'episode_no_world_pose_convention')
    await wait_model(page, 'ready')
    unconvention = await page_attrs(page)
    check('an unstated root convention withholds only the chassis; the arm keeps driving',
          unconvention['modelBase'] == 'false' and unconvention['modelJoints'] == '5' and unconvention['modelTcp'] == 'true'
          and 'supported_hypotheses' in unconvention['modelText']
          and unconvention['valueNames'] == ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'grasp_tcp']
          and 'base_link' not in unconvention['valueNames']
          and unconvention['motionNames'] == unconvention['valueNames'], (unconvention['modelBase'], unconvention['valueNames']))

    # Same mesh bytes, different tree: only the content identity can catch this one.
    set_scene_variant(content_identity='d' * 64)
    await open_episode(page, 'run_a', 'episode_tree_identity')
    await wait_model(page, 'blocked')
    identity = await page_attrs(page)
    check('a tree whose content identity differs from the record is refused even though every mesh matches',
          identity['modelStatus'] == 'blocked' and '静态树与记录的内容身份不一致' in identity['modelStage']
          and 'content_identity_sha256' in identity['modelStage'] and identity['canvas'] == 0
          and identity['assetEqual'] == ['true'] and 'false' in identity['treeEqual'], identity['modelStage'][:200])
    set_scene_variant(arm_order=['joint2', 'joint1', 'joint3', 'joint4', 'joint5'])
    await open_episode(page, 'run_a', 'episode_link_order_swap')
    await wait_model(page, 'blocked')
    swapped = await page_attrs(page)
    check('the same meshes hung on a re-ordered joint chain are refused by the joint-name binding',
          swapped['modelStatus'] == 'blocked' and 'arm_hinge_joints' in swapped['modelStage'] and swapped['canvas'] == 0, swapped['modelStage'][:200])
    # The placement tree itself failing: a candidate without a loaded bundle, and a candidate whose tree
    # is live object state rather than the compiled layout. Neither may leave a model on screen.
    set_scene_variant(mode='unavailable')
    await open_episode(page, 'run_a', 'episode_pose_verified')
    await wait_model(page, 'failed')
    no_tree = await page_attrs(page)
    check('a refused placement tree fails the pane by code, with no canvas and nothing driven',
          no_tree['modelStatus'] == 'failed' and 'geometry bundle 清单读取失败' in no_tree['modelStage']
          and 'geometry_bundle_unavailable' in no_tree['modelStage'] and no_tree['canvas'] == 0 and no_tree['modelCanvas'] == 0
          and no_tree['modelJoints'] == '0' and no_tree['modelBase'] == 'false' and no_tree['modelTcp'] == 'false'
          and no_tree['modelFramePose'] == 'false' and no_tree['modelDisplayed'] == 'none'
          and no_tree['valueNames'] == [] and no_tree['valueNoneRow'] == 1
          and no_tree['motionVisited'] == '0' and no_tree['motionNoneRow'] == 1
          and no_tree['modelTreeReads'] == '1' and no_tree['modelTreeReadEpisode'] == 'episode_pose_verified', no_tree['modelStage'][:200])
    set_scene_variant(mode='live')
    await open_episode(page, 'run_a', 'episode_zero_angles')
    await wait_model(page, 'failed')
    live_tree = await page_attrs(page)
    check('a tree that says it carries live object state is refused as a history reference, not rendered',
          live_tree['modelStatus'] == 'failed' and 'bundle 语义不是编译初始布局' in live_tree['modelStage']
          and '不用它装配历史参考' in live_tree['modelStage'] and live_tree['canvas'] == 0
          and live_tree['modelJoints'] == '0' and live_tree['modelTreeSource'] == 'none', live_tree['modelStage'][:200])
    set_scene_variant()
    await open_episode(page, 'run_a', 'episode_ok')
    await wait_model(page, 'ready')
    recovered = await page_attrs(page)
    check('the same Episode assembles again once the route answers, so the failure was not sticky',
          recovered['modelStatus'] == 'ready' and recovered['modelCanvas'] == 1 and recovered['modelJoints'] == '5'
          and recovered['modelAttribution'] == 'matched' and recovered['modelTreeReads'] == '1', (recovered['modelStatus'], recovered['modelStage'][:160]))

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
    check('the frame whose state is ambiguous still assembles the tree but drives no recorded value',
          after_ambiguous['modelStatus'] == 'ready' and after_ambiguous['modelJoints'] == '0'
          and after_ambiguous['modelBase'] == 'false' and after_ambiguous['modelTcp'] == 'false'
          and after_ambiguous['modelFramePose'] == 'false' and after_ambiguous['modelDisplayed'] == 'rgbd_state_ambiguous'
          and after_ambiguous['modelAttribution'] == 'matched' and int(after_ambiguous['modelWithheld']) == 8
          and len(after_ambiguous['partCaps']) == 9 and after_ambiguous['partDrivable'].count('true') == 1
          and after_ambiguous['partCaps'][0] == 'fixed_model_reference_assembly'
          and '界面没有该能力的处理规则' not in after_ambiguous['modelText']
          and '不挑候选、不补 0、不沿用上一帧' in after_ambiguous['modelText']
          and 'candidate_records=2' in after_ambiguous['modelText'] and 'no single record can be reported' in after_ambiguous['modelText'],
          (after_ambiguous['modelDrive'], after_ambiguous['modelWithheld']))

    await open_episode(page, 'run_a', 'episode_no_time_bases')
    empty_bases = await page_attrs(page)
    options = await page.locator('select[aria-label="帧时间基"] option').evaluate_all('els=>els.map(e=>e.value)')
    check('an empty selectable_time_bases page offers no numeric base at all instead of a default list',
          empty_bases['selectable'] == [] and options == [''] and empty_bases['windowGate'] == 'refused'
          and '未选择时间基' in empty_bases['windowReason'] and await page.locator('[data-frame-window-apply]').is_disabled()
          and 'reader 未声明（空数组就是本页的答案，不回退默认基）' in await page.locator('[data-frame-selectable-bases]').inner_text(),
          (options, empty_bases['windowReason']))

    # The previous backend candidate answered without these keys at all; the pane must say that, not invent them.
    await open_episode(page, 'run_a', 'episode_no_sim_keys')
    legacy_time = await page_attrs(page)
    check('an older reader answer without the sim keys or corrections is reported as absent, not filled in',
          'reader 未声明 sim 时间量清单（本版无该键）' in legacy_time['simKeys'] and legacy_time['corrections'] == []
          and SIM_KEYS[0] not in legacy_time['simKeys'] and SIM_KEYS[1] not in legacy_time['simKeys']
          and SIM_KEYS[0] in legacy_time['quantityKeys'] and SIM_KEYS[1] not in legacy_time['quantityKeys'],
          (legacy_time['simKeys'], legacy_time['corrections']))

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
    await page.locator('[data-frame-play]').click()
    # Playing re-reads each frame it lands on, so the pose only has to catch up with the selection
    # after the walk stops; while it is still in flight the pane says whose pose it is showing.
    await wait_model(page, 'ready')
    await page.wait_for_function("()=>(document.querySelector('[data-model-pane]')?.getAttribute('data-model-attribution') ?? '')==='matched'", timeout=30000)
    played = await page_attrs(page)
    check('play advances on a UI cadence only, re-reading the state of each frame it lands on',
          playing == 'pause' and int(played['index']) >= 1 and played['modelDisplayed'] == played['currentSample']
          and '节奏只控制界面推进，不是录制帧率' in played['text'] and '帧率' not in played['explanation'], (playing, played['index'], played['modelDisplayed']))


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
