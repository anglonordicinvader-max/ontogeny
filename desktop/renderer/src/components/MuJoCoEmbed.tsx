import { useEffect, useRef, useState, useCallback } from 'react';
import { Panel } from './Panel';

interface MuJoCoEmbedProps {
  backendPort?: number;
}

interface Telemetry {
  frame: number;
  mode: string;
  robot_model: string;
  body: { pos: number[]; quat: number[]; vel: number[]; angvel: number[] };
  joints: Record<string, { pos: number; vel: number; target: number }>;
  joint_count: number;
  com: number[];
  sensor: {
    imu: { acceleration: number[]; angular_velocity: number[] };
    contacts: { num_contacts: number; total_force: number[]; foot_contact: { left: boolean; right: boolean } };
  };
  controller: { mode: string; walk_phase: number; walk_speed: number; walk_cmd: number[] };
}

export function MuJoCoEmbed({ backendPort = 8768 }: MuJoCoEmbedProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [_mode, setMode] = useState<string>('anatomy');
  const [controlMode, setControlMode] = useState<string>('stand');
  const [_world, setWorld] = useState<{ name: string; description: string; difficulty: number; tags: string[] } | null>(null);
  const [fps, setFps] = useState(0);
  const [status, setStatus] = useState('Connecting...');
  const [_emotion, setEmotion] = useState('neutral');
  const [drives, setDrives] = useState<Record<string, number>>({});
  const [autonomousStatus, setAutonomousStatus] = useState('');
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const frameCount = useRef(0);
  const lastFpsTime = useRef(Date.now());
  const [mujocoPort, setMuJoCoPort] = useState<number>(backendPort);

  useEffect(() => {
    if (typeof window !== 'undefined' && (window as any).electronAPI?.getMuJoCoPort) {
      (window as any).electronAPI.getMuJoCoPort().then((port: number) => {
        setMuJoCoPort(port);
      }).catch(() => {});
    }
  }, [backendPort]);

  const sendCommand = useCallback((command: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'command', command }));
    }
  }, []);

  useEffect(() => {
    let retryTimeout: ReturnType<typeof setTimeout>;
    let retryCount = 0;
    const MAX_RETRY_DELAY = 30000;
    const BASE_DELAY = 1000;

    const connect = () => {
      setConnectionError(null);
      const ws = new WebSocket(`ws://127.0.0.1:${mujocoPort}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setLoading(false);
        setStatus('Streaming');
        setConnectionError(null);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'frame' && msg.data) {
            renderFrame(msg.data);
            if (msg.mode) setMode(msg.mode);
            if (msg.world) setWorld(msg.world);
            if (msg.emotion) setEmotion(msg.emotion);
            if (msg.blend_drives) setDrives(msg.blend_drives);
            frameCount.current++;
            const now = Date.now();
            if (now - lastFpsTime.current >= 1000) {
              setFps(frameCount.current);
              frameCount.current = 0;
              lastFpsTime.current = now;
            }
          } else if (msg.type === 'telemetry') {
            setTelemetry(msg as Telemetry);
            if (msg.controller?.mode) setControlMode(msg.controller.mode);
          } else if (msg.type === 'blend') {
            if (msg.payload.blend_mode) setMode(msg.payload.blend_mode);
            if (msg.payload.blend_world) setWorld({ name: msg.payload.blend_world, description: '', difficulty: 0.5, tags: [] });
            if (msg.payload.blend_emotion) setEmotion(msg.payload.blend_emotion);
            if (msg.payload.blend_drives) setDrives(msg.payload.blend_drives);
          }
        } catch { /* ignore */ }
      };

      ws.onclose = () => {
        setConnected(false);
        setLoading(false);
        const delay = Math.min(BASE_DELAY * Math.pow(2, retryCount), MAX_RETRY_DELAY);
        setAutonomousStatus(`Disconnected - retrying in ${(delay / 1000).toFixed(1)}s...`);
        retryCount++;
        retryTimeout = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        setConnectionError('Connection failed - is MuJoCo running?');
        ws.close();
      };
    };

    connect();
    return () => {
      clearTimeout(retryTimeout);
      wsRef.current?.close();
    };
  }, [mujocoPort]);

  const renderFrame = (data: string) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const img = new Image();
    img.onload = () => {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);
      }
    };
    img.src = `data:image/png;base64,${data}`;
  };

  const body = telemetry?.body;
  const sensor = telemetry?.sensor;
  const ctrl = telemetry?.controller;
  const footContact = sensor?.contacts?.foot_contact;

  return (
    <div ref={containerRef} className="relative w-full h-full glass-panel overflow-hidden">
      <canvas
        ref={canvasRef}
        width={640}
        height={480}
        className="w-full h-full object-contain"
      />

      {!connected && loading && (
        <div className="absolute inset-0 flex items-center justify-center glass-panel">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-primary">{status}</p>
            {autonomousStatus && <p className="text-sm text-text-tertiary mt-2">{autonomousStatus}</p>}
          </div>
        </div>
      )}

      {!connected && !loading && connectionError && (
        <div className="absolute inset-0 flex items-center justify-center glass-panel p-4">
          <div className="text-center max-w-md">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-surface-3 flex items-center justify-center">
              <svg className="w-6 h-6 text-status-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <p className="text-text-primary font-medium mb-1">MuJoCo Connection Failed</p>
            <p className="text-text-secondary text-sm mb-4">{connectionError}</p>
            <button onClick={() => window.location.reload()} className="btn-ghost px-4 py-2">
              Retry Connection
            </button>
          </div>
        </div>
      )}

      {/* Top-left: Physics Telemetry */}
      {connected && (
        <Panel title="Physics" className="absolute top-2 left-2 w-56" accentGlow>
          <div className="space-y-1 font-mono text-xs">
            <div className="flex justify-between">
              <span className="text-text-tertiary">FPS</span>
              <span className="text-text-primary tabular-nums">{fps}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-tertiary">Control</span>
              <span className={`font-medium ${controlMode === 'walk' ? 'text-status-success' : controlMode === 'freeze' ? 'text-status-warning' : 'text-text-primary'}`}>
                {controlMode.toUpperCase()}
              </span>
            </div>
            {body && (
              <>
                <div className="pt-1 border-t border-border">
                  <div className="text-text-tertiary uppercase tracking-wide text-[10px] mb-1">Root Body</div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-text-secondary">Position</span>
                    <span className="text-text-primary tabular-nums">z={body.pos[2]?.toFixed(3)}m</span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-text-secondary">Velocity</span>
                    <span className="text-text-primary tabular-nums">{Math.sqrt(body.vel[0]**2 + body.vel[1]**2 + body.vel[2]**2).toFixed(3)} m/s</span>
                  </div>
                </div>
                <div className="pt-1 border-t border-border">
                  <div className="text-text-tertiary uppercase tracking-wide text-[10px] mb-1">IMU</div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-text-secondary">Accel</span>
                    <span className="text-text-primary tabular-nums">{sensor?.imu?.acceleration?.[2]?.toFixed(1) || '—'} m/s²</span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-text-secondary">Gyro</span>
                    <span className="text-text-primary tabular-nums">{sensor?.imu?.angular_velocity?.map((v: number) => v.toFixed(2)).join(', ') || '—'}</span>
                  </div>
                </div>
                <div className="pt-1 border-t border-border">
                  <div className="text-text-tertiary uppercase tracking-wide text-[10px] mb-1">Contacts</div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-text-secondary">Count</span>
                    <span className="text-text-primary tabular-nums">{sensor?.contacts?.num_contacts || 0}</span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-text-secondary">Force</span>
                    <span className="text-text-primary tabular-nums">{sensor?.contacts?.total_force?.map((v: number) => v.toFixed(1)).join(', ') || '0, 0, 0'} N</span>
                  </div>
                  <div className="flex gap-2 text-[11px]">
                    <span className={footContact?.left ? 'text-status-success' : 'text-text-tertiary'}>
                      L-sole {footContact?.left ? '●' : '○'}
                    </span>
                    <span className={footContact?.right ? 'text-status-success' : 'text-text-tertiary'}>
                      R-sole {footContact?.right ? '●' : '○'}
                    </span>
                  </div>
                </div>
              </>
            )}
            {Object.keys(drives).length > 0 && (
              <div className="pt-1 border-t border-border">
                <div className="text-text-tertiary uppercase tracking-wide text-[10px] mb-1">Drives</div>
                {Object.entries(drives).map(([key, val]) => (
                  <div key={key} className="flex justify-between text-[11px]">
                    <span className="text-text-secondary capitalize">{key}</span>
                    <span className={val > 0.6 ? 'text-status-success' : val > 0.3 ? 'text-status-warning' : 'text-text-tertiary'} tabular-nums>
                      {Math.round(val * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Panel>
      )}

      {/* Top-right: Robot model badge */}
      {connected && (
        <div className="absolute top-2 right-2 glass-panel rounded-lg px-3 py-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-status-success"></span>
            <span className="text-text-primary font-medium">{telemetry?.robot_model?.toUpperCase() || 'TOCABI'}</span>
            <span className="text-text-tertiary">{telemetry?.joint_count || 33}-DOF</span>
          </div>
        </div>
      )}

      {/* Bottom-right: Control Mode */}
      {connected && (
        <div className="absolute bottom-2 right-2 flex flex-col items-end gap-1">
          {/* Walk direction */}
          {controlMode === 'walk' && (
            <div className="glass-panel rounded-lg px-3 py-1.5 text-[11px] font-mono">
              <span className="text-text-tertiary">v=</span>
              <span className="text-text-primary">{ctrl?.walk_cmd?.[0]?.toFixed(2) || '0.00'}</span>
              <span className="text-text-tertiary ml-2">w=</span>
              <span className="text-text-primary">{ctrl?.walk_cmd?.[1]?.toFixed(2) || '0.00'}</span>
              <span className="text-text-tertiary ml-2">phase=</span>
              <span className="text-text-primary">{ctrl?.walk_phase?.toFixed(1) || '0.0'}</span>
            </div>
          )}
          <div className="glass-panel rounded-lg p-1 flex gap-1">
            {[
              { key: 'stand', label: 'Stand', color: 'text-status-success' },
              { key: 'walk', label: 'Walk', color: 'text-status-success' },
              { key: 'freeze', label: 'Freeze', color: 'text-status-warning' },
              { key: 'reset', label: 'Reset', color: 'text-status-error' },
            ].map((btn) => (
              <button
                key={btn.key}
                onClick={() => {
                  if (btn.key === 'reset') {
                    sendCommand('reset');
                    setControlMode('stand');
                  } else {
                    sendCommand(btn.key);
                  }
                }}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-150 ${
                  (btn.key === 'reset' ? controlMode === 'stand' : controlMode === btn.key)
                    ? 'bg-surface-elevated text-text-primary shadow-md'
                    : `text-text-secondary hover:text-text-primary hover:bg-surface-3`
                }`}
              >
                {btn.label}
              </button>
            ))}
          </div>
          {/* Walk command slider */}
          {controlMode === 'walk' && (
            <div className="glass-panel rounded-lg px-3 py-2 text-[11px] flex items-center gap-3">
              <div className="flex flex-col items-center">
                <span className="text-text-tertiary mb-0.5">Speed</span>
                <input
                  type="range"
                  min="-1" max="1" step="0.05"
                  defaultValue={ctrl?.walk_cmd?.[0]?.toString() || '0'}
                  onChange={(e) => sendCommand(`walk_cmd:${e.target.value},0`)}
                  className="w-20 accent-[var(--accent-glow)]"
                />
              </div>
              <div className="flex flex-col items-center">
                <span className="text-text-tertiary mb-0.5">Turn</span>
                <input
                  type="range"
                  min="-1" max="1" step="0.05"
                  defaultValue={ctrl?.walk_cmd?.[1]?.toString() || '0'}
                  onChange={(e) => sendCommand(`walk_cmd:0,${e.target.value}`)}
                  className="w-20 accent-[var(--accent-glow)]"
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Bottom: Status */}
      {autonomousStatus && connected && (
        <div className="absolute bottom-2 left-2 glass-panel rounded-lg px-3 py-2 text-xs animate-slide-up">
          <div className="flex items-center gap-2">
            <span className="status-dot status-dot-active" />
            <span className="text-text-secondary flex-1 truncate">{autonomousStatus}</span>
          </div>
        </div>
      )}
    </div>
  );
}
