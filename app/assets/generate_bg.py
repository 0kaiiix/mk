from PIL import Image, ImageDraw

# 建立新圖片
img = Image.new('RGBA', (500, 500), (255, 255, 255, 20))
draw = ImageDraw.Draw(img)

# 繪製花紋
for i in range(50):
    draw.ellipse([(i*20-10, i*10), (i*20+10, i*10+20)], fill=(255, 150, 180, 10))
for i in range(50):
    draw.ellipse([(i*10, i*20-10), (i*10+20, i*20+10)], fill=(255, 100, 150, 10))

# 儲存圖片
img.save('bg_pattern.png')
print('背景圖案已保存至 bg_pattern.png') 