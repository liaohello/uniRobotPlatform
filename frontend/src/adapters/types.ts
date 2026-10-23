// Frontend projections of CT-STATE / CT-COMMAND / CT-TIME-FRAMES and native mobilecar-1.0.
// These view models are not a second public wire contract. See docs/backend-gaps.md.
export type Vec3 = [number, number, number];
export type Quat = [number, number, number, number];
export interface Transform { position_m: Vec3; orientation_xyzw: Quat }
export interface SceneGeom { name: string; geom_type: string; size_m: number[]; local_transform: Transform; rgba: number[]; mesh_asset_id: string | null; collision: boolean; group: number }
export interface SceneLink { name: string; parent_name: string | null; joint_name: string | null; joint_type: string; joint_axis: Vec3; local_transform: Transform; geoms: SceneGeom[] }
export interface SceneManifest { contract_version: string; model_id: string; model_sha256: string; scene_id: string; links: SceneLink[]; world_links: SceneLink[]; mesh_assets: { asset_id: string; uri: string; sha256: string }[]; camera_ids: string[]; tcp_site: string; source: string }
export interface NativeSnapshot {
  run_id: string; backend_generation: number; episode_id: string;
  sim_time_s: number; backend_monotonic_s: number; wall_utc: string; clock_id: string; control_tick_id: string;
  base: { position_world_sim_m: Vec3; orientation_world_sim_xyzw: Quat };
  arm: { user_joint_positions_rad: number[]; model_joint_positions_rad: number[]; model_limits_rad: [number, number][] };
  tcp: { frame_id: string; position_m: Vec3; orientation_xyzw: Quat };
  model_joint_positions_rad: Record<string, number>;
  diagnostics: Record<string, unknown>;
}
export interface Capabilities { arm_joint_names: string[]; arm_user_limits_rad: [number, number][]; sensor_streams: string[]; tcp_orientation_is_soft: boolean; camera_parent_body: string; tcp_parent_body: string }
export interface ArmSpec { user_coordinates: { zero_model_rad: number[]; direction: number[] }; tcp: { body: string; position: Vec3 }; mimic: Record<string, { joint: string; multiplier: number; offset: number }>; limits: Record<string, [number, number]> }
export type SourceKind = 'frozen' | 'mock' | 'history' | 'live';
export interface SourceIdentity { kind: SourceKind; label: string; captured_at_utc: string; identity: { run_id: string; backend_generation: number; episode_id: string }; interface_profile: string; is_platform_session: boolean; is_episode_replay: boolean }
export interface ViewSample { scene: SceneManifest; actual: NativeSnapshot; capabilities: Capabilities; armSpec: ArmSpec; source: SourceIdentity }
export interface LocalTarget { mode: 'joint' | 'tcp'; revision: number; jointModelRad: Record<string, number>; tcpWorldM: Vec3; frame: 'world_sim'; preview: 'joint-pose' | 'local-position-ik' | 'unreachable'; residualM: number | null }
export interface TimelineEvent { id: number; kind: 'local'; label: string; time: number }
export interface WorkbenchService { load(signal: AbortSignal): Promise<ViewSample>; submit(): Promise<{ status: 'unsupported'; reason: string }>; dispose(): void }
