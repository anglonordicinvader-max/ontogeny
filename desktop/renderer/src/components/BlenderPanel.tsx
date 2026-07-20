import { useState } from 'react';
import { BlenderEmbed } from './BlenderEmbed';

interface BlenderPanelProps {
  backendPort?: number;
}

export function BlenderPanel({ backendPort = 8766 }: BlenderPanelProps) {
  const [worldSelectorOpen, setWorldSelectorOpen] = useState(false);

  return (
    <div className="h-full flex flex-col relative">
      <BlenderEmbed backendPort={backendPort} />

      {/* Feature overlay */}
      <div className="absolute top-2 right-2 glass-panel rounded-lg p-3 text-xs max-w-xs animate-panel-in">
        <div className="font-medium mb-2 text-text-primary">Blender Sandbox</div>
        <div className="space-y-1 text-text-secondary">
          <div>• 3D scene rendering with Cycles</div>
          <div>• TOCABI humanoid embodiment (38 meshes)</div>
          <div>• Autonomous world selection (39 worlds)</div>
          <div>• Emotion-driven visualization</div>
          <div>• Real-time agent synchronization</div>
        </div>
        <button
          onClick={() => setWorldSelectorOpen(!worldSelectorOpen)}
          className="mt-2 btn-ghost w-full text-left text-xs"
        >
          {worldSelectorOpen ? 'Hide' : 'Show'} World Selector
        </button>
      </div>

      {worldSelectorOpen && (
        <div className="absolute top-36 right-2 glass-panel rounded-lg p-4 text-xs max-w-sm animate-panel-in">
          <div className="font-medium mb-3 text-text-primary">World Selection</div>
          <div className="space-y-2 text-text-secondary">
            <div>• Selects worlds based on agent goals and skill needs</div>
            <div>• Balances difficulty with current capabilities</div>
            <div>• Adapts to intrinsic drives (curiosity, mastery)</div>
            <div>• Prevents repetition and ensures variety</div>
          </div>
          <div className="mt-3 p-2 glass-subtle rounded border border-border-subtle">
            <div className="font-medium mb-1 text-text-primary">Selection Criteria</div>
            <div className="text-text-tertiary text-[11px] leading-relaxed">
              <div>• Weak skills analysis</div>
              <div>• Goal alignment</div>
              <div>• Difficulty progression</div>
              <div>• Historical variety</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
