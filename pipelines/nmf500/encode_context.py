"""Encode bounded case context and direction names in the existing BGE-M3 space.

Uses the workspace's Python 3.10 ONNX GPU runtime; no stage values enter text.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO.parent
sys.path[:0] = [str(ROOT / 'aaaa/bge_m3/_runtime'), str(ROOT / 'aaaa/bge_m3/_core')]
import numpy as np
from tokenizers import Tokenizer
import onnxruntime as ort


def contexts():
    def read(name):
        return json.loads((REPO / 'data' / (name + '.json')).read_text())
    evidence = read('evidence')
    sources = {s['source_id']: s for s in read('sources')}
    rows = []
    for obj in read('objects'):
        own = [e for e in evidence if e['case_id'] == obj['case_id']]
        text = '\n'.join([obj['canonical_name'], obj['object_configuration'], obj['application_or_target_function']] + [sources[e['source_id']]['title'] + '\n' + e['quote'] for e in own])
        rows.append({'entity_type': 'case', 'entity_id': obj['case_id'], 'name': obj['canonical_name'], 'text': text})
    for direction in read('technology_registry'):
        if direction['entity_level'] == 'direction_candidate':
            text = direction['canonical_name'] + '\n' + direction.get('function', '')
            rows.append({'entity_type': 'direction', 'entity_id': direction['technology_id'], 'name': direction['canonical_name'], 'text': text})
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, default=REPO / 'work/nmf500/context')
    args = p.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    rows = contexts()
    signature = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    final = out / 'embeddings.npy'
    audit_path = out / 'ENCODING.json'
    if final.exists() and audit_path.exists():
        audit = json.loads(audit_path.read_text())
        if audit['input_sha256'] != signature:
            raise ValueError('Context changed: use a new output directory')
        print('Reusing verified context embeddings', flush=True)
        return
    (out / 'contexts.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    model = ROOT / 'aaaa/bge_m3/models/bge-m3'
    tokenizer = Tokenizer.from_file(str(model / 'tokenizer.json'))
    tokenizer.enable_truncation(max_length=2048)
    tokenizer.no_padding()
    encoded = [tokenizer.encode(r['text']) for r in rows]
    lengths = np.array([len(e.ids) for e in encoded])
    order = np.argsort(lengths, kind='stable')
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    options.enable_mem_pattern = False
    session = ort.InferenceSession(str(model / 'onnx/model_fp16.onnx'), sess_options=options, providers=[('CUDAExecutionProvider', {'gpu_mem_limit': 12000 * 1024**2, 'arena_extend_strategy': 'kNextPowerOfTwo'}), 'CPUExecutionProvider'])
    if 'CUDAExecutionProvider' not in session.get_providers():
        raise RuntimeError('Existing full BGE-M3 CUDA runtime unavailable')
    embeddings = np.zeros((len(rows), 1024), dtype=np.float32)
    start = time.time()
    pos = 0
    last = 0
    while pos < len(rows):
        length = int(lengths[order[min(pos + 15, len(rows) - 1)]])
        batch = max(1, min(16, 4096 // max(32, length)))
        ids = order[pos:pos + batch]
        width = int(lengths[ids].max())
        input_ids = np.full((len(ids), width), 1, dtype=np.int64)
        mask = np.zeros((len(ids), width), dtype=np.int64)
        for j, i in enumerate(ids):
            input_ids[j, :lengths[i]] = encoded[i].ids
            mask[j, :lengths[i]] = 1
        v = session.run(['sentence_embedding'], {'input_ids': input_ids, 'attention_mask': mask})[0]
        if not np.isfinite(v).all():
            raise ValueError('Nonfinite embeddings')
        embeddings[ids] = v / np.linalg.norm(v, axis=1, keepdims=True)
        pos += len(ids)
        if time.time() - last > 20 or pos == len(rows):
            print(f'CONTEXT {pos}/{len(rows)} seconds={time.time()-start:.1f}', flush=True)
            last = time.time()
    np.save(final, embeddings)
    audit = {'input_sha256': signature, 'model': 'BAAI/bge-m3', 'dimension': 1024, 'max_tokens': 2048, 'text': 'object name/configuration/function and accepted source titles/quotes; direction name/function; no TRL/CRL stages', 'documents': len(rows), 'providers': session.get_providers(), 'seconds': time.time()-start, 'mapping_role': 'automatic retrieval association only; semantic review required'}
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
