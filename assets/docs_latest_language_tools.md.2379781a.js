import{_ as e,o as t,c as o,Q as n,k as s,a}from"./chunks/framework.980cae92.js";const k=JSON.parse('{"title":"Tool Augmentation","description":"","frontmatter":{},"headers":[],"relativePath":"docs/latest/language/tools.md","filePath":"docs/latest/language/tools.md"}'),l={name:"docs/latest/language/tools.md"},p=n(`<h1 id="tool-augmentation" tabindex="-1">Tool Augmentation <a class="header-anchor" href="#tool-augmentation" aria-label="Permalink to &quot;Tool Augmentation&quot;">​</a></h1><div class="subtitle">Augment LLM reasoning with Python tool integration</div><p>LMQL is a superset of Python and thus query programs can incorporate arbitrary Python constructs including function calls. For instance, below, we ask the model for a simple math problem and then use Python&#39;s <code>eval</code> function to evaluate the solution.</p><div class="language- vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang"></span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># generates an arithmetic expression</span>
<span class="hljs-string">&quot;A simple math problem for addition (without solution, \\
    without words): <span class="hljs-placeholder">[MATH]</span>&quot;</span> <span class="hljs-keyword">where</span> STOPS_BEFORE(MATH, <span class="hljs-string">&quot;=&quot;</span>)

<span class="hljs-comment"># evaluate the expression and feed it back into the prompt</span>
<span class="hljs-string">&quot;= <span class="hljs-subst">{<span class="hljs-built_in">eval</span>(MATH.strip())}</span>&quot;</span>
</span></code></pre></div>`,4),r=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`A simple math problem for addition (without solution, without words):
[MATH| 7 + 8 =] 15
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1516",text:"A","pd-insertion-point":"true"},[a(`A simple math problem for addition (without solution, without words):
`),s("span",{"pd-shadow-id":"1518","pd-instant":"false",text:"",class:"promptdown-var color-red"},[s("span",{"pd-shadow-id":"1519",text:"M",class:"promptdown-var-name"},"MATH"),a(" 7 + 8 =")]),a(` 15
`)])])],-1),i=n(`<p>Here, similar to a python <a href="https://peps.python.org/pep-0498" target="_blank" rel="noreferrer">f-string</a>, we use the <code>{...}</code> syntax to re-insert the result of the <code>eval</code> function into the prompt. This allows us to augment the reasoning capabilities of the large language model with a simple calculator.</p><div class="warning custom-block"><p class="custom-block-title">WARNING</p><p>While <code>eval</code> is handy for the examples in this section and allows to perform simple math, generally it can pose a security risk and should not be used in production.</p></div><h2 id="calculator" tabindex="-1">Calculator <a class="header-anchor" href="#calculator" aria-label="Permalink to &quot;Calculator&quot;">​</a></h2><p>Building on the previous example, we can now create an improved calculator that can handle more complex expressions:</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">import</span> re
<span class="hljs-keyword">from</span> lmql.demo <span class="hljs-keyword">import</span> gsm8k_samples

<span class="hljs-keyword">def</span> <span class="hljs-title function_">calc</span>(<span class="hljs-params">expr</span>):
      expr = re.sub(r<span class="hljs-string">&quot;<span class="hljs-placeholder">[^<span class="hljs-number">0</span>-<span class="hljs-number">9</span>+\\-*/().]</span>&quot;</span>, <span class="hljs-string">&quot;&quot;</span>, expr)
      <span class="hljs-keyword">return</span> <span class="hljs-built_in">eval</span>(expr)

QUESTION = <span class="hljs-string">&quot;Josh decides to try flipping a house. \\
He buys a house for $80,000 and then puts in $50,000 in repairs. \\
This increased the value of the house by 150%. \\
How much profit did he make?&quot;</span>

<span class="hljs-comment"># insert few shot demonstrations</span>
<span class="hljs-string">&quot;<span class="hljs-subst">{gsm8k_samples()}</span>&quot;</span>

<span class="hljs-comment"># prompt template</span>
<span class="hljs-string">&quot;Q: <span class="hljs-subst">{QUESTION}</span>\\n&quot;</span>
<span class="hljs-string">&quot;Let&#39;s think step by step.\\n&quot;</span>

<span class="hljs-comment"># reasoning loop</span>
<span class="hljs-keyword">for</span> i <span class="hljs-keyword">in</span> <span class="hljs-built_in">range</span>(<span class="hljs-number">4</span>):
    <span class="hljs-string">&quot;<span class="hljs-placeholder">[REASON_OR_CALC]</span>&quot;</span> \\
        <span class="hljs-keyword">where</span> STOPS_AT(REASON_OR_CALC, <span class="hljs-string">&quot;&lt;&lt;&quot;</span>) <span class="hljs-keyword">and</span> \\
              STOPS_AT(REASON_OR_CALC, <span class="hljs-string">&quot;So the answer&quot;</span>)
    
    <span class="hljs-keyword">if</span> REASON_OR_CALC.endswith(<span class="hljs-string">&quot;&lt;&lt;&quot;</span>):
        <span class="hljs-string">&quot; <span class="hljs-placeholder">[EXPR]</span>&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(EXPR, <span class="hljs-string">&quot;=&quot;</span>)
        <span class="hljs-comment"># invoke calculator function</span>
        <span class="hljs-string">&quot; <span class="hljs-subst">{calc(EXPR)}</span>&gt;&gt;&quot;</span>
    <span class="hljs-keyword">elif</span> REASON_OR_CALC.endswith(<span class="hljs-string">&quot;So the answer&quot;</span>):
        <span class="hljs-keyword">break</span>

<span class="hljs-comment"># produce the final answer</span>
<span class="hljs-string">&quot;is<span class="hljs-placeholder">[RESULT]</span>&quot;</span>
</span></code></pre></div>`,5),c=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`Q: Josh decides to try flipping a house.  He buys a house for $80,000 and then puts in $50,000 in repairs.  This increased the value of the house by 150%.  How much profit did he make?

Let's think step by step.
[REASON_OR_CALC|Josh bought the house for $80,000 and put in $50,000 in repairs.
The value of the house increased by 150%, so the new value of the house is $80,000 + 150% of $80,000 = <<] [EXPR|80,000 + (80,000*1.5) =] 200000.0>> 
[REASON_OR_CALC|The profit Josh made is the difference between the new value of the house and the amount he spent on it, which is $200,000 - $80,000 - $50,000 = <<] [EXPR|200,000 - 80,000 - 50,000 =] 70000>> [REASON_OR_CALC| $70,000.
So the answer] is [RESULT|$70,000.]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1525",text:"Q","pd-insertion-point":"true"},[a(`Q: Josh decides to try flipping a house.  He buys a house for $80,000 and then puts in $50,000 in repairs.  This increased the value of the house by 150%.  How much profit did he make?

Let's think step by step.
`),s("span",{"pd-shadow-id":"1527","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1528",text:"R",class:"promptdown-var-name"},"REASON_OR_CALC"),a(`Josh bought the house for $80,000 and put in $50,000 in repairs.
The value of the house increased by 150%, so the new value of the house is $80,000 + 150% of $80,000 = <<`)]),a(),s("span",{"pd-shadow-id":"1533","pd-instant":"false",text:"",class:"promptdown-var color-yellow"},[s("span",{"pd-shadow-id":"1534",text:"E",class:"promptdown-var-name"},"EXPR"),a("80,000 + (80,000*1.5) =")]),a(` 200000.0>> 
`),s("span",{"pd-shadow-id":"1539","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1540",text:"R",class:"promptdown-var-name"},"REASON_OR_CALC"),a("The profit Josh made is the difference between the new value of the house and the amount he spent on it, which is $200,000 - $80,000 - $50,000 = <<")]),a(),s("span",{"pd-shadow-id":"1545","pd-instant":"false",text:"",class:"promptdown-var color-yellow"},[s("span",{"pd-shadow-id":"1546",text:"E",class:"promptdown-var-name"},"EXPR"),a("200,000 - 80,000 - 50,000 =")]),a(" 70000>> "),s("span",{"pd-shadow-id":"1551","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1552",text:"R",class:"promptdown-var-name"},"REASON_OR_CALC"),a(` $70,000.
So the answer`)]),a(" is "),s("span",{"pd-shadow-id":"1557","pd-instant":"false",text:"",class:"promptdown-var color-orange"},[s("span",{"pd-shadow-id":"1558",text:"R",class:"promptdown-var-name"},"RESULT"),a("$70,000.")]),a(`
`)])])],-1),d=n(`<p>Here, we define a function <code>calc</code> that leverages the build-in <code>re</code> library for regular expressions, to strip the input of any non-numeric characters before calling <code>eval</code>.</p><p>Further, we use a function <code>gsm8k_samples</code> that returns a few-shot samples for the <code>gsm8k</code> dataset, priming the model on the correct form of tool use.</p><h2 id="beyond-calculators" tabindex="-1">Beyond Calculators <a class="header-anchor" href="#beyond-calculators" aria-label="Permalink to &quot;Beyond Calculators&quot;">​</a></h2><p><strong>Wikipedia Search</strong> Function use is not limited to calculators. In the example below we show how text retrieval, using Python&#39;s <a href="https://docs.python.org/3/library/asyncio.html" target="_blank" rel="noreferrer"><code>async</code>/<code>await</code> syntax</a>, can be used to augment the reasoning capabilities of the large language model.</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">async</span> <span class="hljs-keyword">def</span> <span class="hljs-title function_">wikipedia</span>(<span class="hljs-params">q</span>):
   <span class="hljs-keyword">from</span> lmql.http <span class="hljs-keyword">import</span> fetch
   <span class="hljs-keyword">try</span>:
      q = q.strip(<span class="hljs-string">&quot;\\n &#39;.&quot;</span>)
      pages = <span class="hljs-keyword">await</span> fetch(f<span class="hljs-string">&quot;https://en.wikipedia.org/w/api.php?format=json&amp;action=query&amp;prop=extracts&amp;exintro&amp;explaintext&amp;redirects=1&amp;titles=<span class="hljs-subst">{q}</span>&amp;origin=*&quot;</span>, <span class="hljs-string">&quot;query.pages&quot;</span>)
      <span class="hljs-keyword">return</span> <span class="hljs-built_in">list</span>(pages.values())[<span class="hljs-number">0</span>][<span class="hljs-string">&quot;extract&quot;</span>][:<span class="hljs-number">280</span>]
   <span class="hljs-keyword">except</span>:
      <span class="hljs-keyword">return</span> <span class="hljs-string">&quot;No results&quot;</span>

<span class="hljs-comment"># ask a question</span>
<span class="hljs-string">&quot;Q: From which countries did the Norse originate?\\n&quot;</span>

<span class="hljs-comment"># prepare wikipedia call</span>
<span class="hljs-string">&quot;Action: Let&#39;s search Wikipedia for the term &#39;<span class="hljs-placeholder">[TERM]</span>\\n&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(TERM, <span class="hljs-string">&quot;&#39;&quot;</span>)
result = <span class="hljs-keyword">await</span> wikipedia(TERM)

<span class="hljs-comment"># feed back result</span>
<span class="hljs-string">&quot;Result: <span class="hljs-subst">{result}</span>\\n&quot;</span>

<span class="hljs-comment"># generate final response</span>
<span class="hljs-string">&quot;Final Answer:<span class="hljs-placeholder">[ANSWER]</span>&quot;</span>
</span></code></pre></div>`,5),h=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`Q: From which countries did the Norse originate?
Action: Let's search Wikipedia for the term '[TERM| Norse]'.
Result: Norse is a demonym for Norsemen, a Medieval North Germanic ethnolinguistic group ancestral to modern Scandinavians, defined as speakers of Old Norse from about the 9th to the 13th centuries.
Norse may also refer to:

Final Answer: [ANSWER|The Norse originated from North Germanic countries, including Denmark, Norway, Sweden, and Iceland.]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1564",text:"Q","pd-insertion-point":"true"},[a(`Q: From which countries did the Norse originate?
Action: Let's search Wikipedia for the term '`),s("span",{"pd-shadow-id":"1566","pd-instant":"false",text:"",class:"promptdown-var color-blue"},[s("span",{"pd-shadow-id":"1567",text:"T",class:"promptdown-var-name"},"TERM"),a(" Norse")]),a(`'.
Result: Norse is a demonym for Norsemen, a Medieval North Germanic ethnolinguistic group ancestral to modern Scandinavians, defined as speakers of Old Norse from about the 9th to the 13th centuries.
Norse may also refer to:

Final Answer: `),s("span",{"pd-shadow-id":"1572","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1573",text:"A",class:"promptdown-var-name"},"ANSWER"),a("The Norse originated from North Germanic countries, including Denmark, Norway, Sweden, and Iceland.")]),a(`
`)])])],-1),u=n(`<p><strong>Key-Value Store</strong> LMQL can also access the state of the surrounding python interpreter. To showcase this, we show how to use the <code>assign</code> and <code>get</code> functions to store and retrieve values in a simple key-value store.</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># implement a simple key value storage</span>
<span class="hljs-comment"># with two operations</span>
storage = {}
<span class="hljs-keyword">def</span> <span class="hljs-title function_">assign</span>(<span class="hljs-params">key, value</span>): 
    <span class="hljs-comment"># store a value</span>
    storage[key] = value; <span class="hljs-keyword">return</span> f<span class="hljs-string">&#39;<span>{{</span><span class="hljs-subst">{key}</span>: &quot;<span class="hljs-subst">{value}</span>&quot;}}&#39;</span>
<span class="hljs-keyword">def</span> <span class="hljs-title function_">get</span>(<span class="hljs-params">key</span>): 
    <span class="hljs-comment"># retrieve a value</span>
    <span class="hljs-keyword">return</span> storage.get(key)

<span class="hljs-comment"># instructive prompt, instructing the model to how use the storage</span>
<span class="hljs-string">&quot;&quot;&quot;In your reasoning you can use actions. You do this as follows:
\`action_name(&lt;args&gt;) # result: &lt;inserted result&gt;\`
To remember things, you can use &#39;assign&#39;/&#39;get&#39;:
- To remember something:
\`assign(&quot;Alice&quot;, &quot;banana&quot;) # result: &quot;banana&quot;\`
- To retrieve a stored value:
\`get(&quot;Alice&quot;) # result: &quot;banana&quot;\`
Always tail calls with &quot; # result&quot;. Using these actions, let&#39;s solve
the following question.\\n&quot;&quot;&quot;</span>

<span class="hljs-comment"># actual problem statement</span>
<span class="hljs-string">&quot;&quot;&quot;
Q: Alice, Bob, and Claire are playing a game. At the start 
of the game, they are each holding a ball: Alice has a black 
ball, Bob has a brown ball, and Claire has a blue ball. 

As the game progresses, pairs of players trade balls. First, 
Bob and Claire swap balls. Then, Alice and Bob swap balls. 
Finally, Claire and Bob swap balls. At the end of the game, 
what ball does Alice have?
A: Let&#39;s think step by step.
&quot;&quot;&quot;</span>

<span class="hljs-comment"># core reasoning loop</span>
<span class="hljs-keyword">for</span> i <span class="hljs-keyword">in</span> <span class="hljs-built_in">range</span>(<span class="hljs-number">32</span>):
    <span class="hljs-string">&quot;<span class="hljs-placeholder">[REASONING]</span>&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(REASONING, <span class="hljs-string">&quot;# result&quot;</span>) <span class="hljs-keyword">and</span> \\
                        STOPS_AT(REASONING, <span class="hljs-string">&quot;Therefore, &quot;</span>)
    
    <span class="hljs-keyword">if</span> REASONING.endswith(<span class="hljs-string">&quot;# result&quot;</span>):
        cmd = REASONING.rsplit(<span class="hljs-string">&quot;\`&quot;</span>,<span class="hljs-number">1</span>)[-<span class="hljs-number">1</span>]
        cmd = cmd[:-<span class="hljs-built_in">len</span>(<span class="hljs-string">&quot;# result&quot;</span>)]
        <span class="hljs-string">&quot;<span class="hljs-subst">{<span class="hljs-built_in">eval</span>(cmd)}</span>\`\\n&quot;</span>
    <span class="hljs-keyword">else</span>:
        <span class="hljs-keyword">break</span>

<span class="hljs-comment"># generate final answer</span>
<span class="hljs-string">&quot;Therefore at the end of the game, Alice has the<span class="hljs-placeholder">[OBJECT]</span>&quot;</span> \\
    <span class="hljs-keyword">where</span> STOPS_AT(OBJECT, <span class="hljs-string">&quot;.&quot;</span>) <span class="hljs-keyword">and</span> STOPS_AT(OBJECT, <span class="hljs-string">&quot;,&quot;</span>)
</span></code></pre></div>`,2),m=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`# Model Output
(...)
A: Let's think step by step

[REASONING()| At the start of the game:
\`assign('Alice', 'black') # result] {Alice: 'black'}
[REASONING()| \`assign('Bob', 'brown') # result] {Bob: 'brown'}
[REASONING()| \`assign('Claire', 'blue') # result] {Claire: 'blue'}

[REASONING()| After Bob and Claire swap balls:
\`assign('Bob', 'blue') # result] {Bob: 'blue'}
[REASONING()| \`assign('Claire', 'brown') # result] {Claire: 'brown'}

[REASONING()| After Alice and Bob swap balls:
\`assign('Alice', 'blue') # result] {Alice: 'blue'}
[REASONING()| \`assign('Bob', 'black') # result] {Bob: 'black'}

[REASONING()| After Claire and Bob swap balls:
\`assign('Claire', 'black') # result] {Claire: 'black'}
[REASONING()| \`assign('Bob', 'brown') # result] {Bob: 'brown'}

[REASONING()| At the end of the game, Alice has a blue ball:
\`get('Alice') # result] blue\`
Therefore at the end of the game, Alice has the [OBJECT| blue ball.]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("h1",{"pd-shadow-id":"1580",text:" "}," Model Output"),s("p",{"pd-shadow-id":"1582",text:"(","pd-insertion-point":"true"},[a(`(...)
A: Let's think step by step

`),s("span",{"pd-shadow-id":"1584","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1585",text:"R",class:"promptdown-var-name"},"REASONING"),a(" At the start of the game:\n`assign('Alice', 'black') # result")]),a(` {Alice: 'black'}
`),s("span",{"pd-shadow-id":"1590","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1591",text:"R",class:"promptdown-var-name"},"REASONING"),a(" `assign('Bob', 'brown') # result")]),a(` {Bob: 'brown'}
`),s("span",{"pd-shadow-id":"1596","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1597",text:"R",class:"promptdown-var-name"},"REASONING"),a(" `assign('Claire', 'blue') # result")]),a(` {Claire: 'blue'}

`),s("span",{"pd-shadow-id":"1602","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1603",text:"R",class:"promptdown-var-name"},"REASONING"),a(" After Bob and Claire swap balls:\n`assign('Bob', 'blue') # result")]),a(` {Bob: 'blue'}
`),s("span",{"pd-shadow-id":"1608","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1609",text:"R",class:"promptdown-var-name"},"REASONING"),a(" `assign('Claire', 'brown') # result")]),a(` {Claire: 'brown'}

`),s("span",{"pd-shadow-id":"1614","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1615",text:"R",class:"promptdown-var-name"},"REASONING"),a(" After Alice and Bob swap balls:\n`assign('Alice', 'blue') # result")]),a(` {Alice: 'blue'}
`),s("span",{"pd-shadow-id":"1620","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1621",text:"R",class:"promptdown-var-name"},"REASONING"),a(" `assign('Bob', 'black') # result")]),a(` {Bob: 'black'}

`),s("span",{"pd-shadow-id":"1626","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1627",text:"R",class:"promptdown-var-name"},"REASONING"),a(" After Claire and Bob swap balls:\n`assign('Claire', 'black') # result")]),a(` {Claire: 'black'}
`),s("span",{"pd-shadow-id":"1632","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1633",text:"R",class:"promptdown-var-name"},"REASONING"),a(" `assign('Bob', 'brown') # result")]),a(` {Bob: 'brown'}

`),s("span",{"pd-shadow-id":"1638","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1639",text:"R",class:"promptdown-var-name"},"REASONING"),a(" At the end of the game, Alice has a blue ball:\n`get('Alice') # result")]),a(" blue`\nTherefore at the end of the game, Alice has the "),s("span",{"pd-shadow-id":"1644","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1645",text:"O",class:"promptdown-var-name"},"OBJECT"),a(" blue ball.")]),a(`
`)])])],-1),w=s("p",null,[a("As shown in the example above, the "),s("code",null,"assign"),a(" and "),s("code",null,"get"),a(" functions can be used to store and retrieve values in a simple key-value store. The model is merely instructed to make use of these functions in its reasoning. The query then implements logic to intercept any function use and insert the result of the function call into the reasoning. This allows the model to incorporate the state of the key-value store into its reasoning.")],-1),g=[p,r,i,c,d,h,u,m,w];function b(f,j,y,_,A,q){return t(),o("div",null,g)}const N=e(l,[["render",b]]);export{k as __pageData,N as default};
