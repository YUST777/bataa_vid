import sys
from PIL import Image
out, *ims = sys.argv[1:]
ims = [Image.open(i) for i in ims]
w, h = ims[0].size
cols = 2
rows = (len(ims) + 1) // 2
g = Image.new("RGB", (w * cols, h * rows))
for i, im in enumerate(ims):
    g.paste(im.resize((w, h)), ((i % cols) * w, (i // cols) * h))
g.save(out)
