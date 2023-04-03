var openPlaygroundElement = null;

function getPlaygroundUrl() {
    const host = window.location.host;
    if (host === "docs.lmql.ai") {
        return "https://lmql.ai/playground";
    } else if (host.startsWith("localhost") || host.startsWith("127.0.0.1")) {
        return "http://localhost:3000/playground";
    } else {
        return "https://lbeurerkellner.github.io/green-gold-dachshund-web/playground";
    }
}

function closePlaygroundSnippet() {
    if (openPlaygroundElement) {
        openPlaygroundElement.innerHTML = openPlaygroundElement.originalHTML;
        openPlaygroundElement.classList.remove('playground');
        openPlaygroundElement.style.height = 'auto';

        // show model output div if it exists
        let next = openPlaygroundElement.nextElementSibling;
        while(next.tagName !== 'DIV' && next) {
            next = next.nextElementSibling;
        }

        if (next.classList.contains('highlight-model-output')) {
            next.style.display = 'block';
        }

            openPlaygroundElement = null;
        }
}

function openPlaygroundSnippet(link, snippet) {
    closePlaygroundSnippet();

    const playground = getPlaygroundUrl();
    console.log("playground url: " + playground);

    // this is a that was clicked, replace parent div with iframe (temporarily)
    const container = link.parentElement;
    container.classList.add('playground');
    const iframe = document.createElement('iframe');
    iframe.src = ""
    iframe.src = playground + '?embed=' + snippet + ".json"
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    
    const height = Math.max(400, container.clientHeight);
    container.originalHTML = container.innerHTML;
    container.innerHTML = '';
    container.style.height = height + 'px';
    container.appendChild(iframe);

    // hide the model output div if it exists
    let next = container.nextElementSibling;
    while(next.tagName !== 'DIV' && next) {
        next = next.nextElementSibling;
    }

    if (next.classList.contains('highlight-model-output')) {
        next.style.display = 'none';
    }

    openPlaygroundElement = container;
}