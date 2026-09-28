"""Evaluate explicit gate reviews; never manufacture gates from a proposed grade.

This checks structure, provenance and declared review decisions. It cannot establish
the truth of a publication or replace a technical expert's semantic assessment.
"""
from datetime import date
import hashlib
import math
import re
from .common import canonical_sha
from .rules import requirements, TRL, CRL

STATES = {'met', 'unknown', 'not_met', 'conflict'}
FORBIDDEN = {'trl_expected', 'crl_expected', 'expected_level', 'model_suggested_level',
             'trl_evidence_level', 'crl_evidence_level', 'formal_level'}


def scope_sha256(case):
    """Bind the semantic object, independent of its retrieval/theme association."""
    fields = ['case_id', 'scope_id', 'canonical_name', 'object_configuration',
              'application_or_target_function', 'boundary', 'evidence_period']
    if any(not isinstance(case.get(k), str) or not case[k].strip() for k in fields):
        raise ValueError('Bounded object requires explicit configuration, function and period')
    return canonical_sha({k: case[k] for k in fields})


def rules_sha256():
    return canonical_sha({'TRL': TRL, 'CRL': CRL})


def validate_excerpt(e, cutoff):
    """Enforce excerpt integrity and knowledge time at every public entry point."""
    start, end = e['quote_start'], e['quote_end']
    if not (type(start) is int and type(end) is int and 0 <= start < end
            and isinstance(e['quote'], str) and len(e['quote']) == end - start):
        raise ValueError('Invalid excerpt bounds')
    if hashlib.sha256(e['quote'].encode()).hexdigest() != e['quote_sha256']:
        raise ValueError('Excerpt hash mismatch')
    limit = date.fromisoformat(cutoff)
    if not e.get('available_by') or date.fromisoformat(e['available_by'][:10]) > limit:
        raise ValueError('Evidence unavailable by cutoff')
    if e.get('published_at') and date.fromisoformat(e['published_at'][:10]) > limit:
        raise ValueError('Evidence published after cutoff')


def ensure_no_grade_inputs(value):
    if isinstance(value, dict):
        if FORBIDDEN & value.keys():
            raise ValueError('grade input prohibited: ' + str(sorted(FORBIDDEN & value.keys())))
        for child in value.values():
            ensure_no_grade_inputs(child)
    elif isinstance(value, list):
        for child in value:
            ensure_no_grade_inputs(child)


def unique_index(rows, key):
    values = [r[key] for r in rows]
    if len(values) != len(set(values)):
        raise ValueError('duplicate ' + key)
    return dict(zip(values, rows))


def validate_evidence(evidence, source_texts, cutoff):
    index = unique_index(evidence, 'evidence_id')
    for e in evidence:
        body = source_texts[e['row_id']]
        start, end = e['quote_start'], e['quote_end']
        if not (type(start) is int and type(end) is int and 0 <= start < end <= len(body)):
            raise ValueError('invalid quotation bounds')
        if body[start:end] != e['quote']:
            raise ValueError('quotation does not match source')
        if hashlib.sha256(body.encode()).hexdigest() != e['body_sha256']:
            raise ValueError('source text hash mismatch')
        if date.fromisoformat(e['published_at'][:10]) > date.fromisoformat(cutoff):
            raise ValueError('evidence after cutoff')
    return index


def validate_observation(o, case, evidence):
    if o.get('evidence_id') not in evidence:
        raise ValueError('Unknown observation evidence')
    e = evidence[o['evidence_id']]
    if e['disposition'] != 'accepted' or e['case_id'] != case['case_id']:
        raise ValueError('excluded or cross-object evidence')
    if o['case_id'] != case['case_id'] or o['scope_id'] != case['scope_id']:
        raise ValueError('observation scope mismatch')
    if o['polarity'] not in {'support', 'contradict', 'context'}:
        raise ValueError('invalid observation polarity')
    if o['assertion'] not in {'completed', 'application_concept', 'confirmed_absence', 'planned', 'background'}:
        raise ValueError('invalid assertion')
    start, end = o['quote_start'], o['quote_end']
    if not (type(start) is int and type(end) is int and e['quote_start'] <= start < end <= e['quote_end']):
        raise ValueError('observation outside cited passage')
    if e['quote'][start-e['quote_start']:end-e['quote_start']] != o['quote']:
        raise ValueError('observation quotation mismatch')
    if not o.get('rationale', '').strip():
        raise ValueError('observation needs semantic rationale')
    if o.get('resolution') == 'resolved':
        record = o.get('resolution_record', {})
        if not all(record.get(k) for k in ['reviewer_id', 'rationale', 'evidence_id']):
            raise ValueError('resolved contradiction requires a documented resolution')
        cited = evidence.get(record['evidence_id'], {})
        if cited.get('case_id') != case['case_id'] or cited.get('disposition') != 'accepted':
            raise ValueError('resolution evidence must concern the same object')
    if not o['targets'] or len(o['targets']) != len(set(o['targets'])):
        raise ValueError('Observation requires unique gate targets')
    for target in o['targets']:
        axis, level, key = target.split(':')
        if key not in requirements(axis, int(level)):
            raise ValueError('unknown observation target')


def qualification_supported(gate, profile, supporting):
    """A result cannot create its own acceptance threshold after observation."""
    ids = gate.get('requirement_ids', [])
    reqs = unique_index(profile['performance_requirements'], 'requirement_id')
    if not ids or any(i not in reqs for i in ids):
        raise ValueError('qualification requires identified performance requirements')
    critical = {r['requirement_id'] for r in reqs.values() if r['critical_for_stage'] == gate['stage']}
    if not critical or not critical <= set(ids):
        raise ValueError('critical performance requirements not covered')
    measures = gate.get('measurements', [])
    covered = set()
    for m in measures:
        r = reqs[m['requirement_id']]
        if m['requirement_id'] not in ids:
            raise ValueError('unexpected measurement')
        if r['basis'] not in {'predeclared_in_source', 'expert_approved'} or not r.get('basis_quote'):
            raise ValueError('missing predeclared requirement basis')
        if r['basis'] == 'expert_approved' and profile['status'] != 'approved':
            raise ValueError('unapproved expert criterion')
        if m['observation_id'] not in supporting:
            raise ValueError('measurement evidence mismatch')
        o = supporting[m['observation_id']]
        if r['basis'] == 'predeclared_in_source' and r['basis_quote'] not in o['quote']:
            raise ValueError('requirement not present in cited evidence')
        if r.get('kind') == 'qualitative':
            if not r.get('target') or not r.get('test_method') or m.get('result') != 'pass' or not m.get('observed_quote') or m['observed_quote'] not in o['quote']:
                raise ValueError('qualitative qualification needs an explicit target, method and cited successful outcome')
            covered.add(m['requirement_id'])
            continue
        value, threshold = m['value'], r['target']
        if not all(type(v) in {int, float} and math.isfinite(v) for v in [value, threshold]):
            raise ValueError('missing/non-finite threshold or result')
        if m['unit'] != r['unit']:
            raise ValueError('unit or measurement evidence mismatch')
        literals = re.findall(r'(?<![\w.,])[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?![\w.,])', o['quote'])
        if not any(float(literal.replace(',', '')) == value for literal in literals):
            raise ValueError('measurement literal is not in the cited passage')
        comparator = r['operator']
        passed = {'>=': value >= threshold, '<=': value <= threshold, '==': value == threshold}.get(comparator)
        if passed is not True:
            raise ValueError('measurement does not meet criterion')
        covered.add(m['requirement_id'])
    if not set(ids) <= covered:
        raise ValueError('requirement lacks measured result')


def evaluate_case(case, review, observations, evidence, profile, cutoff):
    date.fromisoformat(cutoff)
    ensure_no_grade_inputs(review)
    if review['case_id'] != case['case_id'] or profile['case_id'] != case['case_id']:
        raise ValueError('case/profile/review mismatch')
    if not review.get('reviewer_id') or review.get('reviewer_type') not in {'agent_assisted', 'human_expert'}:
        raise ValueError('reviewer required')
    if review['profile_sha256'] != canonical_sha(profile):
        raise ValueError('criteria changed: review must be renewed')
    if review.get('scope_sha256') != scope_sha256(case):
        raise ValueError('Object scope changed: review must be renewed')
    if review.get('rules_sha256') != rules_sha256():
        raise ValueError('Stage rules changed: review must be renewed')
    if review.get('review_date') and date.fromisoformat(review['review_date'][:10]) > date.fromisoformat(cutoff):
        raise ValueError('Review unavailable by cutoff')
    if set(review['axes']) != {'TRL', 'CRL'}:
        raise ValueError('Both independent axes must be explicitly recorded')
    obs = unique_index(observations, 'observation_id')
    own = [o for o in observations if o['case_id'] == case['case_id']]
    for o in own:
        validate_observation(o, case, evidence)
        validate_excerpt(evidence[o['evidence_id']], cutoff)
        if o.get('resolution') == 'resolved':
            validate_excerpt(evidence[o['resolution_record']['evidence_id']], cutoff)
    outputs = {}
    all_rows = []
    for axis in ['TRL', 'CRL']:
        stages = review['axes'][axis]
        unique_index(stages, 'level')
        if {st['level'] for st in stages} != set(TRL if axis == 'TRL' else CRL):
            raise ValueError('Every stage needs an explicit reviewed/unreviewed record')
        passed = []
        evaluated = []
        for st in stages:
            level = st['level']
            expected = requirements(axis, level)
            if st.get('review_state') not in {'reviewed', 'unreviewed'}:
                raise ValueError('explicit reviewed/unreviewed state required')
            if st['review_state'] == 'unreviewed' and any(g['status'] != 'unknown' for g in st['gates']):
                raise ValueError('an unreviewed stage cannot contain pass/fail decisions')
            gate_map = unique_index(st['gates'], 'key')
            if set(gate_map) != set(expected):
                raise ValueError(f'{axis}{level}: incomplete or unexpected gates')
            statuses = []
            for key, g in gate_map.items():
                if g['status'] not in STATES or not g.get('rationale', '').strip():
                    raise ValueError('invalid gate review')
                target = f'{axis}:{level}:{key}'
                selected = {}
                for oid in g['observation_ids']:
                    if oid not in obs:
                        raise ValueError('unknown observation')
                    o = obs[oid]
                    validate_observation(o, case, evidence)
                    if target not in o['targets']:
                        raise ValueError('citation does not address this gate')
                    selected[oid] = o
                effective = g['status']
                negative = [o['observation_id'] for o in own
                            if target in o['targets'] and o['polarity'] == 'contradict'
                            and o.get('resolution') != 'resolved']
                if negative:
                    effective = 'conflict'
                if g['status'] == 'met':
                    if not selected or any(o['polarity'] != 'support' for o in selected.values()):
                        raise ValueError('met gate requires supporting observations')
                    allowed = {'completed'}
                    if axis == 'TRL' and level <= 2:
                        allowed.add('application_concept')
                    if axis == 'CRL' and level == 1:
                        allowed = {'confirmed_absence'}
                    if any(o['assertion'] not in allowed for o in selected.values()):
                        raise ValueError('claim is not a completed/eligible event')
                    if key == 'qualification':
                        qualification_supported({**g, 'stage': level}, profile, selected)
                if g['status'] in {'not_met', 'conflict'} and not selected and not negative:
                    raise ValueError('negative determination needs evidence; otherwise use unknown')
                if g['status'] == 'not_met' and not any(o['polarity'] == 'contradict' for o in selected.values()) and not negative:
                    raise ValueError('not_met requires contradicting evidence')
                statuses.append(effective)
                all_rows.append({'case_id': case['case_id'], 'axis': axis, 'level': level,
                                 'key': key, 'requirement': expected[key], 'declared_status': g['status'],
                                 'effective_status': effective, 'rationale': g['rationale'],
                                 'observation_ids': g['observation_ids'], 'unresolved_negative': negative})
            if all(s == 'met' for s in statuses):
                passed.append(level)
            if st['review_state'] == 'reviewed':
                evaluated.append(level)
        outputs[axis] = {'public_evidence_stage': max(passed, default=None),
                         'checked_stages': evaluated, 'formal_level': None,
                         'formal_status': '未完成专属细则审定、自评与独立专家确认',
                         'current_industry_level': None,
                         'interpretation': '仅适用于限定对象与证据期间；未知不代表技术退步'}
    return {'case_id': case['case_id'], 'axes': outputs, 'gates': all_rows,
            'review_sha256': canonical_sha(review), 'profile_sha256': canonical_sha(profile),
            'scope_sha256': scope_sha256(case), 'rules_sha256': rules_sha256(),
            'review_date': review.get('review_date'), 'review_date_known': bool(review.get('review_date'))}
