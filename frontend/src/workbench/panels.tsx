import { useEffect, useRef, useState } from 'react';
import { useWorkbench } from '../app/context';
import { deg,rad,userJoint } from '../app/state';
import { WorkbenchScene } from '../viewport/workbench-scene';
import type { Vec3 } from '../adapters/types';
import { uiSnapshot } from '../app/ui-state';
import { MapWaypointEditor } from '../map/MapWaypointEditor';
import { Icon } from './Icon';
export function HierarchyPanel(){
 const w=useWorkbench();const [search,setSearch]=useState('');const [baseOpen,setBaseOpen]=useState(false);
 const links=w.sample.scene.links;const names=w.sample.capabilities.arm_joint_names;
 const armLinks=links.filter(l=>names.includes(l.joint_name??''));
 const others=links.filter(l=>!armLinks.includes(l));
 const matches=(name:string)=>name.toLowerCase().includes(search.toLowerCase());
 const row=(name:string,label:string,detail:string,level=0)=><button key={name} type="button" className={`tree-row ${w.selected===name?'selected':''}`} style={{paddingLeft:12+level*13}} aria-pressed={w.selected===name} data-object={name} onClick={()=>w.select(name)}><Icon name={detail==='joint'?'joint':'cube'} size={14}/><span>{label}</span>{detail==='joint'&&<small>Joint</small>}</button>;
 return <div className="panel hierarchy"><div className="search"><Icon name="tree" size={15}/><input aria-label="搜索对象" value={search} onChange={e=>setSearch(e.target.value)} placeholder="搜索对象 / 关节"/></div><div className="tree-scroll"><div className="tree-caption">ROBOT <span>{links.length} links</span></div>{row('arm','LanderPi · 机械臂','arm')}{armLinks.filter(l=>matches(l.name+' '+l.joint_name)).map((l,i)=>row(l.name,`J${i+1} · ${l.name}`,'joint',1))}
 <button className="tree-row branch" aria-expanded={baseOpen} onClick={()=>setBaseOpen(!baseOpen)}><Icon name="chevron" size={12} style={{transform:baseOpen?'rotate(90deg)':undefined}}/><span>底盘与附属部件</span><small>{others.length}</small></button>
 {(baseOpen||search)&&others.filter(l=>matches(l.name)).map(l=>row(l.name,l.name,'link',1))}<div className="tree-caption">SCENE · 编译初态 <span>{w.sample.scene.world_links.length} objects</span></div>{w.sample.scene.world_links.filter(l=>matches(l.name)).map(l=>row(l.name,l.name==='target_cube'?'目标方块':l.name==='world_static'?'场景静态基座':l.name,'world'))}</div>
 <div className="tree-footer"><span className="status-dot amber"/>选择只改变观察对象<p>Arm / Active Joint / Owner 独立。模型自由度以原生数据为准。</p></div></div>;
}
export function ViewportPanel(){
 const w=useWorkbench();const host=useRef<HTMLDivElement>(null);const latest=useRef(w);latest.current=w;const [error,setError]=useState('');const [layers,setLayers]=useState(false);const [navOpen,setNavOpen]=useState(false);
 useEffect(()=>{
   let view:WorkbenchScene;
   try {view=new WorkbenchScene(host.current!,w.sample,{
     select:id=>latest.current.select(id),joint:(name,value)=>latest.current.editJoint(name,value),tcp:p=>latest.current.editTcp(p),notice:m=>latest.current.setNotice(m),interaction:active=>latest.current.setInteracting(active),assetError:m=>latest.current.setAssetError(m),
   });}catch(e){setError(`3D 初始化失败：${(e as Error).message}`);return;}
   w.view.current=view;view.setSelection(latest.current.selected);view.setTool(latest.current.tool);view.syncTarget(latest.current.target);view.setLayers(latest.current.ghost,latest.current.world);
   if(new URLSearchParams(location.search).has('inspect'))Object.assign(window,{__workbenchInspect:()=>({scene:view.inspect(),target:latest.current.target,actual:latest.current.sample.actual,selected:latest.current.selected,source:latest.current.sample.source,live:latest.current.sample.live,monitor:latest.current.monitor,assetError:latest.current.assetError,ui:{...uiSnapshot,canvas:canvasFacts()},interacting:latest.current.interacting})});
   function canvasFacts(){const rect=view.renderer.domElement.getBoundingClientRect();return {width:rect.width,height:rect.height};}
   return ()=>{view.dispose();if(w.view.current===view)w.view.current=null;if(new URLSearchParams(location.search).has('inspect'))delete (window as unknown as Record<string,unknown>).__workbenchInspect;};
 },[w.sample.scene]);
 useEffect(()=>{w.view.current?.updateActual(w.sample);w.view.current?.setLayers(w.ghost,w.world);},[w.sample.actual]);
 useEffect(()=>{w.view.current?.setSelection(w.selected);},[w.selected]);
 useEffect(()=>{w.view.current?.setTool(w.tool);},[w.tool]);
 useEffect(()=>{w.view.current?.syncTarget(w.target);},[w.target]);
 useEffect(()=>{w.view.current?.setLayers(w.ghost,w.world);},[w.ghost,w.world,w.target]);
 const zoom=(factor:number)=>{const applied=w.view.current?.zoomBy(factor);if(applied===false)w.setNotice('相机已到距离边界；这是观察相机缩放，不是模型缩放。');};
 return <div className="viewport-panel">
   <div className="viewport-toolbar">
     <div className="tool-group">{(['select','joint','tcp'] as const).map((tool,i)=><button key={tool} title={tool!=='select'&&!w.sample.armSpec?(w.sample.live?.kinematics.reason||'缺少版本化运动学元数据，本地预览禁用'):undefined} className={w.tool===tool?'active':''} aria-pressed={w.tool===tool} disabled={w.interacting||(tool!=='select'&&!w.sample.armSpec)} onClick={()=>{w.setTool(tool);if(tool==='joint'&&!w.sample.capabilities.arm_joint_names.includes(w.sample.scene.links.find(l=>l.name===w.selected)?.joint_name??''))w.select('link1');}}><Icon name={tool==='select'?'cursor':tool}/>{['选择','Joint','TCP'][i]}</button>)}</div>
     <span className="tool-sep"/>
     <div className="tool-group icon-group" role="group" aria-label="观察相机">
       <button aria-label="放大" title="放大：相机推近（等同滚轮向前）" onClick={()=>zoom(0.8)}><Icon name="zoomIn" size={15}/></button>
       <button aria-label="缩小" title="缩小：相机拉远（等同滚轮向后）" onClick={()=>zoom(1.25)}><Icon name="zoomOut" size={15}/></button>
       <button aria-label="适配模型" title="适配模型：框住机器人，保持当前视角方向" onClick={()=>{if(!w.view.current?.fitModel())w.setNotice('没有可用的机器人几何，无法适配模型。');}}><Icon name="fit" size={15}/></button>
       <button aria-label="恢复全景" title="恢复全景：框住机器人与场景对象，保持当前视角方向" onClick={()=>{if(!w.view.current?.fitScene())w.setNotice('场景为空，无法恢复全景。');}}><Icon name="reset" size={15}/></button>
       <button aria-label="聚焦选中对象" title="聚焦选中对象（视口内按 F）" onClick={()=>w.view.current?.focusSelection()}><Icon name="focus" size={15}/></button>
     </div>
     <span className="tool-sep"/>
     <div className="tool-group view-group" role="group" aria-label="标准视角">{(['front','side','top'] as const).map((preset,i)=><button key={preset} title={['车头视图：world_sim +X，从车前方看','车侧视图：world_sim −Y，从车右方看','顶视图：world_sim +Z'][i]} onClick={()=>w.view.current?.standardView(preset)}>{['车头','车侧','顶视'][i]}</button>)}</div>
     <span className="toolbar-spacer"/>
     <button className={navOpen?'active':''} aria-expanded={navOpen} aria-label="导航小窗" title="导航小窗：当前草案或明确选中的固定版本；查看不等于采用或执行" onClick={()=>setNavOpen(!navOpen)}>导航</button>
     <button className={layers?'active':''} aria-expanded={layers} aria-label="图层选项" title="图层选项：Ghost 候选与场景对象" onClick={()=>setLayers(!layers)}><Icon name="layers" size={15}/></button>
   </div>
   <div className="canvas-area">
     <div className="canvas-host" ref={host}/>{error&&<div role="alert" className="viewport-error">{error}</div>}
     <div className="viewport-hud">
       <span className="hud-chip"><span className={`status-dot ${w.monitor.state==='stale'?'amber':'green'}`}/>{w.sample.live?'实时只读 Actual':'冻结场景'} · world_sim · m</span>
       {w.target&&<span className="hud-chip target"><i className="target-color"/>本地 Target r{w.target.revision}<button aria-label="取消本地目标" title="取消本地目标（Esc）" onClick={w.cancelTarget}><Icon name="close" size={11}/></button></span>}
       {w.interacting&&<span className="hud-chip gesture">拖动中 · Orbit 已锁定</span>}
     </div>
     {navOpen&&<div className="navigation-mini" data-nav-mini data-nav-source={w.route.viewed?`version-${w.route.viewed.version}`:w.route.serverDraft?'server-draft':'local-unbound'} data-nav-map-mode={w.route.offlineMode?'offline-test':'backend'}>
       <div className="navigation-mini-head"><b>导航路线</b><span>{w.route.viewed?`固定版本 ${w.route.viewed.version} · ${w.route.viewed.contentDigest.slice(0,12)} · 查看不等于采用`:w.route.serverDraft?`服务端草案 r${w.route.serverDraft.draftRevision} · ${w.route.dirty?'本地有未保存编辑':'与服务端一致'}`:'本地草案 · 未绑定服务端'}</span><button aria-label="关闭导航小窗" onClick={()=>setNavOpen(false)}><Icon name="close" size={12}/></button></div>
       <MapWaypointEditor map={w.route.viewed?w.route.selectedMap??w.route.working.map:w.route.working.map} waypoints={w.route.viewed?w.route.viewed.waypoints:w.route.working.waypoints} selectedId={null} readOnly compact/>
       <div className="navigation-mini-meta"><span>PointGoal {(w.route.viewed?w.route.viewed.waypoints:w.route.working.waypoints).length} 个 · 箭头来自{w.route.viewed?'该固定版本':'当前草案'}</span><span>执行反馈：无（本轮不导航）</span><span>编辑连线，非规划安全路径 · navigation_eligible={String(w.route.viewed?w.route.viewed.navigationEligible:w.route.serverDraft?w.route.serverDraft.validation.navigationEligible:false)} · execution_supported={String(w.route.viewed?w.route.viewed.executionSupported:w.route.serverDraft?w.route.serverDraft.validation.executionSupported:false)}</span></div>
     </div>}
     {layers&&<div className="layer-menu"><label><input type="checkbox" checked={w.ghost} onChange={e=>w.setGhost(e.target.checked)}/>显示 Ghost 候选</label><label><input type="checkbox" checked={w.world} onChange={e=>w.setWorld(e.target.checked)}/>显示场景对象</label><small>虚线仅连接 Actual 与 Target，未规划。</small></div>}
     <div className="viewport-legend"><span><i className="actual-color"/>Actual · {w.sample.live?(w.monitor.state==='stale'?'陈旧':'后端反馈'):'冻结实测'}</span><span><i className="target-color"/>Target · 本地草案</span><span><i className="ghost-color"/>Ghost · 未校验候选</span></div>
     <div className="viewport-bottom"><span>{w.tool==='select'?'空白拖动旋转 · 右键平移 · 滚轮缩放 · 双击部件选 Arm':w.tool==='joint'?'拖动关节环编辑单个目标 · 不提交运动':'拖动轴 / 平面编辑 TCP 位置 · world_sim'}<br/><b>F 聚焦 · Esc 取消本地目标 · 工具栏 ± 可缩放相机</b></span><span className="axis-key"><b>X</b><b>Y</b><b>Z</b><small>MuJoCo Z↑</small></span></div>
   </div>
 </div>;
}
function NumericInput({label,value,onValue,min,max,step='any'}:{label:string;value:number;onValue:(value:number)=>void;min?:number;max?:number;step?:string|number}){
 const [text,setText]=useState(String(Number(value.toFixed(5))));const focused=useRef(false);
 useEffect(()=>{if(!focused.current)setText(String(Number(value.toFixed(5))));},[value]);
 const invalid=text.trim()!=='' && (!Number.isFinite(Number(text)) || (min!==undefined&&Number(text)<min) || (max!==undefined&&Number(text)>max));
 return <input type="number" aria-label={label} aria-invalid={invalid} min={min} max={max} step={step} value={text} onFocus={()=>{focused.current=true;}} onChange={e=>{setText(e.target.value);if(e.target.value!==''&&Number.isFinite(e.target.valueAsNumber))onValue(e.target.valueAsNumber);}} onBlur={()=>{focused.current=false;if(text.trim()===''||invalid)setText(String(Number(value.toFixed(5))));}}/>;
}
function Field({label,value,onChange,min,max,step='any',suffix}:{label:string;value:number;onChange:(value:number)=>void;min?:number;max?:number;step?:string|number;suffix:string}){
 return <label className="number-field"><span>{label}</span><NumericInput label={label} value={value} min={min} max={max} step={step} onValue={onChange}/><small>{suffix}</small></label>;
}
export function InspectorPanel(){
 const w=useWorkbench();const {sample,target}=w;const [units,setUnits]=useState<'deg'|'rad'>('deg');const selectedLink=sample.scene.links.find(l=>l.name===w.selected)??sample.scene.world_links.find(l=>l.name===w.selected);const activeJoint=selectedLink?.joint_name;
 const p=target?.tcpWorldM??sample.actual.tcp.position_m;
 return <div className="panel inspector"><div className="inspector-scroll">
 <div className="inspector-object"><div className="object-icon"><Icon name={w.selected==='arm'?'joint':'cube'} size={20}/></div><div><b>{w.selected==='arm'?'LanderPi Arm':w.selected??'未选中对象'}</b><small>{selectedLink?.joint_name??'观察选择'} · Owner 未接入</small></div></div>
 <section><h3><span className="status-dot green"/>Actual <small>{sample.live?(w.monitor.state==='stale'?'陈旧 · 只读':'后端反馈 · 只读'):'冻结实测 · 只读'}</small></h3><div className="xyz-readout">{sample.actual.tcp.position_m.map((v,i)=><div key={i}><small>{['X','Y','Z'][i]} / m</small><strong data-actual-axis={i}>{v.toFixed(4)}</strong></div>)}</div><p className="subtle">TCP · {sample.actual.tcp.frame_id} · 夹爪 {sample.actual.gripper.width_m.toFixed(4)} m / {sample.actual.gripper.model_drive_position_rad.toFixed(4)} rad<br/>采样 {sample.actual.wall_utc.slice(0,19).replace('T',' ')+' UTC'}</p></section>
 <section><h3><span className="status-dot amber"/>本地 Target <small>{target?`本地 r${target.revision}`:'尚未编辑'}</small></h3><div className="target-tabs"><button className={w.tool==='joint'?'active':''} disabled={!sample.armSpec} title={sample.armSpec?undefined:sample.live?.kinematics.reason} onClick={()=>{w.setTool('joint');if(!sample.capabilities.arm_joint_names.includes(activeJoint??''))w.select('link1');}}>Joint</button><button className={w.tool==='tcp'?'active':''} disabled={!sample.armSpec} title={sample.armSpec?undefined:sample.live?.kinematics.reason} onClick={()=>w.setTool('tcp')}>TCP 位置</button><span>Preview</span></div>
 {!sample.armSpec&&sample.live&&<div className="preview-state" role="status"><Icon name="info" size={14}/><span>本地 Joint / TCP 预览不可用：{sample.live.kinematics.reason||'缺少版本化运动学元数据'}<small>只读 Actual 监控继续；不会回退到冻结 profile 或猜测映射。</small></span></div>}
 {w.tool==='tcp'?<><div className="target-fields">{p.map((v,i)=><Field key={i} label={`TCP ${['X','Y','Z'][i]}`} value={v} suffix="m" step={0.005} onChange={value=>{const next=[...p] as Vec3;next[i]=value;w.editTcp(next);}}/>)}</div><div className="frame-note">world_sim / Z-up <span>仅位置 · 姿态未约束</span></div></>:<div className="joint-edit-note">选择 Joint 工具和关节后编辑目标。下方 Actual 始终只读。</div>}
 <div className="preview-state"><Icon name="info" size={14}/><span>{!target?'编辑目标后显示本地 Ghost 预览。':target.preview==='unreachable'?`本地 IK 未收敛 · 残差 ${((target.residualM??0)*1000).toFixed(1)} mm；隐藏 Ghost。`:target.mode==='tcp'?`本地位置 IK 候选 · 残差 ${((target.residualM??0)*1000).toFixed(2)} mm`:'关节目标姿态 · 本地 FK 预览'}<small>未规划 / 未碰撞检查 / 未授权 / 未执行</small></span></div></section>
 <section><h3>Joint Monitor <div className="unit-switch"><button className={units==='deg'?'active':''} onClick={()=>setUnits('deg')}>°</button><button className={units==='rad'?'active':''} onClick={()=>setUnits('rad')}>rad</button></div></h3><div className="joint-head"><span>关节</span><span>Actual</span><span>Target</span></div>{sample.capabilities.arm_joint_names.map((name,i)=>{
 const selected=activeJoint===name;const editable=w.tool==='joint'&&selected&&Boolean(sample.armSpec);const actual=sample.actual.arm.user_joint_positions_rad[i];const value=userJoint(sample,target,name);const convert=units==='deg'?deg:(n:number)=>n;const [min,max]=sample.capabilities.arm_user_limits_rad[i];
 return <div key={name} className={`joint-item ${selected?'selected':''}`}><div className="joint-values"><button aria-label={`选择 ${name}`} onClick={()=>w.select(sample.scene.links.find(l=>l.joint_name===name)!.name)}>J{i+1}</button><output data-joint-actual={name}>{convert(actual).toFixed(2)}</output>{editable?<NumericInput label={`${name} Target ${units}`} value={convert(value)} min={convert(min)} max={convert(max)} step={units==='deg'?1:0.01} onValue={v=>w.editJoint(name,units==='deg'?rad(v):v)}/>:<output>{target?convert(value).toFixed(2):'—'}</output>}</div>{editable&&<div className="joint-slider"><input type="range" aria-label={`${name} 目标滑条`} min={min} max={max} step={0.002} value={value} onChange={e=>w.editJoint(name,+e.target.value)}/><small>{convert(min).toFixed(1)} … {convert(max).toFixed(1)} {units==='deg'?'°':'rad'} · 用户角</small></div>}</div>;
 })}<p className="subtle">显示可切换 ° / rad；用户角与模型角分开；保留 joint4 零位偏移。仅选中关节可编辑，其他目标保留。</p></section>
 {sample.live&&<details className="diag"><summary>后端已有 Target · 只读</summary><div className="backend-joints">{sample.capabilities.arm_joint_names.map((name,i)=><span key={name}>{name} <b data-backend-target={name}>{sample.live!.target.user_joint_positions_rad[i].toFixed(4)}</b> rad</span>)}</div><p className="subtle">用户角；model joint4 {sample.live.target.model_joint_positions_rad[3]?.toFixed(4)} rad<br/>夹爪 {sample.live.target.gripper_width_m.toFixed(4)} m · 底盘 {sample.live.target.base_velocity.vx_m_s.toFixed(3)} / {sample.live.target.base_velocity.vy_m_s.toFixed(3)} m/s · {sample.live.target.base_velocity.wz_rad_s.toFixed(3)} rad/s<br/>TCP / command_id 未提供；不是本方提交成功。</p></details>}
 {sample.live&&<details className="diag"><summary>读取身份与运动学</summary><p className="subtle identity-readout">{sample.source.interface_profile}<br/>{sample.source.identity.run_id}<br/>generation {sample.source.identity.backend_generation} · {sample.source.identity.episode_id}<br/>{sample.live.resource.model_id}<br/>内容 {sample.live.geometryBinding?.content_identity_sha256?.slice(0,16)??'geometry-1 · 无独立内容摘要'} · 运行匹配 {sample.live.geometryBinding?String(sample.live.geometryBinding.runtime_identity_matches):'—'}<br/>本地运动学：{sample.live.kinematics.profileId||'不可用'} · {sample.live.kinematics.status}<br/>{sample.live.kinematics.reason||'元数据与当前 native 限位/父子关系一致；仍非标定结果'}<br/>完整部署内容未核验 · 未授权</p></details>}
 <details className="diag"><summary>命令反馈 · 未提交</summary><div className="empty-feedback"><Icon name="terminal" size={15}/><span>本地预览未生成执行命令。<br/>等待平台 Session / Owner / 命令接口。</span></div></details>
 </div>
 <div className="inspector-actions"><button disabled={!target} onClick={w.cancelTarget}>取消目标 <kbd>Esc</kbd></button><button disabled title="平台命令与控制权尚未接通">提交执行 <Icon name="arrow" size={13}/></button></div></div>;
}
export function SensorsPanel(){const w=useWorkbench();return <div className="sensor-strip">{['RGB','Depth'].map((name,i)=><article key={name} className="sensor-card"><div className="sensor-card-title"><span><Icon name="camera" size={14}/>{name} · RGB-D</span><small>未接入</small></div><div className={`sensor-empty sensor-${i}`}><Icon name={i?'layers':'camera'} size={22}/><span>没有可用图像帧</span><small>相机位于 {w.sample.capabilities.camera_parent_body}；{w.sample.live?'后端仅暴露引用，未开放媒体。':'冻结样本不包含媒体。'}</small></div></article>)}<aside><b>OBSERVATION</b><p>三维视口是观察相机。<br/>不能替代传感器 RGB。</p><span className="source-chip">{w.sample.scene.camera_ids.join(' · ')}</span></aside></div>;}
export function TimelinePanel(){const w=useWorkbench();const [now,setNow]=useState(Date.now());useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),1000);return ()=>clearInterval(timer);},[]);return <div className="timeline-panel"><div className="timeline-source"><span><span className="status-dot amber"/>{w.sample.live?'真实只读状态流':'单帧原生样本'}</span><b>sim {w.sample.actual.sim_time_s.toFixed(3)} s</b><small>{w.sample.actual.clock_id} · {w.sample.actual.control_tick_id}</small>{w.sample.live&&<small>最近接收 {w.monitor.receivedAt?Math.max(0,(now-w.monitor.receivedAt)/1000).toFixed(1):'—'} s 前 · feedback {w.sample.live.feedbackTimeS.toFixed(3)} s</small>}<button disabled title="本轮未接入 Episode 回放">▶ 播放</button></div><div className="timeline-tracks"><div className="track"><label>源状态</label><div className="sample-track"><span className="sample-tick"/><span>{w.sample.live?`${w.monitor.snapshots} 次只读快照 · ${w.monitor.state==='stale'?'陈旧':'监控'} · 请求 ${w.monitor.requestMs?.toFixed(0)} ms`:'1 个冻结采样点 · 无连续轨迹'}</span></div></div><div className="track"><label>本地操作</label><div className="local-events">{w.events.slice(-4).reverse().map(e=><span key={e.id}><i/>{e.label}<small>{new Date(e.time).toLocaleTimeString('zh-CN',{hour12:false})}</small></span>)}{w.events.length===0&&<span className="subtle">尚无本地操作；操作日志不会写入原生 Episode。</span>}</div></div></div></div>;}
