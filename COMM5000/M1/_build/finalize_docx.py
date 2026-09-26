"""Rename embedded images to Word's usual image1.png ... and drop empty custom properties."""
import zipfile, re, sys
src, dst = sys.argv[1], sys.argv[2]
zin = zipfile.ZipFile(src); names = zin.namelist()
media = [n for n in names if n.startswith('word/media/') and not n.endswith('/')]
doc = zin.read('word/document.xml').decode()
order = sorted(media, key=lambda n: doc.find(n.split('/')[-1]) if n.split('/')[-1] in doc else 10**9)
rels = zin.read('word/_rels/document.xml.rels').decode()
ren = {}
for i, n in enumerate(sorted(media, key=lambda n: rels.find(n.split('/')[-1])), 1):
    ren[n] = f'word/media/image{i}.png'
zout = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
for n in names:
    data = zin.read(n)
    if n.endswith('.rels') or n == '[Content_Types].xml':
        t = data.decode()
        for a, b in ren.items(): t = t.replace(a.split('/')[-1], b.split('/')[-1])
        data = t.encode()
    zout.writestr(ren.get(n, n), data)
zout.close(); print('renamed', len(ren))
