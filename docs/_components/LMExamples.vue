<script setup>
import { data as examples } from '../features/examples/examples.data.js'
import LMSideBySide from './LMSideBySide.vue'
import { ref } from 'vue'

const selectedExample = ref(examples[0].id)

</script>

<template>
<div class="examples">
    <!-- only if header is true -->
    <div style="margin-top: 60pt"/>
    <h1><slot name="title"/></h1>
    <!-- <span><slot name="description"/></span> -->

    <div class="btn-group" role="group" aria-label="Basic example">
        <button v-for="example in examples" :key="example.title" class="btn btn-primary" @click="selectedExample = example.id" :class="{ active: selectedExample === example.id }">
            {{ example.title }}
        </button>
    </div>

    <div v-html="examples.find(e => e.id === selectedExample).description" class="description"></div>

    <LMSideBySide>
        <template v-slot:code>
        <h2>LMQL</h2>
        <div v-html="examples.find(e => e.id === selectedExample).code"></div>
        </template>
        <template v-slot:output>
        <h2>Model Output</h2>
        <div v-html="examples.find(e => e.id === selectedExample).output"></div>
        </template>
    </LMSideBySide>
</div>
</template>

<style scoped>
.examples {
    margin: auto;
    max-width: 1030pt;
    margin: auto;
    padding: 0pt 8pt;
}

h1 {
    margin-bottom: 20pt;
}

.btn-group {
    margin-bottom: 1rem;
    font-size: 10pt;
    margin-top: 1em;
}

.btn {
    padding: 4pt;
    margin: 0;
    margin-right: 4pt;
    margin-bottom: 4pt;
}

.btn-group .btn.active {
    background-color: #007bff;
    color: white;
    border: 2pt solid #007bff;
}
.examples .description {
    max-width: 450pt;
    margin-bottom: 30pt;
}
</style>
<style>
.examples .description a {
    text-align: left;
    margin-left: 4pt;
    color: #007bff;
}
/* underline on hover */
.examples .description a:hover {
    text-decoration: underline;
}

.examples .right .distribution {
    position: relative;
    top: -110pt;
    margin-left: 20pt;
    width: 220pt;
}
.examples .left pre {
    margin-top: -4pt !important;
}
</style>