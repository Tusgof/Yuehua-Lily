from __future__ import annotations
import ast
from pathlib import Path
from lib.environment import interpreter_metadata
ROOT=Path(__file__).resolve().parents[1]
def validate_static()->dict:
 tree=ast.parse((ROOT/'lib/l3_b714_date_only_scanner_v4.py').read_text(encoding='utf8'));bad={'decode','float','int','Decimal','loads','load','str'}; names={x.id for x in ast.walk(tree) if isinstance(x,ast.Name)}
 return {'status':'pass' if not names&bad else 'blocked','blockers':sorted(names&bad)}
if __name__=='__main__':
 r=validate_static();print(r);raise SystemExit(r['status']!='pass')
