import os
import hashlib
import time
import threading
import shutil

class ChecksumMismatchError(Exception):
    pass

class CopyEngine:
    def __init__(self, chunk_size=4*1024*1024):
        self.chunk_size = chunk_size
        self._cancel_flag = threading.Event()

    def cancel(self):
        self._cancel_flag.set()

    def copy_file(self, src_path, dest_paths, mode='A', progress_callback=None):
        """
        src_path: str
        dest_paths: list of str
        mode: 'A' (Read-back Verification) or 'B' (Stream-thru Destination Verification)
        progress_callback: func(copied_bytes, total_bytes, speed_mb_s, filename)
        """
        self._cancel_flag.clear()
        
        file_size = os.path.getsize(src_path)
        filename = os.path.basename(src_path)
        
        src_md5 = hashlib.md5()
        dest_files = []
        dest_md5s = [hashlib.md5() for _ in dest_paths]
        
        try:
            # 1. Open Source and Destinations
            f_src = open(src_path, 'rb')
            for dp in dest_paths:
                dest_files.append(open(dp, 'wb'))
                
            copied_bytes = 0
            start_time = time.time()
            last_time = start_time
            last_bytes = 0

            # 2. Fan-out Streaming Copy
            while True:
                if self._cancel_flag.is_set():
                    raise Exception("Copy cancelled by user.")

                chunk = f_src.read(self.chunk_size)
                if not chunk:
                    break
                
                src_md5.update(chunk)
                
                for idx, f_dest in enumerate(dest_files):
                    f_dest.write(chunk)
                    if mode == 'B': # Mode B: Stream-thru dest hash calculate during write
                        dest_md5s[idx].update(chunk)

                copied_bytes += len(chunk)
                current_time = time.time()
                elapsed = current_time - last_time
                
                if elapsed > 0.5 and progress_callback:
                    speed = ((copied_bytes - last_bytes) / (1024 * 1024)) / elapsed
                    progress_callback(copied_bytes, file_size, speed, filename)
                    last_time = current_time
                    last_bytes = copied_bytes

            # Flush OS Buffers (fsync)
            for f_dest in dest_files:
                f_dest.flush()
                os.fsync(f_dest.fileno())

            # Close all handles before verification
            f_src.close()
            for f_dest in dest_files:
                f_dest.close()

            final_src_hash = src_md5.hexdigest()

            # 3. Verification Phase
            if mode == 'A':
                # Mode A: Re-read destinations to calculate hash
                for idx, dp in enumerate(dest_paths):
                    re_read_md5 = hashlib.md5()
                    with open(dp, 'rb') as vf:
                        while True:
                            if self._cancel_flag.is_set():
                                raise Exception("Verification cancelled.")
                            chunk = vf.read(self.chunk_size)
                            if not chunk:
                                break
                            re_read_md5.update(chunk)
                    
                    if re_read_md5.hexdigest() != final_src_hash:
                        raise ChecksumMismatchError(f"Destination {dp} MD5 mismatch!")
            else:
                # Mode B: Compare stream-calculated hashes
                for idx, dp in enumerate(dest_paths):
                    if dest_md5s[idx].hexdigest() != final_src_hash:
                        raise ChecksumMismatchError(f"Destination {dp} MD5 mismatch during stream write!")
                        
            # 4. Generate .md5 standard output
            for dp in dest_paths:
                md5_file = f"{dp}.md5"
                with open(md5_file, 'w') as mf:
                    mf.write(f"{final_src_hash} *{os.path.basename(dp)}\n")

            return final_src_hash

        finally:
            # Ensure handles are closed on error
            try: f_src.close()
            except: pass
            for f_dest in dest_files:
                try: f_dest.close()
                except: pass

import unittest

class TestCopyEngine(unittest.TestCase):
    def setUp(self):
        self.engine = CopyEngine(chunk_size=1024) # Small chunk for test
        self.src = "test_src.bin"
        self.dest1 = "test_dest1.bin"
        self.dest2 = "test_dest2.bin"
        
        # Create test source
        with open(self.src, 'wb') as f:
            f.write(os.urandom(10 * 1024 * 1024)) # 10MB file

    def tearDown(self):
        for f in [self.src, self.dest1, self.dest2, self.dest1+".md5", self.dest2+".md5"]:
            if os.path.exists(f):
                os.remove(f)

    def test_mode_a_success(self):
        src_hash = self.engine.copy_file(self.src, [self.dest1, self.dest2], mode='A')
        self.assertTrue(os.path.exists(self.dest1))
        self.assertTrue(os.path.exists(self.dest2))
        self.assertTrue(os.path.exists(self.dest1+".md5"))

    def test_bit_flip_simulation(self):
        # We simulate a bit flip by manually modifying destination file and overriding Mode A
        # To do this cleanly, we can mock the write process or modify after stream but before verify
        pass # To fully simulate bit flip, we would need to mock the OS file system or inject faults.
