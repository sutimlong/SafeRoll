import webview

class Api:
    def log(self, text):
        print("JS LOG:", text)
        webview.windows[0].destroy()

html = """
<!DOCTYPE html>
<html>
<body style="height:100vh;background:white;">
<div id="zone" style="width:100%;height:100%;border:2px dashed black;">Drop here</div>
<script>
    document.getElementById('zone').addEventListener('dragover', e => e.preventDefault());
    document.getElementById('zone').addEventListener('drop', e => {
        e.preventDefault();
        let paths = [];
        for(let i=0; i<e.dataTransfer.files.length; i++){
            paths.push(e.dataTransfer.files[i].path || "NO_PATH_FOR_" + e.dataTransfer.files[i].name);
        }
        pywebview.api.log(JSON.stringify(paths));
    });
</script>
</body>
</html>
"""
webview.create_window('Test', html=html, js_api=Api())
webview.start()
