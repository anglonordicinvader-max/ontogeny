import { Panel } from './Panel';
import { BlenderEmbed } from './BlenderEmbed';

interface BlenderPanelProps {
  backendPort?: number;
}

export function BlenderPanel({ backendPort = 8766 }: BlenderPanelProps) {
  return (
    <div className="h-full flex flex-col p-4 gap-4">
      <BlenderEmbed backendPort={backendPort} />
      <Panel title="Simulation Controls">
        <div className="flex items-center gap-2">
          <button className="btn-ghost">Play</button>
          <button className="btn-ghost">Pause</button>
          <button className="btn-ghost">Reset</button>
          <button className="btn-ghost">Step</button>
        </div>
      </Panel>
    </div>
  );
}
