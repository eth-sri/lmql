# Pandas

<div class="subtitle">Process LMQL results as Pandas DataFrames.</div>

When used from within Python, LMQL queries can be treated as simple python functions. This means building pipelines with LMQL is as easy as chaining together functions. However, next to easy integration, LMQL queries also offer a guaranteed output format when it comes to the data types and structure of the returned values. This makes it easy to process the output of LMQL queries in a structured way, e.g. with tabular/array-based data processing libraries such as Pandas.

## Tabular Data Generation

For example, to produce tabular data with LMQL, the following code snippet processes the output of an LMQL query with [pandas](https://pandas.pydata.org):

```lmql
import lmql
import pandas as pd

@lmql.query
async def generate_dogs(n):
    '''lmql
    sample(temperature=1.0, n=n)
    
    """Generate a dog with the following characteristics:
    Name:[NAME]
    Age: [AGE]
    Breed:[BREED]
    Quirky Move:[MOVE]
    """ where STOPS_BEFORE(NAME, "\n") and STOPS_BEFORE(BREED, "\n") and \
              STOPS_BEFORE(MOVE, "\n") and INT(AGE) and len(TOKENS(AGE)) < 3
    '''

result = await generate_dogs(8)
df = pd.DataFrame([r.variables for r in result])
df
```
```result
     NAME  AGE                BREED  \
0   Storm    2     Golden Retriever   
1            2     Golden Retriever   
2   Lucky    3     Golden Retriever   
3   Rocky    4   Labrador Retriever   
4     Rex   11     Golden Retriever   
5   Murky    5       Cocker Spaniel   
6   Gizmo    5               Poodle   
7   Bubba    3              Bulldog   

                                              MOVE  
0   Spinning in circles while chasing its own tail  
1             Wiggles its entire body when excited  
2                       Wiggles butt while walking  
3                         Loves to chase squirrels  
4                            Barks at anything red  
5                                      Wiggle butt  
6                              Spinning in circles  
7                                                   
```
Note how we sample multiple sequences (i.e. dog instances) using the `sample(temperature=1.0, n=n)` decoder statement. 

The returned `result` is a list of [`lmql.LMQLResult`](../python.ipynb)), which we can easily convert to a `pandas.DataFrame` by accessing `r.variables` on each item.

In the query, we use [scripted prompting](../../language/scripted-prompting.md) and [constraints](../../language/constraints.md) to make sure the generated dog samples are valid and each provides the attributes name, age, breed, and move.

## Data Processing

Converting the resulting values for LMQL template variables `NAME`, `AGE`, `BREED`, and `MOVE` to a `pandas.DataFrame`, makes it easy to apply
further processing and work with the generated data. 

For instance, we can easily determine the average age of the generated dogs:

```lmql
# determine average age
df["AGE"].mean()
```
```result
6.0
```
Note how the `INT(AGE)` constraints automatically converted the `AGE` values to integers, which makes the generated `AGE` values automatically amendable to arithmetic operations such as `mean()`.

Based on this tabular representation, it is now also easy to filter and aggregate the data. For instance, we can easily determine the average age of the generated dogs per breed:

```lmql
# group df by BREED and compute the average age for each breed
df.groupby("BREED")["AGE"].mean()
```
```result
BREED
 Corgi                  5.00
 Golden Retriever      14.75
 Labrador Retriever     5.00
 Poodle                 2.00
Name: AGE, dtype: float64
```
