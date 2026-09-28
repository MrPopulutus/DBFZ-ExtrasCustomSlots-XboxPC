-- Loads dbfzslots.dll (extra character slots for the Microsoft Store build).
local tag = "[DBFZSlotsStore] "
local function ascii(s) return (tostring(s):gsub("[^%w%p ]", "?")) end
local ok, err = pcall(function()
    local candidates = {}
    local src = debug.getinfo(1, "S").source
    if src:sub(1, 1) == "@" then
        local p = src:sub(2):gsub(string.char(92), "/")
        local dir = p:match("^(.*)/[Ss]cripts/main%.lua$")
        if dir then table.insert(candidates, dir .. "/dbfzslots.dll") end
    end
    table.insert(candidates, "ue4ss/Mods/DBFZSlotsStore/dbfzslots.dll")
    table.insert(candidates, "Mods/DBFZSlotsStore/dbfzslots.dll")
    for _, path in ipairs(candidates) do
        local init, e = package.loadlib(path, "luaopen_dbfzslots")
        if init then
            init()
            print(tag .. "loaded " .. ascii(path) .. " (see ue4ss/dbfzslots.log)\n")
            return
        end
        print(tag .. "loadlib " .. ascii(path) .. " failed: " .. ascii(e) .. "\n")
    end
end)
if not ok then print(tag .. "error: " .. ascii(err) .. "\n") end
