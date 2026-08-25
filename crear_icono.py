from PIL import Image, ImageDraw
import random
W=512
img = Image.new('RGB', (W,W), '#b8e6f0')
draw = ImageDraw.Draw(img)
for _ in range(40):
    x = random.randint(0,W)
    y = random.randint(0,W)
    r = random.randint(5,20)
    draw.ellipse([x-r,y-r,x+r,y+r], outline='#6ec6d6', width=2, fill='#d6f3f8')
draw.ellipse([150,180,362,400], fill='#4dd0e1', outline='white', width=8)
draw.polygon([(256,80),(150,200),(362,200)], fill='#4dd0e1')
draw.ellipse([200,240,230,270], fill='white')
draw.ellipse([210,250,220,265], fill='black')
draw.arc([280,250,310,270], 0, 180, fill='black', width=3)
draw.arc([220,300,290,330], 0, 180, fill='black', width=3)
draw.ellipse([340,270,400,330], fill='#4dd0e1', outline='white', width=4)
img.save('logo.png')
import os
os.makedirs('static', exist_ok=True)
img.save('static/logo.png')
print('logo.png 512x512 creado')
