import{_ as e,C as t,o as l,c as o,H as r,w as c,Q as i,k as s,a as n}from"./chunks/framework.980cae92.js";const y=JSON.parse('{"title":"","description":"","frontmatter":{"title":null,"template":"code"},"headers":[],"relativePath":"features/1-code.md","filePath":"features/1-code.md"}'),p={name:"features/1-code.md"},d=i(`<div class="language-lmql vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">lmql</span><pre class="hljs"><code><span class="line"><div class="window-controls"><div class="window-control window-control-close"></div><div class="window-control window-control-minimize"></div><div class="window-control window-control-maximize"></div></div><span class="hljs-meta">@lmql.query</span>
<span class="hljs-keyword">def</span> <span class="hljs-title function_">meaning_of_life</span>():
    <span class="hljs-inline-lmql"><span class="inline-lmql-delim">&#39;&#39;&#39;lmql</span>
    <span class="hljs-comment"># top-level strings are prompts</span>
    <span class="hljs-string">&quot;Q: What is the answer to life, the \\
     universe and everything?&quot;</span>

    <span class="hljs-comment"># generation via (constrained) variables</span>
    <span class="hljs-string">&quot;A: <span class="hljs-placeholder">[ANSWER]</span>&quot;</span> <span class="hljs-keyword">where</span> \\
        <span class="hljs-built_in">len</span>(ANSWER) &lt; 120 <span class="hljs-keyword">and</span> STOPS_AT(ANSWER, <span class="hljs-string">&quot;.&quot;</span>)

    <span class="hljs-comment"># results are directly accessible</span>
    <span class="hljs-built_in">print</span>(<span class="hljs-string">&quot;LLM returned&quot;</span>, ANSWER)

    <span class="hljs-comment"># use typed variables for guaranteed </span>
    <span class="hljs-comment"># output format</span>
    <span class="hljs-string">&quot;The answer is <span class="hljs-placeholder">[NUM: <span class="hljs-built_in">int</span>]</span>&quot;</span>

    <span class="hljs-comment"># query programs are just functions </span>
    <span class="hljs-keyword">return</span> NUM
    <span class="inline-lmql-delim">&#39;&#39;&#39;</span></span>

<span class="hljs-comment"># so from Python, you can just do this</span>
meaning_of_life() <span class="hljs-comment"># 42</span>
</span></code></pre></div><br>`,2),h=s("p",null,[n("Created by the "),s("a",{href:"http://sri.inf.ethz.ch/",target:"_blank",rel:"noreferrer"},"SRI Lab"),n(" @ ETH Zurich and "),s("a",{href:"https://github.com/eth-sri/lmql",target:"_blank",rel:"noreferrer"},"contributors"),n(".")],-1),m=s("br",null,null,-1),u=s("div",{class:"github-star"},[s("a",{class:"github-button",href:"https://github.com/eth-sri/lmql","data-color-scheme":"light","data-show-count":"true","aria-label":"Star LMQL on GitHub"},"Star")],-1);function _(f,j,w,g,b,v){const a=t("center");return l(),o("div",null,[d,r(a,{style:{"font-size":"10pt"}},{default:c(()=>[h,m,u]),_:1})])}const S=e(p,[["render",_]]);export{y as __pageData,S as default};
