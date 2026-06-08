from pathlib import Path

PIPELINE = Path('backend/services/cv_optimizer/pipeline.py')
if not PIPELINE.exists():
    raise SystemExit('Esegui questo script dalla root del progetto CareerCoach.')

text = PIPELINE.read_text(encoding='utf-8')
original = text

# La patch precedente ha inserito newline reali dentro f-string, causando:
# SyntaxError: unterminated f-string literal
broken_1 = '''            return f"{heading}
{replacement}".strip()'''
fixed_1 = '''            return f"{heading}\\n{replacement}".strip()'''

broken_2 = '''            return (cv_text.rstrip() + f"

{heading}
{replacement}").strip()'''
fixed_2 = '''            return (cv_text.rstrip() + f"\\n\\n{heading}\\n{replacement}").strip()'''

text = text.replace(broken_1, fixed_1)
text = text.replace(broken_2, fixed_2)

# Variante difensiva se Windows/Python ha scritto spazi leggermente diversi.
text = text.replace('return f"{heading}\r\n{replacement}".strip()', 'return f"{heading}\\n{replacement}".strip()')
text = text.replace('return (cv_text.rstrip() + f"\r\n\r\n{heading}\r\n{replacement}").strip()', 'return (cv_text.rstrip() + f"\\n\\n{heading}\\n{replacement}").strip()')

if text == original:
    print('[WARN] Non ho trovato il pattern esatto da sostituire. Controlla manualmente le righe intorno a line 367.')
else:
    PIPELINE.write_text(text, encoding='utf-8')
    print('[OK] Corrette le f-string multilinea in backend/services/cv_optimizer/pipeline.py')
