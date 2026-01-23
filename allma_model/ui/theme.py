from kivy.utils import get_color_from_hex
from kivy.graphics.texture import Texture

class Theme:
    """
    Ethereal / Soft Minimal Theme
    Palette based on 'Sweet/Delicate' user request (Blues, Purples, White)
    """
    # Names are semantic

    # Background Gradient (Vertical: Top -> Bottom)
    # Light Blue/Periwinkle to White
    bg_start = get_color_from_hex('#E3F2FD') 
    bg_end = get_color_from_hex('#FFFFFF')

    # Primary Accents (Soft Purple/Blue)
    primary = get_color_from_hex('#7F5AF0') 
    secondary = get_color_from_hex('#A78BFA') # Lighter purple

    # Text
    text_primary = get_color_from_hex('#2D3436') # Soft Black
    text_secondary = get_color_from_hex('#636E72') # Grey
    text_light = get_color_from_hex('#FFFFFF') # White text

    # Chat Bubbles
    bubble_user_bg = get_color_from_hex('#7F5AF0') # Purple
    bubble_bot_bg = get_color_from_hex('#F3F4F6')  # Very light grey/white
    
    # Input field
    input_bg = get_color_from_hex('#FFFFFF')
    input_border = get_color_from_hex('#E5E7EB')

    @staticmethod
    def get_vertical_gradient_texture(color_top, color_bottom):
        """
        Creates a 1x2 pixel texture for vertical gradient
        """
        texture = Texture.create(size=(1, 2), colorfmt='rgba')
        
        # Convert rgba tuples (0-1) to bytes (0-255)
        # Top color at index 1 (since texture coord 0,0 is bottom-left usually, checks needed)
        # Kivy texture: 0 is bottom row, 1 is top row.
        
        def to_bytes(color):
            return [int(c * 255) for c in color]

        buf = bytes(to_bytes(color_bottom) + to_bytes(color_top))
        texture.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
        return texture
