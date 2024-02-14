import{_ as s,o as n,c as t,Q as o,k as a,a as e}from"./chunks/framework.980cae92.js";const f=JSON.parse('{"title":"🌳 Meta Prompting","description":"","frontmatter":{"title":"🌳 Meta Prompting"},"headers":[],"relativePath":"features/examples/4-meta-prompting.md","filePath":"features/examples/4-meta-prompting.md"}'),p={name:"features/examples/4-meta-prompting.md"},l=o(`<p>LMQL supports <em>program-level</em> decoding algorithms like <code>beam</code>, <code>sample</code> and <code>best_k</code>, allowing for a branching exploration of multi-step reasoning flows.</p><p>%SPLIT%</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># specify a decoding algorithm (e.g. beam, sample, best_k)</span>
<span class="hljs-comment"># to enable multi-branch exploration of your program</span>
<span class="hljs-keyword">beam</span>(n=<span class="hljs-number">2</span>)

<span class="hljs-comment"># pose a question</span>
<span class="hljs-string">&quot;Q: What are Large Language Models?\\n\\n&quot;</span>

<span class="hljs-comment"># use multi-part meta prompting for improved reasoning</span>
<span class="hljs-string">&quot;A good person to answer this question would be<span class="hljs-placeholder">[EXPERT]</span>\\n\\n&quot;</span> <span class="hljs-keyword">where</span> STOPS_AT(EXPERT, <span class="hljs-string">&quot;.&quot;</span>) <span class="hljs-keyword">and</span> STOPS_AT(EXPERT, <span class="hljs-string">&quot;\\n&quot;</span>)

<span class="hljs-comment"># process intermediate results in Python</span>
expert_name = EXPERT.rstrip(<span class="hljs-string">&quot;.\\n&quot;</span>)

<span class="hljs-comment"># generate the final response by leveraging the expert</span>
<span class="hljs-string">&quot;For instance,<span class="hljs-subst">{expert_name}</span> would answer <span class="hljs-placeholder">[ANSWER]</span>&quot;</span> \\ 
    <span class="hljs-keyword">where</span> STOPS_AT(ANSWER, <span class="hljs-string">&quot;.&quot;</span>) 
</span></code></pre></div><p>%SPLIT%</p>`,4),r=a("div",{class:"language-promptdown vp-adaptive-theme"},[a("button",{title:"Copy Code",class:"copy"}),a("span",{class:"lang"},"promptdown"),a("pre",{"pd-text":`Q: What are Large Language Models?⏎

A good person to answer this question would be [EXPERT| a data scientist or a machine learning engineer.]

For instance, (a data scientist or a machine learning engineer) would answer [ANSWER| this question by explaining that large language models are a type of artificial intelligence (AI) model that uses deep learning algorithms to process large amounts of natural language data.]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[a("p",{"pd-shadow-id":"2054",text:"Q","pd-insertion-point":"true"},[e(`Q: What are Large Language Models?⏎

A good person to answer this question would be `),a("span",{"pd-shadow-id":"2056","pd-instant":"false",text:"",class:"promptdown-var color-purple"},[a("span",{"pd-shadow-id":"2057",text:"E",class:"promptdown-var-name"},"EXPERT"),e(" a data scientist or a machine learning engineer.")]),e(`

For instance, (a data scientist or a machine learning engineer) would answer `),a("span",{"pd-shadow-id":"2062","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[a("span",{"pd-shadow-id":"2063",text:"A",class:"promptdown-var-name"},"ANSWER"),e(" this question by explaining that large language models are a type of artificial intelligence (AI) model that uses deep learning algorithms to process large amounts of natural language data.")]),e(`
`)])])],-1),i=[l,r];function c(d,m,g,h,u,_){return n(),t("div",null,i)}const j=s(p,[["render",c]]);export{f as __pageData,j as default};
