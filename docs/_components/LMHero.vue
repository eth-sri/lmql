<template>
  <div class="hero">
    <img src="/lmql.svg" alt="LMQL" />
    <div>
    <h1>
      <img src="/lmql.svg" alt="LMQL" /><slot name="title"></slot><br/>
    </h1>
    <h2 class="tagline">
      <slot name="subtitle"></slot>
    </h2>
    <div class="buttons">
    <a class="primary btn" href="/docs/">
      Get Started
    </a>
    <a class="btn" href="https://github.com/eth-sri/lmql#contribute')">
      Contribute
    </a> 
    </div>
    </div>
  </div>
</template>

<style scoped>
img {
  display: inline;
  height: 130pt;
  position: relative;
  top: -15pt;
  margin-right: 15pt;

  transform: translateX(0);
}

h1, h2 {
  font-size: 2.5em;
  line-height: 1.2em;
  border: none;
  margin: 0;
  padding: 0;
  font-weight: 550;
}

h2 {
  font-size: 1.2em;
  margin-top: 10pt;
  font-weight: 500;
  color: rgb(86, 86, 86);
}

html.dark h2 {
  color: rgb(183, 183, 183);
}
.hero {
  margin: auto;
  display: flex;
  margin-top: 50pt;
  width: 100%;
  max-width: 650pt;
  text-align: left;
  align-items: center;
  justify-content: center;
  padding: 20pt;
}

.hero h1>img {
  display: none;
}

</style>
<style>
html.dark .btn {
  background-color: rgb(40, 40, 40);
  border: 2pt solid rgb(40, 40, 40);
}

html.dark .btn:hover {
  border: 2pt solid rgb(60, 60, 60);
}

html.dark .btn.primary, html.dark .btn.primary:hover {
  background-color: #007bff;
  border: 2pt solid #007bff;
  color: white;
}

@media (max-width: 600px) {
  .hero h1 {
    font-size: 2.0em;
  }
  .hero h2 {
    font-size: 1.4em;
  }
  .hero {
    margin: 70pt 0pt !important;
    align-items: flex-start !important;
    max-width: 200pt;
  }

  .hero button {
    margin-top: 10pt;
    margin-bottom: 0pt;
  }

  .hero img {
    width: 40pt;
    display: none;
  }

  .hero h1>img {
    display: inline !important;
    margin: 0;
    padding: 0;
    position: relative;
    height: 1em;
    top: 3.5pt;
    margin-right: -5pt;
    margin-left: -8pt;
  }

  .hero {
    margin-top: 20pt !important;
  }
}
.buttons {
  margin-top: 20pt;
}
</style>
