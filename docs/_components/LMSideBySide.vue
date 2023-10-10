<template>
<!-- set additional class based on 'template' attribute -->
<div class="code-by-code">
    <div class="left">
        <slot name="code"></slot>
    </div>
    <div class="right">
        <slot name="output"></slot>
    </div>
</div>
</template>

<style>
.code-by-code {
    display: flex;
    flex-direction: row;
    margin: 0;
}

.code-by-code .left, .code-by-code .right {
    flex: 1;
    padding: 0.5em;
    padding: 0;
    max-width: 50%;
}

.code-by-code .left {
    margin-right: 2.5pt;
}

.code-by-code .right {
    margin-left: 2.5pt;
}

.code-by-code .left pre {
    padding: 10pt !important;
    margin-top: -6pt;
    white-space: pre-wrap;
    font-size: 12pt;
    line-height: 1.5em;
}

@media (max-width: 750pt) {
    .code-by-code {
        flex-direction: column;
    }

    .code-by-code .left pre {
        font-size: 11pt;
    }

    .code-by-code .left, .code-by-code .right {
        max-width: 100%;
        width: 100vw;
    }
}

.code-by-code .left h2 {
    color: white;
}

.code-by-code h2 {
    display: block;
    text-align: center;
    margin-bottom: -35pt;
    font-weight: bold;
    opacity: 0.8;
    font-size: 10pt;
}

.code-by-code .language-lmql pre {
    padding-top: 30pt !important;
}

.code-by-code .promptdown, .code-by-code .promptdown.promptdown-compiled,
html.dark .code-by-code .promptdown, html.dark .code-by-code .promptdown.promptdown-compiled {
    padding-top: 30pt !important;
    font-size: 14pt;
}

.code-by-code .promptdown .promptdown-var {
    line-height: 1.5em;
}

</style>