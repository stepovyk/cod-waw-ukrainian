"""Спільні шляхи: гра, оригінали (резервні копії), результат збирання."""
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
GAME = pathlib.Path(r'C:\FOLDER\Games\Call-of-Duty-World-at-War-AnkerGames')
BACKUP = ROOT / 'backup'   # оригінали змінених файлів гри (до встановлення)
OUT = ROOT / 'work' / 'out'

# змінювані файли гри (шлях відносно теки гри)
REPLACED = [
    'CoDWaW.exe',
    'CoDWaWmp.exe',
    'localization.txt',
    'zone/english/code_post_gfx.ff',
    'zone/english/localized_code_post_gfx_mp.ff',
    'zone/english/localized_nazi_zombie_asylum.ff',
    'zone/english/localized_nazi_zombie_factory.ff',
    'zone/english/localized_nazi_zombie_sumpf.ff',
    'zone/english/nazi_zombie_prototype.ff',
    'zone/english/ui.ff',
    'zone/english/common.ff',
    'zone/english/patch.ff',
    'zone/english/ui_mp.ff',
    'zone/english/common_mp.ff',
]
# нові файли (у грі їх не було)
ADDED = [
    'zone/english/localized_common.ff',
    'zone/english/localized_ukrainian_mp.ff',
    'main/localized_english_iw07.iwd',
]


def original(rel):
    """Оригінальний файл гри: з резервної копії, якщо локалізацію вже встановлено."""
    b = BACKUP / rel
    return b if b.exists() else GAME / rel


def built(rel):
    return OUT / pathlib.PurePosixPath(rel).name
