# Azure OpenAI Models

LMQL also supports OpenAI models hosted on Azure. To use these models, you need to configure your Azure API credentials. For this, there are two options: Configuration via environment variables and configuration via `lmql.model`:

## Configuration via Environment Variables

To configure an LMQL runtime as a whole to use Azure endpoints for OpenAI models, you can provide the following environment variables:

```
OPENAI_API_TYPE=azure
AZURE_OPENAI_<ENV_NAME>_ENDPOINT=<endpoint>
AZURE_OPENAI_<ENV_NAME>_KEY=<key>
```

where `<ENV_NAME>` is the name of the hosted OpenAI model, e.g. `gpt-3.5-turbo` but uppercase and with `-` replaced by `_`. For example, to configure the `gpt-3.5-turbo` model, you would use the `AZURE_OPENAI_GPT-3_5-TURBO_ENDPOINT` and `AZURE_OPENAI_GPT-3_5-TURBO_KEY` environment variables.

## Configuration via `lmql.model`

If you prefer to configure Azure credentials on a per-query basis, you can also specify the endpoint and API key to use as part of a `lmql.model(...)` expression:

```{lmql}

name::azure-api-key

import lmql

argmax
    "Hello[WHO]"
from
    lmql.model("openai/gpt-3.5-turbo", endpoint="azure://<ENDPOINT>", azure_api_key="<API_KEY>")
where
    STOPS_AT(WHO, "\n") and len(TOKENS(WHO)) < 10
```

Where `<ENDPOINT>` should not include the `https://` prefix and `<API_KEY>` is the API key for the deployed model.