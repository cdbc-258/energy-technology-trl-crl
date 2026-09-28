"""One-time v0.2.1 migration: bind existing reviewed scopes, never invent gates.

The new fields record which existing object/rule definitions the historical
review refers to. This is integrity migration, not a new semantic expert review.
Run only on unbound legacy reviews; changes to bound reviews require re-review.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from trl_crl.common import read, write
from trl_crl.engine import scope_sha256, rules_sha256


def migrate():
    objects = {c['case_id']: c for c in read(ROOT / 'data/objects.json')}
    reviews = read(ROOT / 'data/gate_reviews.json')
    for review in reviews:
        expected = {'scope_sha256': scope_sha256(objects[review['case_id']]),
                    'rules_sha256': rules_sha256()}
        for key, value in expected.items():
            if key in review and review[key] != value:
                raise ValueError('Already bound review changed; semantic re-review required')
            review[key] = value
    write(ROOT / 'data/gate_reviews.json', reviews)
    print(f'Bound {len(reviews)} historical reviews; no gate decisions changed')


if __name__ == '__main__':
    migrate()
