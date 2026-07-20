import { BlenderEmbed } from './BlenderEmbed';

interface BlenderPanelProps {
  backendPort?: number;
  onCommand?: (command: string) => void;
}

export function BlenderPanel({ backendPort = 8766, onCommand }: BlenderPanelProps) {
  return (
    <div className="h-full flex flex-col relative">
      <BlenderEmbed backendPort={backendPort} onCommand={onCommand} />
    </div>
  );
}
