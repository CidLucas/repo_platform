# Creating a detect-secrets baseline

When you rotate secrets and replace checked-in keys with placeholders, create a
detect-secrets baseline and commit it. The baseline allows CI to enforce that
no *new* secrets are introduced while ignoring the existing, approved findings.

Recommended steps (local):

1. Rotate all secrets and replace any checked-in values with placeholders.

2. Run the baseline creator script:

```bash
chmod +x scripts/create_secrets_baseline.sh
./scripts/create_secrets_baseline.sh
```

3. Review the generated `.secrets.baseline` file. You can use the audit helper:

```bash
pip install detect-secrets
cat .secrets.baseline | detect-secrets audit -
```

4. If everything looks good, commit the baseline:

```bash
git add .secrets.baseline
git commit -m "chore(secrets): add detect-secrets baseline"
git push
```

5. After the baseline is committed, the `secret-scan.yml` job in CI will fail
   on any new findings introduced by future PRs.

Notes:
- The baseline will contain the rule matches that detect-secrets found when
  you generated it. If you later intentionally add a secret-like pattern,
  you will need to update the baseline (review carefully before doing so).
- Keep `.secrets.baseline` under source control. It does not contain secret
  values, only the metadata of detected occurrences.
