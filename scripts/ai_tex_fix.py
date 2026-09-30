"""System python (cv2): clean AI duck textures. Run in assets/ai_duck after ai_duck_fix.py."""
import cv2, numpy as np
S = 2048
uv = np.load('ridge_uv.npy'); w = np.load('ridge_w.npy')
mask = np.zeros((S, S), np.float32)
for tri, ww in zip(uv[w > 0.05], w[w > 0.05]):
    pts = np.round(np.column_stack([tri[:, 0] * S, (1 - tri[:, 1]) * S])).astype(np.int32)
    cv2.fillConvexPoly(mask, pts, float(ww))
mask = cv2.GaussianBlur(cv2.dilate(mask, np.ones((7, 7), np.uint8)), (0, 0), 4)[..., None]
eye = cv2.imread('eye_mask_wide.png', 0)
diff = cv2.imread('texture_diffuse.png'); nrm = cv2.imread('texture_normal.png')
diff = cv2.inpaint(diff, eye, 15, cv2.INPAINT_TELEA)
valid = (diff.sum(2) > 30).astype(np.float32)[..., None]
blur = cv2.GaussianBlur(diff.astype(np.float32) * valid, (0, 0), 14) / np.maximum(cv2.GaussianBlur(valid, (0, 0), 14)[..., None], 1e-3)
# cream sampled from clean body texels right next to the repaired area
ring = (cv2.dilate((mask[..., 0] > 0.1).astype(np.uint8), np.ones((31, 31), np.uint8)) > 0) & (mask[..., 0] < 0.02)
lum = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
cream = np.median(diff[ring & (lum > 170)], axis=0)
noise = cv2.GaussianBlur(np.random.default_rng(1).normal(0, 1, diff.shape[:2]).astype(np.float32), (0, 0), 6)[..., None] * 18
fill = np.clip(cream[None, None, :] + noise * 0.25, 0, 255)
mm = np.clip(mask * 1.3, 0, 1)
diff = (diff * (1 - mm) + fill * mm).clip(0, 255).astype(np.uint8)
print('cream BGR', cream)
flat = np.zeros_like(nrm, np.float32); flat[:] = (255, 128, 128)
em = cv2.GaussianBlur(cv2.dilate(eye, np.ones((15, 15), np.uint8)).astype(np.float32) / 255, (0, 0), 4)[..., None]
m2 = np.maximum(mask, em)
nrm = (nrm * (1 - m2) + flat * m2).astype(np.uint8)
cv2.imwrite('texture_diffuse_fixed.png', diff); cv2.imwrite('texture_normal_fixed.png', nrm)
print('mask coverage', float((mask > 0.1).mean()))
