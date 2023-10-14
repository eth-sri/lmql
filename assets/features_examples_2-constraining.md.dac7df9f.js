import{_ as n,o as t,c as e,Q as o,k as s,a}from"./chunks/framework.4636910e.js";const j=JSON.parse('{"title":"⛓️ Constrained LLMs","description":"","frontmatter":{"title":"⛓️ Constrained LLMs"},"headers":[],"relativePath":"features/examples/2-constraining.md","filePath":"features/examples/2-constraining.md"}'),p={name:"features/examples/2-constraining.md"},l=o(`<p>LMQL&#39;s support for constrained generation enables robust interfacing, to integrate LLMs safely into your applications.<a href="../../docs/constraints.html">Learn More →</a></p><p>%SPLIT%</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># top-level strings are prompts</span>
<span class="hljs-string">&quot;Tell me a joke:\\n&quot;</span>

<span class="hljs-comment"># use &#39;where&#39; constraints to control and restrict generation</span>
<span class="hljs-string">&quot;Q:<span class="hljs-placeholder">[JOKE]</span>\\n&quot;</span> <span class="hljs-keyword">where</span> <span class="hljs-built_in">len</span>(JOKE) &lt; <span class="hljs-number">120</span> <span class="hljs-keyword">and</span> STOPS_AT(JOKE, <span class="hljs-string">&quot;?&quot;</span>)

<span class="hljs-string">&quot;A:<span class="hljs-placeholder">[PUNCHLINE]</span>\\n&quot;</span> <span class="hljs-keyword">where</span> \\ 
    STOPS_AT(PUNCHLINE, <span class="hljs-string">&quot;\\n&quot;</span>) <span class="hljs-keyword">and</span> <span class="hljs-built_in">len</span>(TOKENS(PUNCHLINE)) &gt; <span class="hljs-number">1</span>
</span></code></pre></div><p>%SPLIT%</p>`,4),r=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`Tell me a joke:

Q: [JOKE| What did the fish say when it hit the wall?]
A: [PUNCHLINE| Dam!]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1985",text:"T","pd-insertion-point":"true"},[a(`Tell me a joke:

Q: `),s("span",{"pd-shadow-id":"1987","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1988",text:"J",class:"promptdown-var-name"},"JOKE"),a(" What did the fish say when it hit the wall?")]),a(`
A: `),s("span",{"pd-shadow-id":"1993","pd-instant":"false",text:"",class:"promptdown-var color-orange"},[s("span",{"pd-shadow-id":"1994",text:"P",class:"promptdown-var-name"},"PUNCHLINE"),a(" Dam")]),a(`
`)])])],-1),i=[l,r];function c(d,h,m,_,u,g){return t(),e("div",null,i)}const f=n(p,[["render",c]]);export{j as __pageData,f as default};
