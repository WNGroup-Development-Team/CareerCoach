from pathlib import Path
import re
import py_compile

ROOT = Path.cwd()
PIPELINE = ROOT / "backend" / "services" / "cv_optimizer" / "pipeline.py"
MAIN = ROOT / "backend" / "main.py"

if not PIPELINE.exists():
    raise SystemExit("Esegui questo script dalla root del progetto CareerCoach.")

text = PIPELINE.read_text(encoding="utf-8")
original = text

safe_append_method = r'''    def _append_replacement_to_text_section(self, cv_text: str, instruction: RewriteInstruction) -> str:
        replacement = (instruction.replacement or "").strip()
        if not replacement:
            return cv_text
        if normalize_text(replacement) in normalize_text(cv_text):
            return cv_text

        target = canonical_section(instruction.section or instruction.category or "")
        heading = (instruction.section or target or "COMPETENZE").strip().upper()
        lines = (cv_text or "").splitlines()
        if not lines:
            return f"{heading}\n{replacement}".strip()

        heading_index = None
        for index, line in enumerate(lines):
            if is_section_heading(line) and canonical_section(line) == target:
                heading_index = index
                break

        if heading_index is None:
            return (cv_text.rstrip() + f"\n\n{heading}\n{replacement}").strip()

        insert_at = len(lines)
        for index in range(heading_index + 1, len(lines)):
            if is_section_heading(lines[index]):
                insert_at = index
                break
        return "\n".join([*lines[:insert_at], replacement, *lines[insert_at:]]).strip()

'''

# Sostituisce tutto il metodo inserito dalla patch precedente, anche se contiene stringhe rotte su più righe.
text, method_count = re.subn(
    r"    def _append_replacement_to_text_section\(self, cv_text: str, instruction: RewriteInstruction\) -> str:\n.*?\n(?=    def fallback_text\()",
    safe_append_method,
    text,
    count=1,
    flags=re.DOTALL,
)

# Riparazioni difensive per eventuali stringhe '\n'.join spezzate altrove.
text = re.sub(
    r'return\s+"\s*"\.join\(\[\*lines\[:insert_at\], replacement, \*lines\[insert_at:\]\]\)\.strip\(\)',
    'return "\\\\n".join([*lines[:insert_at], replacement, *lines[insert_at:]]).strip()',
    text,
    flags=re.DOTALL,
)
text = re.sub(
    r'existing_section_text\s*=\s*"\s*"\.join\(existing_section_parts\)',
    'existing_section_text = "\\\\n".join(existing_section_parts)',
    text,
    flags=re.DOTALL,
)

# Ripara eventuali f-string multilinea residue del tipo return f"{heading}\n{replacement}" scritte male.
text = re.sub(
    r'return\s+f"\{heading\}\s*\n\s*\{replacement\}"\.strip\(\)',
    'return f"{heading}\\\\n{replacement}".strip()',
    text,
    flags=re.DOTALL,
)
text = re.sub(
    r'return\s+\(cv_text\.rstrip\(\) \+ f"\s*\n\s*\n\s*\{heading\}\s*\n\s*\{replacement\}"\)\.strip\(\)',
    'return (cv_text.rstrip() + f"\\\\n\\\\n{heading}\\\\n{replacement}").strip()',
    text,
    flags=re.DOTALL,
)

if text == original:
    print("[WARN] Non ho modificato pipeline.py: il pattern non è stato trovato.")
else:
    PIPELINE.write_text(text, encoding="utf-8")
    print(f"[OK] pipeline.py riparato. Metodo append sostituito: {bool(method_count)}")

# Controllo compilazione immediato, così vedi subito se c'è un altro punto da correggere.
for path in [MAIN, PIPELINE]:
    if path.exists():
        try:
            py_compile.compile(str(path), doraise=True)
            print(f"[OK] Compilazione riuscita: {path}")
        except py_compile.PyCompileError as exc:
            print(f"[ERRORE] Compilazione fallita: {path}")
            print(exc.msg)
            raise SystemExit(1)

print("[OK] Fix sintassi completato.")
