import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FrozenSampleService, PlatformService } from '../adapters/services';
import { IdentityChanged, runtimeIdentityKey } from '../adapters/mobilecar-read';
import type { LocalTarget, MonitorStatus, TimelineEvent, Vec3, ViewSample } from '../adapters/types';
import type { Tool, WorkbenchScene } from '../viewport/workbench-scene';
import { WorkbenchContext, type FullscreenState, type LayoutPreset, type Workspace } from './context';
import { uiSnapshot } from './ui-state';
import { jointTarget,tcpTarget } from './state';
import { WorkbenchLayout } from '../workbench/Layout';
import { SessionPanel } from '../workbench/session-panel';
import { Icon } from '../workbench/Icon';
export function App(){
 const [sourceMode,setSourceMode]=useState<'frozen'|'platform'>(new URLSearchParams(location.search).get('source')==='frozen'?'frozen':'platform');const [sample,setSample]=useState<ViewSample|null>(null);const [error,setError]=useState('');
 const [selected,setSelected]=useState<string|null>('arm');const [tool,setTool]=useState<Tool>('select');const [target,setTarget]=useState<LocalTarget|null>(null);
 const [notice,setNotice]=useState('');const [events,setEvents]=useState<TimelineEvent[]>([]);const [interacting,setInteracting]=useState(false);const [ghost,setGhost]=useState(true);const [world,setWorld]=useState(true);
 const [preset,setPreset]=useState<LayoutPreset>(()=>window.innerHeight<700&&window.innerWidth>=900?'focus3d':'standard');const [maximized,setMaximized]=useState(false);const [drawer,setDrawer]=useState<'none'|'session'>('none');
 const [navCollapsed,setNavCollapsed]=useState(false);const [details,setDetails]=useState(false);
 const [fullscreen,setFullscreen]=useState<FullscreenState>({active:false,supported:typeof document!=='undefined'&&document.fullscreenEnabled,reason:''});
 const mainRef=useRef<HTMLElement>(null);
 const view=useRef<WorkbenchScene|null>(null);const targetRef=useRef(target);targetRef.current=target;const serial=useRef(0);
 const [intervalMs,setIntervalMs]=useState(1000);const intervalRef=useRef(intervalMs);intervalRef.current=intervalMs;
 const [monitor,setMonitor]=useState<MonitorStatus>({state:'loading',message:'初始化只读来源',receivedAt:null,requestMs:null,snapshots:0,intervalMs});
 const [assetError,setAssetError]=useState('');const [retry,setRetry]=useState(0);
 const service=useMemo(()=>sourceMode==='frozen'?new FrozenSampleService():new PlatformService(),[sourceMode]);
 useEffect(()=>{
   const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;let current:ViewSample|null=null;let count=0;let failures=0;
   setSample(null);setError('');setAssetError('');targetRef.current=null;setTarget(null);setTool('select');setSelected('arm');setInteracting(false);setEvents([]);setNotice('');setMaximized(false);setDrawer('none');
   setMonitor({state:'loading',message:'加载场景 / 能力 / Actual',receivedAt:null,requestMs:null,snapshots:0,intervalMs:intervalRef.current});
   async function read(){
     const started=performance.now();
     try{
       const signal=AbortSignal.any([abort.signal,AbortSignal.timeout(10000)]);
       const previousRuntime=current?.live?.runtimeKey;
       const next=current&&service instanceof PlatformService?await service.refresh(current,signal):await service.load(signal);
       if(abort.signal.aborted)return;
       if(previousRuntime&&next.live&&runtimeIdentityKey(next.source.identity)!==previousRuntime){
         // geometry-2 keeps verified content across RESET/run identity changes.
         // Only the old run's gesture and pending local target are discarded.
         view.current?.cancelGesture('runtime');
         targetRef.current=null;setTarget(null);
         setNotice('后端 run / generation / episode 已变化；旧本地目标已取消，网格、相机与布局保留。');
         log('运行身份变化 · 旧本地目标作废');
       }
       current=next;count++;failures=0;setSample(next);setError('');
       setMonitor({state:next.live?'current':'frozen',message:next.live?'真实只读监控':'冻结原生样本 · 非实时',receivedAt:Date.now(),requestMs:performance.now()-started,snapshots:count,intervalMs:intervalRef.current});
     }catch(e){
       if(abort.signal.aborted)return;
       failures++;
       if(e instanceof IdentityChanged){
         current=null;targetRef.current=null;setTarget(null);view.current?.cancelGesture();setSample(null);setAssetError('');setTool('select');setSelected('arm');setInteracting(false);
         setMonitor(m=>({...m,state:'reloading',message:`${e.message}；重新加载场景 / 能力`,requestMs:performance.now()-started}));setError('身份变化，旧目标已作废，正在重新加载。');
       }else{
         const message=(e as Error).message;setError(message);
         setMonitor(m=>({...m,state:'stale',message:`${current?'Actual 已陈旧':'来源不可用'} · ${message}`,requestMs:performance.now()-started}));
       }
     }
     // Schedule after settlement: one request group at a time, including failure recovery.
     if(failures>=3){setMonitor(m=>({...m,state:'stale',message:m.message+' · 连续3次失败，自动重试已暂停，请重新加载'}));return;}
     if(!abort.signal.aborted&&service instanceof PlatformService)timer=setTimeout(read,intervalRef.current);
   }
   void read();return ()=>{abort.abort();clearTimeout(timer);service.dispose();};
 },[service,retry]);
 // Renderer/aspect/picking must follow every host-size change: fullscreen,
 // Dockview maximize, sash drag and browser page zoom all land here.
 useEffect(()=>{
   let frame=0;let timer=0;
   const sync=()=>{frame=0;view.current?.handleLayoutChange();};
   const schedule=()=>{if(frame)return;frame=requestAnimationFrame(sync);window.clearTimeout(timer);timer=window.setTimeout(sync,160);};
   window.addEventListener('resize',schedule);
   document.addEventListener('fullscreenchange',schedule);
   return ()=>{window.removeEventListener('resize',schedule);document.removeEventListener('fullscreenchange',schedule);if(frame)cancelAnimationFrame(frame);window.clearTimeout(timer);};
 },[]);
 useEffect(()=>{
   const onChange=()=>{
     const active=Boolean(document.fullscreenElement);
     setFullscreen(current=>({active,supported:document.fullscreenEnabled,reason:active?'':current.reason}));
     requestAnimationFrame(()=>view.current?.handleLayoutChange());
   };
   const onError=()=>setFullscreen(current=>({...current,active:false,reason:'浏览器拒绝进入全屏（fullscreenerror）'}));
   document.addEventListener('fullscreenchange',onChange);document.addEventListener('fullscreenerror',onError);
   return ()=>{document.removeEventListener('fullscreenchange',onChange);document.removeEventListener('fullscreenerror',onError);};
 },[]);
 const toggleFullscreen=useCallback(()=>{
   const element=mainRef.current;
   if(!document.fullscreenEnabled||!element){setFullscreen(current=>({...current,supported:false,reason:'此浏览器或嵌入环境不允许页面全屏；应用内“最大化视口”仍可用'}));return;}
   if(document.fullscreenElement){void document.exitFullscreen().catch(reason=>setFullscreen(current=>({...current,reason:`退出全屏失败：${(reason as Error).name}`})));return;}
   element.requestFullscreen().catch((reason:DOMException)=>{
     // A rejected request is reported verbatim; no optimistic success state.
     setFullscreen(current=>({...current,active:false,reason:`无法进入全屏：${reason.name}（${reason.message||'浏览器拒绝'}）；应用内“最大化视口”仍可用`}));
   });
 },[]);
 function log(label:string){setEvents(items=>[...items.slice(-39),{id:++serial.current,kind:'local',time:Date.now(),label}]);}
 function cancelTarget(){view.current?.cancelGesture();setTarget(null);targetRef.current=null;setNotice('已取消本地目标；Actual 未被本地预览改写，也未发送停止或运动命令。');log('取消本地目标');}
 function editJoint(name:string,value:number){if(!sample)return;try{const next=jointTarget(sample,targetRef.current,name,value);targetRef.current=next;setTarget(next);setNotice('Joint 本地预览已更新；其他关节目标保留。');}catch(e){setNotice((e as Error).message);}}
 function editTcp(position:Vec3){if(!sample)return;try{const next=tcpTarget(sample,targetRef.current,position);targetRef.current=next;setTarget(next);setNotice(next.preview==='unreachable'?'本地位置 IK 未收敛，Target 保留；不能提交执行。':'本地位置 IK 候选已更新；没有轨迹/碰撞/动力学验证。');}catch(e){setNotice((e as Error).message);}}
 useEffect(()=>{const listener=(event:KeyboardEvent)=>{
   const node=event.target as HTMLElement;const typing=node.matches('input,textarea,select')||node.isContentEditable;
   if(typing||interacting)return;
   const inViewport=Boolean(node.closest('.viewport-panel'));
   // Esc is also the browser's fullscreen exit key; cancelling the stored target
   // on that same keypress would delete an unrelated local draft.
   if(event.key==='Escape'&&inViewport&&!document.fullscreenElement){event.preventDefault();cancelTarget();}
   if((event.key==='f'||event.key==='F')&&inViewport){event.preventDefault();view.current?.focusSelection();}
 };window.addEventListener('keydown',listener);return ()=>window.removeEventListener('keydown',listener);},[sample,interacting]);
 useEffect(()=>{
   uiSnapshot.preset=preset;uiSnapshot.maximized=maximized;uiSnapshot.fullscreen=fullscreen.active;
   uiSnapshot.fullscreenSupported=fullscreen.supported;uiSnapshot.fullscreenReason=fullscreen.reason;uiSnapshot.drawer=drawer;
 },[preset,maximized,fullscreen,drawer]);
 const workspace:Workspace|null=sample?{sample,monitor:{...monitor,intervalMs},assetError,setAssetError,selected,select:id=>{setSelected(id);log(`选择 ${id??'空白'}`);},tool,setTool:mode=>{setTool(mode);log(`工具 ${mode}`);},target,editJoint,editTcp,cancelTarget,notice,setNotice,events,log,interacting,setInteracting:active=>{setInteracting(previous=>{if(previous&&!active&&targetRef.current)log('目标拖动结束 · 仅本地');return active;});},view,ghost,setGhost,world,setWorld,preset,setPreset,maximized,setMaximized,fullscreen,toggleFullscreen,drawer,setDrawer}:null;
 const sourceLabel=assetError?'资产不可用':monitor.state==='stale'?'Actual 已陈旧':sample?.source.label??(error?'来源不可用':'加载数据源');
 return <div className={`application ${navCollapsed?'nav-collapsed':''} ${preset==='focus3d'?'preset-focus':''} ${fullscreen.active?'is-fullscreen':''}`}><header className="global-header"><a className="brand" href="./" aria-label="uniRobot 工作台"><span><Icon name="cube" size={22}/></span>uniRobot<small>PLATFORM</small></a><div className="breadcrumb"><span>Project</span><b>LanderPi</b><Icon name="chevron" size={12}/><span>mobile_pick</span></div><div className="header-right"><span className="build-label" title={import.meta.env.VITE_WORKBENCH_RELEASE??'dev'}>M1 · {import.meta.env.VITE_WORKBENCH_RELEASE?.split('-').at(-1)??'dev'}</span><span className="source-label"><span className={`status-dot ${monitor.state==='stale'||assetError?'amber':'green'}`}/>{sourceLabel}</span><button className="icon-button" aria-pressed={navCollapsed} aria-label={navCollapsed?'展开导航':'收起导航'} title={navCollapsed?'展开导航':'收起导航'} onClick={()=>setNavCollapsed(!navCollapsed)}><Icon name="tree" size={16}/></button><span className="avatar">UR</span></div></header>
 <div className="app-body"><nav className={`side-nav ${navCollapsed?'collapsed':''}`} aria-label="主导航"><div className="nav-group-label">WORKSPACE</div>{[['cube','场景布置'],['play','Simulation'],['chart','Replay']].map(([icon,label],i)=><button key={label} className={i===1?'selected':''} disabled={i!==1} title={i===1?'当前工作台':'后续切片接入'}><Icon name={icon} size={18}/><span>{label}</span></button>)}<div className="nav-divider"/><div className="nav-group-label">RESOURCES</div><button disabled title="后续切片接入"><Icon name="layers" size={18}/><span>数据与模型</span></button><div className="nav-bottom"><Icon name="info"/><span>浏览器仅渲染<br/>物理由后端负责</span></div></nav>
 <main ref={mainRef}><div className="control-strip">
   <div className="control-group"><span className="control-label">Session <b>准备抽屉</b></span><button disabled title="请在 Session 准备抽屉中显式 Start；顶部按钮不绕过资格"><Icon name="play" size={13}/>Start</button><button disabled title="没有绑定在线 Session"><Icon name="stop" size={12}/>停止</button></div>
   <div className="control-group"><span className="control-label">Recording <b>未接入</b></span><button disabled title="录制接口属于后续切片"><span className="record-dot"/>录制</button></div>
   <div className="control-group source-group"><label htmlFor="source">数据源</label><select id="source" value={sourceMode} disabled={interacting} onChange={e=>setSourceMode(e.target.value as 'frozen'|'platform')}><option value="frozen">冻结原生样本</option><option value="platform">真实后端 · 只读监控</option></select>{sourceMode==='platform'&&<label className="poll-label">间隔 <select aria-label="轮询间隔" value={intervalMs} onChange={e=>setIntervalMs(+e.target.value)}><option value={1000}>1 s</option><option value={2000}>2 s</option><option value={5000}>5 s</option></select></label>}
     <span className={`monitor-chip ${monitor.state==='stale'||assetError?'stale':''}`} role="status" title={monitor.message}>{assetError?`资产不可用 · ${assetError}`:monitor.message}{monitor.state!=='frozen'&&<small>{monitor.requestMs?.toFixed(0)??'—'} ms · {monitor.snapshots} 次</small>}</span>{sourceMode==='platform'&&<button onClick={()=>setRetry(n=>n+1)} title="重新读取 scene / capabilities / snapshot">重新加载来源</button>}</div>
   <div className="control-group authority-group"><span className="chip strong">Human · 本地预览</span><span className="chip masked">Base <i>{sample?.live?.authority.base_owner_session_id??'无 Owner'}</i></span><span className="chip masked">Arm <i>{sample?.live?.authority.arm_owner_session_id??'无 Owner'}</i></span><button disabled title="需要后端控制权确认">申请接管</button><button aria-expanded={details} aria-label="只读与连接详情" title="只读与连接详情" onClick={()=>setDetails(!details)}><Icon name="info" size={14}/>详情</button><button className={drawer==='session'?'active':''} aria-pressed={drawer==='session'} onClick={()=>setDrawer(drawer==='session'?'none':'session')}>Session 准备</button></div>
 </div>
 {details&&<div className="control-details"><span>执行来源 <b>Human · 本地预览</b></span><span>Gripper <b>继承 Arm / 未接入</b></span><span>只读 Owner <b>≠ 本方授权</b></span><span>运动学 <b title={sample?.live?.kinematics.reason||sample?.live?.kinematics.digest} className={sample?.live&&sample.live.kinematics.status!=='verified'?'kin-warn':''}>{sample?.live?`${sample.live.kinematics.profileId||'不可用'} · ${sample.live.kinematics.status}`:'冻结样本独立参考 profile'}</b></span><span>本地 Target <b>未提交 · 无运动/停止/RESET 请求</b></span><span>快照 <b>{monitor.snapshots}</b> · 请求 <b>{monitor.requestMs?.toFixed(0)??'—'} ms</b></span>{sample?.live?.runtimeMismatchAtInit&&<span className="kin-warn">加载时 scene 与 snapshot 运行身份不同；内容身份一致，采用 snapshot Actual</span>}</div>}
 {workspace?<WorkbenchContext.Provider value={workspace}><WorkbenchLayout/>{drawer==='session'&&<SessionPanel/>}</WorkbenchContext.Provider>:<div className="loading-view">{error?<><Icon name="info" size={30}/><h2>数据源不可用</h2><p role="alert">{error}</p><button className="primary" onClick={()=>setSourceMode('frozen')}>使用冻结原生样本</button></>:<><div className="loading-orbit"/><p>加载场景、模型与只读状态…</p></>}</div>}
 <footer className="status-bar"><span><span className={`status-dot ${monitor.state==='stale'?'amber':'green'}`}/>{notice||(sample?.live?'后端 Actual / 已有 Target 只读；本地 Target 未提交。Session / 运动 / 录制禁用。':'冻结来源：离线观察与目标预览。')}</span><span>{fullscreen.active?'全屏中 · Esc 由浏览器处理':'world_sim · m / rad · 前端渲染，无物理步进'}</span></footer></main></div></div>;
}
