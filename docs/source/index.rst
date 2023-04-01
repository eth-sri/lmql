.. note::

    **This is only a preview/placeholder for LMQL's documentation. The full documentation will be available on official launch.**

Welcome to LMQL!
===================================

**LMQL** (Language Model Query Language) is a programming language for large language model interaction. 
It facilitates LLM interaction by combining the benefits of natural language prompting with the expressiveness 
of Python. With only a few lines of LMQL code, users can express advanced, multi-part and tool-augmented LM queries, 
which then are optimized by the LMQL runtime to run efficiently as part of the LM decoding loop.

LMQL is a research project by the `Secure,  Reliable, and Intelligent Systems Lab <https://www.sri.inf.ethz.ch/>`_ at ETH Zürich.


.. links
.. `Open Food Facts database <https://world.openfoodfacts.org/>`_

.. lmql::
    name::hello
    # this sample was updated
    argmax
        """A list of good dad jokes. A indicates the punchline
        Q: How does a penguin build its house?
        A: Igloos it together.
        Q: Which knight invented King Arthur's Round Table?
        A: Sir Cumference.
        Q:[JOKE]
        A:[PUNCHLINE]"""
    from
        "openai/text-davinci-003"
    where
        len(JOKE) < 120 and 
        STOPS_AT(JOKE, "?") and 
        STOPS_AT(PUNCHLINE, "\n") and 
        len(PUNCHLINE) > 1

.. lmql::
    name::chat
    argmax 
        "{:system} You are a marketing chatbot for the language model query language (LMQL)."
        for i in range(10):
            "{:user} {await input()}"
            "{:assistant} [ANSWER]"
    from
        "chatgpt"

.. code-block:: python
    
    def test(): pass

Test 

.. Quick Start
.. -----------

.. To get started, check out the :doc:`quickstart` section. 

.. For smaller experiments, you can also use the web-based `LMQL Playground <lmql.ai/playground/>`_.

.. .. raw:: html

..     <embed>
..         <iframe src="https://lmql.ai/playground" width="100%" height="450pt"></iframe>
..     </embed>

.. Test

.. Contents
.. --------

.. .. toctree::

   quickstart
   dev-setup
