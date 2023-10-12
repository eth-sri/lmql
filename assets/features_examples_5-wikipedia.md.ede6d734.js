import{_ as a,o as n,c as t,Q as o,k as s,a as e}from"./chunks/framework.4636910e.js";const w=JSON.parse('{"title":"🌎 Tool Augmentation","description":"","frontmatter":{"title":"🌎 Tool Augmentation"},"headers":[],"relativePath":"features/examples/5-wikipedia.md","filePath":"features/examples/5-wikipedia.md"}'),i={name:"features/examples/5-wikipedia.md"},r=o(`<p>LMQL supports <em>arbitrary Python function calls during generation</em>, enabling seamless integration with external tools and APIs, augmenting the model&#39;s capabilities.</p><p>%SPLIT%</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># define or import an external function</span>
<span class="hljs-keyword">async</span> <span class="hljs-keyword">def</span> <span class="hljs-title function_">wikipedia</span>(<span class="hljs-params">q</span>): ...

<span class="hljs-comment"># pose a question</span>
<span class="hljs-string">&quot;Q: From which countries did the Norse originate?\\n&quot;</span>

<span class="hljs-comment"># invoke &#39;wikipedia&#39; function during reasoning</span>
<span class="hljs-string">&quot;Action: Let&#39;s search Wikipedia for the \\
 term &#39;<span class="hljs-placeholder">[TERM]</span>\\n&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(TERM, <span class="hljs-string">&quot;&#39;&quot;</span>)

<span class="hljs-comment"># seamlessly call it *during* generation</span>
result = <span class="hljs-keyword">await</span> wikipedia(TERM)
<span class="hljs-string">&quot;Result: <span class="hljs-subst">{result}</span>\\n&quot;</span>

<span class="hljs-comment"># generate final response using retrieved data</span>
<span class="hljs-string">&quot;Final Answer:<span class="hljs-placeholder">[ANSWER]</span>&quot;</span>
</span></code></pre></div><p>%SPLIT%</p>`,4),p=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`Q: From which countries did the Norse originate?

Action: Let's search Wikipedia for the term [TERM| 'Norse']
Result: (Norse is a demonym for Norsemen, a Medieval North Germanic ethnolinguistic group ancestral to modern Scandinavians, defined as speakers of Old Norse from about the 9th to the 13th centuries.)

Final Answer: [ANSWER| The Norse originated from Scandinavia.]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"2069",text:"Q","pd-insertion-point":"true"},[e(`Q: From which countries did the Norse originate?

Action: Let's search Wikipedia for the term `),s("span",{"pd-shadow-id":"2071","pd-instant":"false",text:"",class:"promptdown-var color-blue"},[s("span",{"pd-shadow-id":"2072",text:"T",class:"promptdown-var-name"},"TERM"),e(" 'Norse'")]),e(`
Result: (Norse is a demonym for Norsemen, a Medieval North Germanic ethnolinguistic group ancestral to modern Scandinavians, defined as speakers of Old Norse from about the 9th to the 13th centuries.)

Final Answer: `),s("span",{"pd-shadow-id":"2077","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"2078",text:"A",class:"promptdown-var-name"},"ANSWER"),e(" The Norse originated from Scandinavia.")]),e(`
`)])])],-1),l=[r,p];function d(c,h,m,u,g,_){return n(),t("div",null,l)}const N=a(i,[["render",d]]);export{w as __pageData,N as default};
