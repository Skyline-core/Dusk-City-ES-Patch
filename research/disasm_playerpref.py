import json, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

GA_PATH = r"E:\Users\ah_3m\Documents\gits\Dusk City\GameAssembly.dll"
SCRIPT = r"E:\Users\ah_3m\Documents\gits\Dusk City\translation\research\il2cpp_dump\script.json"

ga = open(GA_PATH, "rb").read()
pe_off = struct.unpack_from("<I", ga, 0x3C)[0]
num_sections = struct.unpack_from("<H", ga, pe_off + 6)[0]
sec_off = pe_off + 24 + struct.unpack_from("<H", ga, pe_off + 20)[0]

def rva_to_offset(rva):
    for i in range(num_sections):
        so = sec_off + i * 40
        vsize, vaddr, rsize, rptr = struct.unpack_from("<IIII", ga, so + 8)
        if vaddr <= rva < vaddr + max(vsize, rsize):
            return rptr + (rva - vaddr)
    raise ValueError(rva)

script = json.load(open(SCRIPT, encoding="utf-8"))
by_name = {m["Name"]: m for m in script["ScriptMethod"]}
md = Cs(CS_ARCH_X86, CS_MODE_64)

for name in [
    "UnityEngine.Localization.Settings.PlayerPrefLocaleSelector$$GetStartupLocale",
    "UnityEngine.Localization.Settings.PlayerPrefLocaleSelector$$PostInitialization",
    "UnityEngine.Localization.Settings.SystemLocaleSelector$$GetStartupLocale",
]:
    m = by_name.get(name)
    if not m:
        print(name, "MISSING")
        continue
    rva = m["Address"]
    off = rva_to_offset(rva)
    print(f"\n=== {name} @ {rva:#x} ===")
    for ins in md.disasm(ga[off:off+400], rva):
        print(f"  {ins.address:#x}: {ins.mnemonic}\t{ins.op_str}")
