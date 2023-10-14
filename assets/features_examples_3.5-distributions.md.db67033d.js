import{_ as t,o as n,c as a,Q as o,k as s,a as e}from"./chunks/framework.4636910e.js";const w=JSON.parse('{"title":"📐 Measure Distributions","description":"","frontmatter":{"title":"📐 Measure Distributions"},"headers":[],"relativePath":"features/examples/3.5-distributions.md","filePath":"features/examples/3.5-distributions.md"}'),i={name:"features/examples/3.5-distributions.md"},l=o(`<p>Apart from text generation, LMQL also <em>measures model scores</em>, allowing users to extract classification results and confidence scores.</p><p>%SPLIT%</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># prompt with a data sample</span>
<span class="hljs-string">&quot;Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.\\n&quot;</span>

<span class="hljs-comment"># instruct model to do sentiment analysis</span>
<span class="hljs-string">&quot;Q: What is the underlying sentiment of this review and why?\\n&quot;</span>

<span class="hljs-comment"># generate a text-based analysis</span>
<span class="hljs-string">&quot;A:<span class="hljs-placeholder">[ANALYSIS]</span>\\n&quot;</span>

<span class="hljs-comment"># based on the analysis, measure certainity about the sentiment</span>
<span class="hljs-string">&quot;Based on this, the overall sentiment of the message can be considered to be<span class="hljs-placeholder">[CLASSIFICATION]</span>&quot;</span> <span class="hljs-keyword">distribution</span> \\
   CLASSIFICATION <span class="hljs-keyword">in</span> [<span class="hljs-string">&quot; positive&quot;</span>, <span class="hljs-string">&quot; neutral&quot;</span>, <span class="hljs-string">&quot; negative&quot;</span>]
</span></code></pre></div><p>%SPLIT%</p>`,4),d=s("div",{class:"language-promptdown vp-adaptive-theme"},[s("button",{title:"Copy Code",class:"copy"}),s("span",{class:"lang"},"promptdown"),s("pre",{"pd-text":`Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.

Q: What is the underlying sentiment of this review and why?

A: [ANALYSIS|Positive, because the reviewer enjoyed their stay and had positive experiences with both the activities and food.]

Based on this, the overall sentiment of the message 
can be considered to be [_CLS(color='ablue')|\\[CLASSIFICATION\\]]






`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[s("p",{"pd-shadow-id":"2015",text:"R","pd-insertion-point":"true"},[e(`Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.

Q: What is the underlying sentiment of this review and why?

A: `),s("span",{"pd-shadow-id":"2017","pd-instant":"false",text:"",class:"promptdown-var color-red"},[s("span",{"pd-shadow-id":"2018",text:"A",class:"promptdown-var-name"},"ANALYSIS"),e("Positive, because the reviewer enjoyed their stay and had positive experiences with both the activities and food.")]),e(`

Based on this, the overall sentiment of the message 
can be considered to be `),s("span",{"pd-shadow-id":"2023","pd-instant":"false",text:"",class:"promptdown-var color-blue"},[s("span",{"pd-shadow-id":"2024",text:"C",class:"promptdown-var-name",style:{display:"none"}},"CLS"),e("[CLASSIFICATION]")]),e(`






`)])])],-1),p=s("div",{class:"distribution"},[s("i",null,[e("P("),s("b",null,"CLASSIFICATION"),e(") =")]),s("div",null,[e(" - "),s("b",null,"positive 0.9998711120293567"),s("br"),e(" - neutral 0.00012790777085508993"),s("br"),e(" - negative 9.801997880775052e-07 ")])],-1),r=[l,d,p];function c(h,u,m,v,_,g){return n(),a("div",null,r)}const f=t(i,[["render",c]]);export{w as __pageData,f as default};
