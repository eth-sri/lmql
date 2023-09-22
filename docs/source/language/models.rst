Models
===================================

LMQL is a high-level, front-end language for text generation. This means that LMQL is not specific to any particular text generation model. Instead, we support a wide range of text generation models on the backend, including `OpenAI models <https://platform.openai.com/docs/models>`_, as well as self-hosted models via `🤗 Transformers <https://huggingface.co/transformers>`_ or `llama.cpp <./llama.cpp.html>`_. 

Due to the modular design of LMQL, it is easy to add support for new models and backends. If you would like to propose or add support for a new model API or inference engine, please reach out to us via our `Community Discord <https://discord.com/invite/7eJP4fcyNT>`_ or via `hello@lmql.ai <mailto:hello@lmql.ai>`_.

Loading Models
------------------------

To load models in LMQL, you can use the :code:`lmql.model(...)` function which gives you an `lmql.LLM <../lib/generations.html#lmql-llm-objects>`_ object:

.. code-block:: python

    lmql.model("openai/gpt-3.5-turbo-instruct") # OpenAI API model
    lmql.model("random", seed=123) # randomly sampling model
    lmql.model("llama.cpp:<YOUR_WEIGHTS>.bin") # llama.cpp model

    lmql.model("local:gpt2") # load a `transformers` model in-process
    lmql.model("local:gpt2", cuda=True, load_in_4bit=True) # load a `transformers` model in process with additional arguments
    lmql.model("gpt2") # access a `transformers` model hosted via `lmql serve-model`

LMQL supports multiple inference backends, each of which has its own set of parameters. For more details on how to use and configure the different backends, please refer to one of the following sections:

.. toctree::
    :maxdepth: 1
    
    ./openai.md
    ./azure.md
    ./hf.md
    ./llama.cpp.md
    ./replicate.md

Specifying The Model
--------------------

After creating an :code:`lmql.LLM` object, you can use it pass it to a query program to specify the model to use during execution. There are two ways to do this:

**Option A: Queries with `from` Clause**: The first option is to simply specify the model as part of the query itself. For this, you can use the `from` in combination with the indented syntax. This can be particularly useful, if your choice of model is intentional and should be part of your program.

.. lmql:: 
    name::specify-model
    argmax
        "This is a query with a specified decoder: [RESPONSE]
    from
        "openai/text-ada-001"

Here, we specify :code:`openai/text-ada-001` directly, but the shown code is equivalent to the use of :code:`lmql.model(...)`, i.e. :code:`lmql.model("openai/text-ada-001")`.

**Option B: Specifying the Model Externally**: The second option is to specify the model and its parameters externally, i.e. separately from the actual program code:

 
.. lmql::
    name::specify-model-externally

    import lmql

    # uses 'chatgpt' by default
    @lmql.query(model="chatgpt")
    def tell_a_joke():
        '''lmql
        """A great good dad joke. A indicates the punchline
        Q:[JOKE]
        A:[PUNCHLINE]""" where STOPS_AT(JOKE, "?") and  STOPS_AT(PUNCHLINE, "\n")
        '''

    tell_a_joke() # uses chatgpt

    tell_a_joke(model=lmql.model("openai/text-davinci-003")) # uses text-davinci-003

Here, the :code:`tell_a_joke` query will use ChatGPT by default, but can still be configured to use a different model by passing it as an argument to the query function on invocation.

Playground
----------

To specify the mode when running in the playground, you can use the model dropdown available in the top right of the program editor, to set and override the :code:`model` parameter of your query program:

.. raw html  
.. figure:: https://github.com/eth-sri/lmql/assets/17903049/5ba2ffdd-e64d-465c-85be-5d9dc2ab6c14
    :align: center
    :width: 70%
    :alt: Screenshot of the model dropdown in the playground

    Screenshot of the model dropdown in the playground

Using Multiple Models
---------------------

LMQL currently supports the use of only one model per query. If you want to mix multiple models, the advised way is to use multiple queries that are executed in sequence. The main obstacles in supporting this, is the fact that different models produce differently scaled token probabilities, which means an end-to-end decoding process would be difficult to implement. 

However, we are actively exploring ways to `support this in the future <https://github.com/eth-sri/lmql/issues/82>`_. 