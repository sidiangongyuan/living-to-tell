from PIL import Image, ImageDraw, ImageFont

# Create 1024x1024 blue background
img = Image.new('RGB', (1024, 1024), color='#2563eb')
draw = ImageDraw.Draw(img)

# Try to load Arial font, fall back to default
try:
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 600)
except:
    font = ImageFont.load_default()

# Draw white "W"
draw.text((300, 150), 'W', fill='white', font=font)

# Save
img.save('icon.png')
print('Icon created: icon.png')
