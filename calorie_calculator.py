"""Simple desktop demo. Run the review notebook before opening this script."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

import joblib
import numpy as np
import pandas as pd
import shap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

model_path = Path(__file__).with_name("calorie_model.joblib")
if not model_path.exists():
    raise SystemExit("Run all cells in Calories_burnt_prediction_clean.ipynb first, then keep calorie_model.joblib beside this script.")
xgb_pipeline = joblib.load(model_path)
best_scaler = xgb_pipeline.named_steps["scaler"]
xgb_explainer = shap.TreeExplainer(xgb_pipeline.named_steps["model"])

# Colours shared by the window and chart.
background = "#F1F5F9"
ink = "#172B4D"
muted = "#64748B"
accent = "#0F766E"


def run_prediction(event=None):
    try:
        gender_text = entry_gender.get().strip().lower()
        if gender_text not in ("male", "female"):
            raise ValueError("Select male or female for recorded gender.")
        gender = 0 if gender_text == "male" else 1
        age = float(entry_age.get().strip())
        height = float(entry_height.get().strip())
        weight = float(entry_weight.get().strip())
        duration = float(entry_duration.get().strip())
        heart_rate = float(entry_heart_rate.get().strip())
        body_temp = float(entry_body_temp.get().strip())
        input_data = pd.DataFrame(
            [[gender, age, height, weight, duration, heart_rate, body_temp]],
            columns=["Gender", "Age", "Height", "Weight", "Duration", "Heart_Rate", "Body_Temp"],
        )
        if not np.isfinite(input_data.to_numpy()).all() or (input_data.iloc[:, 1:] <= 0).any().any():
            raise ValueError("Enter positive, finite numbers for all measurements.")

        # Predict raw inputs; scale only for the matching SHAP explanation.
        predicted_calories = xgb_pipeline.predict(input_data)[0]
        shap_values = xgb_explainer.shap_values(best_scaler.transform(input_data))
        shap_abs = np.abs(shap_values[0])
        shap_percent = np.zeros_like(shap_abs) if shap_abs.sum() == 0 else shap_abs / shap_abs.sum() * 100
        label_result.config(text=f"{predicted_calories:.2f}")
        label_session.config(text=f"For the entered {duration:g}-minute session")
        label_status.config(text="Estimate updated. Change any measurement and calculate again.")

        # Put the strongest feature first and label the bars directly.
        feature_names = np.array(["Gender", "Age", "Height", "Weight", "Duration", "Heart rate", "Body temperature"])
        order = np.argsort(-shap_percent, kind="stable")
        chart_values = shap_percent[order]
        fig, ax = plt.subplots(figsize=(5.6, 3.1), dpi=100)
        fig.patch.set_facecolor("white")
        ax.barh(feature_names[order], chart_values, color=[accent] + ["#94A9C4"] * 6, height=0.55)
        ax.invert_yaxis()
        ax.set_xlim(0, max(float(chart_values.max()) * 1.25, 10))
        ax.set_axisbelow(True)
        ax.xaxis.grid(True, color="#E8EDF3", linewidth=0.8)
        ax.tick_params(axis="both", length=0, labelsize=10, colors=muted, pad=7)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for position, value in enumerate(chart_values):
            ax.text(value + ax.get_xlim()[1] * 0.02, position, f"{value:.2f}%",
                    va="center", fontsize=10, color=ink)
        ax.set_xlabel("Share of absolute SHAP value (%)", fontsize=9, color=muted, labelpad=12)
        fig.tight_layout(pad=1.2)
        for widget in frame_plot.winfo_children():
            widget.destroy()
        canvas = FigureCanvasTkAgg(fig, master=frame_plot)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        plt.close(fig)
    except ValueError as error:
        messagebox.showwarning("Check your measurements", str(error))
    except Exception as error:
        messagebox.showerror("Prediction error", str(error))


def fill_example():
    # Fictional values to demonstrate the interface.
    entry_gender.set("male")
    for entry, value in [(entry_age, "30"), (entry_height, "175"), (entry_weight, "75"),
                         (entry_duration, "15"), (entry_heart_rate, "100"), (entry_body_temp, "39")]:
        entry.delete(0, tk.END)
        entry.insert(0, value)
    run_prediction()


root = tk.Tk()
root.title("Calorie Lab | Desktop Demo")
root.geometry("1080x790")
root.minsize(960, 760)
root.configure(bg=background)
root.columnconfigure(0, weight=1)
root.rowconfigure(1, weight=1)

style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background=background)
style.configure("Card.TFrame", background="white")
style.configure("TLabel", background="white", foreground=ink, font=("Segoe UI", 10))
style.configure("Muted.TLabel", foreground=muted)
style.configure("Heading.TLabel", font=("Segoe UI", 15, "bold"))
style.configure("Section.TLabel", foreground=accent, font=("Segoe UI", 10, "bold"))
style.configure("TEntry", padding=7, fieldbackground="#F8FAFC", bordercolor="#CBD5E1")
style.configure("TCombobox", padding=6, fieldbackground="#F8FAFC")
style.map("TCombobox", fieldbackground=[("readonly", "#F8FAFC")], foreground=[("readonly", ink)])
style.configure("Accent.TButton", background=accent, foreground="white",
                font=("Segoe UI", 11, "bold"), padding=(14, 12), borderwidth=0)
style.map("Accent.TButton", background=[("active", "#115E59"), ("pressed", "#134E4A")])
style.configure("Quiet.TButton", background="#E8F2F1", foreground=accent,
                font=("Segoe UI", 10), padding=(10, 8), borderwidth=0)
style.map("Quiet.TButton", background=[("active", "#D5E9E6")])

# Header.
header = tk.Frame(root, bg=ink, padx=28, pady=20)
header.grid(row=0, column=0, sticky="ew")
tk.Label(header, text="CALORIE LAB", bg=ink, fg="#5EEAD4", font=("Segoe UI", 10, "bold")).pack(anchor="w")
tk.Label(header, text="Explore your calorie estimate", bg=ink, fg="white",
         font=("Segoe UI", 23, "bold")).pack(anchor="w", pady=(4, 3))
tk.Label(header, text="Enter measurements to see a model prediction and what influenced it.",
         bg=ink, fg="#CBD5E1", font=("Segoe UI", 10)).pack(anchor="w")
content = ttk.Frame(root, padding=(24, 20))
content.grid(row=1, column=0, sticky="nsew")
content.columnconfigure(1, weight=1)
content.rowconfigure(0, weight=1)

# Input card.
input_card = ttk.Frame(content, style="Card.TFrame", padding=22)
input_card.grid(row=0, column=0, sticky="ns", padx=(0, 18))
input_card.columnconfigure(1, weight=1)
ttk.Label(input_card, text="Your measurements", style="Heading.TLabel").grid(
    row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
ttk.Label(input_card, text="Fill every field before calculating.", style="Muted.TLabel").grid(
    row=1, column=0, columnspan=2, sticky="w", pady=(0, 18))
ttk.Label(input_card, text="PERSONAL DETAILS", style="Section.TLabel").grid(
    row=2, column=0, columnspan=2, sticky="w", pady=(0, 8))
ttk.Label(input_card, text="Gender").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=6)
entry_gender = ttk.Combobox(input_card, values=["male", "female"], state="readonly", width=12)
entry_gender.grid(row=3, column=1, sticky="ew", pady=6)
ttk.Label(input_card, text="Age (years)").grid(row=4, column=0, sticky="w", pady=6)
entry_age = ttk.Entry(input_card, width=14)
entry_age.grid(row=4, column=1, sticky="ew", pady=6)
ttk.Label(input_card, text="Height (cm)").grid(row=5, column=0, sticky="w", pady=6)
entry_height = ttk.Entry(input_card, width=14)
entry_height.grid(row=5, column=1, sticky="ew", pady=6)
ttk.Label(input_card, text="Weight (kg)").grid(row=6, column=0, sticky="w", pady=6)
entry_weight = ttk.Entry(input_card, width=14)
entry_weight.grid(row=6, column=1, sticky="ew", pady=6)
ttk.Label(input_card, text="EXERCISE SESSION", style="Section.TLabel").grid(
    row=7, column=0, columnspan=2, sticky="w", pady=(20, 8))
ttk.Label(input_card, text="Duration (min)").grid(row=8, column=0, sticky="w", pady=6)
entry_duration = ttk.Entry(input_card, width=14)
entry_duration.grid(row=8, column=1, sticky="ew", pady=6)
ttk.Label(input_card, text="Heart rate (bpm)").grid(row=9, column=0, sticky="w", pady=6)
entry_heart_rate = ttk.Entry(input_card, width=14)
entry_heart_rate.grid(row=9, column=1, sticky="ew", pady=6)
ttk.Label(input_card, text="Body temp. (°C)").grid(row=10, column=0, sticky="w", pady=6)
entry_body_temp = ttk.Entry(input_card, width=14)
entry_body_temp.grid(row=10, column=1, sticky="ew", pady=6)
ttk.Button(input_card, text="Calculate estimate", style="Accent.TButton", command=run_prediction).grid(
    row=11, column=0, columnspan=2, sticky="ew", pady=(22, 8))
ttk.Button(input_card, text="Try a fictional example", style="Quiet.TButton", command=fill_example).grid(
    row=12, column=0, columnspan=2, sticky="ew")
root.bind("<Return>", run_prediction)

# Result card.
result_card = ttk.Frame(content, style="Card.TFrame", padding=22)
result_card.grid(row=0, column=1, sticky="nsew")
result_card.columnconfigure(0, weight=1)
result_card.rowconfigure(6, weight=1)
ttk.Label(result_card, text="ESTIMATED CALORIES", style="Section.TLabel").grid(row=0, column=0, sticky="w")
result_number = ttk.Frame(result_card, style="Card.TFrame")
result_number.grid(row=1, column=0, sticky="w", pady=(4, 0))
label_result = ttk.Label(result_number, text="—", foreground=accent, font=("Segoe UI", 42, "bold"))
label_result.pack(side="left")
ttk.Label(result_number, text="kcal*", style="Muted.TLabel", font=("Segoe UI", 14)).pack(
    side="left", padx=(10, 0), pady=(22, 0))
label_session = ttk.Label(result_card, text="Your estimate will appear here", style="Muted.TLabel")
label_session.grid(row=2, column=0, sticky="w", pady=(0, 16))
ttk.Separator(result_card).grid(row=3, column=0, sticky="ew", pady=(0, 16))
ttk.Label(result_card, text="What influenced this estimate?", style="Heading.TLabel").grid(row=4, column=0, sticky="w")
ttk.Label(result_card, text="Larger bars mean a greater contribution in this prediction.",
          style="Muted.TLabel", wraplength=470).grid(row=5, column=0, sticky="w", pady=(5, 8))
frame_plot = ttk.Frame(result_card, style="Card.TFrame")
frame_plot.grid(row=6, column=0, sticky="nsew")
ttk.Label(frame_plot, text="Calculate an estimate to reveal\nthe feature contributions.",
          style="Muted.TLabel", anchor="center", justify="center").pack(fill="both", expand=True)
ttk.Label(result_card, text="SHAP percentages show contribution magnitude, not direction or confidence.",
          style="Muted.TLabel", wraplength=470).grid(row=7, column=0, sticky="w", pady=(8, 0))

footer = tk.Frame(root, bg=background, padx=26, pady=10)
footer.grid(row=2, column=0, sticky="ew")
label_status = tk.Label(footer, text="Ready. Enter measurements or try the fictional example.",
                        bg=background, fg=ink, font=("Segoe UI", 9))
label_status.pack(anchor="w")
tk.Label(footer, text="*Dataset label interpreted as kcal; units are unverified. Educational demo, not a health measurement.",
         bg=background, fg=muted, font=("Segoe UI", 9), wraplength=900, justify="left").pack(anchor="w", pady=(4, 0))
root.mainloop()
