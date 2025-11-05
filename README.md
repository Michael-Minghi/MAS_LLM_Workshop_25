# MAS 25/26 LLM Workshop
This is the repository for MAS LLM Workshop

## Installation (Optional)
This project is managed by UV, follow the installation if UV and Python are not installed.

### Install UV

**on Windows**
```sh
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
**on Mac**
```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Python

```sh
uv python install 3.11
```

### Set up API keys
Duplicate `default.env`, rename the copy to `.env` and paste your API Keys in it.

⚠️ DO NOT COMMIT FILES CONTAINING API KEYS TO THE GIT REPO ⚠️
```sh
OPENAI_API_KEY=[Your API KEY]
LOGFIRE_TOKEN=[Your TOKEN]
```

### Run the example