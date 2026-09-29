import webview
import os
import sys
import stat
import time
import shutil
import threading
from datetime import datetime

class Api:
    def __init__(self):
        self.copy_status = 'idle'
        self.copy_progress = 0.0
        self.copied_files = 0
        self.total_files = 0
        self.total_size = 0
        self.copied_size = 0
        self.speed = 0.0

    def format_size(self, size):
        if size == 0: return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.0f} {unit}" if unit in ['B', 'KB'] else f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def format_time(self, timestamp):
        dt = datetime.fromtimestamp(timestamp)
        now = datetime.now()
        if dt.date() == now.date():
            return f"今天 {dt.strftime('%H:%M')}"
        return f"{dt.year}年{dt.month}月{dt.day}日 {dt.strftime('%H:%M')}"
        
    def get_kind(self, name, is_dir):
        if is_dir:
            return "檔案夾"
        ext = os.path.splitext(name)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            return "PNG影像" if ext == '.png' else "影像"
        if ext == '.pdf': return "PDF 文件"
        if ext in ['.html', '.htm']: return "HTML文字"
        if ext == '.css': return "CSS"
        if ext == '.js': return "Javascript file"
        if ext == '.md': return "Markdown document"
        if ext in ['.mp4', '.mov', '.mxf', '.avi']: return "影片"
        return "文件"

    def play_completion_sound(self):
        import subprocess
        try:
            # Play a built-in macOS sound
            subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
        except Exception as e:
            print(f"Error playing sound: {e}")

    def play_error_sound(self):
        import subprocess
        try:
            subprocess.run(["afplay", "/System/Library/Sounds/Basso.aiff"], check=False)
        except Exception as e:
            print(f"Error playing sound: {e}")

    def get_file_info(self, path, name, is_dir=False, force_type=None):
        info = {
            'name': name,
            'path': path,
            'is_dir': is_dir,
            'type': force_type if force_type else ('folder' if is_dir else 'file'),
            'date': '--',
            'size': '--',
            'kind': self.get_kind(name, is_dir)
        }
        try:
            st = os.stat(path)
            info['date'] = self.format_time(st.st_mtime)
            if not is_dir:
                info['size'] = self.format_size(st.st_size)
        except Exception:
            pass
        return info

    def get_file_info_from_path(self, path):
        if not os.path.exists(path):
            return None
        name = os.path.basename(path)
        is_dir = os.path.isdir(path)
        return self.get_file_info(path, name, is_dir)

    def select_folder(self):
        result = webview.windows[0].create_file_dialog(webview.FileDialog.FOLDER)
        return result if result else []

    def select_files(self):
        result = webview.windows[0].create_file_dialog(webview.FileDialog.OPEN, allow_multiple=True)
        return result if result else []

    def get_root_directories(self):
        roots = []
        
        user_home = os.path.expanduser('~')
        username = os.path.basename(user_home)
        roots.append(self.get_file_info(user_home, f"使用者 ({username})", True, 'home'))
        
        if os.path.exists('/Volumes'):
            for item in os.listdir('/Volumes'):
                if not item.startswith('.') and item not in ['Macintosh HD', 'Macintosh HD - Data', 'Recovery']:
                    item_path = os.path.join('/Volumes', item)
                    if os.path.isdir(item_path):
                        roots.append(self.get_file_info(item_path, item, True, 'drive'))
        return roots

    def list_directory(self, path):
        try:
            items = []
            with os.scandir(path) as it:
                for entry in it:
                    if not entry.name.startswith('.'):
                        items.append(self.get_file_info(entry.path, entry.name, entry.is_dir()))
            
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            return items
        except Exception as e:
            print(f"Error reading {path}: {e}")
            return []

    # --- Scanning and Copying Logic ---
    def scan_files(self, paths):
        total_files = 0
        total_size = 0
        for p in paths:
            if os.path.isfile(p):
                total_files += 1
                total_size += os.path.getsize(p)
            elif os.path.isdir(p):
                for root, dirs, files in os.walk(p):
                    for f in files:
                        if not f.startswith('.'): # ignore hidden
                            fp = os.path.join(root, f)
                            total_files += 1
                            total_size += os.path.getsize(fp)
        return {'total_files': total_files, 'total_size': total_size}

    def detect_card_format(self, path):
        if not os.path.isdir(path):
            return ""
            
        try:
            items = os.listdir(path)
            
            # Sony format
            if 'XDROOT' in items or 'BPAV' in items:
                return "Sony 結構"
            if 'PRIVATE' in items:
                private_path = os.path.join(path, 'PRIVATE')
                if os.path.isdir(private_path):
                    p_items = os.listdir(private_path)
                    if 'M4ROOT' in p_items or 'SONY' in p_items or 'JVC' in p_items or 'AVCHD' in p_items:
                        return "Sony/AVCHD 結構"
            
            # RED format
            if path.upper().endswith('.RDM'):
                return "RED 結構"
            for d in items:
                if d.upper().endswith('.RDC') or d.upper().endswith('.RDM'):
                    return "RED 結構"
            
            # ARRI format (often contains .mxf, .ari files or folders like A001R2QM)
            has_arri_xml = any(d.upper().endswith('.XML') for d in items)
            has_arri_mxf = any(d.upper().endswith('.MXF') for d in items)
            if has_arri_xml and has_arri_mxf:
                return "ARRI 結構"
            
            # BMD format (braw at root or inside a folder)
            if any(d.lower().endswith('.braw') for d in items):
                return "Blackmagic 結構"
                
            # Canon / General DCIM
            if 'CONTENTS' in items or 'DCIM' in items:
                return "Canon/DCIM 結構"
                
            return ""
        except Exception:
            return ""

    def open_folder(self, path):
        import subprocess
        if os.path.exists(path):
            subprocess.run(["open", path])

    def get_copy_progress(self):
        p1 = min(100.0, (self.phase1_size / self.total_base_size * 100)) if getattr(self, 'total_base_size', 0) > 0 else 0
        p2 = min(100.0, (self.phase2_size / self.total_base_size * 100)) if getattr(self, 'total_base_size', 0) > 0 else 0
        p3 = min(100.0, (self.phase3_size / self.total_base_size * 100)) if getattr(self, 'total_base_size', 0) > 0 else 0
        
        eta = -1
        if getattr(self, 'speed', 0) > 0 and getattr(self, 'total_size', 0) > getattr(self, 'copied_size', 0):
            remaining_bytes = self.total_size - self.copied_size
            eta = remaining_bytes / (self.speed * 1024 * 1024)
            
        return {
            'status': self.copy_status,
            'progress': getattr(self, 'copy_progress', 0),
            'p1': p1,
            'p2': p2,
            'p3': p3,
            'copied_files': getattr(self, 'copied_files', 0),
            'total_files': getattr(self, 'total_files', 0),
            'speed': getattr(self, 'speed', 0),
            'eta': eta
        }

    def start_copy(self, sources, destinations, settings=None):
        if settings is None: settings = {}
        if self.copy_status == 'copying':
            return False
        
        self.copy_status = 'copying'
        self.copy_progress = 0.0
        self.copied_files = 0
        self.copied_size = 0
        self.phase1_size = 0
        self.phase2_size = 0
        self.phase3_size = 0
        self.speed = 0.0
        self.last_speed_time = time.time()
        self.last_speed_size = 0
        
        t = threading.Thread(target=self._copy_worker, args=(sources, destinations, settings))
        t.daemon = True
        t.start()
        return True

    def _update_progress(self, bytes_added, phase=1):
        self.copied_size += bytes_added
        if phase == 1: self.phase1_size += bytes_added
        elif phase == 2: self.phase2_size += bytes_added
        elif phase == 3: self.phase3_size += bytes_added
        
        if self.total_size > 0:
            self.copy_progress = min(99.9, (self.copied_size / self.total_size) * 100)
            
        current_time = time.time()
        elapsed = current_time - self.last_speed_time
        if elapsed > 0.5:
            bytes_copied_since_last = self.copied_size - self.last_speed_size
            self.speed = (bytes_copied_since_last / (1024 * 1024)) / elapsed
            self.last_speed_time = current_time
            self.last_speed_size = self.copied_size

    def _copy_worker(self, sources, destinations, settings):
        import hashlib
        import xxhash
        
        scan_result = self.scan_files(sources)
        self.total_files = scan_result['total_files']
        self.total_size = scan_result['total_size']
        self.total_base_size = self.total_size
        
        do_md5 = settings.get('use_md5', False)
        do_xxh = settings.get('use_xxhash', False)
        
        if do_md5 or do_xxh:
            self.total_size = self.total_size * 3
        
        if self.total_size == 0:
            self.copy_progress = 100
            self.copy_status = 'done'
            return

        self.last_speed_time = time.time()
        self.last_speed_size = 0
        self.copied_records = []
        
        collision_mode = settings.get('collision_mode', '自動更名加序號')
        
        # Step 0: Gather all tasks
        tasks = []
        for dest in destinations:
            if not os.path.exists(dest):
                try: os.makedirs(dest)
                except: pass
            
            for src in sources:
                if os.path.isfile(src):
                    tasks.append({'src': src, 'dest_dir': dest})
                elif os.path.isdir(src):
                    base_folder = os.path.basename(src.rstrip('/'))
                    target_dir = os.path.join(dest, base_folder)
                    for root, dirs, files in os.walk(src):
                        rel_path = os.path.relpath(root, src)
                        current_dest = os.path.join(target_dir, rel_path) if rel_path != '.' else target_dir
                        
                        if not os.path.exists(current_dest):
                            os.makedirs(current_dest)
                            
                        for f in files:
                            if not f.startswith('.'):
                                src_file = os.path.join(root, f)
                                tasks.append({'src': src_file, 'dest_dir': current_dest})
        
        # Resolve collisions and prepare task objects
        final_tasks = []
        for t in tasks:
            src = t['src']
            dest_file = os.path.join(t['dest_dir'], os.path.basename(src))
            
            if os.path.exists(dest_file):
                if collision_mode.startswith('嚴格報警並中止'):
                    print(f"Collision detected for {dest_file}. Aborting copy process.")
                    self.copy_status = 'error'
                    return
                elif collision_mode == '跳過相同 Checksum 檔案':
                    if os.path.getsize(src) == os.path.getsize(dest_file):
                        self.copied_files += 1
                        multiplier = 3 if (do_md5 or do_xxh) else 1
                        self._update_progress(os.path.getsize(src) * multiplier, phase=1)
                        record = {
                            'file': os.path.basename(src),
                            'path': dest_file,
                            'md5': 'Skipped',
                            'xxhash': 'Skipped',
                            'status': 'Skipped (Collision)'
                        }
                        self.copied_records.append(record)
                        continue # Skip this file completely
                    else:
                        counter = 1
                        name, ext = os.path.splitext(os.path.basename(src))
                        while os.path.exists(dest_file):
                            dest_file = os.path.join(t['dest_dir'], f"{name}_{counter}{ext}")
                            counter += 1
                else:
                    counter = 1
                    name, ext = os.path.splitext(os.path.basename(src))
                    while os.path.exists(dest_file):
                        dest_file = os.path.join(t['dest_dir'], f"{name}_{counter}{ext}")
                        counter += 1
                        
            final_tasks.append({
                'src': src,
                'dest': dest_file,
                'status': 'OK',
                'h_md5': None,
                'h_xxh': None
            })

        chunk_size = 1024 * 1024 * 16 

        # Phase 1: Global Copy
        for t in final_tasks:
            if self.copy_status == 'error': return
            try:
                with open(t['src'], 'rb') as fsrc, open(t['dest'], 'wb') as fdst:
                    while True:
                        buf = fsrc.read(chunk_size)
                        if not buf: break
                        fdst.write(buf)
                        self._update_progress(len(buf), phase=1)
                    fdst.flush()
                    os.fsync(fdst.fileno())
                self.copied_files += 1
            except Exception as e:
                print(f"Failed to copy {t['src']}: {e}")
                t['status'] = 'Copy Error'
                self.copy_status = 'error'

        # Phase 2: Global Source Hash
        if do_md5 or do_xxh:
            for t in final_tasks:
                if self.copy_status == 'error': return
                if t['status'] != 'OK': continue
                
                h_md5 = hashlib.md5() if do_md5 else None
                h_xxh = xxhash.xxh64() if do_xxh else None
                try:
                    with open(t['src'], 'rb') as fsrc:
                        while True:
                            buf = fsrc.read(chunk_size)
                            if not buf: break
                            if h_md5: h_md5.update(buf)
                            if h_xxh: h_xxh.update(buf)
                            self._update_progress(len(buf), phase=2)
                    t['h_md5'] = h_md5
                    t['h_xxh'] = h_xxh
                except Exception as e:
                    print(f"Failed to read src for hash {t['src']}: {e}")
                    t['status'] = 'Source Read Error'
                    self.copy_status = 'error'

        # Phase 3: Global Dest Hash
        if do_md5 or do_xxh:
            for t in final_tasks:
                if self.copy_status == 'error': return
                if t['status'] != 'OK': continue
                
                dest_md5 = hashlib.md5() if do_md5 else None
                dest_xxh = xxhash.xxh64() if do_xxh else None
                try:
                    with open(t['dest'], 'rb') as fdst:
                        while True:
                            buf = fdst.read(chunk_size)
                            if not buf: break
                            if dest_md5: dest_md5.update(buf)
                            if dest_xxh: dest_xxh.update(buf)
                            self._update_progress(len(buf), phase=3)
                            
                    if do_md5 and (not t['h_md5'] or dest_md5.hexdigest() != t['h_md5'].hexdigest()):
                        t['status'] = 'MD5 Error'
                        self.copy_status = 'error'
                    if do_xxh and (not t['h_xxh'] or dest_xxh.hexdigest() != t['h_xxh'].hexdigest()):
                        t['status'] = 'xxhash64 Error'
                        self.copy_status = 'error'
                except Exception as e:
                    print(f"Failed to read dest for hash {t['dest']}: {e}")
                    t['status'] = 'Dest Read Error'
                    self.copy_status = 'error'

        # Record all results
        for t in final_tasks:
            md5_str = t['h_md5'].hexdigest() if t['h_md5'] else 'N/A'
            xxh_str = t['h_xxh'].hexdigest() if t['h_xxh'] else 'N/A'
            record = {
                'file': os.path.basename(t['src']),
                'path': t['dest'],
                'md5': md5_str,
                'xxhash': xxh_str,
                'status': t['status']
            }
            self.copied_records.append(record)

        if settings.get('export_pdf') and len(destinations) > 0:
            self._generate_pdf_report(destinations[0])
        if settings.get('export_csv') and len(destinations) > 0:
            self._generate_csv_report(destinations[0])
            
        self.copy_progress = 100.0
        if self.copy_status != 'error':
            self.copy_status = 'done'

    def _generate_csv_report(self, dest_dir):
        try:
            import csv
            csv_path = os.path.join(dest_dir, f"SafeRoll_Report_{int(time.time())}.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Filename", "Path", "MD5", "xxhash64", "Status"])
                for rec in self.copied_records:
                    writer.writerow([rec['file'], rec['path'], rec['md5'], rec['xxhash'], rec['status']])
        except Exception as e:
            print("Failed to generate CSV:", e)

    def _generate_pdf_report(self, dest_dir):
        try:
            from fpdf import FPDF
            from fpdf.enums import XPos, YPos
            pdf = FPDF()
            pdf.add_page()
            
            pdf.add_font("ArialUnicode", style="", fname="/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
            
            pdf.set_font("ArialUnicode", size=16)
            pdf.cell(200, 10, "SafeRoll Offload Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            
            pdf.set_font("ArialUnicode", size=10)
            pdf.cell(200, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.cell(200, 10, f"Total Files: {len(self.copied_records)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(10)
            
            pdf.set_font("ArialUnicode", size=8)
            pdf.cell(45, 8, "Filename (檔名)", border=1)
            pdf.cell(65, 8, "MD5", border=1)
            pdf.cell(45, 8, "xxhash64", border=1)
            pdf.cell(35, 8, "Status (狀態)", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            for rec in self.copied_records:
                name = rec['file'] if len(rec['file']) < 25 else rec['file'][:22] + "..."
                
                row_h = 10
                
                pdf.cell(45, row_h, name, border=1)
                pdf.cell(65, row_h, rec['md5'], border=1)
                pdf.cell(45, row_h, rec['xxhash'], border=1)
                pdf.cell(35, row_h, rec['status'], border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
            report_path = os.path.join(dest_dir, f"SafeRoll_Report_{int(time.time())}.pdf")
            pdf.output(report_path)
        except Exception as e:
            print("Failed to generate PDF:", e)


def main():
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    html_file = os.path.join(base_dir, 'index.html')

    if not os.path.exists(html_file):
        print(f"Error: {html_file} not found.")
        sys.exit(1)

    api = Api()
    window = webview.create_window(
        title='SafeRoll - Secure Media Offload',
        url=html_file,
        js_api=api,
        width=1200,
        height=800,
        resizable=True,
        text_select=False,
        background_color='#2c3e50'
    )
    webview.start(http_server=True)

if __name__ == '__main__':
    main()
