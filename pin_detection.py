from collections import deque


def detect_orange_pins(image_path: str, min_area: int = 30) -> list:
    """Detect orange shapes (pins) in a PNG footprint image.

    Returns a list of (x, y, w, h) bounding boxes in original image coordinates.
    Orange heuristic: R dominant, moderate G, low B.
    """
    try:
        from PIL import Image as _PILImage
        import numpy as _np

        img = _PILImage.open(image_path).convert("RGB")
        arr = _np.array(img)
        r = arr[:, :, 0].astype(_np.int32)
        g = arr[:, :, 1].astype(_np.int32)
        b = arr[:, :, 2].astype(_np.int32)

        mask = (r > 150) & (g > 50) & (g < 215) & (b < 100) & ((r - b) > 100)
        if not _np.any(mask):
            return []

        H, W = mask.shape
        CELL = 3
        grid_h = (H + CELL - 1) // CELL
        grid_w = (W + CELL - 1) // CELL
        grid = _np.zeros((grid_h, grid_w), dtype=bool)
        ys, xs = _np.where(mask)
        grid[ys // CELL, xs // CELL] = True

        visited = _np.zeros((grid_h, grid_w), dtype=bool)
        bboxes = []
        for gy in range(grid_h):
            for gx in range(grid_w):
                if grid[gy, gx] and not visited[gy, gx]:
                    queue = deque([(gy, gx)])
                    visited[gy, gx] = True
                    cells = [(gy, gx)]
                    while queue:
                        cy, cx = queue.popleft()
                        for dy in range(-1, 2):
                            for dx in range(-1, 2):
                                ny, nx = cy + dy, cx + dx
                                if 0 <= ny < grid_h and 0 <= nx < grid_w:
                                    if grid[ny, nx] and not visited[ny, nx]:
                                        visited[ny, nx] = True
                                        queue.append((ny, nx))
                                        cells.append((ny, nx))
                    min_gy = min(c[0] for c in cells) * CELL
                    max_gy = min(max(c[0] for c in cells) * CELL + CELL, H)
                    min_gx = min(c[1] for c in cells) * CELL
                    max_gx = min(max(c[1] for c in cells) * CELL + CELL, W)
                    area = (max_gy - min_gy) * (max_gx - min_gx)
                    if area >= min_area:
                        bboxes.append((min_gx, min_gy, max_gx - min_gx, max_gy - min_gy))
        return bboxes
    except Exception:
        return []
