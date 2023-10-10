import{_ as a,o as n,c as o,Q as s,k as e,a as t}from"./chunks/framework.c2adf1ba.js";const A=JSON.parse('{"title":"Overview","description":"","frontmatter":{"order":0},"headers":[],"relativePath":"docs/language/overview.md","filePath":"docs/language/overview.md"}'),i={name:"docs/language/overview.md"},d=s(`<h1 id="overview" tabindex="-1">Overview <a class="header-anchor" href="#overview" aria-label="Permalink to &quot;Overview&quot;">​</a></h1><div class="subtitle">A quick tour of LMQL&#39;s syntax and capabilities.</div><p>LMQL is a Python-based programming language for LLM programming with declarative elements. As a simple example consider the following program, demonstrating the basic syntax of LMQL:</p><div class="language- vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang"></span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># review to be analyzed</span>
review = <span class="hljs-string">&quot;&quot;&quot;We had a great stay. Hiking in the mountains 
            was fabulous and the food is really good.&quot;&quot;&quot;</span>

<span class="hljs-comment"># use prompt statements to pass information to the model</span>
<span class="hljs-string">&quot;Review: <span class="hljs-subst">{review}</span>&quot;</span>
<span class="hljs-string">&quot;Q: What is the underlying sentiment of this review and why?&quot;</span>
<span class="hljs-comment"># template variables like [ANALYSIS] are used to generate text</span>
<span class="hljs-string">&quot;A:<span class="hljs-placeholder">[ANALYSIS]</span>&quot;</span> <span class="hljs-keyword">where</span> <span class="hljs-keyword">not</span> <span class="hljs-string">&quot;\\n&quot;</span> <span class="hljs-keyword">in</span> ANALYSIS

<span class="hljs-comment"># use constrained variable to produce a classification</span>
<span class="hljs-string">&quot;Based on this, the overall sentiment of the message\\
 can be considered to be<span class="hljs-placeholder">[CLS]</span>&quot;</span> <span class="hljs-keyword">where</span> CLS <span class="hljs-keyword">in</span> [<span class="hljs-string">&quot; positive&quot;</span>, <span class="hljs-string">&quot; neutral&quot;</span>, <span class="hljs-string">&quot; negative&quot;</span>]

CLS <span class="hljs-comment"># positive</span>
</span></code></pre></div>`,4),l=e("div",{class:"language-promptdown vp-adaptive-theme"},[e("button",{title:"Copy Code",class:"copy"}),e("span",{class:"lang"},"promptdown"),e("pre",{"pd-text":`# Model Output
Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.
Q: What is the underlying sentiment of this review and why?
A: [ANALYSIS|The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.]
Based on this, the overall sentiment of the message can be 
considered to be [CLS| positive]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[e("h1",{"pd-shadow-id":"549",text:" "}," Model Output"),e("p",{"pd-shadow-id":"551",text:"R","pd-insertion-point":"true"},[t(`Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.
Q: What is the underlying sentiment of this review and why?
A: `),e("span",{"pd-shadow-id":"553","pd-instant":"false",text:"",class:"promptdown-var color-red"},[e("span",{"pd-shadow-id":"554",text:"A",class:"promptdown-var-name"},"ANALYSIS"),t("The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.")]),t(`
Based on this, the overall sentiment of the message can be 
considered to be `),e("span",{"pd-shadow-id":"559","pd-instant":"false",text:"",class:"promptdown-var color-purple"},[e("span",{"pd-shadow-id":"560",text:"C",class:"promptdown-var-name"},"CLS"),t(" positive")]),t(`
`)])])],-1),r=s(`<p>In this program, we program an LLM to perform sentiment analysis on a provided user review. We first ask the model to provide some basic analysis, and then we ask it to classify the overall sentiment as one of <code>positive</code>, <code>neutral</code>, or <code>negative</code>. The model is able to correctly identify the sentiment of the review as <code>positive</code>.</p><p>To implement this workflow, we use two template variables <code>[ANALYSIS]</code> and <code>[CLS]</code>, both of which are constrained using designated <code>where</code> expressions.</p><p>For <code>ANALYSIS</code> we constrain the model to not output any newlines, which prevents it from outputting multiple lines that could potentially break the program. For <code>CLS</code> we constrain the model to output one of the three possible values. Using these constraints allows us to decode a fitting answer from the model, where both the analysis and the classification are well-formed and in an expected format.</p><p>Without constraints, the prompt above could produce different final classifications, such as <code>good</code> or <code>bad</code>. To handle this in an automated way, one would have to employ ad-hoc parsing to CLS result to obtain a clear result. Using LMQL&#39;s constraints, however, we can simply restrict the model to only output one of the desired values, thereby enabling robust and reliable integration. To learn more about the different types of constraints available in LMQL, see <a href="./constraints.html">Constraints</a>.</p><h3 id="extracting-more-information-with-distributions" tabindex="-1">Extracting More Information With Distributions <a class="header-anchor" href="#extracting-more-information-with-distributions" aria-label="Permalink to &quot;Extracting More Information With Distributions&quot;">​</a></h3><p>While the query above allows us to extract the sentiment of a review, we do not get any certainty information on the model&#39;s confidence in its classification. To obtain this information, we can additionally employ LMQL&#39;s <code>distribution</code> clause, to obtain the full distribution over the possible values for <code>CLASSIFICATION</code>:</p><div class="language- vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang"></span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">argmax</span>
    <span class="hljs-comment"># review to be analyzed</span>
    review = <span class="hljs-string">&quot;&quot;&quot;We had a great stay. Hiking in the mountains was fabulous and the food is really good.&quot;&quot;&quot;</span>

    <span class="hljs-comment"># use prompt statements to pass information to the model</span>
    <span class="hljs-string">&quot;Review: <span class="hljs-subst">{review}</span>&quot;</span>
    <span class="hljs-string">&quot;Q: What is the underlying sentiment of this review and why?&quot;</span>
    <span class="hljs-comment"># template variables like [ANALYSIS] are used to generate text</span>
    <span class="hljs-string">&quot;A:<span class="hljs-placeholder">[ANALYSIS]</span>&quot;</span> <span class="hljs-keyword">where</span> <span class="hljs-keyword">not</span> <span class="hljs-string">&quot;\\n&quot;</span> <span class="hljs-keyword">in</span> ANALYSIS

    <span class="hljs-comment"># use constrained variable to produce a classification</span>
    <span class="hljs-string">&quot;Based on this, the overall sentiment of the message can be considered to be<span class="hljs-placeholder">[CLS]</span>&quot;</span>
<span class="hljs-keyword">distribution</span>
   CLS <span class="hljs-keyword">in</span> [<span class="hljs-string">&quot; positive&quot;</span>, <span class="hljs-string">&quot; neutral&quot;</span>, <span class="hljs-string">&quot; negative&quot;</span>]
</span></code></pre></div>`,7),p=e("div",{class:"language-promptdown vp-adaptive-theme"},[e("button",{title:"Copy Code",class:"copy"}),e("span",{class:"lang"},"promptdown"),e("pre",{"pd-text":`# Model Output
Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.
Q: What is the underlying sentiment of this review and why?
A: [ANALYSIS| The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.]
Based on this, the overall sentiment of the message can be considered to be [CLS(color='blue')|]

P(CLS)
 -  positive (*) 0.9999244826658527
 -  neutral      7.513155848720942e-05
 -  negative     3.8577566019560874e-07
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[e("h1",{"pd-shadow-id":"567",text:" "}," Model Output"),e("p",{"pd-shadow-id":"569",text:"R","pd-insertion-point":"true"},[t(`Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.
Q: What is the underlying sentiment of this review and why?
A: `),e("span",{"pd-shadow-id":"571","pd-instant":"false",text:"",class:"promptdown-var color-red"},[e("span",{"pd-shadow-id":"572",text:"A",class:"promptdown-var-name"},"ANALYSIS"),t(" The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.")]),t(`
Based on this, the overall sentiment of the message can be considered to be `),e("span",{"pd-shadow-id":"577","pd-instant":"false",text:"",class:"promptdown-var color-lightorange"},[e("span",{"pd-shadow-id":"578",text:"C",class:"promptdown-var-name"},"CLS")]),t(`

P(CLS)
 -  positive (*) 0.9999244826658527
 -  neutral      7.513155848720942e-05
 -  negative     3.8577566019560874e-07
`)])])],-1),h=s(`<p><strong>Distribution Clause</strong></p><p>Instead of constraining <code>CLS</code> with a <code>where</code> expression, we now constrain it in the separate <code>distribution</code> clause. In LMQL, the <code>distribution</code> clause can be used to specify whether we want to additionally obtain the distribution over the possible values for a given variable. In this case, we want to obtain the distribution over the possible values for <code>CLS</code>.</p><blockquote><p><strong>Extended Syntax</strong>: Note, that to use the <code>distribution</code> clause, we have to make our choice of decoding algorithm explicit, by specifying <code>argmax</code> at the beginning of our code (see <a href="./decoding.html">Decoding Algorithms</a> for more information). ¸</p><p>In general, this extended form of LMQL syntax, i.e. indenting your program and explicitly specifying e.g. <code>argmax</code> at the beginning of your code, is optional, but recommended if you want to use the <code>distribution</code> clause. Throughout the documentation we will make use of both syntax variants.</p></blockquote><p>In addition to using the model to perform the <code>ANALYSIS</code>, LMQL now also scores each of the individually provided values for <code>CLS</code> and normalizes the resulting sequence scores into a probability distribution <code>P(CLS)</code> (printed to the Terminal Output of the Playground or Standard Output of the CLI).</p><p>Here, we can see that the model is indeed quite confident in its classification of the review as <code>positive</code>, with an overwhelming probability of <code>99.9%</code>.</p><blockquote><p>Note that currently distribution variables like <code>CLS</code> can only occur at the end of your program.</p></blockquote><h3 id="dynamically-reacting-to-model-output" tabindex="-1">Dynamically Reacting To Model Output <a class="header-anchor" href="#dynamically-reacting-to-model-output" aria-label="Permalink to &quot;Dynamically Reacting To Model Output&quot;">​</a></h3><p>Another way to improve on our initial query, is to implement a more dynamic prompt, where we can react to the model&#39;s output. For example, we could ask the model to provide a more detailed analysis of the review, depending on the model&#39;s classification:</p><div class="language- vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang"></span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">argmax</span>
   review = <span class="hljs-string">&quot;&quot;&quot;We had a great stay. Hiking in the mountains 
               was fabulous and the food is really good.&quot;&quot;&quot;</span>
   <span class="hljs-string">&quot;&quot;&quot;Review: <span class="hljs-subst">{review}</span>
   Q: What is the underlying sentiment of this review and why?
   A:<span class="hljs-placeholder">[ANALYSIS]</span>&quot;&quot;&quot;</span> <span class="hljs-keyword">where</span> <span class="hljs-keyword">not</span> <span class="hljs-string">&quot;\\n&quot;</span> <span class="hljs-keyword">in</span> ANALYSIS
   
   <span class="hljs-string">&quot;Based on this, the overall sentiment of the message can be considered to be<span class="hljs-placeholder">[CLS]</span>&quot;</span> <span class="hljs-keyword">where</span> CLS <span class="hljs-keyword">in</span> [<span class="hljs-string">&quot; positive&quot;</span>, <span class="hljs-string">&quot; neutral&quot;</span>, <span class="hljs-string">&quot; negative&quot;</span>]
   
   <span class="hljs-keyword">if</span> CLS == <span class="hljs-string">&quot; positive&quot;</span>:
      <span class="hljs-string">&quot;What is it that they liked about their stay? <span class="hljs-placeholder">[FURTHER_ANALYSIS]</span>&quot;</span>
   <span class="hljs-keyword">elif</span> CLS == <span class="hljs-string">&quot; neutral&quot;</span>:
      <span class="hljs-string">&quot;What is it that could have been improved? <span class="hljs-placeholder">[FURTHER_ANALYSIS]</span>&quot;</span>
   <span class="hljs-keyword">elif</span> CLS == <span class="hljs-string">&quot; negative&quot;</span>:
      <span class="hljs-string">&quot;What is it that they did not like about their stay? <span class="hljs-placeholder">[FURTHER_ANALYSIS]</span>&quot;</span>
<span class="hljs-keyword">where</span>
   STOPS_AT(FURTHER_ANALYSIS, <span class="hljs-string">&quot;.&quot;</span>)
</span></code></pre></div>`,9),c=e("div",{class:"language-promptdown vp-adaptive-theme"},[e("button",{title:"Copy Code",class:"copy"}),e("span",{class:"lang"},"promptdown"),e("pre",{"pd-text":`# Model Output
Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.

Q: What is the underlying sentiment of this review and why?
A: [ANALYSIS|The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.]

Based on this, the overall sentiment of the message can be considered to be [CLASSIFICATION|positive]

What is it that they liked about their stay?
[FURTHER_ANALYSIS|The reviewer liked the hiking in the mountains and the food.]
`,animate:"true",__animate:"true","animate-speed":"50",class:"promptdown promptdown-compiled",style:{opacity:"1"}},[e("h1",{"pd-shadow-id":"584",text:" "}," Model Output"),e("p",{"pd-shadow-id":"586",text:"R","pd-insertion-point":"true"},[t(`Review: We had a great stay. Hiking in the mountains was fabulous and the food is really good.

Q: What is the underlying sentiment of this review and why?
A: `),e("span",{"pd-shadow-id":"588","pd-instant":"false",text:"",class:"promptdown-var color-red"},[e("span",{"pd-shadow-id":"589",text:"A",class:"promptdown-var-name"},"ANALYSIS"),t("The underlying sentiment of this review is positive because the reviewer had a great stay, enjoyed the hiking and found the food to be good.")]),t(`

Based on this, the overall sentiment of the message can be considered to be `),e("span",{"pd-shadow-id":"594","pd-instant":"false",text:"",class:"promptdown-var color-pink"},[e("span",{"pd-shadow-id":"595",text:"C",class:"promptdown-var-name"},"CLASSIFICATION"),t("positive")]),t(`

What is it that they liked about their stay?
`),e("span",{"pd-shadow-id":"600","pd-instant":"false",text:"",class:"promptdown-var color-pink"},[e("span",{"pd-shadow-id":"601",text:"F",class:"promptdown-var-name"},"FURTHER_ANALYSIS"),t("The reviewer liked the hiking in the mountains and the food.")]),t(`
`)])])],-1),u=s('<p>As shown here, we can use the <code>if</code> statement to dynamically react to the model&#39;s output. In this case, we ask the model to provide a more detailed analysis of the review, depending on the overall positive, neutral, or negative sentiment of the review. All intermediate variables like <code>ANALYSIS</code>, <code>CLASSIFICATION</code> or <code>FURTHER_ANALYSIS</code> can be considered the output of query, and may be processed by an surrounding automated system.</p><p>To learn more about the capabilities of such control-flow-guided prompts, see <a href="./scripted-prompting.html">Scripted Prompting</a>.</p><p>As shown here, in addition to inline <code>where</code> expressions as seen earlier, you can also provide a global <code>where</code> expression at the end of your program, e.g. to specify constraints that should apply for all variables. Depending on your use case, this can be a convenient way to avoid having to repeat the same constraints multiple times, like for <code>FURTHER_ANALYSIS</code> in this example.</p>',3),m=[d,l,r,p,h,c,u];function g(w,v,y,f,b,S){return n(),o("div",null,m)}const _=a(i,[["render",g]]);export{A as __pageData,_ as default};
