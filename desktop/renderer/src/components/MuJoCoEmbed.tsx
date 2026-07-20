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
  sim_time: number;
  step_count: number;
  avg_step_ms: number;
  sensor: {
    imu: { acceleration: number[]; angular_velocity: number[] };
    contacts: { num_contacts: number; total_force: number[]; foot_contact: { left: boolean; right: boolean } };
  };
  controller: { mode: string; walk_phase: number; walk_speed: number; walk_cmd: number[] };
}

export function MuJoCoEmbed({ backendPort = 8768 }: MuJoCoEmbedProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [controlMode, setControlMode] = useState<string>('stand');
  const [fps, setFps] = useState(0);
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
      setLoading(true);
      const ws = new WebSocket(`ws://127.0.0.1:${mujocoPort}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setLoading(false);
        setConnectionError(null);
        retryCount = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'frame' && msg.data) {
            renderFrame(msg.data);
            frameCount.current++;
            const now = Date.now();
            if (now - lastFpsTime.current >= 1000) {
              setFps(frameCount.current);
              frameCount.current = 0;
              lastFpsTime.current = now;
            }
          } else if (msg.type === 'telemetry' || msg.type === 'health') {
            setTelemetry(msg as Telemetry);
            if (msg.controller?.mode) setControlMode(msg.controller.mode);
          }
        } catch { /* ignore */ }
      };

      ws.onclose = () => {
        setConnected(false);
        setLoading(false);
        setTelemetry(null);
        const delay = Math.min(BASE_DELAY * Math.pow(2, retryCount), MAX_RETRY_DELAY);
        retryCount++;
        retryTimeout = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        setConnectionError('MuJoCo is not running or unreachable');
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
  const isStable = body ? (body.pos[2] > 0.3 && Math.abs(body.vel[2]) < 0.5) : false;

  return (
    <div className="relative w-full h-full glass-panel overflow-hidden">
      <canvas
        ref={canvasRef}
        width={640}
        height={480}
        className="w-full h-full object-contain"
      />

      {/* Loading state */}
      {!connected && loading && (
        <div className="absolute inset-0 flex items-center justify-center glass-panel">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-primary text-sm">Connecting to MuJoCo...</p>
          </div>
        </div>
      )}

      {/* Connection error — offline state */}
      {!connected && !loading && (
        <div className="absolute inset-0 flex items-center justify-center glass-panel p-4">
          <div className="text-center max-w-md">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-surface-3 flex items-center justify-center">
              <svg className="w-6 h-6 text-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
            </div>
            <p className="text-text-primary font-medium mb-1">MuJoCo Offline</p>
            <p className="text-text-secondary text-sm mb-1">
              {connectionError || 'MuJoCo process not detected'}
            </p>
            <p className="text-text-tertiary text-xs mb-4">
              Requires: pip install mujoco and valid robot model
            </p>
            <button
              onClick={() => { setLoading(true); setConnectionError(null); wsRef.current?.close(); }}
              className="btn-ghost px-4 py-2 text-sm"
            >
              Retry Connection
            </button>
          </div>
        </div>
      )}

      {/* Physics telemetry overlay */}
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
            <div className="flex justify-between">
              <span className="text-text-tertiary">Stability</span>
              <span className={isStable ? 'text-status-success' : 'text-status-warning'}>
                {telemetry ? (isStable ? 'Stable' : 'Unstable') : '—'}
              </span>
            </div>
            {body && (
              <>
                <div className="pt-1 border-t border-border">
                  <div className="text-text-tertiary uppercase tracking-wide text-[10px] mb-1">Root Body</div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-text-secondary">Height</span>
                    <span className="text-text-primary tabular-nums">{body.pos[2]?.toFixed(3)}m</span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-text-secondary">Velocity</span>
                    <span className="text-text-primary tabular-nums">{Math.sqrt(body.vel[0]**2 + body.vel[1]**2 + body.vel[2]**2).toFixed(3)} m/s</span>
                  </div>
                </div>
                <div className="pt-1 border-t border-border">
                  <div className="text-text-tertiary uppercase tracking-wide text-[10px] mb-1">Sensors</div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-text-secondary">IMU z-accel</span>
                    <span className="text-text-primary tabular-nums">{sensor?.imu?.acceleration?.[2]?.toFixed(1) || '—'} m/s²</span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-text-secondary">Contacts</span>
                    <span className="text-text-primary tabular-nums">{sensor?.contacts?.num_contacts || 0}</span>
                  </div>
                  <div className="flex gap-2 text-[11px]">
                    <span className={footContact?.left ? 'text-status-success' : 'text-text-tertiary'}>
                      L {footContact?.left ? '●' : '○'}
                    </span>
                    <span className={footContact?.right ? 'text-status-success' : 'text-text-tertiary'}>
                      R {footContact?.right ? '●' : '○'}
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>
        </Panel>
      )}

      {/* Robot model badge */}
      {connected && (
        <div className="absolute top-2 right-2 glass-panel rounded-lg px-3 py-2 text-xs">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isStable ? 'bg-status-success' : 'bg-status-warning'}`}></span>
            <span className="text-text-primary font-medium">{telemetry?.robot_model?.toUpperCase() || 'TOCABI'}</span>
            <span className="text-text-tertiary">{telemetry?.joint_count || '—'}-DOF</span>
          </div>
        </div>
      )}

      {/* Control buttons */}
      {connected && (
        <div className="absolute bottom-2 right-2 flex flex-col items-end gap-1">
          {controlMode === 'walk' && (
            <div className="glass-panel rounded-lg px-3 py-1.5 text-[11px] font-mono">
              <span className="text-text-tertiary">v=</span>
              <span className="text-text-primary">{ctrl?.walk_cmd?.[0]?.toFixed(2) || '0.00'}</span>
              <span className="text-text-tertiary ml-2">w=</span>
              <span className="text-text-primary">{ctrl?.walk_cmd?.[1]?.toFixed(2) || '0.00'}</span>
            </div>
          )}
          <div className="glass-panel rounded-lg p-1 flex gap-1">
            {[
              { key: 'stand', label: 'Stand' },
              { key: 'walk', label: 'Walk' },
              { key: 'freeze', label: 'Freeze' },
              { key: 'reset', label: 'Reset' },
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
                  (btn.key === 'reset' ? false : controlMode === btn.key)
                    ? 'bg-surface-elevated text-text-primary shadow-md'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-3'
                }`}
              >
                {btn.label}
              </button>
            ))}
          </div>
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

      {/* Bottom status */}
      {connected && (
        <div className="absolute bottom-2 left-2 glass-panel rounded-lg px-3 py-1.5 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-status-success"></span>
            <span className="text-text-secondary">MuJoCo Connected</span>
          </div>
        </div>
      )}
    </div>
  );
}
