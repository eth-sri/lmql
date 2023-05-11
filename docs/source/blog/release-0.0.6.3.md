metadata:release: 2023-05-11 18:00:00 +0000
metadata:authors: team

# LMQL v0.0.6.3

Today, we are releasing LMQL v0.0.6.3. This update contains several bug fixes and improvements. The most notable changes are:

* **Lighter Runtime** As part of our continued efforts, we made LMQL much lighter (no more mandatory `transformers` dependency). By default LMQL now no longer requires `transformers` or PyTorch. If you rely on local models, just install LMQL via `pip install lmql[hf]` to get full Transformers integration.

* **Token Constraints** A new function `TOKENS(...)` was added to the LMQL constraint language, allowing you to specify lower and upper bounds or the exact number of tokens to generate for a given variable.
    
    ```{lmql}
    name::token_constraints
    argmax 
        "A 10 token response[WHO]" 
    from 
        "openai/text-ada-001" 
    where 
        len(TOKENS(WHO)) == 10
    ```

* **Conditional Stopping** `STOPS_AT` can now be combined with additional side conditions. This allows you to specify stopping phrases that are only enforced, once other conditions are met. 

    For example, below, we stop when the generated text hits a newline character, but only if the overall variable output is already at least 10 tokens long.

    ```{lmql}
    name::conditional_stopping 
    argmax 
        "Hello[WHO]" 
    from 
        "openai/text-ada-001" 
    where 
        len(TOKENS(WHO)) > 10 and STOPS_AT(WHO, "\n")
    ```

* **lmql.run**: Improved input validation for `lmql.run` as contributed by <a href="https://twitter.com/lfegray" target="_blank">@lfegray</a>. More specifically, `lmql.run` wil now provide more helpful error messages when client logic does not specify input values for all required query parameters.

* **Automatic Cache Invalidation**: LMQL's tokenizer cache at `~/.cache/lmql` is now invalidated automatically when upgrading to a new version. This should prevent issues with outdated cache files.

> Note: Version 0.0.6.2 was skipped and yanked from pypi.org, as an invalid release was pushed accidentally.