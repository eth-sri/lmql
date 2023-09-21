(function() {
    // add if latest or dev (root)
    if (!window.location.pathname.includes('/stable/')) {
        var warning = document.createElement('DIV');
        warning.className = 'note latest';
        warning.innerHTML = '<b>Note:</b> This is the <i>latest version</i> of the documentation (preview releases or <code>main</code> branch). You can view the <a href="/en/stable/">stable version of the documentation instead </a> or make sure you are running the <a href="https://github.com/eth-sri/lmql#installing-the-latest-development-version">latest LMQL version.</a>';
        warning.classList.add('sy-alert', 'sy-alert--warning');
        document.querySelector('article[role=main]').prepend(warning);
    }
    }
)();