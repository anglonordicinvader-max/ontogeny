import { useEffect, useRef, useState } from 'react';
import { Panel } from './Panel';

interface BlenderEmbedProps {
  backendPort?: number;
}

export function BlenderEmbed({ backendPort = 8766 }: BlenderEmbedProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://127.0.0.1:${backendPort}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setLoading(false);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'frame' && data.data) {
          renderFrame(data.data);
        }
      } catch {
        console.error('Failed to parse frame data');
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setLoading(false);
    };

    ws.onerror = () => {
      setConnected(false);
      setLoading(false);
    };

    return () => {
      ws.close();
    };
  }, [backendPort]);

  const renderFrame = (base64Data: string) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);
    };
    img.src = `data:image/png;base64,${base64Data}`;
  };

  return (
    <Panel title="Blender Sandbox" className="h-full">
      <div className="relative w-full h-full min-h-[400px] bg-surface-0 rounded-md overflow-hidden">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              <div className="text-sm text-text-tertiary">Connecting to Blender...</div>
            </div>
          </div>
        )}
        {!loading && !connected && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="text-sm text-text-tertiary">Blender not connected</div>
              <div className="text-2xs text-text-tertiary">Start Blender to view simulation</div>
            </div>
          </div>
        )}
        <canvas ref={canvasRef} className="w-full h-full" />
      </div>
    </Panel>
  );
}
