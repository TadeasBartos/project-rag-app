### Hot keys

ca:CLN
c:CLEAN
d:Set of commands that runs purge + audit + -purge commands in sequence.

### Problems

problem001: Český Country Kit pro Autodesk Civil 3D 2026 obsahuje chyby, které způsobují nefunkční české kódy podsestav a chybné zobrazování parametrů u ČSN podsestav. Tyto problémy vychází ze špatně načítaných souborů a odkazů na neaktuální adresáře. Civil 3D načítá pouze výchozí soubor C3DStockSubassemblyScripts.codes, místo správného českého souboru C3DStockSubassemblyScripts_cz-CZ.codes. Výsledkem jsou nefunkční české kódy jako Povrch, RefPovrch, Kryt apod.

solution001: "
1. Otevřete složku: C:\ProgramData\Autodesk\C3D 2026\csy
2. Zkopírujte soubor: C3DStockSubassemblyScripts_cz-CZ.codes
3. Vložte jej zpět do stejné složky.
4. Přejmenujte kopii na: C3DStockSubassemblyScripts.codes
5. Původní soubor se stejným názvem smažte nebo zazálohujte. Tím zajistíte, že Civil 3D bude používat české kódy správně."

problem002: ČSN podsestavy zobrazují čísla místo názvů parametrů (např. šířka, tloušťka). Nastavení podsestavy je pak neintuitivní. Některé podsestavy odkazují na staré umístění knihovny C3DCzechSubassembliesRC.dll z verzí 2022/2023, místo na aktuální složku verze 2026.

solution002: "
Vytvořte zpětnou kompatibilitu:
1. Vytvořte tyto složky:
C:\ProgramData\Autodesk\C3D 2022\csy
C:\ProgramData\Autodesk\C3D 2023\csy
2. Do obou zkopírujte soubor: C3DCzechSubassembliesRC.dll (originál je v: C:\ProgramData\Autodesk\C3D 2026\csy)
3. Civil 3D pak najde knihovnu i na místech, kde ji starší podsestavy očekávají.