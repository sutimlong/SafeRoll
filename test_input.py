import webview

class Api:
    def log(self, text):
        print("JS LOG:", text)
        webview.windows[0].destroy()

html = """
<!DOCTYPE html>
<html><body>
<input type="file" id="file" multiple webkitdirectory style="width:100%;height:200px;border:2px solid red;">
<script>
document.getElementById('file').addEventListener('change', (e) => {
    let p = e.target.files[0].path || "NO_PATH_FOR_" + e.target.files[0].name;
    pywebview.api.log(p);
});
</script>
</body></html>
"""
webview.create_window('Test', html=html, js_api=Api())
webview.start()
