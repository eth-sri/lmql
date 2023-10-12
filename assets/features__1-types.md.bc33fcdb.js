import{_ as s,o as a,c as n,Q as e}from"./chunks/framework.4636910e.js";const m=JSON.parse('{"title":"Typed LLMs","description":"","frontmatter":{"title":"Typed LLMs","template":"side-by-side","new":true},"headers":[],"relativePath":"features/_1-types.md","filePath":"features/_1-types.md"}'),t={name:"features/_1-types.md"},l=e(`<p>To make language model interaction more robust, LMQL provides typed output.<br><br></p><p>Any output <code>[VARIABLE]</code> can be annotated with a type, and LMQL will ensure that the output is valid by enforcing inference constraints.</p><button class="btn"> Learn more </button><p>%SPLIT%</p><div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><span class="hljs-meta">@dataclass</span>
<span class="hljs-keyword">class</span> <span class="hljs-title class_">Person</span>:
    name: <span class="hljs-built_in">str</span>
    age: <span class="hljs-built_in">int</span>
    job: <span class="hljs-built_in">str</span>

<span class="hljs-string">&quot;&quot;&quot;
Alice is <span class="hljs-placeholder">[AGE]</span> years old and has a GPA of <span class="hljs-placeholder">[GPA: <span class="hljs-built_in">float</span>]</span>.
She works at <span class="hljs-placeholder">[COMPANY: <span class="hljs-built_in">str</span>]</span> as a <span class="hljs-placeholder">[JOB: <span class="hljs-built_in">str</span>]</span> in <span class="hljs-placeholder">[CITY: <span class="hljs-built_in">str</span>]</span>.
To summarize, Alice is a <span class="hljs-placeholder">[p: Person]</span>.
&quot;&quot;&quot;</span>
p.name <span class="hljs-comment"># Alice</span>
</span></code></pre></div>`,5),p=[l];function o(c,i,r,d,_,h){return a(),n("div",null,p)}const j=s(t,[["render",o]]);export{m as __pageData,j as default};
