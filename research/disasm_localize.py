"""Disassemble key LocalizeManager methods from GameAssembly.dll (x64)."""
import json
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

GA_PATH = r"E:\Users\ah_3m\Documents\gits\Dusk City\GameAssembly.dll"
SCRIPT = r"E:\Users\ah_3m\Documents\gits\Dusk City\translation\research\il2cpp_dump\script.json"
STRINGS = r"E:\Users\ah_3m\Documents\gits\Dusk City\translation\research\il2cpp_dump\stringliteral.json"

ga = open(GA_PATH, "rb").read()
pe_off = struct.unpack_from("<I", ga, 0x3C)[0]
num_sections = struct.unpack_from("<H", ga, pe_off + 6)[0]
opt_off = pe_off + 24
sec_off = opt_off + struct.unpack_from("<H", ga, pe_off + 20)[0]


def rva_to_offset(rva: int) -> int:
    for i in range(num_sections):
        so = sec_off + i * 40
        vsize, vaddr, rsize, rptr = struct.unpack_from("<IIII", ga, so + 8)
        if vaddr <= rva < vaddr + max(vsize, rsize):
            return rptr + (rva - vaddr)
    raise ValueError(f"RVA {rva:#x} not in any section")


script = json.load(open(SCRIPT, encoding="utf-8"))
lit = json.load(open(STRINGS, encoding="utf-8"))
# build address -> string map from metadata (values only; addrs in il2cpp are via init)
lit_values = {e["value"] for e in lit}

targets = [
    "LocalizeManager$$GetLocalizeNumber",
    "LocalizeManager$$GetLocalizeString",
    "LocalizeManager$$Start",
    "LocalizeManager$$GetLocalizeAsset<object>",
    "LocalizedImage$$OnLanguageUpdate",
    "LocalizedTextTMPro$$OnLanguageUpdate",
    "LocalizeTextFont$$OnLanguageUpdate",
    "Config$$Save",
    "Config$$Load",
]

by_name = {m["Name"]: m for m in script["ScriptMethod"]}
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True

out_lines = []
for name in targets:
    m = by_name.get(name)
    if not m:
        out_lines.append(f"\n=== {name}: NOT FOUND ===\n")
        continue
    rva = m["Address"]
    off = rva_to_offset(rva)
    code = ga[off : off + 512]
    out_lines.append(f"\n=== {name} RVA={rva:#x} file={off:#x} ===")
    out_lines.append(m.get("Signature", ""))
    for ins in md.disasm(code, rva):
        line = f"  {ins.address:#x}: {ins.mnemonic}\t{ins.op_str}"
        out_lines.append(line)
        if ins.mnemonic in ("ret", "int3") and ins.address > rva + 8:
            break

text = "\n".join(out_lines)
out_path = r"E:\Users\ah_3m\Documents\gits\Dusk City\translation\research\disasm_localize.txt"
open(out_path, "w", encoding="utf-8").write(text)
print("Wrote", out_path, "bytes", len(text))
