// Frontend projections of CT-STATE / CT-COMMAND / CT-TIME-FRAMES and native mobilecar-1.0.
// These view models are not a second public wire contract. See docs/backend-gaps.md.
export type Vec3 = [number, number, number];
export type Quat = [number, number, number, number];
export interface Transform { position_m: Vec3; orientation_xyzw: Quat }
export interface SceneGeom { name: string; geom_type: string; size_m: number[]; local_transform: Transform; rgba: number[]; mesh_asset_id: string | null; collision: boolean; group: number; contype?: number; conaffinity?: number }
export interface SceneLink { name: string; parent_name: string | null; joint_name: string | null; joint_type: string; joint_axis: Vec3; local_transform: Transform; geoms: SceneGeom[] }
export interface MeshAsset { asset_id:string; uri:string; sha256:string; coordinate_space?:'mujoco_compiled_mesh'|'legacy_raw_stl'; units?:'m'; mesh_preprocessing_applied?:boolean; source_sha256?:string; source_mesh_name?:string }
export interface SceneManifest { contract_version: string; model_id: string; model_sha256: string; scene_id: string; links: SceneLink[]; world_links: SceneLink[]; mesh_assets: MeshAsset[]; camera_ids: string[]; tcp_site: string; source: string }
export interface NativeSnapshot {
  run_id: string; backend_generation: number; episode_id: string;
  sim_time_s: number; backend_monotonic_s: number; wall_utc: string; clock_id: string; control_tick_id: string;
  base: { position_world_sim_m: Vec3; orientation_world_sim_xyzw: Quat };
  arm: { user_joint_positions_rad: number[]; model_joint_positions_rad: number[]; model_limits_rad: [number, number][] };
  tcp: { frame_id: string; position_m: Vec3; orientation_xyzw: Quat };
  model_joint_positions_rad: Record<string, number>;
  gripper: { width_m: number; model_drive_position_rad: number };
  diagnostics: Record<string, unknown>;
}
export interface Capabilities { arm_joint_names: string[]; arm_user_limits_rad: [number, number][]; sensor_streams: string[]; tcp_orientation_is_soft: boolean; camera_parent_body: string; tcp_parent_body: string;
 backend_kind?: string; arm_velocity_limits_rad_s?: number[]; gripper_min_width_m?: number; gripper_max_width_m?: number;
 base_linear_limit_m_s?: number; base_yaw_limit_rad_s?: number; tcp_position_tolerance_m?: number; supported_commands?: string[] }
export interface ArmSpec { user_coordinates: { zero_model_rad: number[]; direction: number[] }; tcp: { body: string; position: Vec3 }; mimic: Record<string, { joint: string; multiplier: number; offset: number }>; limits: Record<string, [number, number]> }
export type SourceKind = 'frozen' | 'mock' | 'history' | 'live';
export interface SourceIdentity { kind: SourceKind; label: string; captured_at_utc: string; identity: { run_id: string; backend_generation: number; episode_id: string }; interface_profile: string; is_platform_session: boolean; is_episode_replay: boolean }
export interface RuntimeIdentity { run_id: string; backend_generation: number; episode_id: string }
export interface ResourceIdentity { contract_version: string; model_id: string; model_sha256: string; scene_id: string }
export interface BackendTarget {
 base_velocity: { frame_id: string; vx_m_s: number; vy_m_s: number; wz_rad_s: number };
 user_joint_positions_rad: number[]; model_joint_positions_rad: number[];
 gripper_width_m: number; gripper_model_drive_position_rad:number; command_id: null; tcp: null;
}
export interface LiveMetadata {
 identityKey: string; resource: ResourceIdentity; retrievedAt: string; feedbackTimeS: number;
 target: BackendTarget; worldPoseSemantics: string;
 objects: { object_id: string; kind: string; native_name: string; parent_object_id: string|null }[];
 authority: { base_owner_session_id: string|null; arm_owner_session_id: string|null; authorizes_caller: false; lease_status: string };
 recording: { status: string; command_capture_ready: boolean; recording_segment_id: string|null };
 // Verbatim envelope capability flags. These gate the Session preparation UI;
 // false values must never be rendered as ready.
 session: { ready: boolean; platformSessionId: string|null; commandsAvailable: boolean; recordingAvailable: boolean; replayAvailable: boolean;
  resourceMatchesPin: boolean; deployedContentVerified: boolean; recordingRequiredForMotion: boolean; contractVersion: string };
 sensors: { kind: string; fresh: boolean; quality: string; sample_id: string|null; frame_id: null }[];
 kinematicProfile: string; geometryProvenance?:Record<string,unknown>;
}
export interface ViewSample { scene: SceneManifest; actual: NativeSnapshot; capabilities: Capabilities; armSpec: ArmSpec|null; source: SourceIdentity; live?: LiveMetadata }
export interface MonitorStatus { state: 'loading'|'current'|'stale'|'reloading'|'frozen'; message: string; receivedAt: number|null; requestMs: number|null; snapshots: number; intervalMs: number }
export interface LocalTarget { mode: 'joint' | 'tcp'; revision: number; jointModelRad: Record<string, number>; tcpWorldM: Vec3; frame: 'world_sim'; preview: 'joint-pose' | 'local-position-ik' | 'unreachable'; residualM: number | null }
export interface TimelineEvent { id: number; kind: 'local'; label: string; time: number }
export interface WorkbenchService { load(signal: AbortSignal): Promise<ViewSample>; refresh?(sample: ViewSample, signal: AbortSignal): Promise<ViewSample>; submit(): Promise<{ status: 'unsupported'; reason: string }>; dispose(): void }
