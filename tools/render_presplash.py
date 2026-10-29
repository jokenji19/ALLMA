"""Render the tiny native launch layout before Python is available.

Code-drawn typography/ring; uses the existing Inter font, no remote asset.
The launch stage has no progress measurements, so no fake percentage is shown.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
DESTINATION=ROOT/'assets/android/presplash.png'


def render():
    scale=3
    canvas=Image.new('RGB',(720*scale,1560*scale),'#FAF9F5')
    draw=ImageDraw.Draw(canvas)
    def font(size):return ImageFont.truetype(str(ROOT/'assets/web/fonts/Inter-Regular.ttf'),size*scale)
    def text(value,y,size,colour):
        draw.text((360*scale,y*scale),value,font=font(size),anchor='mm',fill=colour)
    # A calm optical centre, independent of status/navigation insets.
    text('ALLMA',678,38,'#38352F')
    cx,cy,r=360*scale,792*scale,25*scale
    box=(cx-r,cy-r,cx+r,cy+r)
    draw.ellipse(box,outline='#E6DFD5',width=2*scale)
    draw.arc(box,start=228,end=302,fill='#99694F',width=2*scale)
    text('Preparo il nostro spazio',863,24,'#777268')
    canvas.resize((720,1560),Image.Resampling.LANCZOS).save(DESTINATION,optimize=True)
    return DESTINATION


if __name__=='__main__':print(render())
