Models
===================================

LMQL is a high-level, front-end language for text generation. This means that LMQL is not specific to any particular text generation model. Instead, we support a wide range of text generation models on the backend, including [OpenAI models](https://platform.openai.com/docs/models), as well as self-hosted models via [🤗 Transformers](https://huggingface.co/transformers).

Due to the modular design of LMQL, it is easy to add support for new models and backends. If you would like to propose or add support for a new model API or inference engine, please reach out to us via our [Community Discord](https://discord.com/invite/7eJP4fcyNT) or via [hello@lmql.ai](mailto:hello@lmql.ai).

Specifying The Model
--------------------

LMQL offers two ways to specify the model that is used as underlying LLM:

**Queries with `from` Clause**: The first option is to simply specify the model as part of the query itself. For this, you can use the `from` in combination with the indented syntax. This can be particularly useful, if your choice of model is intentional and should be part of your program.

.. lmql:: 
    name::specify-model
    argmax
        "This is a query with a specified decoder: [RESPONSE]
    from
        "openai/text-ada-001"

**Specifying the Model Externally**: The second option is to specify the model and its parameters externally, i.e. separately from the actual program code:


.. code-block:: python

    import lmql

    # uses 'chatgpt' by default
    @lmql.query(model="chatgpt")
    def tell_a_joke():
        '''lmql
        """A list of good dad jokes. A indicates the punchline
        Q: How does a penguin build its house?
        A: Igloos it together.
        Q: Which knight invented King Arthur's Round Table?
        A: Sir Cumference.
        Q:[JOKE]
        A:[PUNCHLINE]""" where STOPS_AT(JOKE, "?") and  STOPS_AT(PUNCHLINE, "\n")
        '''

    tell_a_joke() # uses chatgpt

    tell_a_joke(model="openai/text-davinci-003") # uses text-davinci-003

This is only possible when using LMQL from a Python program. When running in the playground, you can alternatively use the model dropdown available in the top right of the program editor:

.. raw html  
.. figure:: https://github.com/eth-sri/lmql/assets/17903049/5ba2ffdd-e64d-465c-85be-5d9dc2ab6c14
    :align: center
    :width: 70%
    :alt: Screenshot of the model dropdown in the playground

    Screenshot of the model dropdown in the playground

Using Multiple Models
---------------------

LMQL currently supports the use of only one model per query. If you want to mix multiple models, the advised way is to use multiple queries that are executed in sequence. The main obstacles in supporting this, is the fact that different models produce differently scaled token probabilities, which means an end-to-end decoding process would be difficult to implement. 

However, we are actively exploring ways to [support this in the future](https://github.com/eth-sri/lmql/issues/82).

Available Model Backends
------------------------

.. toctree::
    :maxdepth: 1
    
    ./openai.md
    ./azure.md
    ./hf.md
    ./llama.cpp.md