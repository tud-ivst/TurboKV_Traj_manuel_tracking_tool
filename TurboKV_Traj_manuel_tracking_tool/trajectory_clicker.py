import tkinter as tk
import TurboKV_Traj_manuel_tracking_tool.traj_tool_helpers as traj_tool_helpers
from tkinter import filedialog
from tkinter import messagebox
import cv2
import queue
import threading
import pandas as pd
import TurboKV_Traj_manuel_tracking_tool.traj_drawing as traj_drawing
import time

class App:
    """ main class for all informations of the program including
        tkinter elements, videos, dataframes etc.
    """

    def __init__(self, window, window_title):
        """initialize the app window with main characteristics, 
        others are splitted into several functions

        Args:
            window (toplevel): tkinter toplevelwindow
            window_title (str): name of the toplevelwindow
        """
        self.window = window
        self.window.title(window_title)
        self.window.geometry("1900x1000")
        self.init_menu_bar()
        self.canvas = None
        self.video = {}
        self.label_hotkeys = None
        self.state_panel = traj_tool_helpers.StatePanel(self.window, 0, 0, "w", width=50)
        self.frame_panel = traj_tool_helpers.StatePanel(self.window, 0, 1, "w", width=50)
        self.queue = None
        self.video_state = {
            "escape": False,
            "close": False,
            "pause": True,
            "current_frameskip": 1,
            "forward_frame": False,
            "backward_frame": False,
            "forward": False,
            "backward": False,
            "change_frameskip_size":True,
            "set_class_mode":False,
            "last_save_time":None,
            "image_resize":0.6,
            "show_markers": True
        }
        self.gui = {}
        self.trajectories_df = pd.DataFrame(columns=["id","class", "frame" ,"x", "y"])
        self.traj_id_now = 0
        self.traj_finished = True
        self.traj_colors = {
            "Rad": (60, 180, 75),
            "Fuß": (0, 130, 200),
            "Unbekannt":(255, 255, 255)
        }
        # mainloop --> make reactions after user inputs possible 
        self.window.mainloop()
    
    def init_menu_bar(self):
        self.menu_bar = tk.Menu(self.window)
        self.window.config(menu=self.menu_bar)
        self.menu_bar.add_command(label="Load Video", command=lambda: self.load_video_draw_first_frame())
        self.menu_bar.add_command(label="Save Trajectory Data", command=lambda: traj_tool_helpers.safe_traj(self))
        self.menu_bar.add_command(label="Help", command=lambda: help(self))

    def load_video_draw_first_frame(self):
        self.video_state["last_save_time"] = time.time()
        self.video["path"] = filedialog.askopenfilename(parent=self.window)
        self.video["video_capture"] = cv2.VideoCapture(self.video["path"])
        self.video["width"] = self.video["video_capture"].get(cv2.CAP_PROP_FRAME_WIDTH)
        self.video["height"] = self.video["video_capture"].get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.video["fps"] = self.video["video_capture"].get(cv2.CAP_PROP_FPS)
        self.video["frames"] = self.video["video_capture"].get(cv2.CAP_PROP_FRAME_COUNT)
        self.video["duration"] = self.video["fps"] * self.video["frames"]
        self.video["current_frame"] = 0
        self.video["current_cap"] = None
        self.video["frame_without_overlay"] = None
        self.video["last_showen_frame"] = None
        self.state_panel.update("loaded video")
        # Create a canvas that can fit the above video source size
        if self.canvas is None:
            self.canvas = tk.Canvas(self.window, width=self.video["width"], height=self.video["height"])
        self.canvas.grid(row=1, column=0, padx='5', pady='3', sticky='w', columnspan=2)
        self.queue = queue.Queue()
        # close window on closing button
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        traj_drawing.draw_frame_with_overlay(self, True)
        # make_counting_available
        traj_tool_helpers.keybindings(self)
        video_playback = traj_tool_helpers.Thread(self.queue, self, "video_playback").start()
        self.window.after(100, self.process_queue)
    def process_queue(self):
        """recursion that stops if the threaded process of mtc is done --> 
        show the escape toplevelwindow, make the tkinter gui still available
        """
        try:
            not_important_variable = self.queue.get(0)
            
        except queue.Empty:
            self.window.after(100, self.process_queue)
        else:

            traj_tool_helpers.escape_window(self)
    def on_closing(self):
        """closing window and loop
        """
        # end the threaded process of the video if it exist
        try:
            self.video_state["close"] = True
            
        except AttributeError:
            pass
        messagebox.showinfo(title="Close", parent=self.window, message="Close")

        print("nach erstem sleep")
        self.window.quit()
        self.window.destroy()
        for thread in threading.enumerate(): 
            print(thread.name)
        
def help(app):
    app.gui["toplevelwindow"] = tk.Toplevel(app.window)
    app.gui["toplevelwindow"].title("Help")
    app.gui["toplevelwindow"].geometry("600x" + str(24*27))
    text = tk.Text(app.gui["toplevelwindow"], height=20, width=100)
    text.grid(row=0, column=0)
    text.insert(tk.END, help_text())
    text.config(state="disabled")

def help_text():
    return ("KEY - FUNKTION" + "\n\n" +
        "Mouse Left | Mouse Right " + " - set trajectory point" + "\n" +
        "Mouse Wheel forward | W  "+ " - jump some frames forward"+ "\n" +
        "Mouse Wheel backward | Q "+" - jump some frames backward"+ "\n" +
        "Mouse Wheel Click | A    " +" - toggle bjump size (for both jump options)"+ "\n" +
        "Right                    " + " - jump many frames forward" +  "\n" +
        "Left                     " + " - jump many frames backward" +  "\n" +
        "1                        " + " - select and jump to trajectory befor" +  "\n" +
        "2                        " + " - select and jump to trajectory afterwards" +  "\n" +
        "E                        " + " - show markers/disable markers" +  "\n" +
        "Delete                   " + " - delete selected trajectory (marked magenta)" +  "\n" +
        "F                        " + " - finish pedestrian trajectory" +  "\n" +
        "R                        " + " - finish biker trajectory" +  "\n" +
        "Space                    " + " - play/pause" +  "\n" +
        "\n"+"all 10 min the program safe the trajectory data as safety"
        "\n"+"safes always at the video location and under the same name (auto_save named diffrently)"
        "\n"+"change Name if you track a video in muliple sessions"


    )

def mainfunction():
    """start the App
    """
    App(tk.Tk(), "Traffic Count Tool")

if __name__ == '__main__':
    mainfunction()