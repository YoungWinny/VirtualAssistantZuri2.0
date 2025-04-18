import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import speech_recognition as sr
import os
import shutil
import pickle
import fnmatch
import subprocess
import pyttsx3
import re
import whisper
import threading
from tkinter.font import Font

# Initialize TTS and Whisper
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Optional, set speech rate if needed
engine.setProperty('volume', 1)  # Optional, set volume to max
model_whisper = whisper.load_model("base")

# Load trained model
with open('file_assistant_model.pkl', 'rb') as f:
    model = pickle.load(f)

# --- Utility Functions ---

def update_status(text, status):
    status_label.config(text=text)
    color_map = {"idle": "#86868b", "active": "#4CAF50", "processing": "#FFC107"}
    status_indicator.itemconfig(status_circle, fill=color_map.get(status, "#86868b"))
    root.update()


def speak(text):
    display_message(text, sender="assistant")  # Display the message first
    root.after(200, lambda: start_speech(text))  # Wait a bit before starting speech
  

def start_speech(text):
    engine.say(text)  # Start speaking after the UI has updated
    engine.runAndWait()  # Ensure speech is completed before continuing

def display_message(text, sender="user"):
    message_frame = tk.Frame(scrollable_frame, bg="#f0f4f8", pady=5)
    message_frame.pack(fill=tk.X, padx=10)

    if sender == "user":
        bubble_frame = tk.Frame(message_frame, bg="#dcf8c6")
        bubble_frame.pack(side=tk.RIGHT, anchor=tk.E, padx=(50, 0))
    else:
        bubble_frame = tk.Frame(message_frame, bg="#ffffff")
        bubble_frame.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 50))

        avatar_label = tk.Label(bubble_frame, text="🤖", font=("Segoe UI", 14), bg="#ffffff")
        avatar_label.pack(side=tk.LEFT, padx=(10, 5), pady=10)

    message_label = tk.Label(bubble_frame, 
                             text=text, 
                             font=MESSAGE_FONT, 
                             bg=bubble_frame["bg"], 
                             fg="#333333",
                             wraplength=450, 
                             justify=tk.LEFT,
                             padx=10, 
                             pady=10)
    message_label.pack(side=tk.RIGHT if sender == "user" else tk.LEFT)

    root.update_idletasks()
    chat_canvas.yview_moveto(1.0)

def get_voice_input():
    update_status("Listening...", "active")
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        speak("I'm listening.")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
    with open("temp_audio.wav", "wb") as f:
        f.write(audio.get_wav_data())
    update_status("Processing speech...", "processing")
    result = model_whisper.transcribe("temp_audio.wav")
    command = result["text"]
    display_message(f"{command} (voice)", sender="user")
    update_status("Ready", "idle")
    return command

def classify_intent(command):
    try:
        update_status("Analyzing...", "processing")
        intent = model.predict([command])[0]
        update_status("Ready", "idle")
        return intent
    except Exception:
        speak("I couldn't understand that.")
        update_status("Ready", "idle")
        return None

def find_file_or_folder(name, file_type='file'):
    for drive in ['C:\\', 'D:\\', 'E:\\']:
        for root, dirs, files in os.walk(drive):
            try:
                if file_type == 'file':
                    for file in files:
                        if fnmatch.fnmatch(file.lower(), f"*{name.lower()}*"):
                            return os.path.join(root, file)
                elif file_type == 'folder':
                    for folder in dirs:
                        if fnmatch.fnmatch(folder.lower(), f"*{name.lower()}*"):
                            return os.path.join(root, folder)
            except:
                continue
    return None

def extract_filename(command, extensions=None):
    if extensions is None:
        extensions = ['mp3', 'mp4', 'pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg','pptx','json','csv','xlsx']
    command = command.lower()
    for word in ['open', 'play', 'delete', 'permanently', 'search', 'file', 'folder', 'move', 'copy']:
        command = command.replace(word, '')
    pattern = r'([\w\s\-]+?)\s*(\d*)\s*\.(' + '|'.join(extensions) + r')'
    match = re.search(pattern, command)
    if match:
        name, num, ext = match.groups()
        return (name + num + '.' + ext).replace(' ', '')
    return None

def open_path(path):
    if os.name == 'nt':
        os.startfile(path)
    else:
        subprocess.call(('xdg-open', path))

def copy_file(source, destination):
    try:
        shutil.copy(source, destination)
        speak(f"Copied to {destination}")
    except Exception as e:
        speak(f"Couldn't copy: {e}")

def move_file(source, destination):
    try:
        shutil.move(source, destination)
        speak(f"Moved to {destination}")
    except Exception as e:
        speak(f"Couldn't move: {e}")

def perform_action(intent, command):
    update_status("Working on it...", "processing")
    command = command.lower()
    filename = extract_filename(command)

    if intent in ['open_file', 'open_media']:
        if filename:
            path = find_file_or_folder(filename)
            speak(f"Opening {filename}" if path else "File not found.")
            if path: open_path(path)

    elif intent == 'open_folder':
        folder_name = command.replace("open folder", "").strip()
        path = find_file_or_folder(folder_name, 'folder')
        speak(f"Opening folder {folder_name}" if path else "Folder not found.")
        if path: open_path(path)

    elif intent == 'play_music':
        path = find_file_or_folder('.mp3')
        speak("Playing music." if path else "No music found.")
        if path: open_path(path)

    elif intent == 'play_movie':
        path = find_file_or_folder('.mp4')
        speak("Enjoy!" if path else "No movie found.")
        if path: open_path(path)

        elif intent == 'search_file':
            path = find_file_or_folder(filename)
        if path:
            speak(f"File found at path = {path}")
        else:
             speak("File not found.")


    elif intent == 'delete_file':
        try:
            import send2trash
            path = find_file_or_folder(filename)
            if path:
                send2trash.send2trash(path)
                speak(f"{filename} was sent to Recycle Bin.")
            else:
                speak("Couldn't find the file.")
        except:
            os.remove(path)
            speak("Deleted permanently.")

    elif intent == 'delete_forever':
        path = find_file_or_folder(filename)
        if path:
            os.remove(path)
            speak(f"{filename} has been permanently deleted.")
        else:
            speak("Couldn't find the file.")

    elif intent == 'copy_file':
        destination = filedialog.askdirectory(title="Select destination for copy")
        if filename and destination:
            path = find_file_or_folder(filename)
            if path: copy_file(path, destination)
            else: speak("Couldn't find the file.")

    elif intent == 'move_file':
        destination = tk.filedialog.askdirectory(title="Select destination for move")
        if filename and destination:
            path = find_file_or_folder(filename)
            if path: move_file(path, destination)
            else: speak("Couldn't find the file.")
    else:
        speak("Intent recognized but not implemented.")
    
    update_status("Ready", "idle")

def process_text_command():
    command = entry.get().strip()
    if not command:
        return
    entry.delete(0, tk.END)
    display_message(command, sender="user")
    threading.Thread(target=lambda: perform_action(classify_intent(command), command)).start()


def process_voice_command():
    def task():
        command = get_voice_input()
        intent = classify_intent(command)
        perform_action(intent, command)
    threading.Thread(target=task).start()


def on_canvas_configure(event):
    chat_canvas.itemconfig(chat_window, width=event.width)

# --- GUI Setup ---

root = tk.Tk()
root.title("Smart Virtual Assistant")
root.geometry("850x650")
root.configure(bg="#f0f4f8")

MESSAGE_FONT = Font(family="Segoe UI", size=11)

# Status bar
status_frame = tk.Frame(root, bg="#f0f4f8")
status_frame.pack(fill=tk.X, pady=5)

status_label = tk.Label(status_frame, text="Ready", bg="#f0f4f8", fg="#444", font=("Segoe UI", 10))
status_label.pack(side=tk.LEFT, padx=10)

status_indicator = tk.Canvas(status_frame, width=15, height=15, bg="#f0f4f8", highlightthickness=0)
status_circle = status_indicator.create_oval(2, 2, 13, 13, fill="#86868b")
status_indicator.pack(side=tk.LEFT)

# Chat area
chat_frame = ttk.Frame(root, style='Chat.TFrame')
chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
chat_canvas = tk.Canvas(chat_frame, bg="#e5e5ea", highlightthickness=0)
scrollbar = ttk.Scrollbar(chat_frame, orient=tk.VERTICAL, command=chat_canvas.yview)
scrollable_frame = tk.Frame(chat_canvas, bg="#e5e5ea")

chat_window = chat_canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
chat_canvas.configure(yscrollcommand=scrollbar.set)
scrollable_frame.bind("<Configure>", lambda e: chat_canvas.configure(scrollregion=chat_canvas.bbox("all")))
chat_canvas.bind("<Configure>", on_canvas_configure)

chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Input section
input_frame = tk.Frame(root, bg="#e5e5ea")
input_frame.pack(fill=tk.X, padx=10, pady=10)

entry = ttk.Entry(input_frame, font=("Segoe UI", 11))
entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=6)

mic_button = ttk.Button(input_frame, text="🎤", command=process_voice_command)
mic_button.pack(side=tk.RIGHT, padx=5)

send_button = ttk.Button(input_frame, text="Send", command=process_text_command)
send_button.pack(side=tk.RIGHT)

def greet_user():
    speak("Hi, I'm Zuri, your virtual assistant. How can I help you?")

# Run the greeting in a separate thread
greet_user()
update_status("Ready", "idle")
root.mainloop()

