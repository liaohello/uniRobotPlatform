// Diagnostics snapshot shared with the ?inspect hook. It is not application
// state: React state stays in App/Layout, this mirror only feeds verification
// so a browser check can read layout facts without reaching into Dockview.
export interface PanelFacts { open: boolean; width: number | null; height: number | null }
export const uiSnapshot: {
  preset: string; maximized: boolean; panels: Record<string, PanelFacts>;
  fullscreen: boolean; fullscreenSupported: boolean; fullscreenReason: string;
  drawer: string; canvas: { width: number; height: number } | null;
} = { preset:'standard', maximized:false, panels:{}, fullscreen:false, fullscreenSupported:false, fullscreenReason:'', drawer:'none', canvas:null };
