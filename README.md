<p align="center"><img src="docs/images/cover.jpg" alt="Call of Duty: World at War українською" width="100%"></p>

# Call of Duty: World at War українською

Повна українська локалізація Call of Duty: World at War для ПК.

**Версія:** 1.0 · **Гра:** 1.7 · **Автор:** Stepovyk

**[Завантажити інсталятор](../../releases/latest)**

[English below](#english)

## Що перекладено

- **Увесь текст гри.** Меню й налаштування, кампанія (субтитри, завдання, підказки, вступи до місій, цитати після загибелі), зомбі, кооператив, мультиплеєр, випробування, титри й системні вікна Windows. Понад 9 600 рядків.
- **Нові шрифти.** Усі шрифти гри перемальовано з повною кирилицею (і, ї, є, ґ, апостроф, «лапки»), рівні й чіткі навіть на великих екранах.
- **Жива мова.** Переклад пройшов окрему редактуру: військова лексика, звертання в кличному відмінку, природні репліки, а не дослівщина.

Голос і відеоролики лишаються англійськими, з українськими субтитрами.

## Як це виглядає

<p>
<img src="docs/images/screen-01.jpg" width="49%" alt="Головне меню">
<img src="docs/images/screen-02.jpg" width="49%" alt="Субтитри в кампанії">
<img src="docs/images/screen-04.jpg" width="49%" alt="Вибір місії">
<img src="docs/images/screen-05.jpg" width="49%" alt="Налаштування">
<img src="docs/images/screen-07.jpg" width="49%" alt="Мультиплеєр">
<img src="docs/images/screen-06.jpg" width="49%" alt="Зомбі">
</p>

## Встановлення

1. Завантажте `WaW-Ukrainian-1.0.zip` з [Releases](../../releases/latest) і розпакуйте.
2. Закрийте гру й запустіть `WaW-Ukrainian-Setup.exe`.
3. Перевірте теку гри (ту, де лежить `CoDWaW.exe`) і натисніть **«Встановити»**.

Щоб повернути англійську, запустіть інсталятор ще раз і натисніть **«Видалити»**.

Потрібна гра версії 1.7 з англійською мовою (диск або Steam). Інсталятор не містить файлів гри: він акуратно змінює лише ваші власні файли, перевіряє версію перед змінами й уміє все повернути назад.

## Підтримати

Переклад безкоштовний. Якщо хочете, щоб українською заговорили й інші частини Call of Duty, підтримайте роботу:

- **Monobank:** https://send.monobank.ua/jar/8aeC9dGFrn
- **Приват24:** https://www.privat24.ua/send/kkyqm

Помилку в перекладі чи ідею можна надіслати через [Issues](../../issues).

## Для розробників

```
python tools/build.py          # зібрати локалізацію з оригінальних файлів гри
python tools/install.py        # поставити в гру (оригінали зберігаються в backup/)
python tools/make_release.py   # зібрати інсталятор для гравців
```

Переклад лежить у `data/uk/*.json`, правила перекладу й глосарій – у `docs/guide.md` і `data/glossary.json`. Шрифти будує `tools/build_fonts.py`, латки exe – `tools/exepatch.py`.

---

## English

A complete Ukrainian localization of Call of Duty: World at War (PC, v1.7): menus, campaign subtitles and objectives, Nazi Zombies, co-op, multiplayer, credits and Windows dialogs, with redrawn game fonts that include full Cyrillic. Voice-over stays English with Ukrainian subtitles.

**Install:** download `WaW-Ukrainian-1.0.zip` from [Releases](../../releases/latest), close the game, run `WaW-Ukrainian-Setup.exe`, pick the game folder and press «Встановити» (Install). Press «Видалити» (Remove) to restore English. The installer ships no game files: it patches your own copy in place, verifies the game version first and can revert every change.

Unofficial fan project, not affiliated with Activision or Treyarch. Code and translation – MIT, see [LICENSE](LICENSE).
