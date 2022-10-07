import PIL.Image
import PIL.ImageTk
import copy
import cv2
import tkinter as tk
import numpy as np

def draw_a_cross(frame, mid_x, mid_y, radius, color, thickness):
    """function for a cross, background cross and upper color cross use same function

    Args:
        frame (dst): image
        mid_x (int): x mid
        mid_y (int): y mid
        radius (int): size of the cross
        color (str]: color string for cross
        thickness (int): thickness of the cross
        entry (bool): is event an entry?
        boundary (bool): is it the black boundary in the background?

    Returns:
        [dst]: image with cross
    """
    # not entry counts get a small circle, if it isnt the black boundary
    # if not entry and not boundary:
    #     cv2.circle(
    #         frame, 
    #         (mid_x, mid_y), 
    #         radius,
    #         (0,0,0),
    #         1
    #     )
    # cross lines
    cv2.line(
        frame, 
        (mid_x + radius, mid_y), 
        (mid_x - radius, mid_y), 
        color,
        thickness
    )
    cv2.line(
        frame, 
        (mid_x, mid_y + radius), 
        (mid_x, mid_y - radius), 
        color,
        thickness
    )
    
    return frame

def draw_lines(app, frame, frame_range):
    """draw a line from entry, other crossed gates and exit of one object

    """
    current_frame = app.video["video_capture"].get(cv2.CAP_PROP_POS_FRAMES)
    points_in_range = app.trajectories_df.loc[
        (current_frame - frame_range/2 < app.trajectories_df["frame"]) &
        (app.trajectories_df["frame"] < current_frame + frame_range/2)]
    ids_traj_to_show = points_in_range["id"].unique().tolist() + [app.traj_id_now]
    points_of_traj_in_range = app.trajectories_df.loc[app.trajectories_df["id"].isin(ids_traj_to_show)]
    points_of_traj_in_range["x2"] = [None] + points_of_traj_in_range["x"].copy().to_list()[:-1]
    points_of_traj_in_range["y2"] = [None] + points_of_traj_in_range["y"].copy().to_list()[:-1]
    for index in ids_traj_to_show:
        
        points_of_traj = points_of_traj_in_range.loc[points_of_traj_in_range["id"]==index]
        
        color = app.traj_colors[points_of_traj["class"].to_list()[0]]
        points_of_traj = points_of_traj.iloc[1:]
        for index, row in points_of_traj.reset_index(drop=True).iterrows():
            x0, y0 = row["x"], row["y"]
            x1, y1 = int(row["x2"]), int(row["y2"])
            # draw the direction arrow
            
            frame = direction_arrow(frame, (x1, y1), (x0, y0), 15, 15, (0, 0, 0), 3)
            
            
            # draw the line (consists of 2 lines) between 2 counting points of the user
            cv2.line(
                frame, 
                (x0, y0), 
                (x1, y1), 
                (0, 0, 0),
                3
            )
            cv2.line(
                frame, 
                (x0, y0), 
                (x1, y1), 
                color,
                2
            )

    return frame

def direction_arrow(frame, p0, p1, width, length, color, thickness):
    """draw direction arrow
    """
    x_m = (p0[0] + p1[0]) // 2
    y_m = (p0[1] + p1[1]) // 2

    
    x = p0[0] - p1[0]
    y = p0[1] - p1[1]
    l = (x ** 2 + y ** 2) ** 0.5
    # no div by 0
    if l > 0:
        x_length_delta = round(x / l * length / 2)
        y_length_delta = round(y / l * length / 2)

        angle_line = calculate_angle(p0, p1)
        (x_width_delta, y_width_delta) = calculate_x_y_deltas(angle_line, width/2)
        
        cv2.line(
            frame, 
            (x_m - x_length_delta, y_m - y_length_delta), 
            (x_m + x_length_delta + x_width_delta, y_m + y_length_delta + y_width_delta), 
            color,
            thickness
        )
        cv2.line(
            frame, 
            (x_m - x_length_delta, y_m - y_length_delta), 
            (x_m + x_length_delta - x_width_delta, y_m + y_length_delta - y_width_delta), 
            color,
            thickness
        )
    return frame

def calculate_angle(center_point, point):
    """calculate the angle that a point have from the center_point 
    (right or center_y == y, center_x < x would be alpha = 0; counter clockwise)

    Args:
        center_point (tuple): center point x,y values
        point (tuple): point (x,y)

    Returns:
        float: angle to the point in rad, None if not possible
    """
    (center_x, center_y) = center_point
    (x, y) = point
    # right above, right
    if center_x < x and center_y >= y:
        return np.arctan((center_y-y)/(x-center_x))
        
    # left above
    elif center_x > x and center_y >= y:
        return np.pi - np.arctan((center_y-y)/(center_x-x))
    # left under
    elif center_x > x and center_y < y:
        return np.pi + np.arctan((y-center_y)/(center_x-x))
    # right under
    elif center_x < x and center_y < y:
        return 2 * np.pi - np.arctan((y-center_y)/(x-center_x))
    # under
    elif center_x == x and center_y < y:
        return 1.5 * np.pi
    # above
    elif center_x == x and center_y > y:
        return 0.5 * np.pi
    else:
        return None

def calculate_x_y_deltas(angle, hyp):
    """calculate angle that is needed to calculate x or y with cos or sin

    Args:
        angle (float): angle in rad
        hyp (float): hypotenose

    Returns:
        tuple: delta x and delta y
    """
    if angle < np.pi / 2:
        angle_x_y = angle
        x_delta = round(np.cos(angle_x_y + np.pi / 2) * hyp)
        y_delta = -1*round(np.sin(angle_x_y + np.pi / 2) * hyp)
    elif angle < np.pi:
        angle_x_y = np.pi - angle
        x_delta = -1*round(np.cos(angle_x_y + np.pi / 2) * hyp)
        y_delta = -1*round(np.sin(angle_x_y + np.pi / 2) * hyp)
    elif angle < np.pi * 2 / 3:
        angle_x_y = angle - np.pi
        x_delta = -1*round(np.cos(angle_x_y + np.pi / 2) * hyp)
        y_delta = round(np.sin(angle_x_y + np.pi / 2) * hyp)
    elif angle < 2 * np.pi:
        angle_x_y = 2 * np.pi - angle
        x_delta = round(np.cos(angle_x_y + np.pi / 2) * hyp)
        y_delta = round(np.sin(angle_x_y + np.pi / 2) * hyp)
    return (x_delta, y_delta)


def draw_multiple_crosses(frame, points, thickness, traj_colors, boundary_color):
    for index, row in points.reset_index(drop=True).iterrows():
        # first the background
        #frame = draw_a_cross(frame, row["x"], row["y"], 12, boundary_color, thickness)
        cv2.circle(frame, (row["x"], row["y"]), 11, boundary_color, thickness)

        frame = draw_a_cross(frame, row["x"], row["y"], 11, traj_colors[row["class"]], thickness)
    return frame


def draw_traj_points(app, frame, frame_range, small_frame_range=12):
    current_frame = app.video["video_capture"].get(cv2.CAP_PROP_POS_FRAMES)
    selection = app.trajectories_df["id"] == app.traj_id_now
    # points of the selected traj
    points_selected = app.trajectories_df.loc[selection]
    # points in the framerange, but not selected
    points_in_framerange = app.trajectories_df.loc[
        (current_frame - frame_range/2 < app.trajectories_df["frame"]) &
        (app.trajectories_df["frame"] < current_frame + frame_range/2) 
        & ~selection]
    selection = (
        (current_frame - small_frame_range/2 < points_selected["frame"])
        & (points_selected["frame"] < current_frame + small_frame_range/2))

    points_selected_at_moment = points_selected.loc[selection]
    points_selected = points_selected.loc[~selection]

    selection = ((current_frame - small_frame_range/2 < points_in_framerange["frame"])
    & (points_in_framerange["frame"] < current_frame + small_frame_range/2))
    # points at the moment (but not selecte)
    point_at_the_moment = points_in_framerange.loc[selection]
    # points in the framerange (but not selected and not at the moment)
    points_in_framerange = points_in_framerange.loc[~selection]
    frame = draw_multiple_crosses(frame, points_in_framerange, 1, app.traj_colors, (0, 0, 0))
    frame = draw_multiple_crosses(frame, point_at_the_moment, 1, app.traj_colors, (255, 255, 255))
    frame = draw_multiple_crosses(frame, points_selected, 1, app.traj_colors, (240, 50, 230))
    frame = draw_multiple_crosses(frame, points_selected_at_moment, 1, app.traj_colors, (255, 255, 255))
    return frame


def get_frame(app):
    """get frame from the file

    Args:
        app ([type]): [description]

    Returns:
        [type]: [description]
    """
    if app.video["video_capture"].isOpened():
        # if it is just a small step in the same video --> change by grab()
        # because grab is way faster than always set the wanted time
        if 27 > app.video_state["current_frameskip"] > 0:
            
            if app.video_state["current_frameskip"] > 1:
                for i in range(app.video_state["current_frameskip"]-1):
                    app.video["video_capture"].grab()
        # get the frame
        ret, frame = app.video["video_capture"].read()

        app.video_state["current_frameskip"] = 0
        if ret:
            # Return a boolean success flag and the current frame converted to BGR
            return (ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        else:
            return (ret, None)
    else:
        return (ret, None)

def draw_frame_with_overlay(app, first_frame, frameskip=None):
    """draw the overlay with the frame, frist_frame is a boolean

    Args:
        app (dict): main dict
        first_frame (bool): draw first image of the video?
        same_tracks_frame (bool, optional): use a already build frame. Defaults to False.
        frameskip (int, optional): None if no frameskip. Defaults to None.
    """
    # print(frameskip)
    if first_frame:
        app.video["video_capture"].set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret = True # default
    # just get the last showen frame if paused, but something got changed 
    # (gates for example)
    # draw_frame_with_overlay only get called if something got changed or
    # the video is not paused
    if app.video["last_showen_frame"] is not None and (app.video_state["set_class_mode"] or (app.video_state["pause"] and frameskip is None)):
        frame = copy.copy(app.video["last_showen_frame"])
        app.video_state["set_class_mode"] = False
    else:
        ret, frame = get_frame(app)
        # set last showen frame
        if ret:
            app.video["last_showen_frame"] = copy.copy(frame)
    # only go forward if frame is valid (ret) or just the 
    if ret:
        current_frame=app.video["video_capture"].get(cv2.CAP_PROP_POS_FRAMES)
        app.frame_panel.update(str(int(current_frame)) + " / " + str(int(app.video["frames"])) + " (" + str(np.round(current_frame/app.video["fps"]/60,2)) + " min)", False)
        # draw traj
        if not app.trajectories_df.empty and app.video_state["show_markers"]:
            frame_range=250
            frame = draw_lines(app, frame, frame_range=frame_range)
            frame = draw_traj_points(app, frame, frame_range=frame_range)
        image = PIL.Image.fromarray(frame)
        image = image.resize(
            (int(app.video["width"]*app.video_state["image_resize"]), 
            int(app.video["height"]*app.video_state["image_resize"])), PIL.Image.ANTIALIAS)
        image = PIL.ImageTk.PhotoImage(image=image)
        app.canvas.create_image(0, 0, image=image, anchor=tk.NW)
        # to solve flickering
        app.canvas.image = image

