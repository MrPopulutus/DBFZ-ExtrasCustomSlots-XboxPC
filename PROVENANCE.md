# Provenance and distribution scope

Modified by MrPopulutus.

WistfulHopes’ [Custom Character Slots for Steam](https://gamebanana.com/mods/596230) inspired this Microsoft Store project. The current installer uses the Store native modules and converts the user's character downloads locally. It does not request the Steam slot bundle as an input.

Earlier development notes record use of that bundle as a source for some ready-made character conversions. Version 0.3.0 changed those recipes to convert the individual authors' downloads locally. This history must not be confused with a current runtime dependency, or erased from a provenance review.

The reviewed source tree contains C/assembly, Lua modules, Python tools and configuration. The review did not establish the independent origin of every algorithm or compare the original author's closed implementation. It therefore does not certify that every component was developed without reference to that work.

The source repository excludes game executables, game resource packages, third-party character packages, runtime binaries, diagnostic dumps and private research files. The separate playable installer contains a cursor-mask resource derived from the game. Its presence must be disclosed; publishing source does not settle distribution rights for that asset.

Credits for character authors remain in CREDITOS.md, including WistfulHopes’ contribution to Sol Badguy. Inspiration credits, component authorship and permission to redistribute are distinct. No author approval is claimed.

Claude and ChatGPT/Codex assisted with development and documentation. Humanizer was used to edit prose; this does not change code provenance or remove the AI disclosure.
