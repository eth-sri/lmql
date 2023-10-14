import{_ as t,o as e,c as n,Q as o,k as s,a}from"./chunks/framework.4636910e.js";const A=JSON.parse('{"title":"🧠 Multi-Part Prompts","description":"","frontmatter":{"title":"🧠 Multi-Part Prompts"},"headers":[],"relativePath":"features/examples/3-multi-part.md","filePath":"features/examples/3-multi-part.md"}'),p={name:"features/examples/3-multi-part.md"},r=o(`<p>LMQL&#39;s programming model supports multi-part prompt programs, enabling enhanced controls over the LLM reasoning process.</p><p>%SPLIT%</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># use multi-part prompting for complicated questions</span>
<span class="hljs-string">&quot;Q: It was Sept. 1st, 2021 a week ago. What is the date 10 days ago in MM/DD/YYYY?&quot;</span>
<span class="hljs-string">&quot;Answer Choices: (A) 08/29/2021 (B) 08/28/2021 (C) 08/29/1925 (D) 08/30/2021 (E) 05/25/2021 (F) 09/19/2021&quot;</span>

<span class="hljs-comment"># use a reasoning step to break down the problem</span>
<span class="hljs-string">&quot;A: Let&#39;s think step by step.\\n <span class="hljs-placeholder">[REASONING]</span>&quot;</span>

<span class="hljs-comment"># use a constrained variable to extract the final response</span>
<span class="hljs-string">&quot;Therefore, the answer is <span class="hljs-placeholder">[ANSWER]</span>&quot;</span> <span class="hljs-keyword">where</span> \\
    ANSWER <span class="hljs-keyword">in</span> [<span class="hljs-string">&quot;A&quot;</span>, <span class="hljs-string">&quot;B&quot;</span>, <span class="hljs-string">&quot;C&quot;</span>, <span class="hljs-string">&quot;D&quot;</span>, <span class="hljs-string">&quot;E&quot;</span>, <span class="hljs-string">&quot;F&quot;</span>]

<span class="hljs-comment"># access results just like a normal variable</span>
ANSWER <span class="hljs-comment"># &quot;A&quot;</span>
</span></code></pre></div><p>%SPLIT%</p>`,4),l=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`Q: It was Sept. 1st, 2021 a week ago. What is the date 10 days ago in MM/DD/YYYY?
Answer Choices: (A) 08/29/2021 (B) 08/28/2021 (C) 08/29/1925 (D) 08/30/2021 (E) 05/25/2021 (F) 09/19/2021

A: Let's think step by step.
[REASONING(color='red')| Sept. 1st, 2021 was a week ago, so 10 days ago would be 8 days before that, which is August 23rd, 2021, so the answer is (A) 08/29/2021.]

Therefore, the answer is [ANSWER| A]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"2000",text:"Q","pd-insertion-point":"true"},[a(`Q: It was Sept. 1st, 2021 a week ago. What is the date 10 days ago in MM/DD/YYYY?
Answer Choices: (A) 08/29/2021 (B) 08/28/2021 (C) 08/29/1925 (D) 08/30/2021 (E) 05/25/2021 (F) 09/19/2021

A: Let's think step by step.
`),s("span",{"pd-shadow-id":"2002","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[s("span",{"pd-shadow-id":"2003",text:"R",class:"promptdown-var-name"},"REASONING"),a(" Sept. 1st, 2021 was a week ago, so 10 days ago would be 8 days before that, which is August 23rd, 2021, so the answer is (A) 08/29/2021.")]),a(`

Therefore, the answer is `),s("span",{"pd-shadow-id":"2008","pd-instant":"false",text:"",class:"promptdown-var color-ochre"},[s("span",{"pd-shadow-id":"2009",text:"A",class:"promptdown-var-name"},"ANSWER"),a(" A")]),a(`
`)])])],-1),i=[r,l];function c(d,h,u,m,w,g){return e(),n("div",null,i)}const q=t(p,[["render",c]]);export{A as __pageData,q as default};
