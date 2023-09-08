def setup(app):
    app.add_js_file('js/warn-about-latest.js')

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    } 