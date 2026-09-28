import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nmf_mapping', ROOT / 'pipelines/nmf500/mapping.py')
mapping = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapping)


class MappingTests(unittest.TestCase):
    def test_invalid_vectors_cannot_be_silently_linked(self):
        catalog = pd.DataFrame({'topic_id': [0, 1, 2], 'name': ['a', 'b', 'c']})
        rows = [dict(entity_type='case', entity_id='case1', name='case')]
        for vector in [[0, 0, 0], [np.nan, 1, 0]]:
            with self.assertRaises(ValueError):
                mapping.ranked_links(rows, np.array([vector]), np.eye(3), catalog)

    def test_cosine_links_are_pending_and_never_transfer_maturity(self):
        catalog = pd.DataFrame({'topic_id': [0, 1, 2], 'name': ['a', 'b', 'c']})
        rows = [dict(entity_type='case', entity_id='case1', name='case')]
        links = mapping.ranked_links(rows, np.array([[2, 2, 0]]), np.eye(3), catalog)
        self.assertEqual(links.topic_id.tolist(), [0, 1, 2])
        self.assertTrue(links.needs_review.all())
        self.assertFalse(links.transfers_maturity.any())
