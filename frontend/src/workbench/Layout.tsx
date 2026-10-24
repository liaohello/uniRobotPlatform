import { useCallback, useEffect, useRef, useState } from 'react';
import { DockviewReact, type DockviewApi, type DockviewReadyEvent, type IDockviewPanel } from 'dockview-react';
import 'dockview-react/dist/styles/dockview.css';
import { useWorkbench, type LayoutPreset } from '../app/context';
import { uiSnapshot } from '../app/ui-state';
import { HierarchyPanel,InspectorPanel,ViewportPanel,SensorsPanel,TimelinePanel } from './panels';
import { Icon } from './Icon';
const components={hierarchy:HierarchyPanel,inspector:InspectorPanel,viewport:ViewportPanel,sensors:SensorsPanel,timeline:TimelinePanel};
const key='unirobot:m12a:layout:v2';
type PanelId='viewport'|'hierarchy'|'inspector'|'sensors'|'timeline';
const order:PanelId[]=['viewport','hierarchy','inspector','sensors','timeline'];
const titles:Record<PanelId,string>={viewport:'3D 场景',hierarchy:'场景层级',inspector:'Inspector',sensors:'传感器视图',timeline:'时间与事件'};
// Sized so the declared minimums are satisfiable at 1366x768 (the previous
// 260+140+100 minimums could not fit the 498px dock).
const defaults:Record<PanelId,{width?:number;height?:number;minWidth?:number;minHeight?:number}>={viewport:{minWidth:360,minHeight:170},hierarchy:{width:216,minWidth:168},inspector:{width:308,minWidth:268},sensors:{height:126,minHeight:82},timeline:{height:86,minHeight:64}};
function addPanel(api:DockviewApi,id:PanelId):IDockviewPanel{
 const size=defaults[id];
 const base={id,component:id,title:titles[id],minimumWidth:size.minWidth,minimumHeight:size.minHeight,initialWidth:id==='viewport'?760:size.width,initialHeight:id==='viewport'?420:size.height};
 if(id==='viewport')return api.addPanel(base);
 if(id==='hierarchy')return api.addPanel({...base,position:{referencePanel:'viewport',direction:'left'}});
 if(id==='inspector')return api.addPanel({...base,position:{referencePanel:'viewport',direction:'right'}});
 if(id==='sensors')return api.addPanel({...base,position:{referencePanel:'viewport',direction:'below'}});
 const reference=api.getPanel('sensors')?'sensors':'viewport';
 return api.addPanel({...base,position:{referencePanel:reference,direction:'below'}});
}
export function WorkbenchLayout(){
 const w=useWorkbench();const api=useRef<DockviewApi|null>(null);const [ready,setReady]=useState(false);
 const [open,setOpen]=useState<Record<PanelId,boolean>>({viewport:true,hierarchy:true,inspector:true,sensors:true,timeline:true});
 const [maximized,setMaximized]=useState(false);
 const settle=useCallback(()=>{
   const sync=()=>w.view.current?.handleLayoutChange();
   requestAnimationFrame(sync);window.setTimeout(sync,180);
   const a=api.current;if(!a)return;
   const facts:typeof uiSnapshot.panels={};
   for(const id of order){const panel=a.getPanel(id);facts[id]=panel?{open:true,width:panel.api.width??null,height:panel.api.height??null}:{open:false,width:null,height:null};}
   uiSnapshot.panels=facts;
 },[w.view]);
 function readyHandler(event:DockviewReadyEvent){
   const a=event.api;api.current=a;
   for(const id of order)addPanel(a,id);
   a.onDidAddPanel(panel=>{setOpen(previous=>({...previous,[panel.id]:true}));settle();});
   a.onDidRemovePanel(panel=>{setOpen(previous=>({...previous,[panel.id]:false}));settle();});
   a.onDidMaximizedGroupChange(event=>{setMaximized(event.isMaximized);w.setMaximized(event.isMaximized);settle();});
   a.onDidLayoutChange(()=>settle());
   setReady(true);rebalance();settle();
 }
 const applySizes=useCallback((preset:LayoutPreset)=>{
   const a=api.current;if(!a)return;
   const sizes=preset==='focus3d'?{hierarchy:196,inspector:300}:{hierarchy:216,inspector:308,sensors:126,timeline:86};
   for(const [id,value] of Object.entries(sizes) as [PanelId,number][]){
     const panel=a.getPanel(id);if(!panel)continue;
     if(id==='hierarchy'||id==='inspector')panel.api.setSize({width:value});
     else panel.api.setSize({height:value});
   }
 },[ ]);
 // Dockview hands a removed view's space to its sibling, which shrank the 3D
 // viewport when the sensor strip was collapsed. Explicitly re-proportion the
 // vertical stack after structural changes; manual sash drags are never touched.
 const rebalance=useCallback(()=>{
   requestAnimationFrame(()=>{
     const a=api.current;const container=document.querySelector('.dock-container') as HTMLElement|null;
     if(!a||!container||a.hasMaximizedGroup())return;
     const total=container.clientHeight;if(total<160)return;
     const viewport=a.getPanel('viewport');const sensors=a.getPanel('sensors');const timeline=a.getPanel('timeline');
     if(!viewport)return;
     const sash=[sensors,timeline].filter(Boolean).length*4;
     const sensorsHeight=sensors?Math.round(total*0.2):0;
     const timelineHeight=timeline?Math.round(total*0.15):0;
     viewport.api.setSize({height:Math.max(180,total-sensorsHeight-timelineHeight-sash)});
     if(sensors)sensors.api.setSize({height:sensorsHeight});
     if(timeline)timeline.api.setSize({height:timelineHeight});
     settle();
   });
 },[settle]);
 const ensure=useCallback((id:PanelId,visible:boolean)=>{
   const a=api.current;if(!a)return;
   const panel=a.getPanel(id);
   // Adding a panel while the viewport is maximized would put it in the
   // maximized group as a tab; leave maximize first so the docked position wins.
   if(visible&&!panel&&a.hasMaximizedGroup())a.exitMaximizedGroup();
   if(visible&&!panel)addPanel(a,id);
   if(!visible&&panel)panel.api.close();
   if(visible!==Boolean(panel))rebalance();
 },[rebalance]);
 const applyPreset=useCallback((preset:LayoutPreset)=>{
   const a=api.current;if(!a)return;
   if(preset==='focus3d'){
     ensure('viewport',true);ensure('hierarchy',true);ensure('inspector',true);
     ensure('sensors',false);ensure('timeline',false);
     applySizes('focus3d');
     const panel=a.getPanel('viewport');if(panel&&!a.hasMaximizedGroup())a.maximizeGroup(panel);
   }else{
     for(const id of order)ensure(id,true);
     if(a.hasMaximizedGroup())a.exitMaximizedGroup();
     applySizes('standard');
   }
   rebalance();settle();
 },[applySizes,ensure,rebalance,settle]);
 useEffect(()=>{if(ready)applyPreset(w.preset);},[ready,w.preset,applyPreset]);
 function toggleMaximize(){
   const a=api.current;const panel=a?.getPanel('viewport');if(!a||!panel)return;
   if(a.hasMaximizedGroup())a.exitMaximizedGroup();else a.maximizeGroup(panel);
   settle();
 }
 function save(){
   const a=api.current;if(!a)return;
   const sizes:Record<string,{width:number|null;height:number|null}>={};
   for(const id of order){const panel=a.getPanel(id);if(panel)sizes[id]={width:panel.api.width??null,height:panel.api.height??null};}
   try{localStorage.setItem(key,JSON.stringify({version:2,open,maximized,sizes}));w.setNotice('布局已保存到此浏览器；目标、控制权与运行状态未改变。');}
   catch(e){w.setNotice(`布局保存失败：${(e as Error).message}`);}
 }
 function restore(){
   const a=api.current;if(!a)return;
   let snapshot:{version?:number;open?:Record<string,boolean>;maximized?:boolean;sizes?:Record<string,{width?:number|null;height?:number|null}>};
   try{const raw=localStorage.getItem(key);if(!raw){w.setNotice('此浏览器尚无已保存布局。');return;}snapshot=JSON.parse(raw);}
   catch(e){w.setNotice(`布局恢复失败：${(e as Error).message}。可使用重置布局。`);return;}
   if(snapshot.version!==2||!snapshot.open){w.setNotice('已保存布局版本不兼容，请使用重置布局。');return;}
   if(a.hasMaximizedGroup())a.exitMaximizedGroup();
   for(const id of order){const visible=id==='viewport'?true:snapshot.open[id]!==false;ensure(id,visible);}
   if(snapshot.sizes)for(const id of order){const panel=a.getPanel(id);const size=snapshot.sizes[id];if(!panel||!size)continue;
     if(id==='hierarchy'||id==='inspector'){if(size.width)panel.api.setSize({width:size.width});}
     else if(size.height)panel.api.setSize({height:size.height});}
   if(snapshot.maximized){const panel=a.getPanel('viewport');if(panel&&!a.hasMaximizedGroup())a.maximizeGroup(panel);}
   else if(a.hasMaximizedGroup())a.exitMaximizedGroup();
   rebalance();settle();w.setNotice('已恢复保存的面板布局；本地 Target、Actual 与控制权保持不变。');
 }
 function reset(){
   const a=api.current;if(!a)return;
   if(a.hasMaximizedGroup())a.exitMaximizedGroup();
   for(const id of order)ensure(id,true);
   applySizes('standard');w.setPreset('standard');rebalance();settle();
   w.setNotice('已重置面板布局；本地 Target、Actual 与来源未改变。');
 }
 const presets:LayoutPreset[]=['standard','focus3d'];
 return <div className={`workspace-layout ${w.interacting?'during-gesture':''}`}>
  <div className="layout-bar">
   <div className="layout-title"><Icon name="cube" size={15}/><span>3D 工作台</span></div>
   <div className="preset-switch" role="group" aria-label="布局预设">
    {presets.map(preset=><button key={preset} aria-pressed={w.preset===preset} title={preset==='standard'?'显示全部面板':'收起传感器与时间轴并最大化 3D 视口'} onClick={()=>w.setPreset(preset)}>{preset==='standard'?'标准工作台':'3D 专注'}</button>)}
   </div>
   <div className="panel-toggles" role="group" aria-label="面板开关">
    {order.filter(id=>id!=='viewport').map(id=><button key={id} aria-pressed={Boolean(open[id])} title={`${open[id]?'收起':'恢复'}${titles[id]}面板`} onClick={()=>{
      // In 3D focus the hidden panels are a preset, not a user choice; showing
      // one returns to the standard workbench rather than a half-open layout.
      if(!open[id]&&w.preset==='focus3d'){w.setPreset('standard');return;}
      ensure(id,!open[id]);
    }}>{titles[id]==='时间与事件'?'时间轴':titles[id]==='场景层级'?'层级':titles[id]}</button>)}
   </div>
   <div className="layout-actions">
    <button aria-pressed={maximized} title={maximized?'还原 3D 视口到工作台布局':'在应用内最大化 3D 视口（Dockview 最大化）'} onClick={toggleMaximize}><Icon name={maximized?'collapse':'expand'} size={14}/>{maximized?'还原视口':'最大化视口'}</button>
    <button aria-pressed={w.fullscreen.active} disabled={!w.fullscreen.supported&&!w.fullscreen.active} title={w.fullscreen.supported?(w.fullscreen.active?'退出浏览器全屏':'浏览器全屏（含视口、来源与目标操作）'):(w.fullscreen.reason||'此环境不支持浏览器全屏')} onClick={w.toggleFullscreen}><Icon name="expand" size={14}/>{w.fullscreen.active?'退出全屏':'浏览器全屏'}</button>
    <span className="layout-divider"/>
    <button title="保存面板尺寸与开关到此浏览器" onClick={save}><Icon name="save" size={13}/>保存</button>
    <button title="恢复保存的面板布局" onClick={restore}>恢复</button>
    <button title="恢复默认面板尺寸并展开全部面板" onClick={reset}><Icon name="reset" size={13}/>重置</button>
   </div>
  </div>
  {!w.fullscreen.active&&w.fullscreen.reason&&<div className="layout-warning" role="status"><Icon name="info" size={14}/><span>{w.fullscreen.reason}</span></div>}
  <div className="dock-container"><DockviewReact className="dockview-theme-abyss" components={components} disableFloatingGroups={true} disableDnd={true} onReady={readyHandler}/></div>
 </div>;
}
