var openPlaygroundElement = null;

function closePlaygroundSnippet() {
    if (openPlaygroundElement) {
        openPlaygroundElement.innerHTML = openPlaygroundElement.originalHTML;
        openPlaygroundElement.classList.remove('playground');
        openPlaygroundElement.style.height = 'auto';
        openPlaygroundElement = null;
    }
}

function openPlaygroundSnippet(link, snippet, playground_url) {
    closePlaygroundSnippet();

    // this is a that was clicked, replace parent div with iframe (temporarily)
    const container = link.parentElement;
    container.classList.add('playground');
    const iframe = document.createElement('iframe');
    iframe.src = ""
    iframe.src = playground_url + '?embed=' + snippet + ".json"
    console.log(iframe.src);
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    
    const height = Math.max(400, container.clientHeight);
    container.originalHTML = container.innerHTML;
    container.innerHTML = '';
    container.style.height = height + 'px';
    container.appendChild(iframe);

    openPlaygroundElement = container;
}