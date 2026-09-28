"""Counterexamples to the v0.2.0 boundary checks, independent of saved grades."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from trl_crl.engine import evaluate_case, qualification_supported
from trl_crl.pipeline import load_inputs
from trl_crl.pipeline import assess

ROOT = Path(__file__).resolve().parents[1]


class BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_inputs(ROOT / 'data')

    def sample(self):
        d = self.data
        return copy.deepcopy((next(x for x in d['objects'] if x['case_id'] == 'W001'),
            next(x for x in d['gate_reviews'] if x['case_id'] == 'W001'),
            [x for x in d['observations'] if x['case_id'] == 'W001'],
            {x['evidence_id']: x for x in d['evidence']},
            next(x for x in d['technical_profiles'] if x['case_id'] == 'W001')))

    def test_direct_api_cannot_use_future_knowledge(self):
        with self.assertRaisesRegex(ValueError, 'cutoff'):
            evaluate_case(*self.sample(), '2000-01-01')

    def test_direct_api_validates_referenced_dates_and_hashes(self):
        for field, value in [('available_by', '2099-01-01'), ('published_at', '2099-01-01'), ('quote_sha256', 'bad')]:
            args = self.sample()
            args[3][args[2][0]['evidence_id']][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                evaluate_case(*args, '2026-09-25')

    def test_changed_object_configuration_invalidates_review(self):
        args = self.sample()
        args[0]['object_configuration'] = 'a different experimental configuration'
        with self.assertRaisesRegex(ValueError, 'scope'):
            evaluate_case(*args, '2026-09-25')

    def test_theme_retrieval_does_not_change_object_scope(self):
        args = self.sample()
        before = evaluate_case(*args, '2026-09-25')['axes']
        args[0]['category_id'] = 'N0123'
        self.assertEqual(before, evaluate_case(*args, '2026-09-25')['axes'])

    def test_missing_stage_and_changed_rules_are_rejected(self):
        args = self.sample()
        args[1]['axes']['TRL'].pop(0)
        with self.assertRaisesRegex(ValueError, 'Every stage'):
            evaluate_case(*args, '2026-09-25')
        args = self.sample()
        args[1]['rules_sha256'] = 'outdated'
        with self.assertRaisesRegex(ValueError, 'rules'):
            evaluate_case(*args, '2026-09-25')

    def test_orphan_observation_is_not_silently_discarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'data'
            shutil.copytree(ROOT / 'data', dest)
            path = dest / 'observations.json'
            observations = json.loads(path.read_text())
            observations[0]['case_id'] = 'missing-object'
            path.write_text(json.dumps(observations))
            with self.assertRaisesRegex(ValueError, 'foreign key'):
                load_inputs(dest)

    def test_substring_of_number_cannot_be_a_measurement(self):
        profile = {'performance_requirements': [{'requirement_id': 'R', 'critical_for_stage': 5,
            'basis': 'predeclared_in_source', 'basis_quote': 'target', 'target': 1,
            'operator': '<=', 'unit': 's'}]}
        gate = {'requirement_ids': ['R'], 'stage': 5, 'measurements': [
            {'requirement_id': 'R', 'observation_id': 'O', 'value': 1, 'unit': 's'}]}
        for number in ['10', '1,000', '1.01', '10e1']:
            with self.subTest(number=number), self.assertRaisesRegex(ValueError, 'literal'):
                qualification_supported(gate, profile, {'O': {'quote': f'target; measured time {number} s'}})

    def test_commissioning_and_intended_uses_do_not_prove_operating_results(self):
        unit = next(u for u in assess(ROOT / 'data')[1]['assessment_units'] if u['case_id'] == 'W011')
        self.assertIsNone(unit['trl_public_evidence_stage'])
        self.assertIsNone(unit['crl_public_evidence_stage'])
