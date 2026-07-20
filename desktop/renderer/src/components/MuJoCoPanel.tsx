import { MuJoCoEmbed } from './MuJoCoEmbed';

interface MuJoCoPanelProps {
  backendPort?: number;
}

export function MuJoCoPanel({ backendPort = 8768 }: MuJoCoPanelProps) {
  return (
    <div className="h-full flex flex-col relative">
      <MuJoCoEmbed backendPort={backendPort} />

      {/* Feature overlay */}
      <div className="absolute top-2 right-2 glass-panel rounded-lg p-3 text-xs max-w-xs animate-panel-in">
        <div className="font-medium mb-2 text-text-primary">MuJoCo Sandbox</div>
        <div className="space-y-1 text-text-secondary">
          <div>• Multi-model: TOCABI (33 DOF) + Unitree G1 (29 DOF)</div>
          <div>• PD position control with model-specific gains</div>
          <div>• Standing balance + sinusoidal walking gait</div>
          <div>• IMU + contact force sensors</div>
          <div>• Real-time joint telemetry to UI</div>
        </div>
      </div>
    </div>
  );
}
