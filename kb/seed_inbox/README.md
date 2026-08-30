# Seed inbox

Supervisor agents write ONE file here: `<domain>.json`
(domain in: python | c_cpp | web | devops | security)

See `kb/seed_merge.py` for the exact JSON shape. Then run:
`python kb/seed_merge.py` to load, then `python kb/kb_export.py` to refresh the mirror.
