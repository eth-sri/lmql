gpt3_tokenizer
===============
| An `OpenAI`_ GPT3 helper library for encoding/decoding strings and counting tokens.
| Counting tokens gives the same output as OpenAI's `tokenizer`_
|
| Tested with versions: **2.7.12**, **2.7.18** and all **3.x.x** versions

Installing
--------------
.. code-block:: bash

    pip install gpt3_tokenizer

    
Examples
---------------------

**Encoding/decoding a string**

.. code-block:: python

    import gpt3_tokenizer

    a_string = "That's my beautiful and sweet string"
    encoded = gpt3_tokenizer.encode(a_string) # outputs [2504, 338, 616, 4950, 290, 6029, 4731]
    decoded = gpt3_tokenizer.decode(encoded) # outputs "That's my beautiful and sweet string"

**Counting tokens**

.. code-block:: python

    import gpt3_tokenizer

    a_string = "That's my beautiful and sweet string"
    tokens_count = gpt3_tokenizer.count_tokens(a_string) # outputs 7

.. _tokenizer: https://platform.openai.com/tokenizer
.. _OpenAI: https://openai.com/