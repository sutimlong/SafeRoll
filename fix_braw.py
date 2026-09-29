import os
def extract_braw_thumb(file_path):
    with open(file_path, 'rb') as f:
        data = f.read(1024 * 1024 * 15)
    start = 0
    found = False
    while True:
        start = data.find(b'\xff\xd8\xff', start)
        if start == -1: break
        end = data.find(b'\xff\xd9', start)
        if end != -1:
            thumb_path = f'/tmp/test_thumb_braw.jpg'
            with open(thumb_path, 'wb') as out:
                out.write(data[start:end+2])
            try:
                from PIL import Image
                img = Image.open(thumb_path)
                img.verify()
                print('Found valid JPEG at', start)
                found = True
                break
            except Exception as e:
                pass
        start += 1
    return found

print(extract_braw_thumb('/Users/tingrongsu/Desktop/論文/色灰卡測試/BMPCC/A001_09020401_C007.braw'))
