# Overview

LMQL is a declarative, SQL-like programming language for language model interaction. As an example consider the following query, demonstrating the basic syntax of LMQL:

```{lmql}

name::overview-query
argmax
   """Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.
   Q: What is the underlying sentiment of this review and why?
   A:[ANALYSIS]
   Based on this, the overall sentiment of the message can be considered to be[CLASSIFICATION]"""
from
   "openai/text-davinci-003"
where
   not "\n" in ANALYSIS and CLASSIFICATION in [" positive", " neutral", " negative"]

model-output::
Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.⏎
Q: What is the underlying sentiment of this review and why?⏎
A: [ANALYSIS The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.]⏎
Based on this, the overall sentiment of the message can be considered to be [CLASSIFICATION positive]
```

In this program, we use the language model `openai/text-davinci-003` (GPT-3.5) to perform a sentiment analysis on a provided user review. We first ask the model to provide some basic analysis of the review, and then we ask the model to classify the overall sentiment as one of `positive`, `neutral`, or `negative`. The model is able to correctly identify the sentiment of the review as `positive`.

Overall, the query consists of four main clauses:

1. **Decoder Clause** First, we specify the decoding algorithm to use for text generation. In this case we use `argmax` decoding, however, LMQL also support branching decoding algorithms like beam search. See [Decoders](./decoders.md) to learn more about this.

2. **Prompt Clause**

   ```python
   """Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.
   Q: What is the underlying sentiment of this review and why?
   A:[ANALYSIS]
   Based on this, the overall sentiment of the message can be considered to be[CLASSIFICATION]"""
   ```

   In this part of the program, you specify your prompt. Here, we include the user review, as well as the two questions we want to ask the model. Template variables like `[ANALYSIS]` are automatically completed by the model. Apart from simple textual prompts, LMQL also support multi-part and scripted prompts. To learn more, see [Scripted Prompting](./scripted_prompts.md).

3. **Model Clause**

    ```python
    from "openai/text-davinci-003"
    ```

    Next, we specify what model we want to use for text generation. In this case, we use the language model `openai/text-davinci-003`. To learn more about the different models available in LMQL, see [Models](./models.md).

4. **Constraint Clause**

    ```python
    not "\n" in ANALYSIS and CLASSIFICATION in [" positive", " neutral", " negative"]
    ```

    In this part of the query, users can specify logical, high-level constraints on the generated text.<br>
    
    Here, we specify two constraints: For `ANALYSIS` we constrain the model to not output any newlines, which prevents the model from outputting multiple lines, which could potentially breaking the prompt. For `CLASSIFICATION` we constrain the model to output one of the three possible values. Using these constraints allows us to decode a fitting answer from the model, where both the analysis and the classification are well-formed and in an expected format.

   Without constraints, the prompt above could produce different final classifications, such as `good`, `bad`, or `neutral`. To handle this in an automated way, one would again have to employ some model of language understanding to parse the model's CLASSIFICATION result.

   To learn more about the different types of constraints available in LMQL, see [Constraints](./constraints.md).

### Extracting More Information With Distributions

While the query above allows us to extract the sentiment of a review, we do not get any certainty information on the model's confidence in its classification. To obtain this information, we can additionally employ LMQL's `distribution` clause, to obtain the full distribution over the possible values for `CLASSIFICATION`:

```{lmql}

name::sentiment-distribution
argmax
   """Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.
   Q: What is the underlying sentiment of this review and why?
   A:[ANALYSIS]
   Based on this, the overall sentiment of the message can be considered to be[CLASSIFICATION]"""
from
   "openai/text-davinci-003"
where
   not "\n" in ANALYSIS
distribution
   CLASSIFICATION in [" positive", " neutral", " negative"]

model-output::
Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.⏎
Q: What is the underlying sentiment of this review and why?⏎
A: [ANALYSIS The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.]⏎
Based on this, the overall sentiment of the message can be considered to be [CLASSIFICATION]

P(CLASSIFICATION)
 -  positive (*) 0.9999244826658527
 -  neutral      7.513155848720942e-05
 -  negative     3.8577566019560874e-07
```

**Distribution Clause**

Instead of constraining `CLASSIFICATION` as part of the `where` clause, we now constrain in the `distribution` clause. In LMQL, the `distribution` clause is used to specify whether we want to additionally obtain the distribution over the possible values for a given variable. In this case, we want to obtain the distribution over the possible values for `CLASSIFICATION`.

In addition to using the model to perform the `ANALYSIS`, LMQL now also scores each of the individually provided values for `CLASSIFICATION` and normalizes the resulting sequence scores into a probability distribution `P(CLASSIFICATION)` (printed to the Terminal Output of the Playground or Standard Output of the CLI).

Here, we can see that the model is indeed quite confident in its classification of the review as `positive`, with an overwhelming probability of `99.9%`.

> Note that currently distribution variables like `CLASSIFICATION` can only occur at the end of a prompt.

### Dynamically Reacting To Model Output

Another way to improve on our initial query, is to implement a more dynamic prompt, where we can react to the model's output. For example, we could ask the model to provide a more detailed analysis of the review, depending on the model's classification:

```{lmql}

name::dynamic-analysis
argmax
   """Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.
   Q: What is the underlying sentiment of this review and why?
   A:[ANALYSIS]
   Based on this, the overall sentiment of the message can be considered to be[CLASSIFICATION]"""
   if CLASSIFICATION == " positive":
      "What is it that they liked about their stay? [FURTHER_ANALYSIS]"
   elif CLASSIFICATION == " neutral":
      "What is it that could have been improved? [FURTHER_ANALYSIS]"
   elif CLASSIFICATION == " negative":
      "What is it that they did not like about their stay? [FURTHER_ANALYSIS]"
from
    "openai/text-davinci-003"
where
    not "\n" in ANALYSIS and CLASSIFICATION in [" positive", " neutral", " negative"] and STOPS_AT(FURTHER_ANALYSIS, ".")

model-output::
Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.⏎
Q: What is the underlying sentiment of this review and why?⏎
A: [ANALYSIS The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.]⏎
Based on this, the overall sentiment of the message can be considered to be [CLASSIFICATION positive]⏎
What is it that they liked about their stay?⏎
⏎
[FURTHER_ANALYSIS The reviewer liked the hiking in the mountains and the food.]
```

As shown here, we can use the `if` statement to dynamically react to the model's output. In this case, we ask the model to provide a more detailed analysis of the review, depending on the overall positive, neutral, or negative sentiment of the review. All intermediate variables like `ANALYSIS`, `CLASSIFICATION` or `FURTHER_ANALYSIS` can be considered the output of query, and may be processed by an surrounding automated system.

To learn more about the capabilities of such control-flow-guided prompts, see [Scripted Prompting](./scripted_prompts.md).
