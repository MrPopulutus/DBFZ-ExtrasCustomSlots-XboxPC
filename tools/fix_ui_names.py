"""Make every texture's object name match the file it is in (paks/DBFZSlotsUI.pak).
The game asks for /Game/UI/.../<leaf>.<leaf>, so the export name must be <leaf>.
Only same-length renames (code swaps) are done; other mismatches are reported."""
import pathlib, sys, re
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root)); sys.path.insert(0, str(root.parent))
from build_char import entries_data, names, write_pak
from build_ui2 import rename_uasset

pak = root / 'paks/DBFZSlotsUI.pak'
files = {n: get() for n, get in entries_data(pak)}
fixed = 0
for n in list(files):
    if not n.endswith('.uasset'): continue
    leaf = n.rsplit('/', 1)[1][:-len('.uasset')]
    pkg = '/Game/' + n[len('RED/Content/'):-len('.uasset')]
    ns = [s for s, *_ in names(files[n])]
    if leaf in ns: continue
    # an object name like the leaf but with another 3-letter code at the end
    cand = [s for s in ns if not s.startswith('/') and len(s) == len(leaf) and s[:-3].lower() == leaf[:-3].lower()]
    if not cand:
        print('cannot fix', n, ns); continue
    old = cand[0]
    def conv(s, old=old, leaf=leaf):
        if s == old: return leaf
        if s.startswith('/') and s.endswith('/' + old): return s[:-len(old)] + leaf
        return s
    files[n] = rename_uasset(files[n], conv)
    fixed += 1
    print('fixed', n, old, '->', leaf)
write_pak(pak, sorted(files.items()))
print('fixed', fixed)
