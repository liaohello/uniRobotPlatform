import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EpisodeContractError, describeHistoryError } from '../src/adapters/platform-episodes';
import {
  HISTORY_POSE_SCHEMA, assertHistoryFrameIdentity, capabilitySummaryText, comparisonRowsOf, drivenValuesOf, etagDigest,
  fkCrossCheckOf, mappingRowsOf, mergeVisitedValues, modelAssetRowsOf, modelResourceText, modelVsUserText,
  motionCoverageOf, notProvenText, partReadinessOf, poseBoundaryText, poseDriveOf, poseReadinessText, poseStateText,
  readHistoryModelAsset, readRobotState, renderingText, treeBindingRowsOf, linkBindingRowsOf, versionBindingText, type HistoryPoseDto,
} from '../src/adapters/platform-history-pose';

// The base fixture copies the shape of the `unirobot-mobilecar-history-pose-1` payload the 18969
// candidate answered for the real COMPLETE frame on 2026-10-26 (nine mapping rows, nothing verified,
// no `part_readiness`). `m15eFixture()` copies the payload measured on the 18970 candidate on
// 2026-10-28: nine `part_readiness` capabilities with their `frontend_rule`, four verified mapping
// rows, a same-frame kinematic cross-check with two tested root conventions, and
// `version_binding.writer_identified=false`. Both are unit fixtures: what the real archive renders is
// proven by the browser suite against a running candidate, not here.
const RUN = 'run_0104613ff7364ae78cf2f3946bd45f7b';
const EPISODE = 'episode_27bfed5427684795b361cd2ec21e9aa7';
const SAMPLE = 'rgbd_e3213e6cb64b4cd693c17d485d064d09';
const MODEL_SHA = '3ca3d6d0a92a48bbfbce5ac7a04e37a0f7cf7a73297045ae327bf461ad50e280';
const BUNDLE_SHA = '275389464eee2f3de0c2ddf96ae85acbedfd382c496a589ec41a3662ee31d171';
const CONTENT_SHA = 'cb7899642604038101c909cb9077c09bd2d4006f3d090c205696317f3a18a7cc';
// The two further content digests the 18970 record and the frozen geometry清单 both publish.
const MODEL_INPUTS_SHA = '9e1b60c04b8d8e2e8b2b60b80464178cc7729d10342dc1133aa95c08e64e360a';
const COMPILED_SCENE_SHA = 'a7b8b2c2d12d871306ec443989ec962ca1c4fe93641c3104a1dbcdb81a6ea109';
const SOURCE = { source_id: 'mobilecar-server-history-20261017', adapter_id: 'mobilecar', recording_root: '/x', access: 'read_only_files', platform_writes: false };
const ARM_RAD = [4.731963891071609e-5, 0.0016603668666036813, 0.0014384481908740504, -1.5696750090681135, 1.1293487091102144e-6];
const BASE_POS = [-0.00023473557897040777, -1.0145992864392481e-6, 0.053540585735473954];
const BASE_QUAT = [-2.027809601592562e-6, 9.433333536306481e-5, -3.230492476047126e-5, 0.9999999950267509];
const TCP_POS = [0.17753849921383363, 0.002461415763947755, 0.30179180035418635];
const PAYLOAD = {
  feedback_time_monotonic: 426494.347898655, sim_time_s: 0.14,
  base_position_world_sim_m: BASE_POS, base_quaternion_xyzw: BASE_QUAT,
  base_twist_body_m_s: [-0.001086000533659529, -5.668342660618616e-5, 0.00030122515201245397],
  wheel_velocity_rad_s: [-0.030412442759356704, -0.03446515577793489, -0.031348075259700646, -0.028323501529422878],
  arm_model_qpos_rad: ARM_RAD, gripper_width_m: 0.024999996765415464, tcp_position_world_m: TCP_POS,
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
    mappingRow('tcp_site_orientation', 'missing', { recorded_field: null, recorded_unit: null, recorded_length: null, target_field: null, gap: 'no TCP orientation is recorded' }),
    mappingRow('camera_extrinsics', 'missing', { recorded_field: null, recorded_unit: null, recorded_length: null, target_field: 'bundle camera link chain', gap: 'no recorded camera calibration' }),
    mappingRow('wheel_joint_velocities', 'not_required_for_pose', { recorded_field: 'wheel_velocity_rad_s', recorded_unit: 'rad/s', recorded_length: 4 }),
    mappingRow('base_twist', 'not_required_for_pose', { recorded_field: 'base_twist_body_m_s', recorded_length: 3, target_field: null }),
    mappingRow('dynamic_scene_objects', 'missing', { recorded_field: null, target_field: 'bundle world links world_static, target_cube', gap: 'no historical position is recorded for dynamic scene objects' }),
  ],
  status_meaning: { verified: 'the record and the fixed bundle agree on this mapping, and nothing had to be assumed', partially_verified: 'some parts of the mapping are attested', unverified: 'the value is recorded, but its frame, order, sign or convention is not attested', missing: 'the value a renderer would need is not recorded at all', not_required_for_pose: 'recorded data that this slice does not need to place the robot' },
  pose_readiness: { model_identity: 'match', mapping_valid_for_this_episode: true, mapped_targets_partially_or_fully_verified: '1/9', robot_state_can_be_rebuilt_without_assumptions: false, blocking_fields: ['base_position', 'base_orientation', 'gripper_joints', 'tcp_site_position', 'camera_extrinsics', 'dynamic_scene_objects'], next_round_owner: 'frontend assembly plus an attested base/gripper mapping source', note: 'resource identity, digests and joint-length checks pass; the remaining gaps are attestation gaps' },
  model_resource: { status: 'match', comparison: equalComparison, bundle_sha256: BUNDLE_SHA, content_identity_sha256: CONTENT_SHA, compiler: { name: 'MuJoCo', version: '3.1.6' },
    tcp_site: 'grasp_tcp',
    link_count: 71, arm_hinge_joints: ['joint1', 'joint2', 'joint3', 'joint4', 'joint5'], gripper_slide_joints: ['left_jaw_joint', 'right_jaw_joint'], wheel_hinge_joints: ['front_left_joint', 'rear_left_joint', 'front_right_joint', 'rear_right_joint'],
    root_joint: { name: 'base_link', parent_name: null, joint_name: 'base_free', joint_type: 'free', joint_axis: [0, 0, 1], local_position_m: [0, 0, 0.0556], local_orientation_xyzw: [0, 0, 0, 1] },
    assets: [{ asset_id: 'base_link', sha256: 'a'.repeat(64), media_type: 'model/stl', coordinate_space: 'mujoco_compiled_mesh', units: 'm', bytes: 525884 },
      { asset_id: 'link1', sha256: '28184761b2f9253022c1b9845ea8075461a8afc6352d397725c2c57a7563c0e7', media_type: 'model/stl', coordinate_space: 'mujoco_compiled_mesh', units: 'm', bytes: 1020984 }],
    live_native_scene_proxied: false, served_via: 'GET /api/v1/episodes/{episode_id}/model/assets/{asset_id} (frozen bundle only)' },
  rendering: { verified: false, frontend_assembly_done: false, note: 'this slice prepares and reports the mapping; it does not render' },
  not_proven: [{ target: 'base_position', status: 'unverified', gap: 'the body origin, frame and z convention is not attested' }, { target: 'dynamic_scene_objects', status: 'missing', gap: 'no historical position is recorded' }],
  capability_limits: ['no replay execution', 'no live geometry or Actual substitution', 'no fabricated dynamic object pose', 'no control, RESET, recording or physics stepping'],
  ...patch,
});

/** The same frame as the 18970 candidate answered it: per-capability readiness plus the FK check. */
const PART = (capability: string, status: string, extra: Record<string, unknown> = {}) => ({
  capability, status, requires: ['fixture requires'], pose_input_required: true, frontend_rule: `rule for ${capability}`, gaps: [], ...extra,
});
const m15eFixture = (patch: Partial<HistoryPoseDto> = {}): HistoryPoseDto => {
  const base = poseFixture();
  return poseFixture({
    ...base,
    mapping: base.mapping.map((row) => {
      if (row.target === 'arm_joint_positions') return { ...row, status: 'verified', gap: null, verified_basis: ['the recorded TCP position is reproduced from these five values through the frozen tree', 'the source chain addresses the joints by name'], draw_source: 'model radians, applied directly to the hinge joints', requires_user_angle_conversion: false };
      if (row.target === 'base_position') return { ...row, status: 'verified', gap: null, verified_basis: ['reproducing the recorded TCP position requires the base pose to be the base body’s world pose; the alternative convention is off by exactly the base body offset'] };
      if (row.target === 'base_orientation') return { ...row, status: 'verified', gap: null, verified_basis: ['the recorded TCP position is reproduced with this quaternion read in xyzw order'] };
      if (row.target === 'tcp_site_position') return { ...row, status: 'verified', gap: null, verified_basis: ['the recomputed site position matches the recorded one within the stated tolerance'] };
      return row;
    }),
    part_readiness: [
      PART('fixed_model_reference_assembly', 'ready', { pose_input_required: false, inputs_available: { identity: 'match', asset_count: 23, link_count: 71 }, frontend_rule: 'the frozen model may be assembled and shown for any frame of this Episode once the identity matches' }),
      PART('arm_local_pose', 'ready_with_caveats', { inputs_available: { recorded_length: 5, bundle_joints: ['joint1', 'joint2', 'joint3', 'joint4', 'joint5'], draw_in_model_radians: true }, frontend_rule: 'apply the recorded five values directly to the five arm hinges in model radians; do not claim an axis is exercised unless the samples actually move it' }),
      PART('base_pose_placement', 'ready_with_caveats', { frontend_rule: 'the base may be placed only with the caveat shown beside it', gaps: ['the MuJoCo quantity behind the field is declared in native source that cannot be tied to a single writer build'] }),
      PART('gripper_visual_appearance', 'conditional', { frontend_rule: 'the jaws may be posed only from the platform reference constants, which declare themselves not native-attested' }),
      PART('tcp_position_marker', 'ready_with_caveats', { frontend_rule: 'a point marker is allowed; it must not be drawn as an oriented frame' }),
      PART('tcp_orientation_frame', 'blocked', { frontend_rule: 'do not synthesise an oriented TCP frame' }),
      PART('camera_view_from_record', 'blocked', { frontend_rule: 'a record-derived camera pose is not allowed' }),
      PART('dynamic_scene_objects_from_record', 'blocked', { frontend_rule: 'keep world objects at the bundle’s compiled initial layout and label it' }),
      PART('wheel_pose_from_record', 'not_required', { frontend_rule: 'wheel angles are not needed to place the robot' }),
    ],
    part_status_meaning: { ready: 'inputs, resources and rule all present', ready_with_caveats: 'usable now with the named limits stated', conditional: 'usable only if the consumer accepts the named unattested assumption', blocked: 'a required input or attestation is absent', not_required: 'not needed to place the robot' },
    capability_summary: { usable_now: ['fixed_model_reference_assembly', 'arm_local_pose', 'base_pose_placement', 'tcp_position_marker'], usable_only_with_the_named_caveat: ['gripper_visual_appearance'], blocked: ['tcp_orientation_frame', 'camera_view_from_record', 'dynamic_scene_objects_from_record'],
      fixed_model_assembly_available: true, whole_robot_pose_rebuildable: false, escalation_forbidden: 'a usable part never upgrades into whole-robot rebuild', defaults_forbidden: 'no part may be filled with an assumed value',
      kinematic_agreement: 'consistent', abs_tcp_error_m: 1.6454375138849238e-14 },
    tcp_kinematic_cross_check: { status: 'computed', method: 'pure forward kinematics over the frozen bundle tree', recorded_tcp_position_m: TCP_POS, computed_tcp_position_m: [0.17753849921384954, 0.002461415763947644, 0.30179180035419056],
      abs_error_m: 1.6454375138849238e-14, verdict: 'consistent', consistency_tolerance_m: 0.005, tolerance_authority: 'stated by this slice to judge kinematic agreement; it is not a calibration limit and not a contract threshold',
      supported_hypotheses: ['recorded_pose_is_base_body_world_pose'], chain_links: ['base_link', 'link1'],
      hypotheses: [
        { hypothesis: 'recorded_pose_is_base_body_world_pose', status: 'computed', computed_tcp_position_m: [0.17753849921384954, 0.002461415763947644, 0.30179180035419056], abs_error_m: 1.6454375138849238e-14, verdict: 'consistent' },
        { hypothesis: 'recorded_pose_needs_the_bundle_base_offset', status: 'computed', computed_tcp_position_m: [0.17753849921384954, 0.002461415763947644, 0.35739180035419055], abs_error_m: 0.0556000000000042, verdict: 'inconsistent' },
      ] },
    version_binding: { reference_source: 'native working tree at commit a5cef52 (dirty)', chain_verified_in_reference_source: true, writer_identified: false, record_carries_no: ['native release id', 'build id', 'git commit'], conclusion: 'narrows the writer to that release family; it does not identify a single build' },
    model_vs_user_angles: { render_source: 'arm_model_qpos_rad applied to the bundle hinge joints, in model radians, with no conversion step', conversion_is_required_for_drawing: false,
      user_angle_formula: { q_user: 'q_user = (q_model - zero_model_rad) / user_direction', zero_model_rad: [0, 0, 0, -1.5707963267948966, 0], user_direction: [1, 1, 1, 1, 1], used_for: 'user-facing display and limit comparison only' },
      zero_pose_authority: { zero_status: 'user_defined_photo_pose_not_hardware_500', calibration_session: 'uncalibrated', authority: 'platform_reference_not_native_attested' } },
    pose_readiness: { ...base.pose_readiness!, mapped_targets_partially_or_fully_verified: '4/10', parts_ready: ['fixed_model_reference_assembly'], parts_conditional: ['gripper_visual_appearance'], parts_blocked: ['tcp_orientation_frame'], kinematic_agreement: 'consistent' },
    model_resource: { ...base.model_resource!, model_inputs_sha256: MODEL_INPUTS_SHA, compiled_scene_sha256: COMPILED_SCENE_SHA,
      world_links: [{ name: 'world_static', geom_types: ['box', 'plane'] }, { name: 'target_cube', geom_types: ['box'] }],
      tcp_parent_body_view: { name: 'guide_rod_link', joint_type: 'fixed' }, link_frames: "each link's local_transform is the model body offset relative to its parent body" },
    ...patch,
  });
};

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

describe('per-capability drive gate', () => {
  const part = (drive: ReturnType<typeof poseDriveOf>, capability: string) => drive.parts.find((row) => row.capability === capability);

  it('drives nothing while the reader offers no part_readiness at all', () => {
    const drive = poseDriveOf(poseFixture());
    expect(drive.joints).toEqual({});
    expect(drive.base).toBeNull();
    expect(drive.tcp).toBeNull();
    expect(part(drive, 'arm_local_pose')?.allowed).toBe(false);
    expect(part(drive, 'arm_local_pose')?.reason).toContain('reader 未返回该能力的就绪状态');
    expect(drive.summary).toContain('未放置');
  });

  it('drives the arm, the chassis and the TCP point once M1.5e marks those parts usable', () => {
    const drive = poseDriveOf(m15eFixture());
    expect(drive.joints).toEqual({ joint1: ARM_RAD[0], joint2: ARM_RAD[1], joint3: ARM_RAD[2], joint4: ARM_RAD[3], joint5: ARM_RAD[4] });
    expect(drive.base).toEqual({ position: BASE_POS, quaternion: BASE_QUAT });
    expect(drive.tcp).toEqual({ position: TCP_POS });
    expect(part(drive, 'arm_local_pose')?.allowed).toBe(true);
    expect(part(drive, 'base_pose_placement')?.allowed).toBe(true);
    expect(part(drive, 'tcp_position_marker')?.allowed).toBe(true);
    // Model radians verbatim: joint4 stays the recorded value, not that value plus π/2.
    expect(drive.joints.joint4).toBeCloseTo(-1.5696750090681135, 12);
    expect(drive.summary).toContain('whole_robot_pose_rebuildable=false');
  });

  it('places the base at the recorded world pose and never re-adds the compiled root offset', () => {
    const drive = poseDriveOf(m15eFixture());
    expect(drive.base?.position).toEqual(BASE_POS);
    expect(drive.base?.position[2]).not.toBeCloseTo(BASE_POS[2] + 0.0556, 12);
    expect(part(drive, 'base_pose_placement')?.reason).toContain('不再叠加初始根偏移');
    expect(part(drive, 'base_pose_placement')?.reason).toContain('writer_identified=false');
  });

  it('refuses the base when the reader supports no world-pose convention', () => {
    const fk = { ...m15eFixture().tcp_kinematic_cross_check!, supported_hypotheses: [] };
    const drive = poseDriveOf(m15eFixture({ tcp_kinematic_cross_check: fk }));
    expect(drive.base).toBeNull();
    expect(part(drive, 'base_pose_placement')?.reason).toContain('supported_hypotheses');
  });

  it('follows the readiness rule that a disagreeing kinematic cross-check blocks the base only', () => {
    // The reader's own base_pose_placement rule: "if the kinematic cross-check disagrees, do not place the base".
    const fk = { ...m15eFixture().tcp_kinematic_cross_check!, verdict: 'inconsistent' };
    const drive = poseDriveOf(m15eFixture({ tcp_kinematic_cross_check: fk }));
    expect(drive.base).toBeNull();
    expect(part(drive, 'base_pose_placement')?.reason).toContain('verdict=inconsistent');
    expect(Object.keys(drive.joints)).toHaveLength(5);
    expect(drive.tcp?.position).toEqual(TCP_POS);
    const missing = poseDriveOf(m15eFixture({ tcp_kinematic_cross_check: undefined }));
    expect(missing.base).toBeNull();
    expect(part(missing, 'base_pose_placement')?.reason).toContain('未返回 tcp_kinematic_cross_check');
  });

  it('draws the TCP as a position only: no orientation is ever synthesised', () => {
    const drive = poseDriveOf(m15eFixture());
    expect(Object.keys(drive.tcp ?? {})).toEqual(['position']);
    expect(part(drive, 'tcp_orientation_frame')?.allowed).toBe(false);
    expect(part(drive, 'tcp_orientation_frame')?.status).toBe('blocked');
  });

  it('treats zero angles as legal values and still drives them', () => {
    const zeros = [0, 0, 0, 0, 0];
    const dto = m15eFixture({ state: { ...m15eFixture().state, recorded_payload: { ...PAYLOAD, arm_model_qpos_rad: zeros } } });
    const drive = poseDriveOf(dto);
    expect(drive.joints).toEqual({ joint1: 0, joint2: 0, joint3: 0, joint4: 0, joint5: 0 });
    expect(part(drive, 'arm_local_pose')?.reason).toContain('0 是合法数值');
  });

  it('withholds a usable capability whose value count does not match the joint list', () => {
    const dto = m15eFixture({ state: { ...m15eFixture().state, recorded_payload: { ...PAYLOAD, arm_model_qpos_rad: [0.1, 0.2, 0.3] } } });
    const drive = poseDriveOf(dto);
    expect(drive.joints).toEqual({});
    expect(part(drive, 'arm_local_pose')?.reason).toContain('数量不符');
  });

  it('withholds a usable capability whose mapping is not verified', () => {
    const dto = m15eFixture({ mapping: m15eFixture().mapping.map((row) => row.target === 'arm_joint_positions' ? { ...row, status: 'partially_verified' } : row) });
    const drive = poseDriveOf(dto);
    expect(drive.joints).toEqual({});
    expect(part(drive, 'arm_local_pose')?.reason).toContain('不是 verified');
  });

  it('refuses to draw the arm from a user-angle space the reader did not exempt', () => {
    const dto = m15eFixture({ mapping: m15eFixture().mapping.map((row) => row.target === 'arm_joint_positions' ? { ...row, requires_user_angle_conversion: true } : row) });
    expect(poseDriveOf(dto).joints).toEqual({});
    const noFlag = m15eFixture({ mapping: m15eFixture().mapping.map((row) => row.target === 'arm_joint_positions' ? { ...row, draw_source: undefined, requires_user_angle_conversion: undefined } : row) });
    expect(poseDriveOf(noFlag).joints).toEqual({});
  });

  it('keeps a conditional capability off by default and never blocks the other parts for it', () => {
    const drive = poseDriveOf(m15eFixture());
    expect(part(drive, 'gripper_visual_appearance')?.allowed).toBe(false);
    expect(part(drive, 'gripper_visual_appearance')?.status).toBe('conditional');
    expect(part(drive, 'gripper_visual_appearance')?.reason).toContain('不默认开启');
    expect(Object.keys(drive.joints)).toHaveLength(5);
    expect(drive.base).not.toBeNull();
  });

  it('reports a state with no single selected record as it is, and drives nothing', () => {
    const dto = m15eFixture({ state: { ...m15eFixture().state, recorded_payload: null, single_state_selected: false, candidate_records: 2, multiple_candidates_note: 'two records claimed this key; none is chosen' } });
    const drive = poseDriveOf(dto);
    expect(drive.attributable).toBe(false);
    expect(drive.joints).toEqual({});
    expect(drive.base).toBeNull();
    expect(drive.tcp).toBeNull();
    expect(drive.summary).toContain('本帧状态不可归属');
    expect(poseStateText(dto)).toContain('recorded_payload=null（不按第一条候选绘制，不补 0，不沿用上一帧）');
  });

  it('keeps every capability’s own reason when the frame carries no single selected record', () => {
    const dto = m15eFixture({ state: { ...m15eFixture().state, recorded_payload: null, single_state_selected: false } });
    const drive = poseDriveOf(dto);
    expect([...drive.parts.map((row) => row.capability)].sort()).toEqual((m15eFixture().part_readiness ?? []).map((row) => row.capability).sort());
    expect(drive.parts.filter((row) => row.allowed).map((row) => row.capability)).toEqual(['fixed_model_reference_assembly']);
    expect(drive.parts.filter((row) => row.capability !== 'fixed_model_reference_assembly')
      .every((row) => row.reason.includes('本帧没有单一选中的状态记录'))).toBe(true);
    expect(drive.withheld.length).toBe(drive.parts.length - 1);
    expect(drive.parts.find((row) => row.capability === 'gripper_visual_appearance')?.status).toBe('conditional');
    expect(drive.parts.find((row) => row.capability === 'camera_view_from_record')?.status).toBe('blocked');
  });

  it('says so when no pose is readable at all', () => {
    expect(poseDriveOf(null).summary).toContain('未读取 robot-state');
    expect(poseDriveOf(null).parts).toEqual([]);
  });
});

describe('driven value readout (the numbers that moved the screen)', () => {
  /** The readout is asked for exactly what the gate handed the scene, so a row can only exist for a part
   *  that was really driven — never for one that was withheld. */
  const shownOf = (dto: HistoryPoseDto) => {
    const drive = poseDriveOf(dto);
    return { joints: drive.joints, baseApplied: Boolean(drive.base), tcpApplied: Boolean(drive.tcp) };
  };

  it('lists one row per driven joint plus the base and the TCP site, carrying the record values verbatim', () => {
    const rows = drivenValuesOf(m15eFixture(), shownOf(m15eFixture()));
    expect(rows.map((row) => row.name)).toEqual(['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'base_link', 'grasp_tcp']);
    expect(rows.slice(0, 5).map((row) => row.model)).toEqual(ARM_RAD.map((value) => String(value)));
    expect(rows[5].model).toBe(`${JSON.stringify(BASE_POS)} / ${JSON.stringify(BASE_QUAT)}`);
    expect(rows[5].display).toContain('未再叠加');
    expect(rows[5].display).toContain('0.0556');
    expect(rows[6].model).toBe(JSON.stringify(TCP_POS));
    expect(rows[6].display).toContain('不合成朝向');
    expect(rows[6].source).toContain('tcp_position_world_m');
  });

  it('keeps the drawn value in model radians and marks the user angle as display-only', () => {
    const rows = drivenValuesOf(m15eFixture(), shownOf(m15eFixture()));
    const joint4 = rows.find((row) => row.name === 'joint4')!;
    expect(joint4.model).toBe(String(ARM_RAD[3]));
    expect(Number(joint4.display.split('（')[0])).toBeCloseTo(ARM_RAD[3] + Math.PI / 2, 12);
    expect(joint4.display).toContain('未参与绘制');
    expect(joint4.source).toContain('arm_model_qpos_rad[3]');
    expect(joint4.source).toContain('arm_model_qpos_rad applied to the bundle hinge joints');
    const joint1 = rows.find((row) => row.name === 'joint1')!;
    expect(Number(joint1.display.split('（')[0])).toBeCloseTo(ARM_RAD[0], 12);
  });

  it('has no row for a withheld part: the base drops out with the kinematic check, the other parts keep theirs', () => {
    const dto = m15eFixture({ tcp_kinematic_cross_check: undefined });
    const rows = drivenValuesOf(dto, shownOf(dto));
    expect(rows.map((row) => row.kind)).toEqual(['arm', 'arm', 'arm', 'arm', 'arm', 'tcp']);
    expect(rows.some((row) => row.name === 'base_link')).toBe(false);
  });

  it('lists nothing at all when the reader offered no readiness, instead of showing the reference layout as values', () => {
    const dto = poseFixture();
    expect(drivenValuesOf(dto, shownOf(dto))).toEqual([]);
  });

  it('reports a zero model radian as a real row rather than as absence', () => {
    const dto = m15eFixture({ state: { ...m15eFixture().state, recorded_payload: { ...PAYLOAD, arm_model_qpos_rad: [0, 0, 0, 0, 0] } } });
    const rows = drivenValuesOf(dto, shownOf(dto));
    expect(rows.filter((row) => row.kind === 'arm').map((row) => row.model)).toEqual(['0', '0', '0', '0', '0']);
    expect(Number(rows[3].display.split('（')[0])).toBeCloseTo(Math.PI / 2, 12);
  });

  it('refuses to convert an axis the reader gave no zero or direction for, rather than guessing one', () => {
    const dto = m15eFixture({ model_vs_user_angles: { ...m15eFixture().model_vs_user_angles!, user_angle_formula: { q_user: 'q_user = (q_model - zero_model_rad) / user_direction', used_for: 'display only' } } });
    const rows = drivenValuesOf(dto, shownOf(dto)).filter((row) => row.kind === 'arm');
    expect(rows).toHaveLength(5);
    expect(rows.every((row) => row.display.startsWith('reader 未给'))).toBe(true);
    expect(rows.map((row) => row.model)).toEqual(ARM_RAD.map((value) => String(value)));
  });
});

describe('cross-frame motion coverage over visited frames only', () => {
  it('refuses to read motion out of a single visited frame: one value is no coverage', () => {
    const rows = motionCoverageOf([{ sample: 'a', values: { joint1: '0.1', base_link: '[0,0,0.05]' } }]);
    expect(rows.map((row) => [row.name, row.distinct, row.seenCount])).toEqual([['joint1', 1, 1], ['base_link', 1, 1]]);
    expect(rows.every((row) => row.verdict.includes('没有跨帧运动覆盖证据'))).toBe(true);
  });

  it('counts the distinct recorded values an item actually took across the visited frames', () => {
    const rows = motionCoverageOf([
      { sample: 'a', values: { joint1: '0.1', joint2: '0.5' } },
      { sample: 'b', values: { joint1: '0.2', joint2: '0.5' } },
      { sample: 'c', values: { joint1: '0.1', joint2: '0.7' } },
    ]);
    const joint1 = rows.find((row) => row.name === 'joint1')!;
    const joint2 = rows.find((row) => row.name === 'joint2')!;
    expect([joint1.distinct, joint1.seenCount, joint1.samples]).toEqual([2, 3, ['c', 'b']]);
    expect([joint2.distinct, joint2.seenCount]).toEqual([2, 3]);
    expect(joint1.verdict).toContain('有跨帧运动证据');
    expect(joint1.verdict).toContain('只对已访问帧成立');
  });

  it('keeps an item that a later visit does not drive at what it really saw, without inventing a zero', () => {
    const rows = motionCoverageOf([
      { sample: 'a', values: { joint1: '0.1', base_link: '[0,0,0.05]' } },
      { sample: 'b', values: { joint1: '0.2' } },
    ]);
    const base = rows.find((row) => row.name === 'base_link')!;
    expect([base.distinct, base.seenCount, base.samples]).toEqual([1, 1, ['a']]);
    expect(base.verdict).toContain('没有跨帧运动覆盖证据');
    expect(rows.find((row) => row.name === 'joint1')!.distinct).toBe(2);
  });

  it('revisiting a frame rewrites its own entry instead of stacking a second observation', () => {
    const once = mergeVisitedValues([], { sample: 'a', values: { joint1: '0.1' } });
    const again = mergeVisitedValues(once, { sample: 'a', values: { joint1: '0.9' } });
    expect(again).toEqual([{ sample: 'a', values: { joint1: '0.9' } }]);
    expect(motionCoverageOf(again).map((row) => [row.distinct, row.seenCount])).toEqual([[1, 1]]);
    expect(motionCoverageOf(mergeVisitedValues(once, { sample: 'b', values: { joint1: '0.1' } }))[0].seenCount).toBe(2);
    expect(mergeVisitedValues(once, { sample: '', values: { joint1: '0.1' } })).toBe(once);
  });

  it('lists nothing when no frame has been attributed yet, so the surface claims no coverage', () => {
    expect(motionCoverageOf([])).toEqual([]);
  });
});

describe('readiness, kinematic and identity projections', () => {
  it('lists every capability with its own status meaning and frontend_rule', () => {
    const rows = partReadinessOf(m15eFixture());
    expect(rows).toHaveLength(9);
    const arm = rows.find((row) => row.capability === 'arm_local_pose');
    expect(arm?.status).toBe('ready_with_caveats');
    expect(arm?.meaning).toContain('usable now');
    expect(arm?.rule).toContain('do not claim an axis is exercised');
    expect(arm?.inputs).toContain('draw_in_model_radians');
    expect(partReadinessOf(poseFixture())).toEqual([]);
  });
  it('carries the capability summary including the kinematic agreement and its error', () => {
    const text = capabilitySummaryText(m15eFixture());
    expect(text).toContain('kinematic_agreement=consistent');
    expect(text).toContain('abs_tcp_error_m=1.6454375138849238e-14');
    expect(text).toContain('whole_robot_pose_rebuildable=false');
    expect(text).toContain('gripper_visual_appearance');
    expect(capabilitySummaryText(poseFixture())).toContain('reader 未返回 capability_summary');
  });
  it('reports both tested root conventions with their own verdicts', () => {
    const fk = fkCrossCheckOf(m15eFixture());
    expect(fk?.verdict).toBe('consistent');
    expect(fk?.tolerance).toBe('0.005');
    expect(fk?.toleranceAuthority).toContain('not a calibration limit');
    expect(fk?.supported).toBe('recorded_pose_is_base_body_world_pose');
    expect(fk?.hypotheses.map((row) => row.verdict)).toEqual(['consistent', 'inconsistent']);
    expect(fk?.hypotheses[1].absError).toContain('0.0556');
    expect(fkCrossCheckOf(poseFixture())).toBeNull();
  });
  it('keeps the version-binding and model-versus-user limits visible', () => {
    expect(versionBindingText(m15eFixture())).toContain('writer_identified=false');
    expect(versionBindingText(m15eFixture())).toContain('git commit');
    expect(modelVsUserText(m15eFixture())).toContain('conversion_is_required_for_drawing=false');
    expect(modelVsUserText(m15eFixture())).toContain('uncalibrated');
    expect(versionBindingText(poseFixture())).toContain('reader 未返回 version_binding');
  });
  it('binds the assembled tree to the record by content identity, not only by mesh digests', () => {
    // The identity the frozen geometry清单 reports for the same compiled content the record names.
    const tree = { bundle_sha256: BUNDLE_SHA, content_identity_sha256: CONTENT_SHA, model_inputs_sha256: MODEL_INPUTS_SHA,
      compiled_scene_sha256: COMPILED_SCENE_SHA, link_count: 71, world_link_count: 2, arm_hinge_joints: ['joint1', 'joint2', 'joint3', 'joint4', 'joint5'] };
    const rows = treeBindingRowsOf(m15eFixture(), tree);
    expect(rows).toHaveLength(7);
    expect(rows.every((row) => row.equal === 'true')).toBe(true);
    // Same meshes, different tree content: the content identity is what catches it.
    const swapped = treeBindingRowsOf(m15eFixture(), { ...tree, content_identity_sha256: 'd'.repeat(64) });
    expect(swapped.filter((row) => row.equal === 'false').map((row) => row.field)).toEqual(['content_identity_sha256']);
    const reordered = treeBindingRowsOf(m15eFixture(), { ...tree, arm_hinge_joints: ['joint2', 'joint1', 'joint3', 'joint4', 'joint5'] });
    expect(reordered.find((row) => row.field === 'arm_hinge_joints')?.equal).toBe('false');
    expect(treeBindingRowsOf(m15eFixture(), { ...tree, world_link_count: 1 }).find((row) => row.field === 'world_link_count')?.equal).toBe('false');
    // The 18969 record published neither of the two further digests, so those rows read null both sides.
    const legacyRows = treeBindingRowsOf(poseFixture(), tree);
    expect(legacyRows.find((row) => row.field === 'model_inputs_sha256')?.equal).toBe('false');
    expect(legacyRows.find((row) => row.field === 'bundle_sha256')?.equal).toBe('true');
    expect(treeBindingRowsOf(m15eFixture(), null)).toEqual([]);
  });
  it('keeps the mapping rows with their own status meanings, basis and gaps', () => {
    const rows = mappingRowsOf(poseFixture());
    expect(rows.length).toBeGreaterThanOrEqual(9);
    const arm = rows.find((row) => row.target === 'arm_joint_positions');
    expect(arm?.statusMeaning).toContain('some parts of the mapping are attested');
    expect(arm?.formula).toContain('platform_reference_not_native_attested');
    expect(arm?.noDefault).toBe('true');
    const verified = mappingRowsOf(m15eFixture()).find((row) => row.target === 'arm_joint_positions');
    expect(verified?.basis).toContain('reproduced from these five values');
    expect(verified?.conversion).toContain('requires_user_angle_conversion=false');
    expect(mappingRowsOf(null)).toEqual([]);
  });
  it('passes the readiness, rendering, not_proven and capability words through', () => {
    expect(poseReadinessText(poseFixture())).toContain('robot_state_can_be_rebuilt_without_assumptions=false');
    expect(poseReadinessText(m15eFixture())).toContain('parts_conditional=gripper_visual_appearance');
    expect(poseReadinessText(m15eFixture())).toContain('kinematic_agreement=consistent');
    expect(renderingText(poseFixture())).toContain('rendering.verified=false');
    expect(notProvenText(poseFixture())).toContain('dynamic_scene_objects[missing]');
    expect(poseBoundaryText(poseFixture())).toContain('no fabricated dynamic object pose');
  });
  it('lists the identity comparison and the asset digests the tree is gated on', () => {
    const comparison = comparisonRowsOf(poseFixture());
    expect(comparison).toHaveLength(4);
    expect(comparison.every((row) => row.equal === 'true')).toBe(true);
    expect(modelAssetRowsOf(poseFixture()).map((row) => row.assetId)).toEqual(['base_link', 'link1']);
    expect(modelResourceText(poseFixture())).toContain('live_native_scene_proxied=false');
    expect(modelResourceText(poseFixture())).toContain('base_link/base_free/free');
    expect(comparisonRowsOf(null)).toEqual([]);
  });
});

describe('link-by-link binding of the nodes the record itself names', () => {
  const mr = () => m15eFixture().model_resource!;
  type TreeNode = { name: string; parent_name?: string | null; joint_name?: string | null; joint_type?: string | null };
  /** A tree that agrees with every name/joint the record declares, built from the record's own lists. */
  const agreeingTree = (): TreeNode[] => [
    { name: 'base_link', parent_name: 'universe', joint_name: 'base_free', joint_type: 'free' },
    ...(mr().arm_hinge_joints ?? []).map((joint) => ({ name: `link_${joint}`, joint_name: joint, joint_type: 'hinge' })),
    ...(mr().gripper_slide_joints ?? []).map((joint) => ({ name: `link_${joint}`, joint_name: joint, joint_type: 'slide' })),
    ...(mr().wheel_hinge_joints ?? []).map((joint) => ({ name: `link_${joint}`, joint_name: joint, joint_type: 'hinge' })),
    { name: 'guide_rod_link', joint_type: 'fixed' },
    ...(mr().world_links ?? []).map((link) => ({ name: link.name })),
  ];

  it('binds every declared node when the tree carries them', () => {
    const rows = linkBindingRowsOf(m15eFixture(), agreeingTree());
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.filter((row) => row.equal !== 'true')).toEqual([]);
    expect(rows.some((row) => row.name === 'guide_rod_link' && row.field === 'joint_type' && row.equal === 'true')).toBe(true);
    expect(rows.filter((row) => row.field.startsWith('joint_in:')).length)
      .toBe((mr().arm_hinge_joints ?? []).length + (mr().gripper_slide_joints ?? []).length + (mr().wheel_hinge_joints ?? []).length);
  });

  it('catches a changed joint type on a named node even when every mesh digest still matches', () => {
    const rows = linkBindingRowsOf(m15eFixture(), agreeingTree().map((node) => node.name === 'guide_rod_link' ? { ...node, joint_type: 'hinge' } : node));
    expect(rows.filter((row) => row.equal === 'false').map((row) => `${row.name}/${row.field}`)).toEqual(['guide_rod_link/joint_type']);
  });

  it('catches a rewired parent when the record itself declares one', () => {
    const declaring = { ...m15eFixture(), model_resource: { ...mr(), tcp_parent_body_view: { name: 'guide_rod_link', parent_name: 'link2', joint_type: 'fixed' } } };
    const agreeing = linkBindingRowsOf(declaring, agreeingTree().map((node) => node.name === 'guide_rod_link' ? { ...node, parent_name: 'link2' } : node));
    expect(agreeing.filter((row) => row.name === 'guide_rod_link' && row.field === 'parent_name').map((row) => row.equal)).toEqual(['true']);
    const rewired = linkBindingRowsOf(declaring, agreeingTree().map((node) => node.name === 'guide_rod_link' ? { ...node, parent_name: 'link3' } : node));
    const row = rewired.find((item) => item.name === 'guide_rod_link' && item.field === 'parent_name');
    expect({ equal: row?.equal, history: row?.history, tree: row?.tree }).toEqual({ equal: 'false', history: 'link2', tree: 'link3' });
    expect(rewired.filter((item) => item.equal === 'false').map((item) => `${item.name}/${item.field}`)).toEqual(['guide_rod_link/parent_name']);
  });

  it('names a declared link the tree does not carry instead of drawing a partial match', () => {
    const rows = linkBindingRowsOf(m15eFixture(), agreeingTree().filter((node) => node.name !== 'base_link'));
    expect(rows.filter((row) => row.equal === 'false').map((row) => `${row.name}/${row.field}`)).toEqual(['base_link/link_exists']);
    expect(rows.find((row) => row.field === 'link_exists')?.tree).toContain('没有同名 link');
  });

  it('reports a joint name the record declares but the tree lacks', () => {
    const rows = linkBindingRowsOf(m15eFixture(), agreeingTree().filter((node) => node.joint_name !== 'joint5'));
    expect(rows.some((row) => row.name === 'joint5' && row.field === 'joint_in:arm_hinge_joints' && row.equal === 'false')).toBe(true);
  });

  it('compares only what the record declares, and stays silent without either side', () => {
    const rows = linkBindingRowsOf(m15eFixture(), agreeingTree());
    expect(rows.filter((row) => row.name === 'base_link' && row.field === 'parent_name')).toEqual([]);
    expect(rows.filter((row) => row.name === 'base_link' && row.field === 'joint_name').map((row) => row.equal)).toEqual(['true']);
    expect(linkBindingRowsOf(null, agreeingTree())).toEqual([]);
    expect(linkBindingRowsOf(m15eFixture(), null)).toEqual([]);
  });

  it('rejects every node the record declares when the tree carries none of them', () => {
    const rows = linkBindingRowsOf(m15eFixture(), []);
    const declaredLinks = [mr().root_joint?.name, mr().tcp_parent_body_view?.name, mr().end_effector_link?.name,
      ...(mr().camera_link_chain ?? []).map((node) => node.name), ...(mr().world_links ?? []).map((node) => node.name),
    ].filter((name): name is string => Boolean(name));
    const jointLists: Record<string, string[] | undefined> = {
      arm_hinge_joints: mr().arm_hinge_joints, gripper_slide_joints: mr().gripper_slide_joints,
      gripper_other_joints_in_bundle: mr().gripper_other_joints_in_bundle, wheel_hinge_joints: mr().wheel_hinge_joints,
    };
    const expected = [
      ...declaredLinks.map((name) => `${name}/link_exists`),
      ...Object.entries(jointLists).flatMap(([list, names]) => (names ?? []).map((joint) => `${joint}/joint_in:${list}`)),
    ].sort();
    expect(rows.map((row) => `${row.name}/${row.field}`).sort()).toEqual(expected);
    expect(declaredLinks.length).toBeGreaterThan(0);
    expect(rows.every((row) => row.equal === 'false')).toBe(true);
    expect(rows.filter((row) => row.field === 'link_exists').every((row) => row.tree.includes('没有同名 link'))).toBe(true);
    expect(rows.filter((row) => row.field.startsWith('joint_in:')).every((row) => row.tree.includes('没有同名关节'))).toBe(true);
  });
});
