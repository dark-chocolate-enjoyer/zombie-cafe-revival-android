#!/usr/bin/env python3
"""Translate the Japanese Java-side strings and rebuild classes.dex.

Input:  work/apktool_a14/  (apktool -r decode of the Android-14 build, which
        already has the 9 device-ID fixes)
Output: work/patched/classes.dex
"""
import os, re, shutil, subprocess, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'work', 'apktool_a14')
TMP = os.path.join(HERE, 'work', 'apktool_en')
REPLACE = {
    'ゾンビカフェ': 'Zombie Cafe',
    '正しい文字を入力してください': 'Please enter valid characters.',
    'これが私のゾンビカフェだ！': 'Check out my Zombie Cafe!',
    'ゾンビカフェを終了しますか？': 'Quit Zombie Cafe?',
    '終了する': 'Quit',
    'キャンセル': 'Cancel',
    'ゾンビカフェは無料でプレイできますが、追加で毒を購入することができます。毒の代金はGoogle Playアカウントから支払われます。':
        'Zombie Cafe is free to play, but you can buy additional Toxin. Toxin is paid for through your Google Play account.',
    '注意！': 'Notice!',
    '保存成功 path = ': 'Saved OK path = ',
    'Texture 保存成功 path = ': 'Texture saved OK path = ',
}
LIT = re.compile(r'(const-string(?:/jumbo)? [vp]\d+, )"((?:[^"\\]|\\.)*)"')

shutil.rmtree(TMP, ignore_errors=True)
shutil.copytree(SRC, TMP)
done = set()
for root, _, files in os.walk(os.path.join(TMP, 'smali')):
    for f in files:
        p = os.path.join(root, f)
        text = open(p, encoding='utf-8').read()

        def sub(m):
            raw = m.group(2)
            if '\\u' not in raw:
                return m.group(0)
            decoded = raw.encode('latin-1', 'backslashreplace').decode('unicode_escape')
            if decoded in REPLACE:
                done.add(decoded)
                return m.group(1) + '"' + REPLACE[decoded].replace('"', '\\"') + '"'
            return m.group(0)
        new = LIT.sub(sub, text)
        if new != text:
            open(p, 'w', encoding='utf-8').write(new)
missing = set(REPLACE) - done
assert not missing, f'not found: {missing}'
built = os.path.join(HERE, 'work', 'apktool_en.apk')
subprocess.run(['apktool', 'b', TMP, '-o', built], check=True, stdout=subprocess.DEVNULL)
out = os.path.join(HERE, 'work', 'patched', 'classes.dex')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'wb').write(zipfile.ZipFile(built).read('classes.dex'))
shutil.rmtree(TMP)
os.remove(built)
print(f'classes.dex: {len(done)} distinct Java strings translated')
