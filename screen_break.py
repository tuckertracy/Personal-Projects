
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

# --- Timing config ---
TICK_MS = 700          # TEST: 3 seconds per "minute". Set to 60000 for real minutes.
BREAK_DURATION = 5  # break length
UNTIL_BREAK = 20    # minutes until next break

# --- Control window ---
control_window = tk.Tk()
control_window.title("Break Reminder App")
control_window.geometry("400x220")

main_frame = ttk.Frame(control_window, padding="10 10 10 10")
main_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

# Make the frame stretch
control_window.columnconfigure(0, weight=1)
control_window.rowconfigure(0, weight=1)
main_frame.columnconfigure(0, weight=1)  # labels stretch
main_frame.columnconfigure(1, weight=0)  # right column stays compact

# --- Reminder window (hidden until break) ---
reminder_window = tk.Toplevel(control_window)

reminder_window.columnconfigure(0, weight=1)
reminder_window.rowconfigure(0, weight=1)

reminder_window.title("Break Reminder")
reminder_window.geometry("320x180")
reminder_window.withdraw()

reminder_frame = ttk.Frame(reminder_window, padding="10 10 10 10")
reminder_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

reminder_frame.columnconfigure(0, weight=1)
reminder_frame.rowconfigure(0, weight=1)


# --- State / text vars ---
countdown_var = tk.StringVar(value=f"{UNTIL_BREAK} minutes remaining")
label_var = tk.StringVar(value="")
status_var = tk.StringVar(value="")

program_status = "idle"            # "idle" | "start" | "paused"
til_break = UNTIL_BREAK      # minutes until break
break_time = 0                     # minutes during break; 0 when not in a break
return_time = None                 # end-of-break time

# Job IDs for after() so we can pause/cancel deterministically
control_timer_job = None           # until-break timer job
break_timer_job = None             # during-break timer job
create_break_window_job = None     # deferred opening of break window

# --- UI widgets (created once) ---

# Row 0: Until-break countdown (spans both columns)
countdown_label = ttk.Label(main_frame, textvariable=countdown_var)
countdown_label.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

# Row 1: Status (col 0), Pause (col 1)
program_running_label = ttk.Label(main_frame, textvariable=status_var)
program_running_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
pause_button = ttk.Button(main_frame, text="Pause timer")
pause_button.grid(row=1, column=1, sticky="e", padx=5, pady=5)

# Row 2: Start/End (spans both columns)
start_button = ttk.Button(main_frame, text="Begin break program")
start_button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=10)

# Row 3: Resume button
resume_button = ttk.Button(main_frame,text="Resume timer")
resume_button.grid(row=1, column=1, columnspan=2, sticky="ew", padx=5, pady=10)
resume_button.grid_remove()

# Reminder window label
reminder_label = ttk.Label(reminder_frame, textvariable=label_var, anchor="center", justify="center", wraplength=280)
reminder_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

# Hide status + pause until Start
program_running_label.grid_remove()
pause_button.grid_remove()

# --- Helpers ---

def safe_cancel(job_id, on_window):
    """Cancel an after() job if it exists."""
    if job_id is not None:
        try:
            on_window.after_cancel(job_id)
        except Exception:
            pass

def reset_until_break():
    """Reset the minutes until next break and refresh display."""
    global til_break
    til_break = UNTIL_BREAK
    countdown_var.set(f"{til_break} minutes remaining")

def start_until_break_timer():
    """(Re)start the 'until break' timer from current til_break."""
    global control_timer_job
    safe_cancel(control_timer_job, control_window)  # avoid duplicate scheduling
    control_timer_job = control_window.after(TICK_MS, update_control_window_text)

def schedule_break_open():
    """Schedule the creation/opening of the break window."""
    global create_break_window_job
    safe_cancel(create_break_window_job, control_window)
    create_break_window_job = control_window.after(TICK_MS, create_break_window)

# --- Countdown updaters ---

def update_control_window_text():
    """Control-window countdown until it's time for a break."""
    global til_break, control_timer_job
    if program_status != "start":
        return

    if til_break > 0:
        til_break -= 1
        countdown_var.set(f"{til_break} minutes remaining")
        control_timer_job = control_window.after(TICK_MS, update_control_window_text)
    else:
        countdown_var.set("Break time!")
        schedule_break_open()

def create_break_window():
    """Open the break window and start the break countdown."""
    global break_time, return_time, break_timer_job
    break_time = BREAK_DURATION
    return_time = datetime.now() + timedelta(minutes=break_time)

    label_var.set(
        f"Take a {BREAK_DURATION}-minute break.\n"
        f"Rest, stretch, hydrate.\n"
        f"Come back at {return_time.strftime('%I:%M %p')}"
    )

    reminder_window.deiconify()
    reminder_window.attributes('-topmost', True)
    reminder_window.lift()
    reminder_window.focus_force()

    if reminder_window.state() == "normal":
        pause_button.state(["disabled"])

    break_timer_job = reminder_window.after(TICK_MS, update_break_window_text)

def update_break_window_text():
    """Break-window countdown; when done, close and reset the next cycle."""
    global break_time, break_timer_job

    if program_status != "start":
        return

    if break_time > 0:
        break_time -= 1
        reminder_window.after(TICK_MS,update_break_window_text)
    else:
        label_var.set("Break is over")

        def end_and_reset_cycle():
            reminder_window.withdraw()
            reminder_window.attributes('-topmost', False)
            reset_until_break()
            if program_status == "start":  # keep the program going if not paused/ended
                start_until_break_timer()
            pause_button.state(["!disabled"])
        reminder_window.after(TICK_MS, end_and_reset_cycle)

# --- Button handlers (no resume) ---

def on_start_click():
    """Start the overall program (always fresh, no resume)."""
    global program_status
    program_status = "start"

    # Show secondary controls
    program_running_label.grid()
    pause_button.grid()
    pause_button.state(["!disabled"])

    status_var.set("The program is now running. Stay focused!")
    start_button.config(text="End break program", command=on_end_click)

    # Fresh cycle
    reset_until_break()
    start_until_break_timer()

def on_pause_click():
    """Pause all timers; do not resume automatically."""
    global program_status
    program_status = "paused"

    # Cancel scheduled jobs safely
    safe_cancel(control_timer_job, control_window)
    safe_cancel(create_break_window_job, control_window)
    safe_cancel(break_timer_job, reminder_window)

    status_var.set("Paused")
    # Disable pause button while paused (no resume here)
    pause_button.state(["disabled"])
    #Show resume button
    resume_button.grid()

def on_end_click():
    """Stop the program entirely and reset UI/state."""
    control_window.destroy()

def on_resume_click():
    global program_status, control_timer_job, break_timer_job

    program_status = "start"

    status_var.set("The program is now running. Stay focused!")
    pause_button.state(["!disabled"])
    resume_button.grid_remove()

    if til_break > 0:
        safe_cancel(control_timer_job, control_window)
        control_timer_job = control_window.after(TICK_MS, update_control_window_text)
    
    if break_time > 0 and reminder_window.state() == "normal":
        safe_cancel(break_timer_job,reminder_window)
        reminder_window.after(TICK_MS,update_break_window_text)

# Wire buttons (Pause only active after Start)
start_button.config(command=on_start_click)
pause_button.config(command=on_pause_click)
resume_button.config(command=on_resume_click)

# --- Run the app ---
control_window.mainloop()