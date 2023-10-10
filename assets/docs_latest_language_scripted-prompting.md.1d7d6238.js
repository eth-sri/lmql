import{_ as n,o as e,c as o,Q as t,k as s,a}from"./chunks/framework.c2adf1ba.js";const j=JSON.parse('{"title":"Scripted Prompting","description":"","frontmatter":{"order":1},"headers":[],"relativePath":"docs/latest/language/scripted-prompting.md","filePath":"docs/latest/language/scripted-prompting.md"}'),p={name:"docs/latest/language/scripted-prompting.md"},l=t(`<h1 id="scripted-prompting" tabindex="-1">Scripted Prompting <a class="header-anchor" href="#scripted-prompting" aria-label="Permalink to &quot;Scripted Prompting&quot;">​</a></h1><div class="subtitle">Programmatic LLM prompting with control flow.</div><p>In LMQL, programs are not just static templates of text, as they also contain control flow (e.g. loops, conditions, function calls). This facilitates dynamic prompt construction and allows LMQL programs to respond dynamically to model output. This scripting mechanic is achieved by a combination of prompt templates, control flow and <a href="./constraints.html">output constraining</a>.</p><div class="tip custom-block"><p class="custom-block-title">Escaping</p><p>LMQL requires special escaping to use <code>[</code>, <code>]</code>, <code>{</code> and <code>}</code> in a literal way, see <a href="#escaping">Escaping</a> for details.</p></div><h2 id="templates-and-control-flow" tabindex="-1">Templates and Control Flow <a class="header-anchor" href="#templates-and-control-flow" aria-label="Permalink to &quot;Templates and Control Flow&quot;">​</a></h2><p><strong>Packing List</strong> For instance, let&#39;s say we want to generate a packing list before going on vacation. One way to do this would be the following query:</p><div class="language- vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang"></span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># use sampling decoder</span>
<span class="hljs-keyword">sample</span>(temperature=<span class="hljs-number">1.0</span>) 
<span class="hljs-comment"># generate a list</span>
<span class="hljs-string">&quot;A few things not to forget when going to the sea (not travelling): \\n&quot;</span>
<span class="hljs-string">&quot;<span class="hljs-placeholder">[LIST]</span>&quot;</span>
</span></code></pre></div>`,7),r=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`A list of things not to forget when going to the sea (not travelling):
[LIST|-A phone with call, texting or tech services
-A copy of the local paper
-A pen or phone Keytar
]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1402",text:"A","pd-insertion-point":"true"},[a(`A list of things not to forget when going to the sea (not travelling):
`),s("span",{"pd-shadow-id":"1404","pd-instant":"false",text:"",class:"promptdown-var color-red"},[s("span",{"pd-shadow-id":"1405",text:"L",class:"promptdown-var-name"},"LIST"),a(`-A phone with call, texting or tech services
-A copy of the local paper
-A pen or phone Keytar
`)]),a(`
`)])])],-1),i=t(`<p>Here, we specify the <code>sample</code> decoder for increased diversity over <code>argmax</code> (cf. <a href="./decoding.html">Decoders</a>), and then execute the program to generate a list using <em>one</em> <code>[LIST]</code> variable.</p><p>This can work well, however, it is unclear if the model will always produce a well-structured list of items in practice. Further, we have to parse the response to separate the various items and process them further.</p><p><strong>Simple Prompt Templates</strong> To address this, we can provide a more rigid template, by providing multiple prompt statements, one per item, to let the model only fill in <code>THING</code>:</p><div class="language- vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang"></span><pre class="hljs"><code><span class="line"><span class="hljs-string">&quot;A list of things not to forget when going to the sea (not travelling): \\n&quot;</span>
<span class="hljs-string">&quot;-<span class="hljs-placeholder">[THING]</span>&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(THING, <span class="hljs-string">&quot;\\n&quot;</span>)
<span class="hljs-string">&quot;-<span class="hljs-placeholder">[THING]</span>&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(THING, <span class="hljs-string">&quot;\\n&quot;</span>)
<span class="hljs-string">&quot;-<span class="hljs-placeholder">[THING]</span>&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(THING, <span class="hljs-string">&quot;\\n&quot;</span>)
<span class="hljs-string">&quot;-<span class="hljs-placeholder">[THING]</span>&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(THING, <span class="hljs-string">&quot;\\n&quot;</span>)
<span class="hljs-string">&quot;-<span class="hljs-placeholder">[THING]</span>&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(THING, <span class="hljs-string">&quot;\\n&quot;</span>)

</span></code></pre></div>`,4),d=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`A list of things not to forget when going to the sea (not travelling):
-[THING|A phone with a/r text]
-[THING|pletter]
-[THING|accoon]
-[THING|Films about/of the sea]
-[THING|A has been in the Poconos for/ Entered the Poconos]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1411",text:"A","pd-insertion-point":"true"},[a(`A list of things not to forget when going to the sea (not travelling):
-`),s("span",{"pd-shadow-id":"1413","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1414",text:"T",class:"promptdown-var-name"},"THING"),a("A phone with a/r text")]),a(`
-`),s("span",{"pd-shadow-id":"1419","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1420",text:"T",class:"promptdown-var-name"},"THING"),a("pletter")]),a(`
-`),s("span",{"pd-shadow-id":"1425","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1426",text:"T",class:"promptdown-var-name"},"THING"),a("accoon")]),a(`
-`),s("span",{"pd-shadow-id":"1431","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1432",text:"T",class:"promptdown-var-name"},"THING"),a("Films about/of the sea")]),a(`
-`),s("span",{"pd-shadow-id":"1437","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1438",text:"T",class:"promptdown-var-name"},"THING"),a("A has been in the Poconos for/ Entered the Poconos")]),a(`
`)])])],-1),c=t(`<p>Note how we use a stopping constraint on each <code>THING</code>, such that a new line in the model output makes sure we progress with our provided template, instead of running-on with the model output. Without the stopping condition, simple template filling would not be possible, as the model would generate more than one item for the first variable already.</p><p><strong>Prompt with Control-Flow</strong> Given this prompt template, we can now leverage control flow in our prompt, to further process results and avoid redundancy, while also guiding text generation.</p><p>First, we simplify our query and use a <code>for</code> loop instead of repeating the variable:</p><div class="language- vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang"></span><pre class="hljs"><code><span class="line"><span class="hljs-string">&quot;A list of things not to forget when going to the sea (not travelling): \\n&quot;</span>
backpack = []
<span class="hljs-keyword">for</span> i <span class="hljs-keyword">in</span> <span class="hljs-built_in">range</span>(<span class="hljs-number">5</span>):
   <span class="hljs-string">&quot;-<span class="hljs-placeholder">[THING]</span>&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(THING, <span class="hljs-string">&quot;\\n&quot;</span>) 
   backpack.append(THING.strip())
<span class="hljs-built_in">print</span>(backpack)

</span></code></pre></div>`,4),h=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`A list of things not to forget when going to the sea (not travelling):
-[THING|A good pair of blue/gel saskaers]
-[THING|A good sun tanner]
-[THING|A good air freshener]
-[THING|A good spot for washing your hands]
-[THING|A good spot for washing your feet]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1444",text:"A","pd-insertion-point":"true"},[a(`A list of things not to forget when going to the sea (not travelling):
-`),s("span",{"pd-shadow-id":"1446","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1447",text:"T",class:"promptdown-var-name"},"THING"),a("A good pair of blue/gel saskaers")]),a(`
-`),s("span",{"pd-shadow-id":"1452","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1453",text:"T",class:"promptdown-var-name"},"THING"),a("A good sun tanner")]),a(`
-`),s("span",{"pd-shadow-id":"1458","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1459",text:"T",class:"promptdown-var-name"},"THING"),a("A good air freshener")]),a(`
-`),s("span",{"pd-shadow-id":"1464","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1465",text:"T",class:"promptdown-var-name"},"THING"),a("A good spot for washing your hands")]),a(`
-`),s("span",{"pd-shadow-id":"1470","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1471",text:"T",class:"promptdown-var-name"},"THING"),a("A good spot for washing your feet")]),a(`
`)])])],-1),g=t(`<div class="language-output vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">output</span><pre class="hljs"><code><span class="line">[<span class="hljs-string">&#39;A good pair of blue/gel saskaers&#39;</span>, 
 <span class="hljs-string">&#39;A good sun tanner&#39;</span>, 
 <span class="hljs-string">&#39;A good air freshener&#39;</span>, <span class="hljs-string">&#39;A good spot for washing your hands&#39;</span>, 
 <span class="hljs-string">&#39;A good spot for washing your feet&#39;</span>]
</span></code></pre></div><p>Because we decode our list <code>THING</code> by <code>THING</code>, we can easily access the individual items, without having to think about parsing or validation. We just add them to a <code>backpack</code> list of things, which we then can process further.</p><p><strong>Cross-Variable Constraints</strong> Now that we have a collected a list of things, we can even extend our program to constrain later parts to choose only the things in our <code>backpack</code>:</p><div class="language- vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang"></span><pre class="hljs"><code><span class="line"><span class="hljs-string">&quot;A list of things not to forget when going to the sea (not travelling): \\n&quot;</span>
backpack = []
<span class="hljs-keyword">for</span> i <span class="hljs-keyword">in</span> <span class="hljs-built_in">range</span>(<span class="hljs-number">5</span>):
   <span class="hljs-string">&quot;-<span class="hljs-placeholder">[THING]</span>&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(THING, <span class="hljs-string">&quot;\\n&quot;</span>) 
   backpack.append(THING.strip())

<span class="hljs-string">&quot;The most essential of which is: <span class="hljs-placeholder">[ESSENTIAL_THING]</span>&quot;</span> \\
    <span class="hljs-keyword">where</span> ESSENTIAL_THING <span class="hljs-keyword">in</span> backpack

</span></code></pre></div>`,4),u=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`A list of things not to forget when going to the sea (not travelling): ⏎
-[THING|Sunscreen]⏎
-[THING|Beach Towels]⏎
-[THING|Beach Umbrella]⏎
-[THING|Beach Chairs]⏎
-[THING|Beach Bag]⏎
The most essential of which is: [ESSENTIAL_THING(color)|Sunscreen]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1477",text:"A","pd-insertion-point":"true"},[a(`A list of things not to forget when going to the sea (not travelling): ⏎
-`),s("span",{"pd-shadow-id":"1479","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1480",text:"T",class:"promptdown-var-name"},"THING"),a("Sunscreen")]),a(`⏎
-`),s("span",{"pd-shadow-id":"1485","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1486",text:"T",class:"promptdown-var-name"},"THING"),a("Beach Towels")]),a(`⏎
-`),s("span",{"pd-shadow-id":"1491","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1492",text:"T",class:"promptdown-var-name"},"THING"),a("Beach Umbrella")]),a(`⏎
-`),s("span",{"pd-shadow-id":"1497","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1498",text:"T",class:"promptdown-var-name"},"THING"),a("Beach Chairs")]),a(`⏎
-`),s("span",{"pd-shadow-id":"1503","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1504",text:"T",class:"promptdown-var-name"},"THING"),a("Beach Bag")]),a(`⏎
The most essential of which is: `),s("span",{"pd-shadow-id":"1509","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"1510",text:"E",class:"promptdown-var-name"},"ESSENTIAL_THING"),a("Sunscreen")]),a(`
`)])])],-1),m=t(`<p>This can be helpful in guiding the model to achieve complete and consistent model reasoning which is less likely to contradict itself.</p><h2 id="escaping" tabindex="-1">Escaping <a class="header-anchor" href="#escaping" aria-label="Permalink to &quot;Escaping&quot;">​</a></h2><p>Inside prompt strings, the characters <code>[</code>, <code>]</code>, <code>{</code>, and <code>}</code> are reserved for template variable use and cannot be used directly. To use them as literals, they need to be escaped as <code>[[</code>, <code>]]</code>, <code><span>{{</span></code>, and <code>}}</code>, respectively. Beyond this, the <a href="https://www.w3schools.com/python/gloss_python_escape_characters.asp" target="_blank" rel="noreferrer">standard string escaping rules</a> for Python strings and <a href="https://peps.python.org/pep-0498/#escape-sequences" target="_blank" rel="noreferrer">f-strings</a> apply, as all top-level strings in LMQL are interpreted as Python f-strings.</p><p>For instance, if you want to use JSON syntax as part of your prompt string, you need to escape the curly braces and squared brackets as follows:</p><div class="language- vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang"></span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">argmax</span> 
    <span class="hljs-string">&quot;&quot;&quot;
    Write a summary of Bruno Mars, the singer:
    <span>{{</span>
      &quot;name&quot;: &quot;<span class="hljs-placeholder">[STRING_VALUE]</span>&quot;,
      &quot;age&quot;: <span class="hljs-placeholder">[INT_VALUE]</span>,
      &quot;top_songs&quot;: <span class="hljs-placeholder">[[
         <span class="hljs-string">&quot;[STRING_VALUE]&quot;</span>,
         <span class="hljs-string">&quot;[STRING_VALUE]&quot;</span>
      ]</span>]
    }}
    &quot;&quot;&quot;</span>
<span class="hljs-keyword">from</span>
    <span class="hljs-string">&quot;openai/text-davinci-003&quot;</span> 
<span class="hljs-keyword">where</span>
    STOPS_BEFORE(STRING_VALUE, <span class="hljs-string">&#39;&quot;&#39;</span>) <span class="hljs-keyword">and</span> INT(INT_VALUE) <span class="hljs-keyword">and</span> <span class="hljs-built_in">len</span>(TOKENS(INT_VALUE)) &lt; <span class="hljs-number">2</span>
         
         
</span></code></pre></div><h2 id="python-compatibility" tabindex="-1">Python Compatibility <a class="header-anchor" href="#python-compatibility" aria-label="Permalink to &quot;Python Compatibility&quot;">​</a></h2><p>Going beyond simple control flow, LMQL also supports most valid Python constructs in the prompt clause of a query, where top-level strings like <code>&quot;-[THING]&quot;</code> are automatically interpreted as model input and template variables are assigned accordingly. For more advanced usage, see also the <a href="./tools.html">Tool Augmentation</a> chapter.</p>`,7),w=[l,r,i,d,c,h,g,u,m];function T(f,_,v,y,I,N){return e(),o("div",null,w)}const q=n(p,[["render",T]]);export{j as __pageData,q as default};
