# Overview

LMQL is a Python-based programming language for LLM programming with declarative elements. As a simple example consider the following program, demonstrating the basic syntax of LMQL:

```{lmql}

name::overview-query

# review to be analyzed
review = """We had a great stay. Hiking in the mountains 
            was fabulous and the food is really good."""

# use prompt statements to pass information to the model
"Review: {review}"
"Q: What is the underlying sentiment of this review and why?"
# template variables like [ANALYSIS] are used to generate text
"A:[ANALYSIS]" where not "\n" in ANALYSIS

# use constrained variable to produce a classification
"Based on this, the overall sentiment of the message\
 can be considered to be[CLS]" where CLS in [" positive", " neutral", " negative"]

CLS # positive

model-output::
Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.⏎
Q: What is the underlying sentiment of this review and why?⏎
A: [ANALYSIS The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.]⏎
Based on this, the overall sentiment of the message can be considered to be [CLS positive]
```

In this program, we program an LLM to perform sentiment analysis on a provided user review. We first ask the model to provide some basic analysis, and then we ask it to classify the overall sentiment as one of `positive`, `neutral`, or `negative`. The model is able to correctly identify the sentiment of the review as `positive`.

To implement this workflow, we use two template variables `[ANALYSIS]` and `[CLS]`, both of which are constrained using designated `where` expressions. 

For `ANALYSIS` we constrain the model to not output any newlines, which prevents it from outputting multiple lines that could potentially break the program. For `CLS` we constrain the model to output one of the three possible values. Using these constraints allows us to decode a fitting answer from the model, where both the analysis and the classification are well-formed and in an expected format.

Without constraints, the prompt above could produce different final classifications, such as `good` or `bad`. To handle this in an automated way, one would have to employ ad-hoc parsing to CLS result to obtain a clear result. Using LMQL's constraints, however, we can simply restrict the model to only output one of the desired values, thereby enabling robust and reliable integration. To learn more about the different types of constraints available in LMQL, see [Constraints](./constraints.md).

### Extracting More Information With Distributions

While the query above allows us to extract the sentiment of a review, we do not get any certainty information on the model's confidence in its classification. To obtain this information, we can additionally employ LMQL's `distribution` clause, to obtain the full distribution over the possible values for `CLASSIFICATION`:

```{lmql}

name::sentiment-distribution
argmax
    # review to be analyzed
    review = """We had a great stay. Hiking in the mountains was fabulous and the food is really good."""

    # use prompt statements to pass information to the model
    "Review: {review}"
    "Q: What is the underlying sentiment of this review and why?"
    # template variables like [ANALYSIS] are used to generate text
    "A:[ANALYSIS]" where not "\n" in ANALYSIS

    # use constrained variable to produce a classification
    "Based on this, the overall sentiment of the message can be considered to be[CLS]"
distribution
   CLS in [" positive", " neutral", " negative"]

model-output::
Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.⏎
Q: What is the underlying sentiment of this review and why?⏎
A: [ANALYSIS The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.]⏎
Based on this, the overall sentiment of the message can be considered to be [CLS]

P(CLS)
 -  positive (*) 0.9999244826658527
 -  neutral      7.513155848720942e-05
 -  negative     3.8577566019560874e-07
```

**Distribution Clause**

Instead of constraining `CLS` with a `where` expression, we now constrain it in the separate `distribution` clause. In LMQL, the `distribution` clause can be used to specify whether we want to additionally obtain the distribution over the possible values for a given variable. In this case, we want to obtain the distribution over the possible values for `CLS`. 

> **Extended Syntax**: Note, that to use the `distribution` clause, we have to make our choice of decoding algorithm explicit, by specifying `argmax` at the beginning of our code (see [Decoding Algorithms](./decoding.md) for more information). ¸
>
> In general, this extended form of LMQL syntax, i.e. indenting your program and explicitly specifying e.g. `argmax` at the beginning of your code, is optional, but recommended if you want to use the `distribution` clause. Throughout the documentation we will make use of both syntax variants.

In addition to using the model to perform the `ANALYSIS`, LMQL now also scores each of the individually provided values for `CLS` and normalizes the resulting sequence scores into a probability distribution `P(CLS)` (printed to the Terminal Output of the Playground or Standard Output of the CLI).

Here, we can see that the model is indeed quite confident in its classification of the review as `positive`, with an overwhelming probability of `99.9%`.

> Note that currently distribution variables like `CLS` can only occur at the end of your program.

### Dynamically Reacting To Model Output

Another way to improve on our initial query, is to implement a more dynamic prompt, where we can react to the model's output. For example, we could ask the model to provide a more detailed analysis of the review, depending on the model's classification:

```{lmql}

name::dynamic-analysis
argmax
   review = """We had a great stay. Hiking in the mountains 
               was fabulous and the food is really good."""
   """Review: {review}
   Q: What is the underlying sentiment of this review and why?
   A:[ANALYSIS]""" where not "\n" in ANALYSIS
   
   "Based on this, the overall sentiment of the message can be considered to be[CLS]" where CLS in [" positive", " neutral", " negative"]
   
   if CLS == " positive":
      "What is it that they liked about their stay? [FURTHER_ANALYSIS]"
   elif CLS == " neutral":
      "What is it that could have been improved? [FURTHER_ANALYSIS]"
   elif CLS == " negative":
      "What is it that they did not like about their stay? [FURTHER_ANALYSIS]"
where
   STOPS_AT(FURTHER_ANALYSIS, ".")

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

As shown here, in addition to inline `where` expressions as seen earlier, you can also provide a global `where` expression at the end of your program, e.g. to specify constraints that should apply for all variables. Depending on your use case, this can be a convenient way to avoid having to repeat the same constraints multiple times, like for `FURTHER_ANALYSIS` in this example.