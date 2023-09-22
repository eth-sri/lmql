Welcome To LMQL
===================================
 
.. raw:: html
  
  <div class="subtitle"><img class="inline-logo" src="_static/images/lmql.svg"/> LMQL is a programming language for large language model interaction.</div>

LMQL facilitates LLM interaction by combining the benefits of natural language prompting with the expressiveness 
of Python. The project is focused on enabling type-safe and robust LLM interaction, while providing a seamless experience via `scripted prompting <language/scripted_prompts.md>`_, `constraint-guided decoding <language/constraints.md>`_, `nested functions <language/functions.md>`_ and `program interoperation <language/tools.md>`_.

Quick Start
-----------

To get started with LMQL, check out the :doc:`quickstart` guide or one of the following resources:


.. raw:: html

    <div class="getting-started-options">
      <div class="columns is-getting-started">
        <div class="column getting-started">
          <h2>Explore LMQL</h2>
          <a class="primary" href="https://lmql.ai/playground">
            Playground IDE
          </a>
          <a href="quickstart.html">
            🚀 Getting Started Guide
          </a>
          <a href="https://lmql.ai">
            🖼️ Examples Gallery
          </a>
        </div>

        <div class="column getting-started">
          <h2>Run Locally</h2>
          <div class="cmd"> 
              pip install lmql
          </div> 
          To run LMQL locally, read the <span><a href="installation.html">Installation Instructions</a> section of the documentation.</span>
        </div>
        <div class="column getting-started">
          <h2>Community</h2>
          <a href="https://discord.gg/7eJP4fcyNT">
            💬 Discord Server
          </a>
          <a href="https://twitter.com/lmqllang">
            🐥 Twitter
          </a>
          <a href="mailto:hello@lmql.ai">
            ✉️ E-Mail
          </a>
        </div>
      </div>
    </div>

Contents
--------

To learn more about LMQL, select one of the following sections or navigate the documentation using the sidebar.

.. grid:: 2

    .. grid-item-card:: 🏔️ Language Overview
        :link: language/overview.md
          
        Get started with the LMQL language and learn about its core concepts.

    .. grid-item-card:: ⛓️ Constraints
       :link: language/constraints.md

       Learn more about token-level constraints and how to use them to guide LLM reasoning.

    .. grid-item-card:: 🐍 Python Integration
       :link: python/python.ipynb

       Seamlessly interleave LMQL with Python code to integrate LMQL into your existing workflows.

    .. grid-item-card:: 💬 Chat Applications
       :link: lib/chat.rst

       Learn how to build a chat application with LMQL.

    .. grid-item-card:: 🚜 Available Backends
       :link: language/models.rst

       Use LMQL with a range of inference backends, including llama.cpp,
       `transformers`, and OpenAI.
      
    .. grid-item-card:: 💻 Generations API
       :link: lib/generations.md

       Start using LMQL via a lightweight Python API, before diving deeper into the language.
      

.. toctree::
  :hidden:
  :maxdepth: 1

  quickstart
  installation

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: 📖 LMQL Language 
   
   language/overview.md
   language/scripted_prompts.md
   language/constraints.md
   language/decoders.md
   language/functions.md
   language/decorators.md
   language/models.rst
   language/tools.md

.. toctree::
    :hidden:
    :maxdepth: 2
    :caption: 📦 Library
    
    lib/generations.md
    lib/chat.rst
    lib/output.md

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: 🔗 Python Integration
    
    python/python.ipynb
    python/langchain.ipynb
    python/llama_index.ipynb
    python/pandas.ipynb
    python/comparison.md

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: 💬 Contribute
    
    dev-setup
    docker-setup
    Discord <https://discord.gg/7eJP4fcyNT>
    GitHub Issues <https://github.com/eth-sri/lmql/issues>
    E-Mail <mailto:hello@lmql.ai>
