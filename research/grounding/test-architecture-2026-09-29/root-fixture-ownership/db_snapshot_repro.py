import gc
import runpy
import sqlite3
import tempfile
import warnings
from pathlib import Path

fixture = runpy.run_path('/Users/jwross/Documents/cairn/tests/conftest.py')['db_snapshot']
root = Path(tempfile.mkdtemp(prefix='cairn-db-snapshot-'))
db = root / 'owned.sqlite'
conn = sqlite3.connect(db)
conn.execute('create table evidence(value integer)')
conn.execute('insert into evidence values(7)')
conn.commit()
conn.close()
gc.collect()
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always', ResourceWarning)
    snapshot = fixture.__wrapped__()
    assert snapshot(db, 'real-file') == {'evidence': 1}
    gc.collect()
    unclosed = [str(w.message) for w in caught if issubclass(w.category, ResourceWarning) and 'unclosed database' in str(w.message)]
    print('scratch', root)
    print('unclosed', unclosed)
    assert len(unclosed) == 1, unclosed
print('REPRODUCED: path snapshot abandons one unclosed SQLite connection.')
