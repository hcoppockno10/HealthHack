# Welcome to the HealthHack repo!

Prerequistes: docker, uv, python > 3.12

```bash
git clone https://github.com/hcoppockno10/HealthHack.git
python -m venv .venv
source .venv/bin/activate 
uv install
```

To run the analysis:

First get the data from Harry and store in .data/
Then also get the temp api key from harry.

```
inspect eval main.py --model <provider>/<model> --limit 5
```

