import bpy
import sys
import json
import asyncio
import websockets
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import io
import base64

class BlenderFrameServer:
    def __init__(self):
        self.frame_data = None
        self.clients = set()
        self.running = True
    
    def capture_frame(self):
        bpy.context.scene.render.filepath = '//'
        bpy.ops.render.render(write_still=False)
        
        scene = bpy.context.scene
        scale = scene.render.resolution_percentage / 100
        width = int(scene.render.resolution_x * scale)
        height = int(scene.render.resolution_y * scale)
        
        pixels = bpy.context.scene.render.image_pixels
        pixel_data = [pixels[i] for i in range(len(pixels))]
        
        import struct
        import zlib
        
        def create_png(width, height, pixels):
            def chunk(chunk_type, data):
                c = chunk_type + data
                crc = zlib.crc32(c) & 0xffffffff
                return struct.pack('>I', len(data)) + c + struct.pack('>I', crc)
            
            signature = b'\x89PNG\r\n\x1a\n'
            ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
            
            raw_data = b''
            for y in range(height):
                raw_data += b'\x00'
                for x in range(width):
                    idx = (y * width + x) * 4
                    raw_data += struct.pack('BBB', 
                        int(pixels[idx] * 255),
                        int(pixels[idx + 1] * 255),
                        int(pixels[idx + 2] * 255))
            
            compressed = zlib.compress(raw_data)
            
            png = signature
            png += chunk(b'IHDR', ihdr)
            png += chunk(b'IDAT', compressed)
            png += chunk(b'IEND', b'')
            
            return png
        
        png_data = create_png(width, height, pixel_data)
        self.frame_data = base64.b64encode(png_data).decode('ascii')
        return self.frame_data
    
    async def handler(self, websocket, path):
        self.clients.add(websocket)
        try:
            while self.running:
                if self.frame_data:
                    await websocket.send(json.dumps({
                        'type': 'frame',
                        'data': self.frame_data
                    }))
                await asyncio.sleep(1/30)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
    
    async def broadcast_frame(self):
        while self.running:
            self.capture_frame()
            if self.clients:
                message = json.dumps({
                    'type': 'frame',
                    'data': self.frame_data
                })
                await asyncio.gather(*[
                    client.send(message) for client in self.clients.copy()
                ], return_exceptions=True)
            await asyncio.sleep(1/30)

def main():
    port = 8766
    for arg in sys.argv:
        if arg.startswith('--port='):
            port = int(arg.split('=')[1])
    
    server = BlenderFrameServer()
    
    async def run():
        async with websockets.serve(server.handler, '127.0.0.1', port):
            await server.broadcast_frame()
    
    asyncio.run(run())

if __name__ == '__main__':
    main()
