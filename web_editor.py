from __future__ import annotations
import os
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)

EDITOR_HTML = """
<!doctype html>
<title>NovaAtom Web Editor</title>
<textarea id="editor" style="width:100%;height:80vh;">{{ content }}</textarea>
<div style="margin-top:10px;">
  <input id="path" type="text" value="{{ path }}" placeholder="File path" style="width:70%;"/>
  <button onclick="save()">Save</button>
</div>
<script>
function save() {
  fetch('/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({path: document.getElementById('path').value, content: document.getElementById('editor').value})
  }).then(resp => resp.json()).then(data => alert(data.message || data.status));
}
</script>
"""

@app.route('/')
def index():
    path = request.args.get('path', '')
    content = ''
    if path:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            content = ''
    return render_template_string(EDITOR_HTML, content=content, path=path)

@app.route('/save', methods=['POST'])
def save_file():
    data = request.get_json(force=True)
    path = data.get('path')
    content = data.get('content', '')
    if not path:
        return jsonify({'status': 'error', 'message': 'No path provided'}), 400
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'status': 'ok', 'message': 'File saved'})
    except Exception as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)
