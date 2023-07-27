💬 Welcome to LMQL
===================================

**LMQL** (Language Model Query Language) is a programming language for large language model (LM) interaction. 
It facilitates LLM interaction by combining the benefits of natural language prompting with the expressiveness 
of Python. It has a focus on multi-part prompting and enables novel forms of LM interaction via `scripting <language/scripted_prompts.md>`_, `constraint-guided decoding <language/constraints.md>`_, `tool augmentation <language/functions.md>`_, and efficiency.

LMQL is a research project by the `Secure,  Reliable, and Intelligent Systems Lab <https://www.sri.inf.ethz.ch/>`_ at ETH Zürich.

Quick Start
-----------

To get started with LMQL, check out the :doc:`quickstart` guide.


We also provide the following resources to get started with LMQL:


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

.. toctree::
  :maxdepth: 1

  quickstart
  installation

.. toctree::
   :maxdepth: 2
   :caption: 📖 LMQL Language 
   
   language/overview.md
   language/scripted_prompts.md
   language/constraints.md
   language/decoders.md
   language/models.rst
   language/functions.md

.. toctree::
    :maxdepth: 1
    :caption: 🔗 Python Integration
    
    python/python.ipynb
    python/langchain.ipynb
    python/llama_index.ipynb
    python/pandas.ipynb
    python/output.md
    python/comparison.md
   
.. toctree::
    :maxdepth: 1
    :caption: 💬 Contribute
    
    dev-setup
    docker-setup
    Discord <https://discord.gg/7eJP4fcyNT>
    GitHub Issues <https://github.com/eth-sri/lmql/issues>
    E-Mail <mailto:hello@lmql.ai>
