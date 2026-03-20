"""
Generate simple PNG icons for the PWA manifest.
Uses only Python standard library.
"""
import struct
import zlib
import os

def create_png(width, height, color_rgb, text="🏸"):
    """Create a minimal PNG file with a solid color background."""
    # Create raw pixel data (RGBA)
    raw_data = b''
    bg_r, bg_g, bg_b = color_rgb
    
    # Create a simple icon with the club green color
    for y in range(height):
        raw_data += b'\x00'  # Filter byte (none)
        for x in range(width):
            # Create a rounded-rectangle-ish shape with padding
            margin = width // 8
            if margin < x < width - margin and margin < y < height - margin:
                # Inner area - gradient effect
                factor = 1.0 - (abs(x - width/2) / (width/2)) * 0.15 - (abs(y - height/2) / (height/2)) * 0.15
                r = max(0, min(255, int(bg_r * factor)))
                g = max(0, min(255, int(bg_g * factor)))
                b = max(0, min(255, int(bg_b * factor)))
                
                # Add a simple padel racket shape in the center
                cx, cy = width // 2, height // 2
                dx, dy = abs(x - cx), abs(y - cy)
                
                # Racket head (ellipse)
                head_w, head_h = width // 5, height // 4
                in_head = (dx * dx) / (head_w * head_w) + ((dy - height//8) * (dy - height//8)) / (head_h * head_h) < 1
                
                # Handle
                handle_w = width // 16
                in_handle = dx < handle_w and height // 8 + head_h - 5 < (y - cy) < height // 3
                
                if in_head or in_handle:
                    raw_data += bytes([255, 255, 255, 255])  # White
                else:
                    raw_data += bytes([r, g, b, 255])
            else:
                raw_data += bytes([bg_r, bg_g, bg_b, 255])
    
    # Compress
    compressed = zlib.compress(raw_data)
    
    def make_chunk(chunk_type, data):
        chunk = chunk_type + data
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', zlib.crc32(chunk) & 0xffffffff)
    
    # Build PNG
    png = b'\x89PNG\r\n\x1a\n'
    
    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    png += make_chunk(b'IHDR', ihdr_data)
    
    # IDAT
    png += make_chunk(b'IDAT', compressed)
    
    # IEND
    png += make_chunk(b'IEND', b'')
    
    return png


if __name__ == '__main__':
    icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'icons')
    os.makedirs(icons_dir, exist_ok=True)
    
    green = (26, 86, 50)  # West Hants green
    
    # 192x192
    png_192 = create_png(192, 192, green)
    with open(os.path.join(icons_dir, 'icon-192.png'), 'wb') as f:
        f.write(png_192)
    
    # 512x512
    png_512 = create_png(512, 512, green)
    with open(os.path.join(icons_dir, 'icon-512.png'), 'wb') as f:
        f.write(png_512)
    
    print("Icons generated successfully!")
