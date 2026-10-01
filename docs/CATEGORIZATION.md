# Human-reviewed multi-label categorization

Implemented in PHASE 14. Suggestions only reference active database categories.
Neither inference method changes book categories. Librarian/Admin must explicitly
review and confirm the final set; readers cannot generate or review predictions.

## Methods and evidence

`categorization-v1` uses title, description, authors, language, year and publisher.
Existing category labels are excluded from input to prevent target leakage.

1. TF-IDF word unigrams/bigrams, sublinear TF, 30,000 maximum features; One-vs-Rest
   Logistic Regression (C=1, balanced classes, max_iter=1000, seed=42). Vocabulary,
   IDF and classifiers fit training records only. Saved JSON coefficients are
   checked against sklearn inference; no executable pickle is loaded.
2. Pinned multilingual E5 base from SEMANTIC_SEARCH.md compares book query vectors
   with passage vectors of actual category names/descriptions. Scores are cosine
   similarities, not probabilities. Newly created categories can participate.

The versioned seed-derived dataset `ml/data/categorization.json` contains only
12 books and 10 labels. Deterministic split: 8 training, 2 validation, 2 test.
Thresholds maximize validation micro F1, choosing the higher threshold on ties.
TF-IDF searches 0.05–0.95 in 0.05 steps; embeddings search observed validation
similarities. Selected thresholds: 0.45 and 0.8116545353204155 respectively.

| Method | Validation micro F1 | Test micro precision/recall/F1 | Test macro F1 |
|---|---:|---:|---:|
| TF-IDF/OVR | 0.333333 | 0 / 0 / 0 | 0 |
| E5 categories | 0.666667 | 0.666667 / 0.666667 / 0.666667 | 0.2 |

These two held-out books cannot establish general accuracy. Psychology and Science
have zero training positives, and several other labels have only one. Constant
negative classical classifiers and all per-category/support results are reported
honestly in `ml/evaluation/categorization_results.json`. A larger representative
labeled corpus is needed for useful quality estimates. Review acceptance rate is
operational feedback, never ML accuracy. Two actual pipeline runs reproduced the
same split, thresholds, coefficients, artifact revision and metrics.

Dataset SHA-256: bf15f64c7f0c9f57c3605a1b3310b1dbe61d8ce37c1c753536c6c33945cbbced.
Artifact revision: f0c7479b3f8d0b0c93bb1d7a4c85f94f33ea752e91b904b346ef59c33d86c399.

## Operations and review

Save book metadata first, then use **AI санаттау** in the book editor or
`/admin/category-predictions` / `/librarian/category-predictions`. Generate either
method; accept/remove suggestions, add existing categories, or reject all.
Confirmation saves the displayed final category set, including an empty set.

Run, individual predictions and manual selections retain model/dataset provenance,
score kind, reviewer and review time. Under row locks, review rechecks live staff
permission, source hash, previous assigned categories and the active taxonomy hash.
Any changed taxonomy conservatively requires regeneration. Same-final-set retries
are idempotent; competing different reviews fail. ACCEPTED means unchanged nonempty
predictions, MODIFIED means a different nonempty final set, REJECTED means empty.
Book category changes invalidate embeddings and dispatch regeneration after commit.

APIs: POST `/api/v1/ai/categorize`; GET `/api/v1/ai/category-predictions` and `/{id}`;
POST `/{id}/review`. Lists are paginated/filterable. Origin checks, live RBAC and
per-staff rate limits apply. Missing/invalid artifacts return
`CATEGORIZATION_UNAVAILABLE`; stale reviews return `STALE_PREDICTION`.

## Reproduce

From the workspace, with native backend dependencies and downloaded E5 weights:

```powershell
$env:PYTHONPATH='C:/SmartLibrary/backend'
$env:MODEL_CACHE_DIRECTORY='C:/SmartLibrary/work/model-cache'
$env:HF_HUB_OFFLINE='1'
backend/.venv/Scripts/python.exe -m app.ai.categorization.training --dataset ml/data/categorization.json --metrics ml/evaluation/categorization_results.json
```

The JSON artifact is written to MODEL_CACHE_DIRECTORY/categorization/model.json.
Deploy it into the shared Docker model volume at `/app/var/models/categorization/model.json`.
Weights/generated artifacts remain Git-ignored; versioned data and metrics contain
no private user exports. Training is an explicit offline command, never an
interactive request. Inference validates bounded finite coefficients and dimensions.

References: [sklearn OneVsRestClassifier](https://sklearn.org/stable/modules/generated/sklearn.multiclass.OneVsRestClassifier.html),
[sklearn leakage guidance](https://scikit-learn.org/1.8/common_pitfalls.html).
