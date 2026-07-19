import { useEffect, useRef, useState, useCallback } from 'react';
import { Panel } from './Panel';

interface BlenderEmbedProps {
  backendPort?: number;
}

type Mode = 'sphere' | 'anatomy' | 'both';

export function BlenderEmbed({ backendPort = 8766 }: BlenderEmbedProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<Mode>('sphere');
  const [world, setWorld] = useState<{name: string; description: string; difficulty: number; tags: string[]} | null>(null);
  const [fps, setFps] = useState(0);
  const [status, setStatus] = useState('Connecting...');
  const [emotion, setEmotion] = useState('neutral');
  const [drives, setDrives] = useState<Record<string, number>>({});
  const [autonomousStatus, setAutonomousStatus] = useState('');
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const frameCount = useRef(0);
  const lastFpsTime = useRef(Date.now());
  const [blenderPort, setBlenderPort] = useState<number>(backendPort + 1);

  // Get dynamic blender port from electron API
  useEffect(() => {
    if (typeof window !== 'undefined' && (window as any).electronAPI?.getBlenderPort) {
      (window as any).electronAPI.getBlenderPort().then((port: number) => {
        setBlenderPort(port);
      }).catch(() => {
        // fallback to backendPort + 1
      });
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
      const ws = new WebSocket(`ws://127.0.0.1:${blenderPort}`);
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
          } else if (msg.type === 'status') {
            if (msg.payload.emotion) setEmotion(msg.payload.emotion);
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
        setConnectionError('Connection failed - is Blender running?');
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
    <div ref={containerRef} className="relative w-full h-full glass-panel overflow-hidden">
      <canvas
        ref={canvasRef}
        width={480}
        height={360}
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
            <p className="text-text-primary font-medium mb-1">Blender Connection Failed</p>
            <p className="text-text-secondary text-sm mb-4">{connectionError}</p>
            <button
              onClick={() => window.location.reload()}
              className="btn-ghost px-4 py-2"
            >
              Retry Connection
            </button>
          </div>
        </div>
      )}

      {connected && (
        <Panel
          title="Telemetry"
          className="absolute top-2 left-2 w-48"
          accentGlow
        >
          <div className="space-y-1 font-mono text-xs">
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
              <span className="text-text-primary truncate max-w-[120px]">{world?.name || 'none'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-tertiary">Emotion</span>
              <span className="text-text-primary capitalize">{emotion}</span>
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

      {/* Autonomous status banner */}
      {autonomousStatus && connected && (
        <div className="absolute bottom-2 left-2 right-2 glass-panel rounded-lg px-3 py-2 text-xs animate-slide-up">
          <div className="flex items-center gap-2">
            <span className="status-dot status-dot-active" />
            <span className="text-text-secondary flex-1 truncate">{autonomousStatus}</span>
          </div>
        </div>
      )}

      {/* Mode segmented control */}
      <div className="absolute bottom-2 right-2 flex items-center gap-1 glass-panel rounded-lg p-1">
        {['sphere', 'anatomy', 'both'].map((m) => (
          <button
            key={m}
            onClick={() => { setMode(m as Mode); sendCommand(`mode:${m}`); }}
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
    </div>
  );
}