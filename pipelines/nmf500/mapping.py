"""Cosine retrieval only; a link never assigns maturity to a theme."""
import numpy as np
import pandas as pd


def ranked_links(rows, embeddings, centroids, catalog):
    embeddings = np.asarray(embeddings, dtype=np.float64)
    centroids = np.asarray(centroids, dtype=np.float64)
    if embeddings.ndim != 2 or centroids.ndim != 2 or len(rows) != len(embeddings) or embeddings.shape[1] != centroids.shape[1]:
        raise ValueError('Misaligned context embeddings and topic centroids')
    if not np.isfinite(embeddings).all() or not np.isfinite(centroids).all():
        raise ValueError('Non-finite mapping vectors')
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    cnorm = np.linalg.norm(centroids, axis=1, keepdims=True)
    if (norms <= 1e-12).any():
        raise ValueError('Zero context vector cannot receive a topic')
    active = np.flatnonzero(cnorm.ravel() > 1e-12)
    if len(active) < 3:
        raise ValueError('Top3 mapping requires three active topic centroids')
    if not catalog.topic_id.is_unique or not set(active) <= set(catalog.topic_id):
        raise ValueError('Incomplete or duplicate topic catalog')
    similarity = (embeddings / norms) @ (centroids[active] / cnorm[active]).T
    local = np.argsort(-similarity, axis=1, kind='stable')[:, :3]
    names = catalog.set_index('topic_id')['name']
    links = []
    for i, row in enumerate(rows):
        margin = float(similarity[i, local[i, 0]] - similarity[i, local[i, 1]])
        for rank, column in enumerate(local[i], 1):
            tid = int(active[column])
            links.append(dict(entity_type=row['entity_type'], entity_id=row['entity_id'], entity_name=row['name'],
                rank=rank, topic_id=tid, category_id=f'N{tid + 1:04d}', category_name=names.loc[tid],
                cosine=float(similarity[i, column]), top1_top2_margin=margin,
                association_status='automatic_candidate_needs_semantic_review', needs_review=True,
                transfers_maturity=False))
    return pd.DataFrame(links)
