from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
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
from datetime import datetime
from tkinter.font import Font
import send2trash

# ================== Database Models ==================
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    commands = relationship('CommandHistory', back_populates='user')

class CommandHistory(Base):
    __tablename__ = 'command_history'
    id = Column(Integer, primary_key=True)
    command_text = Column(Text)
    intent = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='commands')

# ================== Core Application Classes ==================
class DatabaseManager:
    def __init__(self, db_url='sqlite:///assistant.db'):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    def get_session(self):
        return self.Session()

class FileManager:
    @staticmethod
    def get_prioritized_directories():
        home = os.path.expanduser('~')
        return [
            os.path.join(home, 'Desktop'),
            os.path.join(home, 'Documents'),
            os.path.join(home, 'Downloads'),
            os.path.join(home, 'Pictures'),
            os.path.join(home, 'Music'),
            os.path.join(home, 'Videos'),
            home,
            os.path.join(home, 'OneDrive'),
            os.path.join(home, 'Dropbox'),
        ]

    @staticmethod
    def find_file_or_folder(name, file_type='file'):
        for directory in FileManager.get_prioritized_directories():
            if not os.path.exists(directory):
                continue
            try:
                for root, dirs, files in os.walk(directory):
                    try:
                        if file_type == 'file':
                            for file in files:
                                if fnmatch.fnmatch(file.lower(), f"*{name.lower()}*"):
                                    return os.path.join(root, file)
                        elif file_type == 'folder':
                            for folder in dirs:
                                if fnmatch.fnmatch(folder.lower(), f"*{name.lower()}*"):
                                    return os.path.join(root, folder)
                    except PermissionError:
                        continue
            except Exception:
                continue

        drives = ['C:\\', 'D:\\', 'E:\\'] if os.name == 'nt' else ['/']
        for drive in drives:
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
                except PermissionError:
                    continue
                except Exception:
                    continue
        return None

    @staticmethod
    def open_path(path):
        if os.path.exists(path):
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.call(('xdg-open', path))
            return True
        return False

    @staticmethod
    def copy_file(source, destination):
        try:
            shutil.copy(source, destination)
            return True, f"Copied to {destination}"
        except Exception as e:
            return False, f"Couldn't copy: {e}"

    @staticmethod
    def move_file(source, destination):
        try:
            # Validate source
            if not os.path.exists(source):
                return False, "Source file does not exist"
                
            # Validate destination
            if not os.path.isdir(destination):
                return False, "Destination is not a valid directory"
                
            # Construct destination path
            dest_path = os.path.join(destination, os.path.basename(source))
            
            # Check for existing file
            if os.path.exists(dest_path):
                return False, "File already exists in destination"
            
            # Perform atomic move
            shutil.move(source, dest_path)
            
            # Verify move succeeded
            if os.path.exists(dest_path) and not os.path.exists(source):
                return True, "File moved successfully"
            return False, "Move operation incomplete"
            
        except PermissionError:
            return False, "Permission denied - check file/directory permissions"
        except shutil.Error as e:
            return False, f"System error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
        

    @staticmethod
    def delete_file(path, permanent=False):
        try:
            if permanent:
                os.remove(path)
                return True, "Permanently deleted"
            send2trash.send2trash(path)
            return True, "Sent to Recycle Bin"
        except Exception as e:
            return False, f"Deletion failed: {e}"

class SpeechManager:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1)
        self.recognizer = sr.Recognizer()
        self.whisper_model = whisper.load_model("base")

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    def transcribe_audio(self, audio_path):
        return self.whisper_model.transcribe(audio_path)

# class CommandProcessor:
#     def __init__(self):
#         with open('file_assistant_model.pkl', 'rb') as f:
#             self.model = pickle.load(f)
#         self.file_manager = FileManager()
#         self.extensions = ['mp3', 'mp4', 'pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg','pptx','doc','json','csv','xlsx']

#     def extract_filename(self, command):
#         command = command.lower()
#         for word in ['open', 'play', 'delete', 'permanently', 'search', 'file', 'folder', 'move', 'copy']:
#             command = command.replace(word, '')
#         pattern = r'([\w\s\-]+?)\s*(\d*)\s*\.(' + '|'.join(self.extensions) + r')'
#         match = re.search(pattern, command)
#         if match:
#             name, num, ext = match.groups()
#             return (name + num + '.' + ext).replace(' ', '')
#         return None

class CommandProcessor:
    def __init__(self):
        with open('file_assistant_model.pkl', 'rb') as f:
            self.model = pickle.load(f)
        self.file_manager = FileManager()
        self.extensions = ['mp3', 'mp4', 'pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg']

    def extract_filename(self, command):
        # Remove common command phrases while preserving filename structure
        command = command.lower()
        command = re.sub(r'\b(open|play|delete|permanently|search|file|folder|move|copy|the|a|an)\b', '', command)
        command = re.sub(r'\s+', ' ', command).strip()  # Clean extra spaces
        
        # Match various filename patterns with improved regex
        pattern = r'''
            (?:.*?)          # Any preceding text
            (                 # Capture group 1: filename
                (?:           # Either:
                    [^\s]+    # - Single word filename with extension
                    \.        # - Explicit extension separator
                    \w{2,4}   # - File extension (2-4 chars)
                ) | (?:       # Or:
                    [\w\s-]+  # - Multi-word filename
                    (?:       # - Optional extension
                        \.    # - Extension separator
                        \w{2,4}
                    )?
                )
            )
            (?:\s*|$)         # End of string or trailing spaces
        '''
        
        match = re.search(pattern, command, re.VERBOSE)
        if match:
            filename = match.group(1).strip()
            
            # Check if filename exists as-is first
            if self.file_manager.find_file_or_folder(filename):
                return filename
            
            # If not found, try adding missing extensions
            if '.' not in filename:
                for ext in self.extensions:
                    potential_name = f"{filename}.{ext}"
                    if self.file_manager.find_file_or_folder(potential_name):
                        return potential_name
            return filename
        
        return None

    def classify_intent(self, command):
        try:
            return self.model.predict([command])[0]
        except Exception as e:
            raise RuntimeError(f"Classification error: {str(e)}")

class AssistantGUI:
    def __init__(self, root, core):
        self.root = root
        self.core = core
        self.setup_gui()
        self.setup_styles()
        
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.configure('Chat.TFrame', background='#e5e5ea')
        self.message_font = Font(family="Segoe UI", size=11)

    def setup_gui(self):
        self.root.title("Smart Virtual Assistant")
        self.root.geometry("850x650")
        self.root.configure(bg="#f0f4f8")
        
        self.status_frame = tk.Frame(self.root, bg="#f0f4f8")
        self.status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = tk.Label(self.status_frame, text="Ready", bg="#f0f4f8", 
                                   fg="#444", font=("Segoe UI", 10))
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.status_indicator = tk.Canvas(self.status_frame, width=15, height=15, 
                                        bg="#f0f4f8", highlightthickness=0)
        self.status_circle = self.status_indicator.create_oval(2, 2, 13, 13, fill="#86868b")
        self.status_indicator.pack(side=tk.LEFT)
        
        self.chat_frame = ttk.Frame(self.root, style='Chat.TFrame')
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.chat_canvas = tk.Canvas(self.chat_frame, bg="#e5e5ea", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.chat_frame, orient=tk.VERTICAL, 
                                      command=self.chat_canvas.yview)
        self.scrollable_frame = tk.Frame(self.chat_canvas, bg="#e5e5ea")
        
        self.chat_window = self.chat_canvas.create_window((0, 0), window=self.scrollable_frame, 
                                                        anchor='nw')
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollable_frame.bind("<Configure>", 
                                 lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))
        self.chat_canvas.bind("<Configure>", self.on_canvas_configure)
        
        self.chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.input_frame = tk.Frame(self.root, bg="#e5e5ea")
        self.input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.entry = ttk.Entry(self.input_frame, font=("Segoe UI", 11))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=6)
        
        self.mic_button = ttk.Button(self.input_frame, text="🎤", command=self.process_voice_command)
        self.mic_button.pack(side=tk.RIGHT, padx=5)
        
        self.send_button = ttk.Button(self.input_frame, text="Send", command=self.process_text_command)
        self.send_button.pack(side=tk.RIGHT)
        
    def update_status(self, text, status):
        color_map = {"idle": "#86868b", "active": "#4CAF50", "processing": "#FFC107"}
        self.status_label.config(text=text)
        self.status_indicator.itemconfig(self.status_circle, fill=color_map.get(status, "#86868b"))
        self.root.update()

    def display_message(self, text, sender="user"):
        message_frame = tk.Frame(self.scrollable_frame, bg="#f0f4f8", pady=5)
        message_frame.pack(fill=tk.X, padx=10)

        bubble_frame = tk.Frame(message_frame, bg="#dcf8c6" if sender == "user" else "#ffffff")
        bubble_frame.pack(side=tk.RIGHT if sender == "user" else tk.LEFT, 
                         anchor=tk.E if sender == "user" else tk.W, 
                         padx=(50, 0) if sender == "user" else (0, 50))

        if sender == "assistant":
            avatar_label = tk.Label(bubble_frame, text="🤖", font=("Segoe UI", 14), bg="#ffffff")
            avatar_label.pack(side=tk.LEFT, padx=(10, 5), pady=10)

        message_label = tk.Label(bubble_frame, text=text, font=self.message_font,
                                bg=bubble_frame["bg"], fg="#333333",
                                wraplength=450, justify=tk.LEFT,
                                padx=10, pady=10)
        message_label.pack(side=tk.RIGHT if sender == "user" else tk.LEFT)

        self.root.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def on_canvas_configure(self, event):
        self.chat_canvas.itemconfig(self.chat_window, width=event.width)

    def process_text_command(self):
        command = self.entry.get().strip()
        if not command:
            return
        self.entry.delete(0, tk.END)
        self.display_message(command, sender="user")
        threading.Thread(target=self.core.process_command, args=(command,)).start()

    def process_voice_command(self):
        threading.Thread(target=self.core.process_voice_input).start()

class AssistantCore:
    def __init__(self, root):
        self.root = root
        self.db = DatabaseManager()
        self.gui = AssistantGUI(root, self)
        self.speech = SpeechManager()
        self.processor = CommandProcessor()
        self.file_manager = FileManager()
        self.current_user = None
        
        self.setup_user()
        self.greet_user()

    def setup_user(self):
        session = self.db.get_session()
        self.current_user = session.query(User).first()
        if not self.current_user:
            self.current_user = User(username="DefaultUser")
            session.add(self.current_user)
            session.commit()
        session.close()

    def log_command(self, command_text, intent):
        session = self.db.get_session()
        try:
            history_entry = CommandHistory(
                command_text=command_text,
                intent=intent,
                user=self.current_user
            )
            session.add(history_entry)
            session.commit()
        except Exception as e:
            session.rollback()
            self.gui.display_message(f"Error logging command: {str(e)}", sender="assistant")
        finally:
            session.close()

    def greet_user(self):
        self.speak("Hi, I'm Zuri, your virtual assistant. How can I help you?")

    def speak(self, text):
        self.gui.display_message(text, sender="assistant")
        self.root.after(200, lambda: self.speech.speak(text))

    def process_voice_input(self):
        self.gui.update_status("Listening...", "active")
        try:
            with sr.Microphone() as source:
                self.speak("I'm listening.")
                audio = self.speech.recognizer.listen(source)
                with open("temp_audio.wav", "wb") as f:
                    f.write(audio.get_wav_data())
                
                self.gui.update_status("Processing speech...", "processing")
                result = self.speech.transcribe_audio("temp_audio.wav")
                command = result["text"]
                
                self.gui.display_message(f"{command} (voice)", sender="user")
                self.process_command(command)
                
        except Exception as e:
            self.gui.display_message(f"Voice input error: {str(e)}", sender="assistant")
        finally:
            self.gui.update_status("Ready", "idle")
            if os.path.exists("temp_audio.wav"):
                os.remove("temp_audio.wav")

    def process_command(self, command):
        try:
            self.gui.update_status("Analyzing...", "processing")
            intent = self.processor.classify_intent(command)
            self.log_command(command, intent)
            self.perform_action(intent, command)
        except Exception as e:
            self.speak(f"Error processing command: {str(e)}")
        finally:
            self.gui.update_status("Ready", "idle")

    def perform_action(self, intent, command):
        self.gui.update_status("Working...", "processing")
        filename = self.processor.extract_filename(command)
        session = self.db.get_session()

        try:
            if intent in ['open_file', 'open_media']:
                path = self.file_manager.find_file_or_folder(filename)
                if path and self.file_manager.open_path(path):
                    self.speak(f"Opening {filename}")
                else:
                    self.speak("File not found.")

            elif intent == 'open_folder':
                folder_name = command.replace("open folder", "").strip()
                path = self.file_manager.find_file_or_folder(folder_name, 'folder')
                if path and self.file_manager.open_path(path):
                    self.speak(f"Opening folder {folder_name}")
                else:
                    self.speak("Folder not found.")

            elif intent == 'play_music':
                path = self.file_manager.find_file_or_folder('.mp3')
                if path and self.file_manager.open_path(path):
                    self.speak("Playing music.")
                else:
                    self.speak("No music found.")

            elif intent == 'play_movie':
                path = self.file_manager.find_file_or_folder('.mp4')
                if path and self.file_manager.open_path(path):
                    self.speak("Enjoy your movie!")
                else:
                    self.speak("No movie found.")

            elif intent == 'search_file':
                path = self.file_manager.find_file_or_folder(filename)
                if path:
                    self.speak(f"File found at {path}")
                else:
                    self.speak("File not found.")

            elif intent == 'delete_file':
                path = self.file_manager.find_file_or_folder(filename)
                if path:
                    success, message = self.file_manager.delete_file(path)
                    self.speak(message if success else "Deletion failed")
                else:
                    self.speak("File not found.")

            elif intent == 'delete_forever':
                path = self.file_manager.find_file_or_folder(filename)
                if path:
                    success, message = self.file_manager.delete_file(path, permanent=True)
                    self.speak(message if success else "Permanent deletion failed")
                else:
                    self.speak("File not found.")

            elif intent == 'copy_file':
                destination = filedialog.askdirectory(title="Select destination for copy")
                if filename and destination:
                    path = self.file_manager.find_file_or_folder(filename)
                    if path:
                        success, message = self.file_manager.copy_file(path, destination)
                        self.speak(message if success else "Copy failed")
                    else:
                        self.speak("File not found.")

            elif intent == 'move_file':
                if not filename:
                    self.speak("Please specify a file to move")
                    return

                source_path = self.file_manager.find_file_or_folder(filename)
                if not source_path:
                    self.speak(f"Could not find {filename}")
                    return

                # Show file dialog for destination selection
                destination = filedialog.askdirectory(
                    title="Select destination for move",
                    mustexist=True  # Ensure valid existing directory
                )
                
                if not destination:
                    self.speak("Move operation cancelled")
                    return

                try:
                    # Attempt the move operation
                    success, message = self.file_manager.move_file(source_path, destination)
                    
                    if success:
                        new_path = os.path.join(destination, os.path.basename(source_path))
                        self.speak(f"Moved {filename} to {os.path.basename(destination)}")
                        self.log_command(
                            command, 
                            f"{intent}: {source_path} -> {new_path}"
                        )
                    else:
                        self.speak(f"Move failed: {message}")
                        
                except PermissionError:
                    self.speak("Permission denied - try running as administrator")
                except Exception as e:
                    self.speak(f"Error moving file: {str(e)}")

            else:
                self.speak("Command not recognized")

        except Exception as e:
            self.speak(f"Operation failed: {str(e)}")
        finally:
            session.close()

def main():
    root = tk.Tk()
    assistant = AssistantCore(root)
    root.mainloop()

if __name__ == "__main__":
    main()