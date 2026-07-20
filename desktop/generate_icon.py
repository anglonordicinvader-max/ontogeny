"""Generate the Ontogeny app icon: white infinity symbol on black with geometric grid."""
from PIL import Image, ImageDraw
import math
import os

def create_icon(size=512):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2

    # --- Grid: hexagonal lattice with dots at intersections ---
    grid_r = size * 0.42
    spacing = size * 0.14

    points = []
    for row in range(-5, 6):
        for col in range(-5, 6):
            x = cx + col * spacing + (row % 2) * (spacing * 0.5)
            y = cy + row * (spacing * 0.866)
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist <= grid_r:
                points.append((x, y))

    line_color = (255, 255, 255, 180)
    line_w = max(1, size // 300)
    for i, (x1, y1) in enumerate(points):
        for j, (x2, y2) in enumerate(points):
            if i >= j:
                continue
            dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if dist < spacing * 1.15:
                draw.line([(x1, y1), (x2, y2)], fill=line_color, width=line_w)

    dot_r = max(2, size // 160)
    for x, y in points:
        draw.ellipse(
            [x - dot_r, y - dot_r, x + dot_r, y + dot_r],
            fill=(255, 255, 255, 255),
        )

    # --- Infinity symbol (lemniscate of Bernoulli) ---
    inf_scale = size * 0.28
    thickness = max(3, size // 65)

    num_pts = 500
    curve_pts = []
    for i in range(num_pts + 1):
        t = 2 * math.pi * i / num_pts
        denom = 1 + math.sin(t) ** 2
        x = cx + inf_scale * math.cos(t) / denom
        y = cy + inf_scale * math.sin(t) * math.cos(t) / denom
        curve_pts.append((x, y))

    # Draw thick infinity
    for k in range(len(curve_pts) - 1):
        draw.line([curve_pts[k], curve_pts[k + 1]], fill=(255, 255, 255, 255), width=thickness)

    return img


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    public = os.path.join(base, "renderer", "public")

    # Generate all sizes
    sizes = [16, 32, 48, 64, 128, 256, 512]
    images = [create_icon(s) for s in sizes]

    # Save ICO — Pillow needs all images passed as append_images
    ico_path = os.path.join(public, "icon.ico")
    # The first image is the base; append the rest
    base_img = images[0].copy()
    base_img.save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"Saved ICO: {ico_path} ({os.path.getsize(ico_path)} bytes)")

    # Save PNG
    png_path = os.path.join(public, "icon.png")
    images[-1].save(png_path, format="PNG")
    print(f"Saved PNG: {png_path} ({os.path.getsize(png_path)} bytes)")


if __name__ == "__main__":
    main()
