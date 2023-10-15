import{_ as s,o as a,c as e,Q as n}from"./chunks/framework.980cae92.js";const g=JSON.parse('{"title":"Pandas","description":"","frontmatter":{},"headers":[],"relativePath":"docs/latest/lib/integrations/pandas.md","filePath":"docs/latest/lib/integrations/pandas.md"}'),t={name:"docs/latest/lib/integrations/pandas.md"},l=n(`<h1 id="pandas" tabindex="-1">Pandas <a class="header-anchor" href="#pandas" aria-label="Permalink to &quot;Pandas&quot;">​</a></h1><div class="subtitle">Process LMQL results as Pandas DataFrames.</div><p>When used from within Python, LMQL queries can be treated as simple python functions. This means building pipelines with LMQL is as easy as chaining together functions. However, next to easy integration, LMQL queries also offer a guaranteed output format when it comes to the data types and structure of the returned values. This makes it easy to process the output of LMQL queries in a structured way, e.g. with tabular/array-based data processing libraries such as Pandas.</p><h2 id="tabular-data-generation" tabindex="-1">Tabular Data Generation <a class="header-anchor" href="#tabular-data-generation" aria-label="Permalink to &quot;Tabular Data Generation&quot;">​</a></h2><p>For example, to produce tabular data with LMQL, the following code snippet processes the output of an LMQL query with <a href="https://pandas.pydata.org" target="_blank" rel="noreferrer">pandas</a>:</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">import</span> lmql
<span class="hljs-keyword">import</span> pandas <span class="hljs-keyword">as</span> pd

<span class="hljs-meta">@lmql.query</span>
<span class="hljs-keyword">async</span> <span class="hljs-keyword">def</span> <span class="hljs-title function_">generate_dogs</span>(<span class="hljs-params">n</span>):
    <span class="hljs-inline-lmql"><span class="inline-lmql-delim">&#39;&#39;&#39;lmql</span>
    <span class="hljs-keyword">sample</span>(temperature=1.0, n=n)
    
    <span class="hljs-string">&quot;&quot;&quot;Generate a dog with the following characteristics:
    Name:<span class="hljs-placeholder">[NAME]</span>
    Age: <span class="hljs-placeholder">[AGE]</span>
    Breed:<span class="hljs-placeholder">[BREED]</span>
    Quirky Move:<span class="hljs-placeholder">[MOVE]</span>
    &quot;&quot;&quot;</span> <span class="hljs-keyword">where</span> STOPS_BEFORE(NAME, <span class="hljs-string">&quot;\\n&quot;</span>) <span class="hljs-keyword">and</span> STOPS_BEFORE(BREED, <span class="hljs-string">&quot;\\n&quot;</span>) <span class="hljs-keyword">and</span> \\
              STOPS_BEFORE(MOVE, <span class="hljs-string">&quot;\\n&quot;</span>) <span class="hljs-keyword">and</span> INT(AGE) <span class="hljs-keyword">and</span> <span class="hljs-built_in">len</span>(TOKENS(AGE)) &lt; 3
    <span class="inline-lmql-delim">&#39;&#39;&#39;</span></span>

result = <span class="hljs-keyword">await</span> generate_dogs(<span class="hljs-number">8</span>)
df = pd.DataFrame([r.variables <span class="hljs-keyword">for</span> r <span class="hljs-keyword">in</span> result])
df
</span></code></pre></div><div class="language-result vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">result</span><pre class="hljs"><code><span class="line">     NAME  AGE                BREED  \\
<span class="hljs-number">0</span>   Storm    <span class="hljs-number">2</span>     Golden Retriever   
<span class="hljs-number">1</span>            <span class="hljs-number">2</span>     Golden Retriever   
<span class="hljs-number">2</span>   Lucky    <span class="hljs-number">3</span>     Golden Retriever   
<span class="hljs-number">3</span>   Rocky    <span class="hljs-number">4</span>   Labrador Retriever   
<span class="hljs-number">4</span>     Rex   <span class="hljs-number">11</span>     Golden Retriever   
<span class="hljs-number">5</span>   Murky    <span class="hljs-number">5</span>       Cocker Spaniel   
<span class="hljs-number">6</span>   Gizmo    <span class="hljs-number">5</span>               Poodle   
<span class="hljs-number">7</span>   Bubba    <span class="hljs-number">3</span>              Bulldog   

                                              MOVE  
<span class="hljs-number">0</span>   Spinning <span class="hljs-keyword">in</span> circles <span class="hljs-keyword">while</span> chasing its own tail  
<span class="hljs-number">1</span>             Wiggles its entire body when excited  
<span class="hljs-number">2</span>                       Wiggles butt <span class="hljs-keyword">while</span> walking  
<span class="hljs-number">3</span>                         Loves to chase squirrels  
<span class="hljs-number">4</span>                            Barks at anything red  
<span class="hljs-number">5</span>                                      Wiggle butt  
<span class="hljs-number">6</span>                              Spinning <span class="hljs-keyword">in</span> circles  
<span class="hljs-number">7</span>                                                   
</span></code></pre></div><p>Note how we sample multiple sequences (i.e. dog instances) using the <code>sample(temperature=1.0, n=n)</code> decoder statement.</p><p>The returned <code>result</code> is a list of <a href="../python.ipynb"><code>lmql.LMQLResult</code></a>), which we can easily convert to a <code>pandas.DataFrame</code> by accessing <code>r.variables</code> on each item.</p><p>In the query, we use <a href="./../../language/scripted-prompting.html">scripted prompting</a> and <a href="./../../language/constraints.html">constraints</a> to make sure the generated dog samples are valid and each provides the attributes name, age, breed, and move.</p><h2 id="data-processing" tabindex="-1">Data Processing <a class="header-anchor" href="#data-processing" aria-label="Permalink to &quot;Data Processing&quot;">​</a></h2><p>Converting the resulting values for LMQL template variables <code>NAME</code>, <code>AGE</code>, <code>BREED</code>, and <code>MOVE</code> to a <code>pandas.DataFrame</code>, makes it easy to apply further processing and work with the generated data.</p><p>For instance, we can easily determine the average age of the generated dogs:</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># determine average age</span>
df[<span class="hljs-string">&quot;AGE&quot;</span>].mean()
</span></code></pre></div><div class="language-result vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">result</span><pre class="hljs"><code><span class="line">6.0
</span></code></pre></div><p>Note how the <code>INT(AGE)</code> constraints automatically converted the <code>AGE</code> values to integers, which makes the generated <code>AGE</code> values automatically amendable to arithmetic operations such as <code>mean()</code>.</p><p>Based on this tabular representation, it is now also easy to filter and aggregate the data. For instance, we can easily determine the average age of the generated dogs per breed:</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># group df by BREED and compute the average age for each breed</span>
df.groupby(<span class="hljs-string">&quot;BREED&quot;</span>)[<span class="hljs-string">&quot;AGE&quot;</span>].mean()
</span></code></pre></div><div class="language-result vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">result</span><pre class="hljs"><code><span class="line">BREED
 Corgi                  5.00
 Golden Retriever      14.75
 Labrador Retriever     5.00
 Poodle                 2.00
Name: AGE, dtype: float64
</span></code></pre></div>`,19),p=[l];function r(o,c,i,d,h,u){return a(),e("div",null,p)}const b=s(t,[["render",r]]);export{g as __pageData,b as default};
