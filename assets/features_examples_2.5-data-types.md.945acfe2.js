import{_ as t,o as n,c as e,Q as p,k as s,a}from"./chunks/framework.4636910e.js";const j=JSON.parse('{"title":"🔢 Types and Regex","description":"","frontmatter":{"title":"🔢 Types and Regex"},"headers":[],"relativePath":"features/examples/2.5-data-types.md","filePath":"features/examples/2.5-data-types.md"}'),o={name:"features/examples/2.5-data-types.md"},l=p(`<p>LMQL supports integer and regex constraints, enabling advanced output formatting. The results are automatically represented as the appropriate Python type, and can be manipulated as such.</p><p>%SPLIT%</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># restrict generation to MM/DD format</span>
<span class="hljs-string">&quot;Q: It&#39;s the last day of June. What day is it?\\n&quot;</span>
<span class="hljs-string">&quot;A: Today is <span class="hljs-placeholder">[RESPONSE: r<span class="hljs-string">&#39;[0-9]<span class="hljs-subst">{<span class="hljs-number">2</span>}</span>/[0-9]<span class="hljs-subst">{<span class="hljs-number">2</span>}</span>&#39;</span>]</span>\\n&quot;</span>

<span class="hljs-comment"># generate numbers</span>
<span class="hljs-string">&quot;Q: What&#39;s the month number?\\n&quot;</span>
<span class="hljs-string">&quot;A: <span class="hljs-placeholder">[ANSWER: <span class="hljs-built_in">int</span>]</span>&quot;</span>

<span class="hljs-comment"># results are automatically cast to int...</span>
<span class="hljs-built_in">type</span>(ANSWER) <span class="hljs-comment"># -&gt; int</span>

<span class="hljs-comment"># ...and can be easily manipulated</span>
<span class="hljs-number">10</span> * ANSWER <span class="hljs-comment"># -&gt; 60</span>
</span></code></pre></div><p>%SPLIT%</p>`,4),c=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`Q: It's the last day of June. What day is it?
A: Today is [RESPONSE| 30/06]

Q: What's the month number?
A: [ANSWER| 6]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"2000",text:"Q","pd-insertion-point":"true"},[a(`Q: It's the last day of June. What day is it?
A: Today is `),s("span",{"pd-shadow-id":"2002","pd-instant":"false",text:"",class:"promptdown-var color-pink"},[s("span",{"pd-shadow-id":"2003",text:"R",class:"promptdown-var-name"},"RESPONSE"),a(" 30/06")]),a(`

Q: What's the month number?
A: `),s("span",{"pd-shadow-id":"2008","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"2009",text:"A",class:"promptdown-var-name"},"ANSWER"),a(" 6")]),a(`
`)])])],-1),r=[l,c];function d(i,m,h,u,_,y){return n(),e("div",null,r)}const f=t(o,[["render",d]]);export{j as __pageData,f as default};
