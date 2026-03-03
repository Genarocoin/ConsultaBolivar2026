# create_banners.py
from PIL import Image, ImageDraw, ImageFont
import os

# Asegurarse que la carpeta static existe
os.makedirs('static', exist_ok=True)

def create_banner(filename, text_lines, bg_color='#1B4F9B'):
    # Crear imagen de 1200x300 píxeles
    img = Image.new('RGB', (1200, 300), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Intentar usar una fuente del sistema
    try:
        # Para Windows
        font = ImageFont.truetype("arial.ttf", 40)
        font_small = ImageFont.truetype("arial.ttf", 30)
    except:
        try:
            # Para Linux
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except:
            # Usar fuente por defecto
            font = ImageFont.load_default()
            font_small = ImageFont.load_default()
    
    y_position = 50
    for i, line in enumerate(text_lines):
        if i == 0:  # Primera línea más grande
            draw.text((100, y_position), line.strip(), fill='white', font=font)
            y_position += 60
        else:
            draw.text((120, y_position), line.strip(), fill='#F5A623' if 'AQUÍ' in line else 'white', font=font_small)
            y_position += 45
    
    # Guardar imagen
    img.save(f'static/{filename}')
    print(f"✅ Creado: static/{filename}")

# Texto del banner
banner_text = [
    "CONSULTA",
    "POPULAR NACIONAL",
    "2026",
    "¡AQUÍ MANDA EL PUEBLO!",
    "",
    "CENTROS Y",
    "MESAS ELECTORALES",
    "PARA LA CONSULTA POPULAR NACIONAL DEL 8M"
]

# Crear ambos banners (puedes usar diferentes colores)
create_banner('banner_header.jpg', banner_text, bg_color='#1B4F9B')  # Azul
create_banner('banner_footer.jpg', banner_text, bg_color='#D7263D')  # Rojo

print("¡Banners creados exitosamente!")