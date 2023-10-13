import{_ as t,o as a,c as i,Q as n,k as e,a as s}from"./chunks/framework.4636910e.js";const v=JSON.parse('{"title":"Inference Certificates","description":"","frontmatter":{},"headers":[],"relativePath":"docs/lib/inference-certificates.md","filePath":"docs/lib/inference-certificates.md"}'),c={name:"docs/lib/inference-certificates.md"},l=n(`<h1 id="inference-certificates" tabindex="-1">Inference Certificates <a class="header-anchor" href="#inference-certificates" aria-label="Permalink to &quot;Inference Certificates&quot;">​</a></h1><div class="subtitle">Trace and reproduce LLM inference results.</div><p>An inference certificate is a simple data structure that records essential information needed to reproduce an inference result. Certificates can be generated for any LLM call that happens in a LMQL context.</p><p>The primary use case of certificates is to provide a way to document, trace and reproduce LLM inference results by recording the <em>exact (tokenized) prompts</em> and information on the <em>environment and generation parameters</em>.</p><h2 id="obtaining-certificates" tabindex="-1">Obtaining Certificates <a class="header-anchor" href="#obtaining-certificates" aria-label="Permalink to &quot;Obtaining Certificates&quot;">​</a></h2><p>To obtain a certificate, specify <code>certificate=True</code> as an argument to your current generation context (e.g. a query function or <code>lmql.generate</code> call).</p><p>This will produce a certificate including all LLM calls made during the execution of the context. Setting <code>certificate=True</code> just prints the resulting data structure to the console. To save the certificate to a file, specify a path as the <code>certificate</code> argument.</p><p>To illustrate, consider the following code that produces a certificate and saves it to the file <code>my-certificate.json</code> in the current working directory:</p><div class="language-python vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">python</span><pre class="hljs"><code><span class="line"><span class="hljs-comment"># define a simple query function</span>
say_hello = lmql.F(<span class="hljs-string">&quot;Greet the world:<span class="hljs-placeholder">[GREETING]</span>&quot;</span>)

<span class="hljs-comment"># call and save certificate</span>
say_hello(certificate=<span class="hljs-string">&quot;my-certificate.json&quot;</span>)
</span></code></pre></div>`,9),r=e("div",{class:"info custom-block"},[e("p",{class:"custom-block-title"},"Certificate File"),e("div",{class:"language-truncated vp-adaptive-theme"},[e("button",{title:"Copy Code",class:"copy"}),e("span",{class:"lang"},"truncated"),e("pre",{class:"hljs"},[e("code",null,[e("span",{class:"line"},[s(`{
    `),e("span",{class:"hljs-string"},'"name"'),s(": "),e("span",{class:"hljs-string"},'"say_hello"'),s(`,
    `),e("span",{class:"hljs-string"},'"type"'),s(": "),e("span",{class:"hljs-string"},'"lmql.InferenceCertificate"'),s(`,
    `),e("span",{class:"hljs-string"},'"lmql.version"'),s(": "),e("span",{class:"hljs-string"},'"0.999999 (dev) (build on dev, commit dev)"'),s(`,
    `),e("span",{class:"hljs-string"},'"time"'),s(": "),e("span",{class:"hljs-string"},'"2023-10-02 23:37:55 +0200"'),s(`,
    `),e("span",{class:"hljs-string"},'"events"'),s(`: [
        {
            `),e("span",{class:"hljs-string"},'"name"'),s(": "),e("span",{class:"hljs-string"},'"openai.Completion"'),s(`,
            `),e("span",{class:"hljs-string"},'"data"'),s(`: {
                `),e("span",{class:"hljs-string"},'"endpoint"'),s(": "),e("span",{class:"hljs-string"},'"https://api.openai.com/v1/completions"'),s(`,
                `),e("span",{class:"hljs-string"},'"headers"'),s(`: {
                    `),e("span",{class:"hljs-string"},'"Authorization"'),s(": "),e("span",{class:"hljs-string"},'"<removed>"'),s(`,
                    `),e("span",{class:"hljs-string"},'"Content-Type"'),s(": "),e("span",{class:"hljs-string"},'"application/json"'),s(`
                },
                `),e("span",{class:"hljs-string"},'"tokenizer"'),s(": "),e("span",{class:"hljs-string"},`"<LMQLTokenizer 'gpt-3.5-turbo-instruct' using tiktoken <Encoding 'cl100k_base'>>"`),s(`,
                `),e("span",{class:"hljs-string"},'"kwargs"'),s(`: {
                    `),e("span",{class:"hljs-string"},'"model"'),s(": "),e("span",{class:"hljs-string"},'"gpt-3.5-turbo-instruct"'),s(`,
                    `),e("span",{class:"hljs-string"},'"prompt"'),s(`: [
                        `),e("span",{class:"hljs-string"},'"Greet the world:"'),s(`
                    ],
                    `),e("span",{class:"hljs-string"},'"max_tokens"'),s(": "),e("span",{class:"hljs-number"},"64"),s(`,
                    `),e("span",{class:"hljs-string"},'"temperature"'),s(": "),e("span",{class:"hljs-number"},"0"),s(`,
                    `),e("span",{class:"hljs-string"},'"logprobs"'),s(": "),e("span",{class:"hljs-number"},"1"),s(`,
                    `),e("span",{class:"hljs-string"},'"user"'),s(": "),e("span",{class:"hljs-string"},'"lmql"'),s(`,
                    `),e("span",{class:"hljs-string"},'"stream"'),s(`: true,
                    `),e("span",{class:"hljs-string"},'"echo"'),s(`: true
                },
                `),e("span",{class:"hljs-string"},[s('"result'),e("span",{class:"hljs-placeholder"},[s("["),e("span",{class:"hljs-number"},"0"),s("]")]),s('"')]),s(": "),e("span",{class:"hljs-string"},`"Greet the world:\\n\\nHello world! It's nice to meet you. I am excited to explore and learn from all the different cultures, people, and experiences you have to offer. Let's make the most of our time together and create meaningful connections. Cheers to new beginnings!"`),s(`
            }
        },
        {
            `),e("span",{class:"hljs-string"},'"name"'),s(": "),e("span",{class:"hljs-string"},'"lmql.LMQLResult"'),s(`,
            `),e("span",{class:"hljs-string"},'"data"'),s(`: [
                {
                    `),e("span",{class:"hljs-string"},'"prompt"'),s(": "),e("span",{class:"hljs-string"},`"Greet the world:\\n\\nHello world! It's nice to meet you. I am excited to explore and learn from all the different cultures, people, and experiences you have to offer. Let's make the most of our time together and create meaningful connections. Cheers to new beginnings!"`),s(`,
                    `),e("span",{class:"hljs-string"},'"variables"'),s(`: {
                        `),e("span",{class:"hljs-string"},'"GREETING"'),s(": "),e("span",{class:"hljs-string"},`"\\n\\nHello world! It's nice to meet you. I am excited to explore and learn from all the different cultures, people, and experiences you have to offer. Let's make the most of our time together and create meaningful connections. Cheers to new beginnings!"`),s(`
                    },
                    `),e("span",{class:"hljs-string"},'"distribution_variable"'),s(`: null,
                    `),e("span",{class:"hljs-string"},'"distribution_values"'),s(`: null
                }
            ]
        }
    ],
    `),e("span",{class:"hljs-string"},'"metrics"'),s(`: {
        `),e("span",{class:"hljs-string"},'"openai"'),s(`: {
            `),e("span",{class:"hljs-string"},'"requests"'),s(": "),e("span",{class:"hljs-number"},"1"),s(`,
            `),e("span",{class:"hljs-string"},'"batch_size"'),s(": "),e("span",{class:"hljs-number"},"1"),s(`,
            `),e("span",{class:"hljs-string"},'"tokens"'),s(": "),e("span",{class:"hljs-number"},"57"),s(`
        }
    }
}
`)])])])]),e("button",{class:"btn expand",onclick:"this.parentElement.classList.toggle('show')"}," Show All ")],-1),o=n(`<p><strong>Prompts and Generation Parameters</strong> A certificate contains the parameters of all LLM inference calls made during execution. For API-based LLMs, this includes the request headers and parameters, as well as the response. For local LLMs, it includes the tokenized prompt and the exact parameters and configuration used to instantiate the model.</p><p><strong>Metrics</strong> The certificate also includes basic metrics on the inference calls made. For API-based LLMs, this includes the number of requests made, the batch size and the number of tokens used.</p><p><strong>Environment</strong> The certificate also captures information on the environment, including the LMQL version and the version of the backend libraries in use.</p><div class="warning custom-block"><p class="custom-block-title">Redacting Sensitive Information</p><p>By default, parameters such as the OpenAI key are removed from inference certificates. Note however, that certificates may still contain sensitive information such as the prompt used for generation or information on the environment. To remove additional fields from the generated certificates, use the <code>lmql.runtime.tracing.add_extra_redact_keys</code> function.</p></div><h2 id="generating-certificates-for-multiple-calls-in-a-context" tabindex="-1">Generating Certificates for Multiple Calls In a Context <a class="header-anchor" href="#generating-certificates-for-multiple-calls-in-a-context" aria-label="Permalink to &quot;Generating Certificates for Multiple Calls In a Context&quot;">​</a></h2><p>To generate a certificate for multiple generations in a given context, the <code>lmql.traced</code> context manager can be used:</p><div class="language-python vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">python</span><pre class="hljs"><code><span class="line"><span class="hljs-keyword">with</span> lmql.traced(<span class="hljs-string">&quot;my-context&quot;</span>) <span class="hljs-keyword">as</span> t:
    <span class="hljs-comment"># call a query </span>
    res1 = say_hello(verbose=<span class="hljs-literal">True</span>)

    <span class="hljs-comment"># call lmql.generate</span>
    res2 = lmql.generate_sync(<span class="hljs-string">&quot;Greet the animals of the world:&quot;</span>, max_tokens=<span class="hljs-number">10</span>, verbose=<span class="hljs-literal">True</span>)

    <span class="hljs-comment"># generate a combined certificate for</span>
    <span class="hljs-comment"># all calls made in this context</span>
    <span class="hljs-built_in">print</span>(lmql.certificate(t))
</span></code></pre></div><p>This produces one certificate for all calls made in the defined context, where each query is represented as a separate item in the list of <code>children</code> certificates. Recorded events are are nested in child certificates. Additionally, an aggregated <code>metrics</code> object ranging over all (recursive) calls is included in the top-level certificate.</p><h2 id="certificate-callbacks-and-return-values" tabindex="-1">Certificate Callbacks And Return Values <a class="header-anchor" href="#certificate-callbacks-and-return-values" aria-label="Permalink to &quot;Certificate Callbacks And Return Values&quot;">​</a></h2><p>As an alternative to directly writing certificates to a file, certificates can also be handled via a callback or returned as a function return value.</p><p>To specify a callback function that is called with the generated certificate as an argument, specify it as the <code>certificate=&lt;FCT&gt;</code> argument.</p><p>The callback is provided with a single <code>certificate</code> object, which is of type <code>lmql.InferenceCertificate</code>. The certificate can be directly serialized to JSON using string conversion, i.e., <code>str(certificate)</code>.</p>`,12),p=[l,r,o];function d(h,u,f,m,g,j){return a(),i("div",null,p)}const _=t(c,[["render",d]]);export{v as __pageData,_ as default};
