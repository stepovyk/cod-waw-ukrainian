"""Точкова заміна перекладу за ключем у data/uk/*.json без зміни форматування файлу.
python tools/setstr.py KEY "новий текст" [KEY2 "текст2" ...]"""
import sys, json, pathlib
ROOT = pathlib.Path(__file__).parent.parent


def set_value(key, value):
    for f in sorted((ROOT / 'data' / 'uk').glob('*.json')):
        data = json.loads(f.read_text(encoding='utf-8'))
        if key not in data:
            continue
        text = f.read_bytes().decode('utf-8')
        old = '"%s": %s' % (key, json.dumps(data[key], ensure_ascii=False))
        new = '"%s": %s' % (key, json.dumps(value, ensure_ascii=False))
        if text.count(old) != 1:
            sys.exit(f'{key}: не знайдено однозначно у {f.name}')
        f.write_bytes(text.replace(old, new).encode('utf-8'))
        assert json.loads(f.read_text(encoding='utf-8'))[key] == value
        print(f'{f.name} {key}: {data[key]!r} -> {value!r}')
        return
    sys.exit(f'{key}: ключа немає')


if __name__ == '__main__':
    args = sys.argv[1:]
    for k, v in zip(args[::2], args[1::2]):
        set_value(k, v)
