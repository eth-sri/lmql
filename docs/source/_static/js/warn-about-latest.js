(function() {
    // add if latest or dev (root)
    if (!window.location.pathname.includes('/stable/')) {
        var warning = document.createElement('DIV');
        warning.className = 'note latest';
        warning.innerHTML = '<b>Note</b> You are viewing the <i>latest version</i> of the docs. This means some documented features may not be available in the version you are using. You can view the <a href="/en/stable/">stable version instead </a> or make sure you are running the <a href="https://github.com/eth-sri/lmql#installing-the-latest-development-version">latest LMQL version.</a>';
        warning.classList.add('sy-alert', 'sy-alert--warning');
        document.querySelector('article[role=main]').prepend(warning);
    }
    }
)();