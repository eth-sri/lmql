import{_ as e,o as t,c as o,Q as n,k as s,a}from"./chunks/framework.c2adf1ba.js";const q=JSON.parse('{"title":"LangChain","description":"","frontmatter":{},"headers":[],"relativePath":"docs/lib/integrations/langchain.md","filePath":"docs/lib/integrations/langchain.md"}'),l={name:"docs/lib/integrations/langchain.md"},p=n(`<h1 id="langchain" tabindex="-1">LangChain <a class="header-anchor" href="#langchain" aria-label="Permalink to &quot;LangChain&quot;">​</a></h1><div class="subtitle">Leverage your LangChain stack with LMQL</div><p>LMQL can also be used together with the <a href="https://python.langchain.com/en/latest/index.html#" target="_blank" rel="noreferrer">🦜🔗 LangChain</a> python library. Both, using langchain libraries from LMQL code and using LMQL queries as part of chains are supported.</p><h2 id="using-langchain-from-lmql" tabindex="-1">Using LangChain from LMQL <a class="header-anchor" href="#using-langchain-from-lmql" aria-label="Permalink to &quot;Using LangChain from LMQL&quot;">​</a></h2><p>We first consider the case, where one may want to use LangChain modules as part of an LMQL program. In this example, we want to leverage the LangChain <code>Chroma</code> retrieval model, to enable question answering about a text document (the LMQL paper in this case).</p><p>First, we need to import the required libraries.</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">import</span> lmql
<span class="hljs-keyword">import</span> asyncio
<span class="hljs-keyword">from</span> langchain.embeddings.openai <span class="hljs-keyword">import</span> OpenAIEmbeddings
<span class="hljs-keyword">from</span> langchain.vectorstores <span class="hljs-keyword">import</span> Chroma
</span></code></pre></div><p>Next, we load and embed the text of the relevant document (<code>lmql.txt</code> in our case).</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># load text of LMQL paper</span>
<span class="hljs-keyword">with</span> <span class="hljs-built_in">open</span>(<span class="hljs-string">&quot;lmql.txt&quot;</span>) <span class="hljs-keyword">as</span> f:
    contents = f.read()
texts = []
<span class="hljs-keyword">for</span> i <span class="hljs-keyword">in</span> <span class="hljs-built_in">range</span>(<span class="hljs-number">0</span>, <span class="hljs-built_in">len</span>(contents), <span class="hljs-number">120</span>):
    texts.append(contents[i:i+<span class="hljs-number">120</span>])

embeddings = OpenAIEmbeddings()
docsearch = Chroma.from_texts(texts, embeddings, 
    metadatas=[{<span class="hljs-string">&quot;text&quot;</span>: t} <span class="hljs-keyword">for</span> t <span class="hljs-keyword">in</span> texts], persist_directory=<span class="hljs-string">&quot;lmql-index&quot;</span>)
</span></code></pre></div><p>We then construct a chatbot function, using a simple LMQL query, that first prompts the user for a question via <code>await input(...)</code>, retrieves relevant text paragraphs using LangChain and then produces an answer using <code>openai/gpt-3.5-turbo</code> (ChatGPT).</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">import</span> termcolor

<span class="hljs-meta">@lmql.query(<span class="hljs-params">model=<span class="hljs-string">&quot;openai/gpt-3.5-turbo&quot;</span></span>)</span>
<span class="hljs-keyword">async</span> <span class="hljs-keyword">def</span> <span class="hljs-title function_">chatbot</span>():
    <span class="hljs-inline-lmql"><span class="inline-lmql-delim">&#39;&#39;&#39;lmql</span>
    <span class="hljs-comment"># system instruction</span>
    <span class="hljs-string">&quot;&quot;&quot;<span class="hljs-subst">{:system}</span> You are a chatbot that helps users answer questions.
    You are first provided with the question and relevant information.&quot;&quot;&quot;</span>
    
    <span class="hljs-comment"># chat loop</span>
    <span class="hljs-keyword">while</span> <span class="hljs-literal">True</span>:
        <span class="hljs-comment"># process user input</span>
        q = <span class="hljs-keyword">await</span> <span class="hljs-built_in">input</span>(<span class="hljs-string">&quot;\\nQuestion: &quot;</span>)
        <span class="hljs-keyword">if</span> q == <span class="hljs-string">&quot;exit&quot;</span>: <span class="hljs-keyword">break</span>
        <span class="hljs-comment"># expose question to model</span>
        <span class="hljs-string">&quot;<span class="hljs-subst">{:user}</span> <span class="hljs-subst">{q}</span>\\n&quot;</span>
        
        <span class="hljs-comment"># insert retrieval results</span>
        <span class="hljs-built_in">print</span>(termcolor.colored(<span class="hljs-string">&quot;Reading relevant pages...&quot;</span>, <span class="hljs-string">&quot;green&quot;</span>))
        results = <span class="hljs-built_in">set</span>([d.page_content <span class="hljs-keyword">for</span> d <span class="hljs-keyword">in</span> docsearch.similarity_search(q, 4)])
        information = <span class="hljs-string">&quot;\\n\\n&quot;</span>.join([<span class="hljs-string">&quot;...&quot;</span> + r + <span class="hljs-string">&quot;...&quot;</span> <span class="hljs-keyword">for</span> r <span class="hljs-keyword">in</span> <span class="hljs-built_in">list</span>(results)])
        <span class="hljs-string">&quot;<span class="hljs-subst">{:system}</span> \\nRelevant Information: <span class="hljs-subst">{information}</span>\\n&quot;</span>
        
        <span class="hljs-comment"># generate model response</span>
        <span class="hljs-string">&quot;<span class="hljs-subst">{:assistant}</span> <span class="hljs-placeholder">[RESPONSE]</span>&quot;</span>
    <span class="inline-lmql-delim">&#39;&#39;&#39;</span></span>

<span class="hljs-keyword">await</span> chatbot(output_writer=lmql.stream(variable=<span class="hljs-string">&quot;RESPONSE&quot;</span>))
</span></code></pre></div>`,11),i=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`# Chat Log
[bubble:system| You are a chatbot that helps users answer questions. 
You are first provided with the question and relevant information.]
[bubble:user| What is LMQL?]
[bubble:system| Relevant Information: (inserted by retriever)]
[bubble:assistant| LMQL is a high-level query language for LMs that allows for great expressiveness and supports scripted prompting.]
[bubble:user| How to write prompts?]
[bubble:system| Relevant Information: (inserted by retriever)]
[bubble:assistant| To write prompts, you can use a language model to expand the prompt and obtain the answer to a specific question.]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("h1",{"pd-shadow-id":"1706",text:" "}," Chat Log"),s("p",{"pd-shadow-id":"1708",text:"","pd-insertion-point":"true"},[s("div",{"pd-shadow-id":"1712",class:"promptdown-bubble-container system"},[s("span",{"pd-shadow-id":"1709","pd-instant":"false",text:"",class:"promptdown-var promptdown-bubble system"},[s("span",{"pd-shadow-id":"1710",text:"b",class:"promptdown-var-name"},"bubble:system"),a(` You are a chatbot that helps users answer questions. 
You are first provided with the question and relevant information.`)])]),a(`
`),s("div",{"pd-shadow-id":"1719",class:"promptdown-bubble-container user"},[s("span",{"pd-shadow-id":"1716","pd-instant":"false",text:"",class:"promptdown-var promptdown-bubble user"},[s("span",{"pd-shadow-id":"1717",text:"b",class:"promptdown-var-name"},"bubble:user"),a(" What is LMQL?")])]),a(`
`),s("div",{"pd-shadow-id":"1726",class:"promptdown-bubble-container system"},[s("span",{"pd-shadow-id":"1723","pd-instant":"false",text:"",class:"promptdown-var promptdown-bubble system"},[s("span",{"pd-shadow-id":"1724",text:"b",class:"promptdown-var-name"},"bubble:system"),a(" Relevant Information: (inserted by retriever)")])]),a(`
`),s("div",{"pd-shadow-id":"1733",class:"promptdown-bubble-container assistant"},[s("span",{"pd-shadow-id":"1730","pd-instant":"false",text:"",class:"promptdown-var promptdown-bubble assistant"},[s("span",{"pd-shadow-id":"1731",text:"b",class:"promptdown-var-name"},"bubble:assistant"),a(" LMQL is a high-level query language for LMs that allows for great expressiveness and supports scripted prompting.")])]),a(`
`),s("div",{"pd-shadow-id":"1740",class:"promptdown-bubble-container user"},[s("span",{"pd-shadow-id":"1737","pd-instant":"false",text:"",class:"promptdown-var promptdown-bubble user"},[s("span",{"pd-shadow-id":"1738",text:"b",class:"promptdown-var-name"},"bubble:user"),a(" How to write prompts?")])]),a(`
`),s("div",{"pd-shadow-id":"1747",class:"promptdown-bubble-container system"},[s("span",{"pd-shadow-id":"1744","pd-instant":"false",text:"",class:"promptdown-var promptdown-bubble system"},[s("span",{"pd-shadow-id":"1745",text:"b",class:"promptdown-var-name"},"bubble:system"),a(" Relevant Information: (inserted by retriever)")])]),a(`
`),s("div",{"pd-shadow-id":"1754",class:"promptdown-bubble-container assistant"},[s("span",{"pd-shadow-id":"1751","pd-instant":"false",text:"",class:"promptdown-var promptdown-bubble assistant"},[s("span",{"pd-shadow-id":"1752",text:"b",class:"promptdown-var-name"},"bubble:assistant"),a(" To write prompts, you can use a language model to expand the prompt and obtain the answer to a specific question.")])]),a(`
`)])])],-1),r=n(`<p>As shown in the query, inline LMQL code appearing in a Python script can access the outer scope containing e.g. the <code>docsearch</code> variable, and access any relevant utility functions and object provided by LangChain.</p><p>For more details on building Chat applications with LMQL, see the <a href="./../chat.html">Chat API documentation</a></p><h2 id="using-lmql-from-langchain" tabindex="-1">Using LMQL from LangChain <a class="header-anchor" href="#using-lmql-from-langchain" aria-label="Permalink to &quot;Using LMQL from LangChain&quot;">​</a></h2><p>In addition to using langchain utilities in LMQL query code, LMQL queries can also seamlessly be integrated as a <code>langchain</code> <code>Chain</code> component.</p><p>For this consider, the sequential prompting example from the <code>langchain</code> documentation, where we first prompt the language model to propose a company name for a given product, and then ask it for a catchphrase.</p><p>To get started, we first import the relevant langchain components, as well as LMQL.</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">from</span> langchain <span class="hljs-keyword">import</span> LLMChain, PromptTemplate
<span class="hljs-keyword">from</span> langchain.chat_models <span class="hljs-keyword">import</span> ChatOpenAI
<span class="hljs-keyword">from</span> langchain.prompts.chat <span class="hljs-keyword">import</span> (ChatPromptTemplate,HumanMessagePromptTemplate)
<span class="hljs-keyword">from</span> langchain.llms <span class="hljs-keyword">import</span> OpenAI

<span class="hljs-keyword">import</span> lmql
</span></code></pre></div><p>Our chain has two stages: (1) Asking the model for a company name, and (2) asking the model for a catchphrase. For the sake of this example, we will implement (1) in with a langchain prompt and (2) with an LMQL query.</p><p>First, we define the langchain prompt for the company name and instantiate the resulting <code>LLMChain</code>:</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># setup the LM to be used by langchain</span>
llm = OpenAI(temperature=<span class="hljs-number">0.9</span>)

human_message_prompt = HumanMessagePromptTemplate(
        prompt=PromptTemplate(
            template=<span class="hljs-string">&quot;What is a good name for a company that makes <span class="hljs-subst">{product}</span>?&quot;</span>,
            input_variables=[<span class="hljs-string">&quot;product&quot;</span>],
        )
    )
chat_prompt_template = ChatPromptTemplate.from_messages([human_message_prompt])
chat = ChatOpenAI(temperature=<span class="hljs-number">0.9</span>)
chain = LLMChain(llm=chat, prompt=chat_prompt_template)
</span></code></pre></div><p>This can already be executed to produce a company name:</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line">chain.run(<span class="hljs-string">&quot;colorful socks&quot;</span>)
</span></code></pre></div><div class="language-result vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">result</span><pre class="hljs"><code><span class="line"><span class="hljs-string">&#39;VibrantSock Co.\\nColorSplash Socks\\nRainbowThreads\\nChromaSock Co.\\nKaleidosocks\\nColorPop Socks\\nPrismStep\\nSockMosaic\\nHueTrend Socks\\nSpectrumStitch\\nColorBurst Socks&#39;</span>
</span></code></pre></div><p>Next, we define prompt (2) in LMQL, i.e. the LMQL query generating the catchphrase:</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-meta">@lmql.query(<span class="hljs-params">model=<span class="hljs-string">&quot;chatgpt&quot;</span></span>)</span>
<span class="hljs-keyword">async</span> <span class="hljs-keyword">def</span> <span class="hljs-title function_">write_catch_phrase</span>(<span class="hljs-params">company_name: <span class="hljs-built_in">str</span></span>):
    <span class="hljs-string">&#39;&#39;&#39;
    &quot;Write a catchphrase for the following company: <span class="hljs-subst">{company_name}</span>. <span class="hljs-placeholder">[catchphrase]</span>&quot;
    &#39;&#39;&#39;</span>
</span></code></pre></div><p>Again, we can run this part in isolation, like so:</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line">(<span class="hljs-keyword">await</span> write_catch_phrase(<span class="hljs-string">&quot;Socks Inc&quot;</span>)).variables[<span class="hljs-string">&quot;catchphrase&quot;</span>]
</span></code></pre></div><div class="language-result vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">result</span><pre class="hljs"><code><span class="line"><span class="hljs-string">&#39; &quot;Step up your style with Socks Inc. - where comfort meets fashion!&quot;&#39;</span>
</span></code></pre></div><p>To chain the two prompts together, we can use a <code>SimpleSequentialChain</code> from <code>langchain</code>. To make an LMQL query compatible for use with <code>langchain</code>, just call <code>.aschain()</code> on it, before passing it to the <code>SimpleSequentialChain</code> constructor.</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">from</span> langchain.chains <span class="hljs-keyword">import</span> SimpleSequentialChain
overall_chain = SimpleSequentialChain(chains=[chain, write_catch_phrase.aschain()], verbose=<span class="hljs-literal">True</span>)
</span></code></pre></div><p>Now, we can run the overall chain, relying both on LMQL and langchain components:</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># Run the chain specifying only the input variable for the first chain.</span>
catchphrase = overall_chain.run(<span class="hljs-string">&quot;colorful socks&quot;</span>)
<span class="hljs-built_in">print</span>(catchphrase) 
</span></code></pre></div><div class="language- vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang"></span><pre class="hljs"><code><span class="line">&gt; Entering new SimpleSequentialChain chain...
RainbowSocks Co.
 <span class="hljs-string">&quot;Step into a world of color with RainbowSocks Co.!&quot;</span>

&gt; Finished chain.
 <span class="hljs-string">&quot;Step into a world of color with RainbowSocks Co.!&quot;</span>
</span></code></pre></div><p>Overall, we thus have a chain that combines langchain and LMQL components, and can be used as a single unit.</p><div class="info custom-block"><p class="custom-block-title">Asynchronous Use</p><p>You may encounter problems because of the mismatch of LangChain&#39;s synchronous APIs with LMQL&#39;s <code>async</code>-first design.</p><p>To avoid problems with this, you can install the <a href="https://pypi.org/project/nest-asyncio/" target="_blank" rel="noreferrer"><code>nest_asyncio</code></a> package and call <code>nest_asyncio.apply()</code> to enable nested event loops. LMQL will then handle event loop nesting and sync-to-async conversion for you.</p></div>`,25),c=[p,i,r];function h(d,m,u,b,g,w){return t(),o("div",null,c)}const v=e(l,[["render",h]]);export{q as __pageData,v as default};
