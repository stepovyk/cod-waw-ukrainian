"""Графіка для релізу: банер інсталятора, обкладинки для сторінок, значок, аватар Telegram, скріншоти.
Фони – скріншоти локалізованої гри (work/shots), шрифт – Fira Sans Condensed.
python tools/make_art.py"""
import sys, pathlib
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / '.deps'))
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

SHOTS = ROOT / 'work' / 'shots'
ART = ROOT / 'work' / 'art'
INST = ROOT / 'tools' / 'installer'
FONT = ROOT / 'fonts'
BLUE, YELLOW, WHITE = (0, 87, 183), (255, 213, 0), (245, 245, 245)


def font(weight, size):
    return ImageFont.truetype(str(FONT / f'FiraSansCondensed-{weight}.ttf'), size)


BACKS = {  # чисті ділянки скріншотів, без тексту гри
    'castle': ('06-mp-team.png', (300, 125, 1100, 440)),
    'beach': ('mission-52.png', (180, 0, 1600, 590)),
}


def backdrop(src, size, darken=0.6, blur=1.2):
    file, box = BACKS[src]
    im = Image.open(SHOTS / file).convert('RGB').crop(box)
    w, h = size
    scale = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    im = im.crop((x, y, x + w, y + h)).filter(ImageFilter.GaussianBlur(blur))
    im = ImageEnhance.Brightness(im).enhance(darken)
    # м'яке затемнення зліва, щоб текст читався
    shade = Image.linear_gradient('L').rotate(90).resize(size)
    black = Image.new('RGB', size, (8, 9, 11))
    return Image.composite(im, black, shade.point(lambda v: 90 + v * 165 // 255))


def flag_bar(draw, x, y, w, h):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=BLUE)
    draw.rounded_rectangle((x + w // 2, y, x + w, y + h), radius=h // 2, fill=YELLOW)
    draw.rectangle((x + w // 2, y, x + w // 2 + h, y + h), fill=YELLOW)


def title_card(size, src, pad, title_size, sub_size, tag=None):
    w, h = size
    im = backdrop(src, size)
    d = ImageDraw.Draw(im)
    t1 = font('Bold', title_size)
    t2 = font('Bold', sub_size)
    small = font('Medium', max(14, sub_size // 3))
    y = (h - (title_size * 2 + sub_size + pad)) // 2
    d.text((pad, y), 'CALL OF DUTY', font=t1, fill=WHITE)
    d.text((pad, y + title_size), 'WORLD AT WAR', font=t1, fill=WHITE)
    yb = y + title_size * 2 + pad // 3
    flag_bar(d, pad, yb, round(sub_size * 0.9), round(sub_size * 0.16))
    d.text((pad, yb + round(sub_size * 0.32)), 'УКРАЇНСЬКОЮ', font=t2, fill=YELLOW)
    if tag:
        d.text((pad, h - pad // 2 - small.size), tag, font=small, fill=(190, 194, 200))
    return im


def emblem(size):
    """Знак «Ї»: суцільний синій квадрат зі скругленням, жовта літера."""
    s = size * 4
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=s // 5, fill=BLUE)
    f = font('Bold', round(s * 0.78))
    l, t, r, b = d.textbbox((0, 0), 'Ї', font=f, anchor='ls')
    d.text(((s - (r - l)) // 2 - l, (s - (b - t)) // 2 - t), 'Ї', font=f, fill=YELLOW, anchor='ls')
    return im.resize((size, size), Image.LANCZOS)


def avatar(size):
    """Аватар Telegram (обрізається колом): синє тло на весь квадрат, жовта «Ї»."""
    s = size * 2
    im = Image.new('RGB', (s, s), BLUE)
    d = ImageDraw.Draw(im)
    f = font('Bold', round(s * 0.62))
    l, t, r, b = d.textbbox((0, 0), 'Ї', font=f, anchor='ls')
    d.text(((s - (r - l)) // 2 - l, (s - (b - t)) // 2 - t), 'Ї', font=f, fill=YELLOW, anchor='ls')
    return im.resize((size, size), Image.LANCZOS)


def main():
    ART.mkdir(parents=True, exist_ok=True)
    title_card((1200, 400), 'castle', 64, 92, 74).save(INST / 'banner.png')
    tag = 'Українська локалізація від Stepovyk'
    title_card((1920, 1080), 'beach', 140, 190, 150, tag).save(ART / 'cover-1920x1080.jpg', quality=92)
    title_card((1280, 640), 'beach', 96, 118, 94, tag).save(ART / 'social-1280x640.png')
    title_card((1280, 720), 'castle', 96, 128, 100, tag).save(ART / 'cover-1280x720.jpg', quality=92)
    emblem(256).save(INST / 'icon.ico', sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    emblem(512).save(ART / 'emblem-512.png')
    avatar(640).save(ART / 'telegram-avatar.png')
    shots = ['01-menu', 'mission-44', 'mission-52', '04-missions', '02-settings', '05-zombies', '06-mp-team', '07-mp-class']
    for i, name in enumerate(shots, 1):
        Image.open(SHOTS / f'{name}.png').convert('RGB').save(ART / f'screen-{i:02d}.jpg', quality=92)
    full = Image.open(SHOTS / 'dialog_full.png').convert('RGB')
    full.crop((760, 425, 1160, 650)).save(ART / 'screen-09-windows.png')
    print('готово:', ART)


if __name__ == '__main__':
    main()
