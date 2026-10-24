import type { CSSProperties } from 'react';
const paths:Record<string,string>={
 cube:'m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3ZM4 7.5l8 4.5 8-4.5M12 12v9',
 play:'m8 5 11 7-11 7V5Z', layers:'m12 3 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 16l9 5 9-5',
 cursor:'m5 3 15 9-7 1-4 7L5 3Z', joint:'M7 5a3 3 0 1 0 0 .01M17 17a3 3 0 1 0 0 .01M9 7l6 8',
 tcp:'M12 2v7m0 6v7M2 12h7m6 0h7M12 8l4 4-4 4-4-4 4-4Z', camera:'M4 7h4l2-3h4l2 3h4v13H4V7Zm8 3a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z',
 tree:'M5 3v13h4M5 8h4m0-2h9v4H9V6Zm0 8h9v4H9v-4Z', chart:'M4 3v17h17M7 15l4-6 4 3 5-7',
 focus:'M3 8V3h5m8 0h5v5m0 8v5h-5m-8 0H3v-5M8 12h8m-4-4v8', reset:'M4 10a8 8 0 1 1 1 8M4 3v7h7',
 save:'M4 3h13l3 3v15H4V3Zm4 0v6h8V3M8 21v-7h8v7', eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Zm10-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z',
 info:'M12 10v7m0-10v.1M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Z', chevron:'m9 5 7 7-7 7', arrow:'M4 12h16m-6-6 6 6-6 6',
 close:'m6 6 12 12M6 18 18 6', check:'m4 12 5 5L20 6', terminal:'m4 6 5 6-5 6m8 0h8', stop:'M5 5h14v14H5V5Z',
 zoomIn:'M10.5 4a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13Zm4.8 11.3L21 21M10.5 7.5v6m-3-3h6',
 zoomOut:'M10.5 4a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13Zm4.8 11.3L21 21M7.5 10.5h6',
 fit:'M4 9V4h5m6 0h5v5m0 6v5h-5m-6 0H4v-5',
 expand:'M4 10V4h6M20 14v6h-6M4 4l6 6M20 20l-6-6',
 collapse:'M10 4v6H4M14 20v-6h6M10 10 4 4M14 14l6 6',
};
export function Icon({name,size=18,style}:{name:string;size?:number;style?:CSSProperties}){return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}><path d={paths[name]??paths.cube}/></svg>;}
