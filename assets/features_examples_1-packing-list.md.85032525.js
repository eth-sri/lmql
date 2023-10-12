import{_ as n,o as t,c as e,Q as p,k as s,a}from"./chunks/framework.4636910e.js";const T=JSON.parse('{"title":"🌴 Packing List","description":"","frontmatter":{"title":"🌴 Packing List"},"headers":[],"relativePath":"features/examples/1-packing-list.md","filePath":"features/examples/1-packing-list.md"}'),o={name:"features/examples/1-packing-list.md"},l=p(`<p>Prompt construction and generation is implemented via expressive <em>Python control flow and string interpolation</em>.</p><p>%SPLIT%</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># top level strings are prompts</span>
<span class="hljs-string">&quot;My packing list for the trip:&quot;</span>

<span class="hljs-comment"># use loops for repeated prompts</span>
<span class="hljs-keyword">for</span> i <span class="hljs-keyword">in</span> <span class="hljs-built_in">range</span>(<span class="hljs-number">4</span>):
    <span class="hljs-comment"># &#39;where&#39; denotes hard constraints enforced by the runtime</span>
    <span class="hljs-string">&quot;- <span class="hljs-placeholder">[THING]</span> \\n&quot;</span> <span class="hljs-keyword">where</span> THING <span class="hljs-keyword">in</span> \\ 
        [<span class="hljs-string">&quot;Volleyball&quot;</span>, <span class="hljs-string">&quot;Sunscreen&quot;</span>, <span class="hljs-string">&quot;Bathing Suite&quot;</span>]
</span></code></pre></div><p>%SPLIT%</p>`,4),r=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`My packing list for the trip:

- [THING| Volleyball]
- [THING| Bathing Suite]
- [THING| Sunscreen]
- [THING| Volleyball]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"1958",text:"M","pd-insertion-point":"true"},[a(`My packing list for the trip:

- `),s("span",{"pd-shadow-id":"1960","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1961",text:"T",class:"promptdown-var-name"},"THING"),a(" Volleyball")]),a(`
- `),s("span",{"pd-shadow-id":"1966","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1967",text:"T",class:"promptdown-var-name"},"THING"),a(" Bathing Suite")]),a(`
- `),s("span",{"pd-shadow-id":"1972","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1973",text:"T",class:"promptdown-var-name"},"THING"),a(" Sunscreen")]),a(`
- `),s("span",{"pd-shadow-id":"1978","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"1979",text:"T",class:"promptdown-var-name"},"THING"),a(" Volleyball")]),a(`
`)])])],-1),i=[l,r];function c(d,m,h,u,g,_){return t(),e("div",null,i)}const f=n(o,[["render",c]]);export{T as __pageData,f as default};
