import { useRef, useState } from 'react';
import { DockviewReact, type DockviewReadyEvent, type DockviewApi } from 'dockview-react';
import 'dockview-react/dist/styles/dockview.css';
import { useWorkbench } from '../app/context';
import { HierarchyPanel,InspectorPanel,ViewportPanel,SensorsPanel,TimelinePanel } from './panels';
import { Icon } from './Icon';
const components={hierarchy:HierarchyPanel,inspector:InspectorPanel,viewport:ViewportPanel,sensors:SensorsPanel,timeline:TimelinePanel};
const key='unirobot:m12a:layout:v1';
export function WorkbenchLayout(){
 const w=useWorkbench();const api=useRef<DockviewApi|null>(null);const [epoch,setEpoch]=useState(0);
 function ready(event:DockviewReadyEvent){
   api.current=event.api;const a=event.api;
   a.addPanel({id:'viewport',component:'viewport',title:'3D 场景',initialWidth:800,initialHeight:460,minimumHeight:260});
   a.addPanel({id:'hierarchy',component:'hierarchy',title:'场景层级',position:{referencePanel:'viewport',direction:'left'},initialWidth:226});
   a.addPanel({id:'inspector',component:'inspector',title:'Inspector',position:{referencePanel:'viewport',direction:'right'},initialWidth:320});
   a.addPanel({id:'sensors',component:'sensors',title:'传感器视图',position:{referencePanel:'viewport',direction:'below'},initialHeight:160,minimumHeight:140});
   a.addPanel({id:'timeline',component:'timeline',title:'时间与事件',position:{referencePanel:'sensors',direction:'below'},initialHeight:115,minimumHeight:100});
 }
 function save(){try{if(api.current)localStorage.setItem(key,JSON.stringify(api.current.toJSON()));w.setNotice('布局已保存到此浏览器；未改变目标、控制权或运行状态。');}catch(e){w.setNotice(`布局保存失败：${(e as Error).message}`);}}
 function restore(){try{const json=localStorage.getItem(key);if(!json){w.setNotice('此浏览器尚无已保存布局。');return;}api.current?.fromJSON(JSON.parse(json));w.setNotice('已恢复布局；本地目标保持不变。');}catch(e){w.setNotice(`布局恢复失败：${(e as Error).message}。可使用重置布局。`);}}
 return <div className={`workspace-layout ${w.interacting?'during-gesture':''}`}><div className="layout-bar"><span><Icon name="cube" size={16}/> Simulation <i>/</i> 3D 工作台</span><div><button disabled={w.interacting} onClick={save}><Icon name="save" size={14}/>保存布局</button><button disabled={w.interacting} onClick={restore}>恢复布局</button><button disabled={w.interacting} onClick={()=>{api.current=null;setEpoch(epoch+1);w.setNotice('已重置面板布局；本地 Target 与 Actual 未改变。');}}><Icon name="reset" size={14}/>重置布局</button></div></div><div className="dock-container"><DockviewReact key={epoch} className="dockview-theme-abyss" components={components} disableFloatingGroups={true} disableDnd={w.interacting} onReady={ready}/></div></div>;
}
