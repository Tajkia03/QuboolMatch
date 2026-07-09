# KNN Match Recommendation POC

This folder contains the recommendation model used by the application. It can
also run standalone against `quboolmatch_diverse_500_profiles.csv`.

The model combines:

- KNN profile similarity across physical, background, lifestyle, household,
  hobby, and interest features.
- Two-way partner preference scoring.
- Required-preference checks with a relaxed fallback when necessary.

Sensitive health, disability, fertility, and genetic-condition fields are
normalized and retained in the local profile artifact, but they do not affect
recommendation rankings.

## 1. Create the Python environment

Run these commands from the repository root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pandas numpy scikit-learn joblib pytest
```

On Windows PowerShell, activate the environment with:

```powershell
backend\.venv\Scripts\Activate.ps1
```

## 2. Train the model

Validate that first names and explicitly gendered surnames match profile gender:

```bash
python backend/recommendation/fix_gender_names.py --check
```

To correct mismatches in the bundled or specified CSV, run the script with `--write`, then
retrain the model:

```bash
python backend/recommendation/fix_gender_names.py --write
```

```bash
python backend/recommendation/train_knn.py
```

Training reads the bundled CSV and creates these generated files under
`backend/recommendation/artifacts/`:

- `knn_model.joblib`
- `profiles.joblib`
- `metadata.json`

Retrain whenever the CSV or feature logic changes.

## Database-backed application training

After applying migrations, create the first database-backed model from the
`backend` directory:

```powershell
python retrain_recommendation_model.py
```

The application watches committed `users` and `profiles` changes. Changes are
coalesced for 10 seconds and trained in a separate process. PostgreSQL advisory
locking guarantees that only one trainer publishes at a time, even with
multiple API processes. Requests continue using the last valid artifacts and
switch to the new version without a restart. Runtime versions are not committed
to Git; the tracked CSV artifacts remain the bootstrap fallback.

To make the bundled profiles available as local login accounts, apply the
project migrations yourself and then run from `backend/`:

```powershell
python seed_recommendation_data.py
```

The CSV email is the username and the shared development password is
`seed123`. The command is idempotent and is blocked outside dev/test unless
`--allow-production` is explicitly supplied.

## 3. Get recommendations

Human-readable output for user ID `1`:

```bash
python backend/recommendation/recommend.py --user-id 1 --top-k 5
```

JSON output suitable for later website/API integration:

```bash
python backend/recommendation/recommend.py --user-id 1 --top-k 5 --json
```

Replace `1` with any `user_id` present in the CSV. `--top-k` controls the
maximum number of returned matches and defaults to `5`.

Custom CSV and artifact locations can also be supplied:

```bash
python backend/recommendation/train_knn.py \
  --csv /path/to/profiles.csv \
  --artifacts-dir /path/to/artifacts

python backend/recommendation/recommend.py \
  --user-id 1 \
  --artifacts-dir /path/to/artifacts \
  --json
```

## 4. Run tests

```bash
python -m pytest backend/recommendation/test_recommender.py -q \
  --confcutdir=backend/recommendation
```

## Common errors

- `Artifacts not found`: run `train_knn.py` before requesting recommendations.
- `User not found`: use a `user_id` that exists in the CSV.
- `ModuleNotFoundError`: activate the virtual environment and install the listed
  dependencies.
