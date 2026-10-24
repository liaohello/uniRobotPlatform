import { useEffect, useMemo, useRef, useState } from 'react';
import { FrozenSampleService, PlatformService } from '../adapters/services';
import { IdentityChanged } from '../adapters/mobilecar-read';
import type { LocalTarget, MonitorStatus, TimelineEvent, Vec3, ViewSample } from '../adapters/types';
import type { Tool, WorkbenchScene } from '../viewport/workbench-scene';
import { WorkbenchContext, type Workspace } from './context';
import { jointTarget,tcpTarget } from './state';
import { WorkbenchLayout } from '../workbench/Layout';
import { Icon } from '../workbench/Icon';
export function App(){
 const [sourceMode,setSourceMode]=useState<'frozen'|'platform'>(new URLSearchParams(location.search).get('source')==='frozen'?'frozen':'platform');const [sample,setSample]=useState<ViewSample|null>(null);const [error,setError]=useState('');
 const [selected,setSelected]=useState<string|null>('arm');const [tool,setTool]=useState<Tool>('select');const [target,setTarget]=useState<LocalTarget|null>(null);
 const [notice,setNotice]=useState('');const [events,setEvents]=useState<TimelineEvent[]>([]);const [interacting,setInteracting]=useState(false);const [ghost,setGhost]=useState(true);const [world,setWorld]=useState(true);
 const view=useRef<WorkbenchScene|null>(null);const targetRef=useRef(target);targetRef.current=target;const serial=useRef(0);
 const [intervalMs,setIntervalMs]=useState(1000);const intervalRef=useRef(intervalMs);intervalRef.current=intervalMs;
 const [monitor,setMonitor]=useState<MonitorStatus>({state:'loading',message:'初始化只读来源',receivedAt:null,requestMs:null,snapshots:0,intervalMs});
 const [assetError,setAssetError]=useState('');const [retry,setRetry]=useState(0);
 const service=useMemo(()=>sourceMode==='frozen'?new FrozenSampleService():new PlatformService(),[sourceMode]);
 useEffect(()=>{
   const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;let current:ViewSample|null=null;let count=0;let failures=0;
   setSample(null);setError('');setAssetError('');targetRef.current=null;setTarget(null);setTool('select');setSelected('arm');setInteracting(false);setEvents([]);setNotice('');
   setMonitor({state:'loading',message:'加载场景 / 能力 / Actual',receivedAt:null,requestMs:null,snapshots:0,intervalMs:intervalRef.current});
   async function read(){
     const started=performance.now();
     try{
       const signal=AbortSignal.any([abort.signal,AbortSignal.timeout(10000)]);
       const next=current&&service instanceof PlatformService?await service.refresh(current,signal):await service.load(signal);
       if(abort.signal.aborted)return;
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
 function log(label:string){setEvents(items=>[...items.slice(-39),{id:++serial.current,kind:'local',time:Date.now(),label}]);}
 function cancelTarget(){view.current?.cancelGesture();setTarget(null);targetRef.current=null;setNotice('已取消本地目标；Actual 未被本地预览改写，也未发送停止或运动命令。');log('取消本地目标');}
 function editJoint(name:string,value:number){if(!sample)return;try{const next=jointTarget(sample,targetRef.current,name,value);targetRef.current=next;setTarget(next);setNotice('Joint 本地预览已更新；其他关节目标保留。');}catch(e){setNotice((e as Error).message);}}
 function editTcp(position:Vec3){if(!sample)return;try{const next=tcpTarget(sample,targetRef.current,position);targetRef.current=next;setTarget(next);setNotice(next.preview==='unreachable'?'本地位置 IK 未收敛，Target 保留；不能提交执行。':'本地位置 IK 候选已更新；没有轨迹/碰撞/动力学验证。');}catch(e){setNotice((e as Error).message);}}
 useEffect(()=>{const listener=(event:KeyboardEvent)=>{
   const node=event.target as HTMLElement;const typing=node.matches('input,textarea,select')||node.isContentEditable;
   if(typing)return;
   const inViewport=Boolean(node.closest('.viewport-panel'));
   if(event.key==='Escape'&&inViewport){event.preventDefault();cancelTarget();}
   if((event.key==='f'||event.key==='F')&&inViewport){event.preventDefault();view.current?.focusSelection();}
 };window.addEventListener('keydown',listener);return ()=>window.removeEventListener('keydown',listener);},[sample]);
 const workspace:Workspace|null=sample?{sample,monitor:{...monitor,intervalMs},assetError,setAssetError,selected,select:id=>{setSelected(id);log(`选择 ${id??'空白'}`);},tool,setTool:mode=>{setTool(mode);log(`工具 ${mode}`);},target,editJoint,editTcp,cancelTarget,notice,setNotice,events,log,interacting,setInteracting:active=>{setInteracting(active);if(!active&&targetRef.current)log('目标拖动结束 · 仅本地');},view,ghost,setGhost,world,setWorld}:null;
 return <div className="application"><header className="global-header"><a className="brand" href="./" aria-label="uniRobot 工作台"><span><Icon name="cube" size={24}/></span>uniRobot<small>PLATFORM</small></a><div className="breadcrumb"><span>Project</span><b>LanderPi</b><Icon name="chevron" size={12}/><span>mobile_pick</span></div><div className="header-right"><span className="build-label" title={import.meta.env.VITE_WORKBENCH_RELEASE??'dev'}>M1 / 车体渲染 · {import.meta.env.VITE_WORKBENCH_RELEASE?.split('-').at(-1)??'dev'}</span><span className="source-label"><span className="status-dot amber"/>{assetError?'资产不可用':monitor.state==='stale'?'Actual 已陈旧':sample?.source.label??(error?'来源不可用':'加载数据源')}</span><span className="avatar">UR</span></div></header>
 <div className="app-body"><nav className="side-nav" aria-label="主导航"><div className="nav-group-label">WORKSPACE</div>{[['cube','场景布置'],['play','Simulation'],['chart','Replay']].map(([icon,label],i)=><button key={label} className={i===1?'selected':''} disabled={i!==1} title={i===1?'当前工作台':'后续切片接入'}><Icon name={icon} size={20}/><span>{label}</span></button>)}<div className="nav-divider"/><div className="nav-group-label">RESOURCES</div><button disabled title="后续切片接入"><Icon name="layers" size={20}/><span>数据与模型</span></button><div className="nav-bottom"><Icon name="info"/><span>浏览器仅渲染<br/>物理由后端负责</span></div></nav>
 <main><div className="runtime-strip"><div className="runtime-controls"><span className="group-title">Session <small>未绑定</small></span><button disabled title="prepared / Start 接口尚未接通"><Icon name="play" size={14}/>Start</button><button disabled title="没有绑定在线 Session"><Icon name="stop" size={13}/>停止</button></div><div className="runtime-controls"><span className="group-title">Recording <small>未接入</small></span><button disabled title="录制接口属于后续切片"><span className="record-dot"/>开始录制</button></div><div className="runtime-controls source-select"><label htmlFor="source">数据源</label><select id="source" value={sourceMode} disabled={interacting} onChange={e=>setSourceMode(e.target.value as 'frozen'|'platform')}><option value="frozen">冻结原生样本</option><option value="platform">真实后端 · 只读监控</option></select>{sourceMode==='platform'&&<label className="poll-label">间隔 <select aria-label="轮询间隔" value={intervalMs} onChange={e=>setIntervalMs(+e.target.value)}><option value={1000}>1 s</option><option value={2000}>2 s</option><option value={5000}>5 s</option></select></label>}</div><div className="source-safety"><Icon name="info" size={16}/><span>可编辑本地 Target<br/><b>未授权 · 不发送机器人命令</b></span></div></div>
 <div className="authority-strip"><span>执行来源 <b>Human · 本地预览</b></span><span>Base <i>{sample?.live?.authority.base_owner_session_id??'无已观测 Owner'}</i></span><span>Arm <i>{sample?.live?.authority.arm_owner_session_id??'无已观测 Owner'}</i></span><span>Gripper <i>继承 Arm / 未接入</i></span><button disabled title="需要后端控制权确认">申请接管</button><span className="authority-help">只读 Owner ≠ 本方授权</span></div>
 {sourceMode==='platform'&&<div className={`monitor-strip ${monitor.state==='stale'||assetError?'stale':''}`} role="status"><span>{assetError?`资产不可用 · ${assetError}`:monitor.message}</span><span>请求 {monitor.requestMs?.toFixed(0)??'—'} ms · {monitor.snapshots} 次快照</span><button onClick={()=>setRetry(n=>n+1)}>重新加载来源</button></div>}
 {workspace?<WorkbenchContext.Provider value={workspace}><WorkbenchLayout/></WorkbenchContext.Provider>:<div className="loading-view">{error?<><Icon name="info" size={32}/><h2>数据源不可用</h2><p role="alert">{error}</p><button className="primary" onClick={()=>setSourceMode('frozen')}>使用冻结原生样本</button></>:<><div className="loading-orbit"/><p>加载场景、模型与只读状态…</p></>}</div>}
 <footer className="status-bar"><span><span className="status-dot amber"/>{notice||(sample?.live?'后端 Actual / 已有 Target 只读；本地 Target 未提交。Session / 运动 / 录制禁用。':'冻结来源：离线观察与目标预览。')}</span><span>world_sim · m / rad <i/>前端渲染，无物理步进</span></footer></main></div></div>;
}
