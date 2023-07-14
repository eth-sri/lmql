# Azure OpenAI Models

LMQL also supports OpenAI models hosted on Azure. To use these models, you need to configure your Azure API credentials. For this, there are two options: Configuration via environment variables and configuration via `lmql.model`:

## Configuration via Environment Variables

To configure an LMQL runtime as a whole to use a specific Azure deployed model for OpenAI calls, you can provide the following environment variables:

```
# set the API type based on whether you want to use a completion or chat endpoint
OPENAI_API_TYPE=azure|azure-chat 

# your Azure API base URL, e.g. 'https://<YOUR_BASE>.openai.azure.com/'
OPENAI_API_BASE=<API_BASE> 

# set your API key, can also be provided per deployment 
# via OPENAI_API_KEY_{<your-deployment-name>.upper()}
OPENAI_API_KEY=<key>
```

When using your Azure models, make sure to invoke them as `openai/<DEPLOYMENT NAME>` in your query code. If you need more control, or want to use different deployments, base URLs or api versions across your application, please refer to the next section.

## Configuration via `lmql.model`

If you need to configure Azure credentials on a per-query basis, you can also specify the Azure access credentials as part of an `lmql.model(...)` object:

```python
my_azure_model = lmql.model(
    # the name of your deployed model/engine, e.g. 'my-model'
    "openai/<DEPLOYMENT>", 
    # set to 'azure-chat' for chat endpoints and 'azure' for completion endpoints
    api_type="azure|azure-chat",  
    # your Azure API base URL, e.g. 'https://<YOUR_BASE>.openai.azure.com/'
    api_base="<API_BASE>", 
    # your API key, can also be provided via env variable OPENAI_API_KEY 
    # or OPENAI_API_KEY_{<your-deployment-name>.upper()}
    [api_key="<API_KEY>"] , 
    # API version, defaults to '2023-05-15'
    [api_version="API_VERSION",]
    # prints the full endpoint URL to stdout on each query (alternatively OPENAI_VERBOSE=1)
    [verbose=False] 
)
```

You can then use this model in your query code as follows:

```{lmql}
name::use-azure-model

argmax "Hello [WHO]" from my_azure_model
```

Configuration parameters specified as part of an `lmql.model(...)` object take precedence over environment variables. The latter just act as a fallback, e.g. when `api_key=` is not specified as a keyword argument.