import tkinter as tk
import threading
import time
import cv2
import queue
import copy
import PIL.Image
import PIL.ImageTk
import TurboKV_Traj_manuel_tracking_tool.traj_drawing as traj_drawing
from pathlib import Path
import os
import time
import numpy as np
class StatePanel:
    """feedback information for the user
    """
    # initialize StatePanel
    def __init__(self, window, row, column, sticky, width):
        """init state panel
        """
        self.scrollbar = tk.Scrollbar(window)
        self.text = tk.Text(window, height=2, width=width, yscrollcommand=self.scrollbar.set, state="disabled")
        self.scrollbar.config(command=self.text.yview)
        self.scrollbar.grid(row=row, column=column, columnspan=2, padx='5', pady='3', sticky='e')
        self.text.grid(row=row, column=column, padx='5', pady='3', sticky=sticky)

    def update(self, text, with_minus=True):
        """new information to show --> update

        Args:
            text (str): new text to show
        """
        self.text.config(state="normal")
        if with_minus:
            self.text.insert(tk.END, "\n"+"- " + str(text))
        else:
            self.text.insert(tk.END, "\n"+str(text))
        self.text.see("end")
        self.text.config(state="disabled")


    def move(self, row, column, sticky, columnspan=2):
        """change position

        Args:
            row (int): new row
            column (int): new column
            sticky (str): new sticky for all the elments
            columnspan (int, optional): new columnspan. Defaults to 2.
        """
        self.scrollbar.grid(row=row, column=column, padx='5', pady='3', sticky='e')
        self.text.grid(row=row, column=column, padx='5', pady='3', sticky=sticky, columnspan=columnspan)

#threadLock = threading.Lock()
class Thread (threading.Thread):
    """class for new thread

    Args:
        threading (thread): thread
    """
    def __init__(self, queue, app, name):
        """init thread

        Args:
            queue (queue): queue to prove if the video thread already has stoped
            app (dict): main dict
            name (str): name of the thread
        """
        threading.Thread.__init__(self)
        self.name = name
        self.queue = queue
        self.app = app

    def run(self):
        """run the thread
        """

        update_video_frame(self.app)
        # if escape is pressed or the video comes to the last frame        
        # if self.app.general["video"].current_frame > self.app.general["video"].frames:
        #     self.app.state_panel.update("reached the end of the video")
        if self.app.video_state["escape"]:
            self.app.video_state["escape"] = False
        
        self.queue.put("Task finished")


"""
functions for the video/key loop
"""
def change_current_video_position(app, current_frameskip):
    """change current video pos

    Args:
        app (dict): main dict
        current_frameskip (int): current_frameskip in ms
    """
    # for easier reading
    video = app.video["video_capture"]
    app.video["current_cap"] = app.video["video_capture"].get(cv2.CAP_PROP_POS_FRAMES)
    new_frame_id = int(round(app.video["current_cap"] + current_frameskip)) - 1
    # only change by set to specific time if frameskip isnt 
    # just a small forward step in the same video
    # if it is just a small step in the same video --> change by grab() befor read
    # (see mtc_dict.get_frame function)
    # because grab is way faster than always set the wanted time
    if (
        27 < current_frameskip 
        or current_frameskip < 0 
    ):
        # in borders of the current video; 
        # video_duration_limit(video) because if set to the video duration, it will not show the last frame
        if new_frame_id >= 0 and new_frame_id <= app.video["frames"] - 1:
            app.video["video_capture"].set(cv2.CAP_PROP_POS_FRAMES, new_frame_id)
        # set to 0 if negativ new frame and there is no video befor
        elif new_frame_id < 0:
            app.video["video_capture"].set(cv2.CAP_PROP_POS_FRAMES, 0)
            
        # set to end if higher than duration and no video after the current video is loaded
        elif new_frame_id > app.video["frames"]:
            app.video["video_capture"].set(cv2.CAP_PROP_POS_FRAMES, app.video["frames"] - 1)

def query_video_keys(video_state):
    """query if some of the video hotkeys got pressed and if yes, 
    change the video_state

    Args:
        video_state (dict): dict for video options by button

    Returns:
        int: frameskip in ms
    """
    # value if nothing was pressed
    frameskip = video_state["current_frameskip"]
    # jump forward or backward, 4 diffrent options, all in ms
    if video_state["forward"] and video_state["change_frameskip_size"]:
        frameskip = 750
        video_state["forward"] = False
    elif video_state["backward"] and video_state["change_frameskip_size"]:
        frameskip = -750
        video_state["backward"] = False
    elif video_state["forward"] and not video_state["change_frameskip_size"]:
        frameskip = 15000
        video_state["forward"] = False
    elif video_state["backward"] and not video_state["change_frameskip_size"]:
        frameskip = -15000
        video_state["backward"] = False
    elif video_state["forward_frame"] and video_state["change_frameskip_size"]:
        frameskip = 2
        video_state["forward_frame"] = False
    elif video_state["backward_frame"] and video_state["change_frameskip_size"]:
        frameskip = -2
        video_state["backward_frame"] = False
    elif video_state["forward_frame"] and not video_state["change_frameskip_size"]:
        frameskip = 25
        video_state["forward_frame"] = False
    elif video_state["backward_frame"] and not video_state["change_frameskip_size"]:
        frameskip = -25
        video_state["backward_frame"] = False

    return frameskip

def update_video_frame(app):
    """update the gui framewise

    Args:
        app (dict): main dict
    """
    while (
        not app.video_state["escape"] 
        and not app.video_state["close"] 
    ):
        befor = time.time()
        # query if a video hotkey was pressed
        # as for loop propably slower

        current_frameskip = query_video_keys(app.video_state)
        # autosave
        if time.time() - app.video_state["last_save_time"] > 600:
            safe_traj(app, auto_save=True)
            app.video_state["last_save_time"] = time.time()


        # draw the actual frame if not paused or there is a frameskip
        if not app.video_state["pause"] or current_frameskip != 0 or app.video_state["draw_new"]:
            
            app.video_state["current_frameskip"] = current_frameskip
            print(app.video_state["current_frameskip"])
            change_current_video_position(app, current_frameskip)
            traj_drawing.draw_frame_with_overlay(app, False, frameskip=current_frameskip)
            app.video_state["current_frameskip"]=0
            app.video_state["draw_new"] = False
            # play in real time
            cal_time = time.time()-befor
            if app.video_state["every_x_frame"] is None:
                app.video_state["every_x_frame"] = int(np.round(cal_time // (1 / app.video["fps"])))
            sleep_time = cal_time - 1/app.video_state["every_x_frame"] 
            if sleep_time > 0:
                time.sleep(sleep_time)
            
        # sleep time to get a normal speed (ca.)
        time.sleep(0.001)



def end_counting(app, toplevelwindow):
    """end the counting (back to the main window)

    Args:
        app (dict): main dict
        toplevelwindow (window): toplevelwindow
    """
    if not toplevelwindow is None:
        toplevelwindow.destroy()
    app.state_panel.update("end the manual traffic counting")

def continue_counting(app, toplevelwindow):
    """continue with the video for counting

    Args:
        app (dict): main dict
        toplevelwindow (window): toplevelwindow
    """
    toplevelwindow.destroy()
    app.state_panel.update("continue with playing the video file")
    #key_assignment = mtc_dict.key_assignment_init()
    #shortcuts(app, key_assignment)
    app.queue = queue.Queue()
    video_playback = Thread(app.queue, app, "video_playback").start()
    app.window.after(100, app.process_queue)

def escape_window(app):
    """creates a toplevelwindow if escape is pressed or the video is finished

    Args:
        app (dict): main dict
    """
    # second window for what doing next?
    toplevelwindow = tk.Toplevel(app.window)
    toplevelwindow.title("Escape")
    toplevelwindow.geometry("400x" + str(2*30))

    label = tk.Label(toplevelwindow, text="What do you want to do?")
    label.grid(row=0, column=0, columnspan=2, padx='5', pady='3')

    continue_counting_button = tk.Button(toplevelwindow, text="Continue counting", command = lambda : continue_counting(app, toplevelwindow))
    continue_counting_button.grid(row=1, column=0, padx='5', pady='3', sticky='w')

    end_counting_button = tk.Button(toplevelwindow, text="End counting", command = lambda : end_counting(app, toplevelwindow))
    end_counting_button.grid(row=1, column=1, padx='5', pady='3', sticky='w')


def keybindings(app):
    app.canvas.bind("<Button-1>", lambda event: click_canvas_callback(event, app=app))
    app.canvas.bind("<Button-3>", lambda event: click_canvas_callback(event, app=app))
    # mousewheel for forward and backward in the video
    app.window.bind("<MouseWheel>", lambda event: mouse_wheel(event, app=app))
    app.window.bind("<Button-2>", lambda event: mouse_button(event, app=app))
    app.window.bind("a", lambda event: mouse_button(event, app=app))
    
    app.window.bind("<Right>", lambda event: jump_many_frames(event, app=app, forward=True))
    app.window.bind("<Left>", lambda event: jump_many_frames(event, app=app, forward=False))

    # class and finishing of the traj
    app.window.bind("r", lambda event: finish_traj_r(event, app=app))
    app.window.bind("f", lambda event: finish_traj_f(event, app=app))
    # jump to another traj
    app.window.bind("1", lambda event: jump_traj_befor(event, app=app))
    app.window.bind("2", lambda event: jump_traj_after(event, app=app))

    app.window.bind("q", lambda event: jump_frames(event, app=app, forward=False))
    app.window.bind("w", lambda event: jump_frames(event, app=app, forward=True))

    app.window.bind("e", lambda event: disable_markers(event, app=app))
    app.window.bind("a", lambda event: disable_all_markers(event, app=app))

    # del
    app.window.bind("<Delete>", lambda event: del_traj(event, app=app))
    # pause
    app.window.bind("<space>", lambda event: pause_play(event, app=app))

def disable_markers(event, app):
    if app.video_state["show_markers"]:
        app.state_panel.update("disable markers")
    else:
        app.state_panel.update("show markers")
    app.video_state["show_markers"] = not app.video_state["show_markers"]
    traj_drawing.draw_frame_with_overlay(app, False)
def disable_all_markers(event, app):
    if app.video_state["show_all_markers"]:
        app.state_panel.update("show not all markers")
    else:
        app.state_panel.update("show all markers")
    app.video_state["show_all_markers"] = not app.video_state["show_all_markers"]
    traj_drawing.draw_frame_with_overlay(app, False)

def pause_play(event, app):
    if app.video_state["pause"]:
        app.state_panel.update("play")
        app.video_state["time_for_loading"] = None
    else:
        app.state_panel.update("pause")
    app.video_state["pause"] = not app.video_state["pause"]

def jump_many_frames(event, app, forward):
    if forward:
        app.video_state["forward"] = True
        app.state_panel.update("forward")
    else:
        app.video_state["backward"] = True
        app.state_panel.update("backward")

def jump_frames(event, app, forward):
    if forward:
        app.video_state["forward_frame"] = True
        app.state_panel.update("forward_frame")
    else:
        app.video_state["backward_frame"] = True
        app.state_panel.update("backward_frame")

def finish_traj_r(event, app):
    app.trajectories_df.loc[app.trajectories_df["id"] == app.traj_id_now, "class"] = "Rad"
    if not app.traj_finished:
        right_of_way_question(app)
    app.video_state["set_class_mode"] = True
    traj_drawing.draw_frame_with_overlay(app, False)
    app.state_panel.update("finished bike trajectory")

def finish_traj_f(event, app):
    app.trajectories_df.loc[app.trajectories_df["id"]== app.traj_id_now, "class"] = "Fuß"
    if not app.traj_finished:
        right_of_way_question(app)
    app.video_state["set_class_mode"] = True
    traj_drawing.draw_frame_with_overlay(app, False)
    app.state_panel.update("finished pedestrian trajectory")

def jump_traj_befor(event, app):
    if app.traj_finished == True and not app.trajectories_df.empty:
        (app.traj_id_now,  app.video_state["current_frameskip"]) = get_next_id(app, app.traj_id_now, id_befor=True)
        app.video_state["draw_new"] = True # always draw new frame, even if frameskip = 0
        app.state_panel.update("selected trajectory befor")

def jump_traj_after(event, app):
    if app.traj_finished == True and not app.trajectories_df.empty:    
        (app.traj_id_now,  app.video_state["current_frameskip"]) = get_next_id(app, app.traj_id_now, id_befor=False)
        app.video_state["draw_new"] = True # always draw new frame, even if frameskip = 0
        app.state_panel.update("selected next trajectory")

# delete selected traj
def del_traj(event, app):
    if not app.trajectories_df.empty:
        app.trajectories_df = app.trajectories_df.loc[app.trajectories_df["id"] != app.traj_id_now]
        traj_del = copy.deepcopy(app.traj_id_now)
        app.traj_finished = True
        (app.traj_id_now,  app.video_state["current_frameskip"]) = get_next_id(app, app.traj_id_now, id_befor=False)
        app.video_state["draw_new"] = True # always draw new frame, even if frameskip = 0
        app.state_panel.update("deleted traj " + str(traj_del) + "; now selected:" + str(app.traj_id_now))


def get_next_id(app, source_id, id_befor):
    if id_befor:
        selected_df = app.trajectories_df.loc[app.trajectories_df["id"] < source_id]
    else:
        selected_df = app.trajectories_df.loc[app.trajectories_df["id"] > source_id]
    if selected_df.empty:
        if source_id in app.trajectories_df["id"].to_list():
            id = copy.deepcopy(source_id) 
        else:
            if id_befor:
                id = app.trajectories_df["id"].min()
            else:
                id = app.trajectories_df["id"].max()
    else:
        if id_befor:
            id = selected_df["id"].max()
        else:
            id = selected_df["id"].min()

    # get frame of first traj point
    traj_df = app.trajectories_df.loc[app.trajectories_df["id"]==id].reset_index(drop=True)
    if traj_df.empty:
        frameskip=0
    else:
        frameskip = int(traj_df.at[0,"frame"] - app.video["video_capture"].get(cv2.CAP_PROP_POS_FRAMES))
    return (id, frameskip)


def right_of_way_question(app):
    app.gui["toplevelwindow"] = tk.Toplevel(app.window)
    app.gui["toplevelwindow"].title("Was the road user deprived of his right of way?")
    app.gui["toplevelwindow"].geometry("600x80")
    app.gui["toplevelwindow"].focus_force()
    text = tk.Text(app.gui["toplevelwindow"], height=3, width=70)
    text.grid(row=0, column=0)
    text.insert(tk.END, "Press T - Was not deprived (Vorfahrt wurde der Person gewährt oder hat keine)\nPress G - Was deprived (Vorfahrt wurde der Person genommen)")
    text.config(state="disabled")
    app.gui["toplevelwindow"].bind("g", lambda event: right_of_way_answer(event, app=app, deprived=True))
    app.gui["toplevelwindow"].bind("t", lambda event: right_of_way_answer(event, app=app, deprived=False))

def right_of_way_answer(event, app, deprived):
    app.trajectories_df.loc[app.trajectories_df["id"]==app.traj_id_now, "deprived"] = deprived
    app.gui["toplevelwindow"].destroy()
    app.traj_finished = True
    app.window.grab_set()
    # jump to frame of the start of the traj
    traj_df = app.trajectories_df.loc[app.trajectories_df["id"]==app.traj_id_now].reset_index(drop=True)
    app.video_state["current_frameskip"] = int(traj_df.at[0,"frame"] - app.video["video_capture"].get(cv2.CAP_PROP_POS_FRAMES))



def mouse_wheel(event, app):
    """event for jump forward or backward in the video witht he mouse wheel

    Args:
        event (event): mouse wheel input
        app (dict): main dict
    """
    if event.delta == 120:
        app.video_state["forward_frame"] = True
        app.state_panel.update("forward_frame")
    elif event.delta == -120:
        app.video_state["backward_frame"] = True
        app.state_panel.update("backward_frame")

def mouse_button(event, app):
    """event for toggle length of mouse_wheel jump

    Args:
        event (event): mouse button event
        app (dict): main dict
    """
    app.video_state["change_frameskip_size"] = not app.video_state["change_frameskip_size"]
    app.state_panel.update("change_frameskip_size")

def click_canvas_callback(event, app):
    """callback function for the canvas

    Args:
        event (event): click on canvas --> position
        app (dict): main dict
    """
    # has to be sorted
    if app.video_state["pause"]:
        if app.trajectories_df.empty:
            app.traj_id_now = 0
            app.traj_finished = False
            new_index = 0
        else:
            new_index = list(app.trajectories_df.index)[-1] + 1
            if app.traj_finished:
                app.traj_id_now = app.trajectories_df["id"].max() + 1
                app.traj_finished = False
        # add point
        app.trajectories_df.loc[new_index] = [
            app.traj_id_now, "Unbekannt", app.video["video_capture"].get(cv2.CAP_PROP_POS_FRAMES), int(event.x / app.video_state["image_resize"]), int(event.y / app.video_state["image_resize"]), None]
        # jump 25 frames
        app.video_state["current_frameskip"] = 25
        print(app.trajectories_df)
        print("ausgewählt: " + str(app.traj_id_now))


    # click_canvas_two_any_number_clicks(event, app)

#safe
def safe_traj(app, auto_save = False):
    if auto_save:
        text = "_autosave"
    else:
        text=""
    app.trajectories_df.to_csv(os.path.dirname(app.video["path"]) + "/" + os.path.splitext(os.path.basename(app.video["path"]))[0] + text + ".csv", sep=";")
    app.state_panel.update("saved" + text)
