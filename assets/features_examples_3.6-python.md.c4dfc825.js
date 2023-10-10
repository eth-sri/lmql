import{_ as n,o as t,c as e,Q as p,k as s,a}from"./chunks/framework.c2adf1ba.js";const j=JSON.parse('{"title":"🐍 Python Support","description":"","frontmatter":{"title":"🐍 Python Support"},"headers":[],"relativePath":"features/examples/3.6-python.md","filePath":"features/examples/3.6-python.md"}'),o={name:"features/examples/3.6-python.md"},l=p(`<p>LMQL can be used directly from within Python, allowing for seamless integration with your existing codebase.</p><p>%SPLIT%</p><div class="language-python vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">python</span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">import</span> lmql

<span class="hljs-comment"># defines an LMQL function from within Python</span>
<span class="hljs-meta">@lmql.query</span>
<span class="hljs-keyword">def</span> <span class="hljs-title function_">say</span>(<span class="hljs-params">phrase</span>):
    <span class="hljs-inline-lmql"><span style="opacity:0.4;">&#39;&#39;&#39;lmql</span>
    <span class="hljs-comment"># we can seamlessly use &#39;phrase&#39; in LMQL</span>
    <span class="hljs-string">&quot;Say &#39;<span class="hljs-subst">{phrase}</span>&#39;: <span class="hljs-placeholder">[TEST]</span>&quot;</span>
    <span class="hljs-comment"># return the result to the caller</span>
    <span class="hljs-keyword">return</span> TEST
    &#39;&#39;&#39;</span>

<span class="hljs-comment"># call your LMQL function like any other Python function</span>
<span class="hljs-built_in">print</span>(say(<span class="hljs-string">&quot;Hello World!&quot;</span>, model=<span class="hljs-string">&quot;openai/gpt-3.5-turbo&quot;</span>))
</span></code></pre></div><p>%SPLIT%</p>`,4),r=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`Say 'Hello World!': [TEST| Hello World!]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"2045",text:"S","pd-insertion-point":"true"},[a("Say 'Hello World': "),s("span",{"pd-shadow-id":"2047","pd-instant":"false",text:"",class:"promptdown-var color-pink"},[s("span",{"pd-shadow-id":"2048",text:"T",class:"promptdown-var-name"},"TEST"),a(" Hello World")]),a(`
`)])])],-1),c=[l,r];function i(d,h,m,u,_,y){return t(),e("div",null,c)}const T=n(o,[["render",i]]);export{j as __pageData,T as default};
