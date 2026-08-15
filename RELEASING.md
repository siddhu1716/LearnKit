# Releasing LearnKit

LearnKit has historical PyPI uploads `0.0.1`, `0.0.2`, and `0.0.3`. The first formal GitHub prerelease uses tag `v2.0`; its canonical Python package version is `2.0.0`.

## One-time setup

### PyPI Trusted Publishing

In the PyPI project settings for `learnkit-ai`, add a pending or existing Trusted Publisher with:

- Owner: `siddhu1716`
- Repository: `LearnKit`
- Workflow: `release.yml`
- Environment: `pypi`

In GitHub repository settings, create the `pypi` environment. Add required reviewers if desired. No long-lived PyPI token is needed.

### Branch and marketplace checks

Before the first stable release:

1. Merge the release commit into the repository's default branch.
2. Update marketplace refs that still point to a development branch.
3. Confirm every plugin manifest version matches `pyproject.toml`.
4. Confirm the developer guide uses the final tag and default-branch URLs.

## Release checklist

1. Update `version` in `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. Run:

   ```bash
   python -m pip install -e ".[dev,coding-agents]"
   pytest -q
   ruff check learnkit
   python -m benchmarks.make_results --check
   python -m build
   twine check dist/*
   ```

4. Commit and push the release changes.
5. Create a GitHub Release with tag `v<version>`. A trailing patch zero may be omitted, so package `2.0.0` may use tag `v2.0` or `v2.0.0`.
6. Publish the release.

The `Release` GitHub Actions workflow then:

- verifies that the tag matches `pyproject.toml`;
- runs the test suite;
- builds the wheel and source distribution once;
- checks distribution metadata;
- uploads both files to the GitHub Release; and
- publishes the same files to PyPI using Trusted Publishing.

## Verify the release

Use a clean environment:

```bash
pipx install "learnkit-ai[coding-agents]==2.0.0"
learnkit --version
learnkit plugin doctor
```

Verify the GitHub Release contains both `.whl` and `.tar.gz` distribution files. Verify PyPI shows the expected license, Python requirement, project links, and version.

## Failure handling

- A PyPI version cannot be overwritten. Fix the issue, increment the version, and publish a new release.
- Do not delete and recreate a Git tag after users may have fetched it.
- If PyPI publishing fails before upload, fix Trusted Publisher/environment configuration and rerun the failed workflow job.
- If GitHub assets fail but PyPI succeeds, rerun only the release-assets job.

### Recover an already-published release

If a GitHub Release was published before its package metadata was corrected, commit and push the corrected metadata, then run the `Release` workflow manually from that branch with the existing tag in `release_tag`. For the current release, use `v2.0`. This preserves the published tag while building and publishing the corrected branch commit.

The existing `v2.0` tag points to the pre-correction commit. If strict tag-to-artifact source provenance is required, do not use manual recovery; publish a new release tag from the corrected commit instead.

## License

LearnKit remains Apache-2.0. Existing Apache permissions for public revisions are irrevocable. Relicensing future versions requires documented rights or consent for all contributed code.
