import { useEffect, useRef, useState, useCallback } from 'react';
import { Panel } from './Panel';
import { Eye } from 'lucide-react';

interface BlenderEmbedProps {
  backendPort?: number;
}

type Mode = 'sphere' | 'anatomy' | 'both';

interface BlenderHealth {
  status: string;
  mode: string;
  world: string | null;
  emotion: string;
  frame: number;
  running: boolean;
}

export function BlenderEmbed({ backendPort = 8766 }: BlenderEmbedProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<Mode>('sphere');
  const [world, setWorld] = useState<{ name: string; description: string; difficulty: number; tags: string[] } | null>(null);
  const [fps, setFps] = useState(0);
  const [emotion, setEmotion] = useState('neutral');
  const [drives, setDrives] = useState<Record<string, number>>({});
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [health, setHealth] = useState<BlenderHealth | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const frameCount = useRef(0);
  const lastFpsTime = useRef(Date.now());
  const [blenderPort, setBlenderPort] = useState<number>(backendPort + 1);

  useEffect(() => {
    if (typeof window !== 'undefined' && (window as any).electronAPI?.getBlenderPort) {
      (window as any).electronAPI.getBlenderPort().then((port: number) => {
        setBlenderPort(port);
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
      const ws = new WebSocket(`ws://127.0.0.1:${blenderPort}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setLoading(false);
        setConnectionError(null);
        retryCount = 0;
        // Request health status
        ws.send(JSON.stringify({ type: 'command', command: 'health' }));
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
          } else if (msg.type === 'health') {
            setHealth({
              status: msg.status,
              mode: msg.mode,
              world: msg.world,
              emotion: msg.emotion,
              frame: msg.frame,
              running: msg.running,
            });
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
        setHealth(null);
        const delay = Math.min(BASE_DELAY * Math.pow(2, retryCount), MAX_RETRY_DELAY);
        retryCount++;
        retryTimeout = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        setConnectionError('Blender is not running or unreachable');
        ws.close();
      };
    };

    connect();
    return () => {
      clearTimeout(retryTimeout);
      wsRef.current?.close();
    };
  }, [blenderPort]);

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

  return (
    <div className="relative w-full h-full glass-panel overflow-hidden">
      <canvas
        ref={canvasRef}
        width={480}
        height={360}
        className="w-full h-full object-contain"
      />

      {/* Loading state */}
      {!connected && loading && (
        <div className="absolute inset-0 flex items-center justify-center glass-panel">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-text-primary text-sm">Connecting to Blender...</p>
          </div>
        </div>
      )}

      {/* Connection error — offline state */}
      {!connected && !loading && (
        <div className="absolute inset-0 flex items-center justify-center glass-panel p-4">
          <div className="text-center max-w-md">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-surface-3 flex items-center justify-center">
              <Eye className="w-6 h-6 text-text-tertiary" />
            </div>
            <p className="text-text-primary font-medium mb-1">Blender Offline</p>
            <p className="text-text-secondary text-sm mb-1">
              {connectionError || 'Blender process not detected'}
            </p>
            <p className="text-text-tertiary text-xs mb-4">
              Start Blender with: blender --background --python blender_simulation.py -- --port {blenderPort}
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

      {/* Telemetry overlay — only when connected */}
      {connected && (
        <Panel
          title="Scene"
          className="absolute top-2 left-2 w-48"
          accentGlow
        >
          <div className="space-y-1 font-mono text-xs">
            <div className="flex justify-between">
              <span className="text-text-tertiary">Status</span>
              <span className="text-status-success">{health?.running ? 'Running' : 'Paused'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-tertiary">FPS</span>
              <span className="text-text-primary tabular-nums">{fps}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-tertiary">Mode</span>
              <span className="text-text-primary capitalize">{mode}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-tertiary">World</span>
              <span className="text-text-primary truncate max-w-[120px]">{world?.name || health?.world || 'none'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-tertiary">Emotion</span>
              <span className="text-text-primary capitalize">{emotion}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-tertiary">Frames</span>
              <span className="text-text-primary tabular-nums">{health?.frame || 0}</span>
            </div>
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

      {/* Mode control */}
      {connected && (
        <div className="absolute bottom-2 right-2 flex items-center gap-1 glass-panel rounded-lg p-1">
          {(['sphere', 'anatomy', 'both'] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); sendCommand(`mode:${m}`); }}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-150 ${
                mode === m
                  ? 'bg-surface-elevated text-text-primary shadow-md'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-3'
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      )}

      {/* Bottom status */}
      {connected && (
        <div className="absolute bottom-2 left-2 glass-panel rounded-lg px-3 py-1.5 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-status-success"></span>
            <span className="text-text-secondary">Blender Connected</span>
          </div>
        </div>
      )}
    </div>
  );
}
