import sqlite3
import difflib

DB='c:\\Users\\silvi\\OneDrive\\Desktop\\CareerCoach\\backend\\careercoach.db'
USER_ID=32
OPT_ID=55

conn=sqlite3.connect(DB)
cur=conn.cursor()
cur.execute('SELECT text, file_base64 FROM optimized_cvs WHERE id=? AND user_id=?', (OPT_ID, USER_ID))
row=cur.fetchone()
opt_text = row[0] if row else ''

cur.execute('SELECT cv_file_base64, cv_text FROM users WHERE id=?', (USER_ID,))
row2=cur.fetchone()
orig_text = ''
if row2:
    # cv_text may be saved in users.cv_text (column index may vary); try both
    orig_text = row2[1] if len(row2)>1 and row2[1] else ''

conn.close()

if not orig_text:
    print('Original text not found in users table. Showing optimized excerpt:')
    print(opt_text[:4000])
else:
    print('Original vs Optimized diff (context lines):')
    o_lines = orig_text.splitlines()
    n_lines = opt_text.splitlines()
    diff = difflib.unified_diff(o_lines, n_lines, fromfile='original', tofile='optimized', lineterm='')
    for line in diff:
        print(line)
    # Also print lines in optimized containing common skills
    print('\n--- Optimized lines with skills ---')
    skills = ['Python','SQL','Java','Big Data','ML & AI','HARD SKILLS','SOFT SKILLS','COMPETENZE']
    for s in skills:
        matches = [ln for ln in n_lines if s.lower() in ln.lower()]
        if matches:
            print(f"{s}: {len(matches)}")
            for m in matches[:5]:
                print('  -', m)
