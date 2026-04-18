import re
from collections import Counter

try:
    content = open('templates/index.html', encoding='utf-8').read()
    ids = re.findall(r'id=["\']([^"\']+)["\']', content)
    dupes = [item for item, count in Counter(ids).items() if count > 1]
    if dupes:
        print('Duplicate IDs:', dupes)

    tags = re.findall(r'<(/?[a-zA-Z0-9]+)\b', content)
    open_counts, close_counts = Counter(), Counter()
    for t in tags:
        if t.startswith('/'):
            close_counts[t[1:].lower()] += 1
        else:
            open_counts[t.lower()] += 1

    ignore = ['meta', 'link', 'input', 'hr', 'br', 'path', 'img', 'source', 'option', 'circle', 'line', 'polyline', 'rect', '!doctype']
    for k in open_counts:
        if k not in ignore:
            if open_counts[k] != close_counts[k]:
                print(f'Mismatch for tag {k}: <{k}>={open_counts[k]}, </{k}>={close_counts[k]}')
except Exception as e:
    print('Error:', e)
