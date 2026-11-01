"""Переклад текстів, які розробники вписали в меню буквально (без @-ключа локалізації).
Такі рядки лежать усередині зон меню, тому правляться на місці: новий текст доповнюється пробілами
до тієї ж довжини в байтах, щоб структура fastfile не змінилася. Вирівнювання пробілами залежить від
того, як елемент вирівняно в меню: 'r' – пробіли зліва, 'l' – справа, 'c' – порівну.
Кандидатів знайдено пошуком англійських фраз у розпакованих зонах (не записи локалізації)."""
import sys, zlib, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from paths import OUT, original

LITERALS = [
    # (англійською, українською, вирівнювання)
    ('Change Stance', 'Зміна стійки', 'r'),
    ('Launch Without Mods', 'Запустити без модів', 'l'),
    ('Unable to apply settings while connected to a server.',
     'Не можна змінити налаштування, поки ви на сервері.', 'c'),
    ('Yes', 'Так', 'l'),
]
ZONES = {
    'ui': ['Change Stance', 'Launch Without Mods'],
    'common': ['Change Stance'],
    'patch': ['Yes'],
    'ui_mp': ['Unable to apply settings while connected to a server.'],
    'common_mp': ['Unable to apply settings while connected to a server.'],
}


def pad(text, size, align):
    gap = size - len(text)
    assert gap >= 0, text
    if align == 'r':
        return ' ' * gap + text
    if align == 'l':
        return text + ' ' * gap
    return ' ' * (gap // 2) + text + ' ' * (gap - gap // 2)


def main():
    table = {en: (uk, al) for en, uk, al in LITERALS}
    for zone, items in ZONES.items():
        src = original(f'zone/english/{zone}.ff').read_bytes()
        raw = bytearray(zlib.decompress(src[12:]))
        total = 0
        for en in items:
            uk, al = table[en]
            old = en.encode('ascii')
            new = pad(uk, len(old), al).encode('cp1251')
            assert len(new) == len(old)
            pos, n = 0, 0
            while (pos := raw.find(old + b'\0', pos)) != -1:
                if pos and raw[pos - 1] in (0, 0xFF):  # початок рядка, а не частина іншого
                    raw[pos:pos + len(old)] = new
                    n += 1
                pos += len(old)
            assert n, f'{zone}: не знайдено «{en}»'
            total += n
        (OUT / f'{zone}.ff').write_bytes(src[:12] + zlib.compress(bytes(raw), 9))
        print(f'{zone}: замінено {total}')


if __name__ == '__main__':
    main()
