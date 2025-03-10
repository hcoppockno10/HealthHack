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

What is inspect? It is an AI evaluation package developed by UK AISI. Please see the the [documentation](https://inspect.ai-safety-institute.org.uk/)

## Things to be cracking on with

- update the workflow to an agentic loop. See [here](https://inspect.ai-safety-institute.org.uk/agents.html) for insp!
- perform a consistency analysis on the LLM flagging. 
- we currently do not extract the decision from the model, please use regex to extract the decision
- any else, go wild!
