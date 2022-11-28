# VideoFrameGrabber
Video Frame Grabber is a tool to grab frames from video using ffmpeg

## Installation
1. Установить ffmpeg
2. Установить Python
3. Запустить скрипт grab.py

### Installation ffmpeg (Windows)
1. Скачать ffmpeg для Windows: https://github.com/BtbN/FFmpeg-Builds/releases
2. Разархивировать в `C:/ffmpeg`
3. Запустить CMD от имени администратора
4. В CMD команду: `setx /m PATH "C:\ffmpeg\bin;%PATH%"`
5. Ввести в CMD команду `ffmpeg -version` чтобы убедиться что ffmpeg работает

### Installation ffmpeg (Ubuntu)
`sudo apt install ffmpeg`

## Running
`python3 main.py -v='path\to\video.mp4'`
By default, results (JPEG images) will be saved to `path\to\video\`

### Parameters
- `-v='path\to\video.mp4'` - путь до исходного видео
- `-o='path\to\frames'` - путь до папки, где будут сохранены изображения (можно опустить, тогда папка будет создана автоматически с именем как у видео в той же директории)
- `-n=1000` - количество фреймов для извлечения (можно опустить, тогда будут извлечены все фреймы)
- `-fps=30` - output FPS. The argument can only be used when --num is omitted
- `-st='00:00:00'` - время начала видео сегмента в формате ЧАСЫ:МИНУТЫ:СЕКУНДЫ (можно опустить, по умолчанию 00:00:00)
- `-et='00:00:10'` - время конца видео сегмента (можно опустить, тогда будет использовано время конца видео)
- `-r=1280x720` - разрешение извлекаемых изображений (можно опустить, тогда будет использовано реальное разрешение видео)
- `-q=2` - качество извлекаемых изображений в диапазоне от 1 до 31, где 1 - максимальное качество, а 31 - минимальное (можно опустить, по умолчанию 2)
