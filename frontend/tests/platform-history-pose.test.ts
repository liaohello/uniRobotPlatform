import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EpisodeContractError, describeHistoryError } from '../src/adapters/platform-episodes';
import {
  HISTORY_POSE_SCHEMA, assertHistoryFrameIdentity, comparisonRowsOf, etagDigest, mappingRowsOf, modelAssetRowsOf,
  modelResourceText, notProvenText, poseBoundaryText, poseDriveOf, poseReadinessText, poseStateText, readHistoryModelAsset,
  readRobotState, renderingText, type HistoryPoseDto,
} from '../src/adapters/platform-history-pose';

// Fixtures copy the shape of the `unirobot-mobilecar-history-pose-1` payload the candidate on 18969
// answered for the real COMPLETE frame on 2026-10-26. The `verified` variants exist only to exercise
// the driving gate: they are labelled synthetic and are not claims about the real archive.
const RUN = 'run_0104613ff7364ae78cf2f3946bd45f7b';
const EPISODE = 'episode_27bfed5427684795b361cd2ec21e9aa7';
const SAMPLE = 'rgbd_e3213e6cb64b4cd693c17d485d064d09';
const MODEL_SHA = '3ca3d6d0a92a48bbfbce5ac7a04e37a0f7cf7a73297045ae327bf461ad50e280';
const SOURCE = { source_id: 'mobilecar-server-history-20261017', adapter_id: 'mobilecar', recording_root: '/x', access: 'read_only_files', platform_writes: false };
const ARM_RAD = [4.731963891071609e-5, 0.0016603668666036813, 0.0014384481908740504, -1.5696750090681135, 1.1293487091102144e-6];
const PAYLOAD = {
  feedback_time_monotonic: 426494.347898655, sim_time_s: 0.14,
  base_position_world_sim_m: [-0.00023473557897040777, -1.0145992864392481e-6, 0.053540585735473954],
  base_quaternion_xyzw: [-2.027809601592562e-6, 9.433333536306481e-5, -3.230492476047126e-5, 0.9999999950267509],
  base_twist_body_m_s: [-0.001086000533659529, -5.668342660618616e-5, 0.00030122515201245397],
  wheel_velocity_rad_s: [-0.030412442759356704, -0.03446515577793489, -0.031348075259700646, -0.028323501529422878],
  arm_model_qpos_rad: ARM_RAD, gripper_width_m: 0.024999996765415464,
  tcp_position_world_m: [0.17753849921383363, 0.002461415763947755, 0.30179180035418635],
};
const equalComparison = { contract_version: { recorded: 'mobilecar-1.0', bundle: 'mobilecar-1.0', equal: true },
  model_id: { recorded: 'landerpi_mecanum_dynamic_5dof_3ca3d6d0a92a', bundle: 'landerpi_mecanum_dynamic_5dof_3ca3d6d0a92a', equal: true },
  model_sha256: { recorded: MODEL_SHA, bundle: MODEL_SHA, equal: true }, scene_id: { recorded: 'mobile_pick', bundle: 'mobile_pick', equal: true } };
const mappingRow = (target: string, status: string, extra: Record<string, unknown> = {}) => ({
  target, recorded_field: 'arm_model_qpos_rad', recorded_unit: 'rad', recorded_length: 5,
  target_field: 'bundle hinge joints joint1, joint2, joint3, joint4, joint5', status,
  evidence: { bundle_arm_hinge_joints_in_document_order: ['joint1', 'joint2', 'joint3', 'joint4', 'joint5'] },
  no_default_applied: true, gap: 'fixture gap', ...extra,
});
const poseFixture = (patch: Partial<HistoryPoseDto> = {}): HistoryPoseDto => ({
  schema_version: HISTORY_POSE_SCHEMA, read_only: true, source: SOURCE, retrieved_at: '2026-10-26T06:16:45.779545Z',
  identity: { run_id: RUN, episode_id: EPISODE, recorded_run_manifest: { contract_version: 'mobilecar-1.0', model_sha256: MODEL_SHA, scene_id: 'mobile_pick' }, identity_source: 'the run manifest the recorder itself wrote' },
  frame: { sample_id: SAMPLE, linkage_schema: 'unirobot-mobilecar-frame-link-2', linkage_status: 'matched', anchor: { relative_path: 'observations/persist.jsonl', line_index: 0, persist_sequence: 1 }, media: {} },
  state: { linkage_status: 'matched', source: { stream_id: 'events', relative_path: 'events.jsonl', line_index: 27, event_seq: 28, event_type: 'feedback' }, candidate_records: 1, single_state_selected: true, recorded_payload: PAYLOAD, declared_reference: { feedback_sample_id: 'joint_feedback_000006551', row_status: 'unresolved_reference' }, units: { '*_rad': 'radians' } },
  time: {},
  mapping: [
    mappingRow('arm_joint_positions', 'partially_verified', { model_to_user_formula: { q_user: '(q_model - zero_model_rad) / user_direction', zero_model_rad: [0, 0, 0, -1.5707963267948966, 0], user_direction: [1, 1, 1, 1, 1], authority: 'platform_reference_not_native_attested' }, gap: 'joint positions for indexes 0, 1, 2 and 4 are mapped by array order without a per-index attestation' }),
    mappingRow('base_position', 'unverified', { recorded_field: 'base_position_world_sim_m', recorded_unit: 'm', recorded_length: 3, target_field: 'bundle root link base_link free joint base_free', gap: 'the body origin, frame and z convention for the recorded base position is not attested' }),
    mappingRow('base_orientation', 'unverified', { recorded_field: 'base_quaternion_xyzw', recorded_length: 4, gap: 'the body and frame it rotates are not attested' }),
    mappingRow('gripper_joints', 'unverified', { recorded_field: 'gripper_width_m', recorded_unit: 'm', recorded_length: 1, target_field: 'bundle slide joints left_jaw_joint, right_jaw_joint', gap: 'no attested rule turns the recorded width into jaw joint values' }),
    mappingRow('tcp_site_position', 'unverified', { recorded_field: 'tcp_position_world_m', recorded_length: 3, target_field: 'bundle tcp_site grasp_tcp', gap: 'whether the recorded position is the named site’s world position is not attested' }),
    mappingRow('camera_extrinsics', 'missing', { recorded_field: null, recorded_unit: null, recorded_length: null, target_field: 'bundle camera link chain', gap: 'no recorded camera calibration' }),
    mappingRow('wheel_joint_velocities', 'not_required_for_pose', { recorded_field: 'wheel_velocity_rad_s', recorded_unit: 'rad/s', recorded_length: 4 }),
    mappingRow('base_twist', 'not_required_for_pose', { recorded_field: 'base_twist_body_m_s', recorded_length: 3, target_field: null }),
    mappingRow('dynamic_scene_objects', 'missing', { recorded_field: null, target_field: 'bundle world links world_static, target_cube', gap: 'no historical position is recorded for dynamic scene objects' }),
  ],
  status_meaning: { verified: 'the record and the fixed bundle agree on this mapping, and nothing had to be assumed', partially_verified: 'some parts of the mapping are attested', unverified: 'the value is recorded, but its frame, order, sign or convention is not attested', missing: 'the value a renderer would need is not recorded at all', not_required_for_pose: 'recorded data that this slice does not need to place the robot' },
  pose_readiness: { model_identity: 'match', mapping_valid_for_this_episode: true, mapped_targets_partially_or_fully_verified: '1/9', robot_state_can_be_rebuilt_without_assumptions: false, blocking_fields: ['base_position', 'base_orientation', 'gripper_joints', 'tcp_site_position', 'camera_extrinsics', 'dynamic_scene_objects'], next_round_owner: 'frontend assembly plus an attested base/gripper mapping source', note: 'resource identity, digests and joint-length checks pass; the remaining gaps are attestation gaps' },
  model_resource: { status: 'match', comparison: equalComparison, bundle_sha256: '2'.repeat(64), content_identity_sha256: 'c'.repeat(64), compiler: { name: 'MuJoCo', version: '3.1.6' },
    link_count: 71, arm_hinge_joints: ['joint1', 'joint2', 'joint3', 'joint4', 'joint5'], gripper_slide_joints: ['left_jaw_joint', 'right_jaw_joint'], wheel_hinge_joints: ['front_left_joint', 'rear_left_joint', 'front_right_joint', 'rear_right_joint'],
    assets: [{ asset_id: 'base_link', sha256: 'a'.repeat(64), media_type: 'model/stl', coordinate_space: 'mujoco_compiled_mesh', units: 'm', bytes: 525884 },
      { asset_id: 'link1', sha256: '28184761b2f9253022c1b9845ea8075461a8afc6352d397725c2c57a7563c0e7', media_type: 'model/stl', coordinate_space: 'mujoco_compiled_mesh', units: 'm', bytes: 1020984 }],
    live_native_scene_proxied: false, served_via: 'GET /api/v1/episodes/{episode_id}/model/assets/{asset_id} (frozen bundle only)' },
  rendering: { verified: false, frontend_assembly_done: false, note: 'this slice prepares and reports the mapping; it does not render' },
  not_proven: [{ target: 'base_position', status: 'unverified', gap: 'the body origin, frame and z convention is not attested' }, { target: 'dynamic_scene_objects', status: 'missing', gap: 'no historical position is recorded' }],
  capability_limits: ['no replay execution', 'no live geometry or Actual substitution', 'no fabricated dynamic object pose', 'no control, RESET, recording or physics stepping'],
  ...patch,
});

let urls: string[] = [];
beforeEach(() => { urls = []; });
afterEach(() => { vi.restoreAllMocks(); });

describe('history-pose-1 client', () => {
  it('refuses to ask for a state without the selected frame', async () => {
    globalThis.fetch = vi.fn() as unknown as typeof fetch;
    await expect(readRobotState({ episodeId: EPISODE, runId: RUN, sampleId: '' }, new AbortController().signal)).rejects.toThrow(/sample_id/);
    expect((globalThis.fetch as unknown as { mock: { calls: unknown[] } }).mock.calls).toHaveLength(0);
  });
  it('sends the frame identity and the run on the exact route', async () => {
    globalThis.fetch = vi.fn(async (input: string) => { urls.push(input); return new Response(JSON.stringify(poseFixture()), { status: 200, headers: { 'content-type': 'application/json' } }); }) as unknown as typeof fetch;
    await readRobotState({ episodeId: EPISODE, runId: RUN, sampleId: SAMPLE }, new AbortController().signal);
    const url = new URL(urls[0], 'http://preview.local');
    expect(url.pathname).toBe(`/api/v1/episodes/${EPISODE}/robot-state`);
    expect(url.searchParams.get('sample_id')).toBe(SAMPLE);
    expect(url.searchParams.get('run_id')).toBe(RUN);
  });
  it('rejects a page that is not history-pose-1 rather than rendering it', async () => {
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify({ ...poseFixture(), schema_version: 'unirobot-mobilecar-history-pose-2' }), { status: 200, headers: { 'content-type': 'application/json' } })) as unknown as typeof fetch;
    await expect(readRobotState({ episodeId: EPISODE, runId: RUN, sampleId: SAMPLE }, new AbortController().signal)).rejects.toBeInstanceOf(EpisodeContractError);
  });
  it('checks the returned frame identity against what was asked', () => {
    expect(() => assertHistoryFrameIdentity(poseFixture(), { episodeId: EPISODE, runId: RUN, sampleId: SAMPLE })).not.toThrow();
    expect(() => assertHistoryFrameIdentity(poseFixture({ frame: { ...poseFixture().frame, sample_id: 'rgbd_other' } }), { episodeId: EPISODE, runId: RUN, sampleId: SAMPLE })).toThrow(/帧身份/);
    expect(() => assertHistoryFrameIdentity(poseFixture({ identity: { ...poseFixture().identity, episode_id: 'episode_other' } }), { episodeId: EPISODE, runId: RUN, sampleId: SAMPLE })).toThrow(/episode_id/);
    expect(() => assertHistoryFrameIdentity(poseFixture({ identity: { ...poseFixture().identity, run_id: 'run_other' } }), { episodeId: EPISODE, runId: RUN, sampleId: SAMPLE })).toThrow(/run_id/);
  });
});

describe('history model asset bytes', () => {
  it('parses only the sha256 ETag form', () => {
    expect(etagDigest('"sha256:28184761b2f9253022c1b9845ea8075461a8afc6352d397725c2c57a7563c0e7"')).toBe('28184761b2f9253022c1b9845ea8075461a8afc6352d397725c2c57a7563c0e7');
    expect(etagDigest('W/"weak"')).toBe('');
  });
  it('requests the asset with its declared digest and reports the recomputed one', async () => {
    const digest = '28184761b2f9253022c1b9845ea8075461a8afc6352d397725c2c57a7563c0e7';
    globalThis.fetch = vi.fn(async (input: string) => { urls.push(input); return new Response(new Uint8Array([1, 2, 3]), { status: 200, headers: { 'content-type': 'model/stl', etag: `"sha256:${digest}"`, 'cache-control': 'no-store' } }); }) as unknown as typeof fetch;
    const value = await readHistoryModelAsset({ episodeId: EPISODE, runId: RUN, assetId: 'link1', sha256: digest }, new AbortController().signal);
    const url = new URL(urls[0], 'http://preview.local');
    expect(url.pathname).toBe(`/api/v1/episodes/${EPISODE}/model/assets/link1`);
    expect(url.searchParams.get('sha256')).toBe(digest);
    expect(value.digest).toBe(digest);
    expect(value.bytes.byteLength).toBe(3);
  });
  it('surfaces a content change as the reader’s own 409 code', async () => {
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify({ detail: { code: 'history_asset_revision_changed', message: 'asset digest differs from the frozen bundle', read_only: true, asset_id: 'link1', bundle_sha256: 'b'.repeat(64), requested_sha256: '0'.repeat(64) } }), { status: 409, headers: { 'content-type': 'application/json' } })) as unknown as typeof fetch;
    try { await readHistoryModelAsset({ episodeId: EPISODE, runId: RUN, assetId: 'link1', sha256: '0'.repeat(64) }, new AbortController().signal); expect.unreachable(); }
    catch (cause) {
      expect((cause as { code?: string }).code).toBe('history_asset_revision_changed');
      const text = describeHistoryError(cause);
      expect(text).toContain('资产 link1');
      expect(text).toContain('bundle 重算 bbbbbbbb');
      expect(text).toContain('请求声明 00000000');
      expect(text).toContain('字节未返回');
    }
  });
  it('names the frame_not_found answer for an unknown sample', async () => {
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify({ detail: { code: 'frame_not_found', message: 'this Episode has no persisted frame matching the request', read_only: true, episode_id: EPISODE, run_id: RUN, sample_id: 'rgbd_missing' } }), { status: 404, headers: { 'content-type': 'application/json' } })) as unknown as typeof fetch;
    try { await readRobotState({ episodeId: EPISODE, runId: RUN, sampleId: 'rgbd_missing' }, new AbortController().signal); expect.unreachable(); }
    catch (cause) { expect(describeHistoryError(cause)).toContain('frame_not_found'); }
  });
});

describe('per-part pose gate', () => {
  it('drives nothing while the only mapped target is partially_verified', () => {
    const drive = poseDriveOf(poseFixture());
    expect(drive.driven).toEqual({});
    expect(drive.parts.arm_joint_positions.drivable).toBe(false);
    expect(drive.parts.arm_joint_positions.gate).toBe('partially_verified');
    expect(drive.withheld.join('\n')).toContain('保持固定参考');
    expect(drive.wholeRobotRebuildable).toBe(false);
    expect(drive.summary).toContain('已驱动 0 个关节值');
  });
  it('drives model radians verbatim once the mapping is verified — synthetic gate, not a real archive claim', () => {
    const dto = poseFixture({ mapping: poseFixture().mapping.map((row) => row.target === 'arm_joint_positions' ? { ...row, status: 'verified', gap: null } : row) });
    const drive = poseDriveOf(dto);
    expect(drive.parts.arm_joint_positions.drivable).toBe(true);
    // No user-zero conversion: joint4 keeps the recorded -1.5696… and not that value plus π/2.
    expect(drive.driven).toEqual({ joint1: ARM_RAD[0], joint2: ARM_RAD[1], joint3: ARM_RAD[2], joint4: ARM_RAD[3], joint5: ARM_RAD[4] });
    expect(drive.driven.joint4).toBeCloseTo(-1.5696750090681135, 12);
  });
  it('withholds a verified target whose value count does not match the joint list', () => {
    const dto = poseFixture({ mapping: poseFixture().mapping.map((row) => row.target === 'arm_joint_positions' ? { ...row, status: 'verified', recorded_length: 3 } : row),
      state: { ...poseFixture().state, recorded_payload: { ...PAYLOAD, arm_model_qpos_rad: [0.1, 0.2, 0.3] } } });
    const drive = poseDriveOf(dto);
    expect(drive.parts.arm_joint_positions.drivable).toBe(false);
    expect(drive.parts.arm_joint_positions.reason).toContain('数量不符');
    expect(drive.driven).toEqual({});
  });
  it('never drives unverified, missing or unknown-status targets and never zero-fills them', () => {
    const drive = poseDriveOf(poseFixture());
    for (const target of ['base_position', 'base_orientation', 'gripper_joints', 'tcp_site_position', 'camera_extrinsics', 'dynamic_scene_objects']) {
      expect(drive.parts[target]?.drivable ?? false).toBe(false);
    }
    const unknown = poseDriveOf(poseFixture({ mapping: [mappingRow('arm_joint_positions', 'attested_by_vibes')] }));
    expect(unknown.parts.arm_joint_positions.drivable).toBe(false);
    expect(unknown.parts.arm_joint_positions.gate).toBe('unknown_status');
    expect(unknown.withheld.join('\n')).toContain('不在 reader 的词表里');
    expect(poseDriveOf(null).summary).toContain('未读取 robot-state');
  });
  it('reports a state with no single selected record as it is', () => {
    const dto = poseFixture({ state: { ...poseFixture().state, recorded_payload: null, single_state_selected: false, candidate_records: 2, multiple_candidates_note: 'two records claimed this key; none is chosen' } });
    expect(poseStateText(dto)).toContain('recorded_payload=null（不按第一条候选绘制，不补 0，不沿用上一帧）');
    expect(poseStateText(dto)).toContain('candidate_records=2');
    expect(poseStateText(dto)).toContain('none is chosen');
    expect(poseDriveOf(dto).driven).toEqual({});
  });
});

describe('mapping and model-resource projections', () => {
  it('keeps the nine rows with their own status meanings and gaps', () => {
    const rows = mappingRowsOf(poseFixture());
    expect(rows).toHaveLength(9);
    const arm = rows.find((row) => row.target === 'arm_joint_positions');
    expect(arm?.statusMeaning).toContain('some parts of the mapping are attested');
    expect(arm?.formula).toContain('platform_reference_not_native_attested');
    expect(arm?.noDefault).toBe('true');
    expect(rows.find((row) => row.target === 'camera_extrinsics')?.recordedField).toContain('没有记录字段');
    expect(mappingRowsOf(null)).toEqual([]);
  });
  it('passes the readiness, rendering, not_proven and capability words through', () => {
    expect(poseReadinessText(poseFixture())).toContain('robot_state_can_be_rebuilt_without_assumptions=false');
    expect(poseReadinessText(poseFixture())).toContain('blocking_fields=base_position/base_orientation');
    expect(renderingText(poseFixture())).toContain('rendering.verified=false');
    expect(notProvenText(poseFixture())).toContain('dynamic_scene_objects[missing]');
    expect(poseBoundaryText(poseFixture())).toContain('no fabricated dynamic object pose');
  });
  it('lists the identity comparison and the asset digests the reference view is gated on', () => {
    const comparison = comparisonRowsOf(poseFixture());
    expect(comparison).toHaveLength(4);
    expect(comparison.every((row) => row.equal === 'true')).toBe(true);
    const assets = modelAssetRowsOf(poseFixture());
    expect(assets.map((row) => row.assetId)).toEqual(['base_link', 'link1']);
    expect(modelResourceText(poseFixture())).toContain('live_native_scene_proxied=false');
    expect(modelResourceText(poseFixture())).toContain('frozen bundle only');
    expect(comparisonRowsOf(null)).toEqual([]);
  });
});
