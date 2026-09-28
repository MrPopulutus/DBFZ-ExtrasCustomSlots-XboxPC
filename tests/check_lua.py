"""Syntax-check the installed Lua mods with Lua 5.4 and test the path logic they use."""
from lupa.lua54 import LuaRuntime
lua = LuaRuntime()
chk = lua.eval('function(s) local f, e = load(s); return f ~= nil, e end')
MODS = r'D:/Games/Dragon Ball FighterZ/RED/Binaries/Win64/ue4ss/Mods'
for name in ['DBFZSlotsIcons', 'DBFZSlotsStore']:
    ok, err = chk(open(f'{MODS}/{name}/Scripts/main.lua', encoding='utf-8').read())
    print(name, 'sintaxis OK' if ok else err)
bs = chr(92)
src = '@D:' + bs + 'Games' + bs + 'Dragon Ball FighterZ' + bs + 'RED' + bs + 'Binaries' + bs + 'Win64' + bs + 'ue4ss' + bs + 'Mods' + bs + 'DBFZSlotsIcons' + bs + 'scripts' + bs + 'main.lua'
get = lua.eval('function(s) local p = s:sub(2):gsub(string.char(92), "/"); return p:match("^(.*)/DBFZSlotsIcons/[Ss]cripts/main%.lua$") end')
mods = get(src)
print('ruta Mods calculada:', mods)
import os
print('DLL existe en esa ruta:', os.path.exists(mods + '/DBFZSlotsStore/dbfzslots.dll'))
