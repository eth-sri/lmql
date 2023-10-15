<script setup>
defineProps(['template', 'new'])
</script>

<template>
<!-- set additional class based on 'template' attribute -->
<div class="feature" :class="template">
    <div>
    <h1>
        <slot></slot>
        <span v-if="new" class="badge">NEW</span>
    </h1>
    <p>
        <slot name="description"></slot>
    </p>
    </div>
    <code class="reveal"><slot name="code"></slot></code>
</div>
</template>

<style scoped>
.feature {
  margin: auto;
  display: flex;
  flex-direction: row;
  margin-top: 100pt;
  width: 100%;
  max-width: 750pt;
  text-align: left;
  align-items: center;
  padding: 20pt;
}

.feature>div:first-child {
    margin-right: 20pt;
    flex: 2;
}

.feature code {
    font-size: 1.0em;
    padding: 10pt;
    border-radius: 8px;
    padding-top: -10pt;
}

.feature code {
    max-width: 60%;
    font-size: 0.8em;
}

.feature code pre {
    margin: 0;
    padding: 10pt;
}

.feature code {
    transform: translateX(0);
    animation: slidefade 0.5s;
    animation-fill-mode: forwards;
}

.feature.code {
    display: flex;
    margin-top: -20pt;
}

</style>
<style>
.feature .btn {
    margin-top: 20pt;
}

.feature code span.lang {
    display: none !important;
}
.feature code pre {
    margin-top: -15pt !important;
    line-break: anywhere;
    overflow-x: scroll;
    -webkit-overflow-scrolling: touch;
    -ms-overflow-style: none;
    padding: 15pt;
}

/* hide scroll bars */
.feature code pre::-webkit-scrollbar {
    display: none;
}


@keyframes slidefade {
    from { opacity: 0; transform: translateX(20pt); }
    to   { opacity: 1; transform: translateX(0); }
}

@keyframes slidefadeleft {
    from { opacity: 0; transform: translateX(-20pt); }
    to   { opacity: 1; transform: translateX(0); }
}

/* every other feature is reversed */
div:nth-child(even)>.feature {
    flex-direction: row-reverse;
}

div:nth-child(even)>.feature>code {
    margin-right: 30pt;
    animation: slidefadeleft 0.2s;
    animation-fill-mode: forwards;
}

.feature pre.promptdown,
.feature pre.promptdown.promptdown-compiled,
html.dark .feature pre.promptdown,
html.dark .feature pre.promptdown.promptdown-compiled {
    width: 320pt;
    max-width: calc(50vw - 30pt);
    overflow-x: scroll;
    min-height: 180pt;
    position: relative;
    top: 20pt;
    white-space: pre-wrap;
    line-break: anywhere;

    /* first line indent */
    text-indent: 10pt !important;
    line-height: 1.5em !important;
}

.feature.left>code {
    display: none;
}

.feature.middle {
    position: relative;
    width: 520pt;
    max-width: 100vw;
}

.feature.middle>code {
    display: none;
}

.feature.middle {
    text-align: center;
}

.cards {
    display: flex;
    flex-direction: row;
    /* break rows */
    flex-wrap: wrap;
    justify-content: center;
    margin-top: 40pt;
    margin-bottom: 40pt;
}

.cards>a {
    border-radius: 5pt;
    border: 1pt solid rgb(192, 190, 190);
    margin: 0pt 2.5pt;
    padding: 10pt;
    padding-top: 30pt;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    line-height: 1.2;
    font-weight: bold;
    width: 100pt;
    height: 100pt;
    margin-top: 5pt;
    transition: all 0.1s;
    cursor: pointer;
    text-align: center;
}

.cards img {
    position: relative;
    bottom: -5pt;
}

.cards h1 {
    margin-top: 0pt;
}

.cards>a:hover {
    background-color: rgb(240, 240, 240);
    transform: scale(1.05);
}

html.dark .cards>a {
    border: 1pt solid rgb(50, 50, 50);
}

html.dark .cards>a:hover {
    background-color: rgba(50, 50, 50, 0.106);
}

.cards>a img {
    width: 50pt;
    height: 40pt;
    margin: auto;
    display: block;
    margin-top: -10pt;
    padding-bottom: 10pt;
}

.cards>a h1 {
    font-weight: bold !important;
    font-size: 10pt;
}


.feature.middle pre {
    text-align: left;
    padding: 10pt;
}

@media (max-width: 700px) {
    .feature {
        flex-direction: column !important;
        margin-top: 20pt !important;
        width: calc(100vw - 15pt) !important;
        
    }

    .feature>div:first-child {
        margin-right: 0;
    }

    .feature.code {
        width: 100vw !important;
    }

    .feature>code {
        margin-right: 0;
        margin-top: 20pt;
        width: 100vw !important;
        max-width: 100vw !important;
        margin-left: 0pt;
        border-radius: 0;
        box-shadow: none !important;
        border: none !important;
        padding-left: 20pt !important;
        margin-right: 0 !important;
    }

    .feature.middle {
        width: calc(100vw - 10pt);
        padding: 0pt 10pt !important;
    }

    .feature.middle>div {
        max-width: 100vw;
        text-align: left;
        margin: 0 !important;
    }

    .feature pre.promptdown,
    .feature pre.promptdown.promptdown-compiled,
    html.dark .feature pre.promptdown,
    html.dark .feature pre.promptdown.promptdown-compiled {
        width: calc(100vw - 30pt);
        max-width: calc(100vw - 30pt);
        font-size: 12pt;
        margin-left: -5pt;
        padding: 0;
        margin-right: 0pt;
        
    }

    .feature pre.promptdown .promptdown-var {
        line-break: word !important;
    }
}

.feature.code pre {
    flex: 1;
    margin: 0pt;
    padding: 20pt;
    white-space: pre-wrap;

    box-shadow: 0pt 0pt 80pt rgba(0, 0, 0, 0.272);
    font-size: 10pt;
}


.feature.code>code {
    display: none;
}

.feature.code>div:first-child {
    margin-right: 0;
}

.feature.code a {
    text-decoration: underline;
}

.feature.code {
    margin-top: 10pt;
    max-width: 480pt;
    font-size: 12pt;
    line-height: 1.4;
    z-index: 100;
}

@media (max-width: 800px) {
    .feature.code {
        margin-top: -30pt !important;
        font-size: 11pt;
        padding: 2pt !important;
        max-width: calc(100vw - 20pt);
        overflow: hidden !important;
    }

    .feature.code pre {
        white-space: pre;
        margin: 0;
        padding: 10pt 10pt;
        font-size: 9pt;
        max-width: calc(100vw - 20pt);
        box-shadow: none;
        overflow-x: scroll;
    }

    .feature.code pre .window-controls {
        display: none;
    }
}

@media (max-width: 600px) {
    .feature.code {
        margin-top: -90pt !important;
    }
}

</style>