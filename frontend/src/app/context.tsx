import { createContext, useContext } from 'react';
import type { LocalTarget, MonitorStatus, TimelineEvent, Vec3, ViewSample } from '../adapters/types';
import type { Tool, WorkbenchScene } from '../viewport/workbench-scene';
export interface Workspace {
 monitor:MonitorStatus; assetError:string; setAssetError(message:string):void;
 sample: ViewSample; selected: string|null; select(id:string|null):void; tool:Tool; setTool(tool:Tool):void;
 target:LocalTarget|null; editJoint(name:string,value:number):void; editTcp(position:Vec3):void; cancelTarget():void;
 notice:string; setNotice(message:string):void; events:TimelineEvent[]; log(message:string):void;
 interacting:boolean; setInteracting(active:boolean):void; view:{current:WorkbenchScene|null};
 ghost:boolean; setGhost(visible:boolean):void; world:boolean; setWorld(visible:boolean):void;
}
export const WorkbenchContext=createContext<Workspace|null>(null);
export function useWorkbench(){const w=useContext(WorkbenchContext);if(!w)throw new Error('WorkbenchContext missing');return w;}
