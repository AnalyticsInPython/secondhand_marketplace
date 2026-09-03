# Generated seed data

Do not edit these files by hand. They are output, not source.

Regenerate with:

```bash
python3 -m seed.generate
```

Full documentation — column reference, load instructions, the constraints your
schema should enforce, and the open questions — is in
[`docs/mock_data_spec.md`](../docs/mock_data_spec.md).

| File | Table |
|---|---|
| `users.csv` | `users` |
| `listings.csv` | `listings` |
| `listing_photos.csv` | `listing_photos` |
| `listing_views.csv` | `listing_views` |
| `saves.csv` | `saves` |
| `enquiries.csv` | `enquiries` |
| `filter_events.csv` | `filter_events` |
| `zip_reference.csv` | `zip_reference` |
| `seed.sql` | all of the above, plus the enum types |

Load the CSVs in the order listed — the foreign keys require it.

The placeholder photos are **not** committed. Rebuild them with
`python3 scripts/make_photos.py --out web/public/photos`.
