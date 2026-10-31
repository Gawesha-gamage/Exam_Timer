# Exam Timer

A simple countdown timer for Windows, built with Python and tkinter. Enter the exam length in hours and minutes, press Start, and it shows how much time is left.

## Features

- Large countdown clock with the time remaining in words, e.g. "1 hour 30 min remaining"
- Shows the clock time when the exam will end
- Pause, Resume, and Reset buttons
- Three beeps and a "Time is up!" message when the exam ends

## Requirements

- Windows
- Python 3.8 or newer (tkinter is included with the standard Python installer)

## Run from source

```
python exam_timer.py
```

## Build a Windows .exe

```
pip install pyinstaller
pyinstaller --onefile --windowed --name ExamTimer exam_timer.py
```

<img width="277" height="323" alt="timer ss" src="https://github.com/user-attachments/assets/bdfed3fc-c7b3-46d3-9854-f4ee3950aedb" />


The program will be in `dist\ExamTimer.exe`. It runs on other Windows computers without Python installed.
