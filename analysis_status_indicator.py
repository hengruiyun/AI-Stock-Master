#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analysis Status Indicator
分析状态指示器

Based on demo_status_messages.py color scheme:
- Not Analyzed: #6c757d (Gray)
- Analyzing: #ff6600 (Orange) 
- Completed: #28a745 (Green)
"""

from config.i18n import t_gui
import tkinter as tk
from tkinter import ttk
from datetime import datetime

class AnalysisStatusIndicator:
    """
    Analysis Status Indicator Component
    分析状态指示器组件
    """
    
    # Color scheme from demo_status_messages.py
    COLORS = {
        'not_analyzed': '#6c757d',    # Gray - 未分析
        'analyzing': '#ff6600',       # Orange - 分析中
        'completed': '#28a745',       # Green - 分析完成
        'error': '#dc3545',           # Red - 错误
        'background': '#f8f9fa',      # Light gray background
        'text': '#212529',            # Dark text
        'label': '#495057'            # Medium gray for labels
    }
    
    def __init__(self, parent, width=200, height=30):
        """
        Initialize status indicator
        
        Args:
            parent: Parent widget
            width: Indicator width
            height: Indicator height
        """
        self.parent = parent
        self.width = width
        self.height = height
        
        # Current status
        self.current_status = 'not_analyzed'
        self.status_text = 'Ready'
        
        # Create UI
        self.setup_ui()
        
        # Set initial status
        self.set_status('not_analyzed', 'Ready')
    
    def setup_ui(self):
        """
        Setup user interface
        """
        # Main frame
        self.frame = tk.Frame(self.parent, bg=self.COLORS['background'])
        
        # Status indicator canvas
        self.canvas = tk.Canvas(
            self.frame,
            width=self.width,
            height=self.height,
            bg='white',
            relief=tk.SUNKEN,
            bd=1
        )
        self.canvas.pack(side=tk.LEFT, padx=5)
        
        # Status text label
        self.status_label = tk.Label(
            self.frame,
            text=self.status_text,
            bg=self.COLORS['background'],
            fg=self.COLORS['text'],
            font=('Microsoft YaHei', 10)
        )
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Time label
        self.time_label = tk.Label(
            self.frame,
            text='',
            bg=self.COLORS['background'],
            fg=self.COLORS['label'],
            font=('Microsoft YaHei', 9)
        )
        self.time_label.pack(side=tk.LEFT, padx=5)
    
    def set_status(self, status, text='', show_time=True):
        """
        Set status indicator
        
        Args:
            status: Status type ('not_analyzed', 'analyzing', 'completed', 'error')
            text: Status text to display
            show_time: Whether to show timestamp
        """
        self.current_status = status
        self.status_text = text or self.get_default_text(status)
        
        # Update visual indicator
        self.update_indicator()
        
        # Update text
        self.status_label.config(
            text=self.status_text,
            fg=self.COLORS[status]
        )
        
        # Update time
        if show_time:
            current_time = datetime.now().strftime('%H:%M:%S')
            self.time_label.config(text=f'[{current_time}]')
        else:
            self.time_label.config(text='')
    
    def get_default_text(self, status):
        """
        Get default text for status
        
        Args:
            status: Status type
            
        Returns:
            Default text for the status
        """
        defaults = {
            'not_analyzed': t_gui('status_not_analyzed'),
            'analyzing': t_gui('status_analyzing'),
            'completed': t_gui('status_completed'),
            'error': t_gui('status_error')
        }
        return defaults.get(status, t_gui('status_unknown'))
    
    def update_indicator(self):
        """
        Update visual indicator based on current status
        """
        self.canvas.delete('all')
        
        color = self.COLORS[self.current_status]
        
        if self.current_status == 'not_analyzed':
            # Gray circle for not analyzed
            self.canvas.create_oval(
                10, 5, 25, 20,
                fill=color, outline=color
            )
            self.canvas.create_text(
                self.width // 2, self.height // 2,
                text=t_gui('status_not_analyzed'),
                fill=color,
                font=('Microsoft YaHei', 9)
            )
            
        elif self.current_status == 'analyzing':
            # Orange spinning indicator for analyzing
            self.canvas.create_oval(
                10, 5, 25, 20,
                fill=color, outline=color
            )
            # Add animated dots
            self.canvas.create_text(
                self.width // 2, self.height // 2,
                text=t_gui('status_analyzing'),
                fill=color,
                font=('Microsoft YaHei', 9)
            )
            # Start animation
            self.animate_analyzing()
            
        elif self.current_status == 'completed':
            # Green checkmark for completed
            self.canvas.create_oval(
                10, 5, 25, 20,
                fill=color, outline=color
            )
            # Checkmark
            self.canvas.create_text(
                17, 12,
                text='✓',
                fill='white',
                font=('Microsoft YaHei', 12, 'bold')
            )
            self.canvas.create_text(
                self.width // 2, self.height // 2,
                text=t_gui('status_completed'),
                fill=color,
                font=('Microsoft YaHei', 9)
            )
            
        elif self.current_status == 'error':
            # Red X for error
            self.canvas.create_oval(
                10, 5, 25, 20,
                fill=color, outline=color
            )
            # X mark
            self.canvas.create_text(
                17, 12,
                text='✗',
                fill='white',
                font=('Microsoft YaHei', 12, 'bold')
            )
            self.canvas.create_text(
                self.width // 2, self.height // 2,
                text=t_gui('status_error'),
                fill=color,
                font=('Microsoft YaHei', 9)
            )
    
    def animate_analyzing(self):
        """
        Animate the analyzing indicator
        """
        if self.current_status == 'analyzing':
            # Simple animation - change the dots
            current_text = self.status_label.cget('text')
            if current_text.endswith('...'):
                new_text = current_text[:-3]
            elif current_text.endswith('..'):
                new_text = current_text + '.'
            elif current_text.endswith('.'):
                new_text = current_text + '.'
            else:
                new_text = current_text + '.'
            
            self.status_label.config(text=new_text)
            
            # Schedule next animation frame
            self.parent.after(500, self.animate_analyzing)
    
    def pack(self, **kwargs):
        """
        Pack the indicator frame
        """
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        """
        Grid the indicator frame
        """
        self.frame.grid(**kwargs)
    
    def place(self, **kwargs):
        """
        Place the indicator frame
        """
        self.frame.place(**kwargs)


class StatusIndicatorDemo:
    """
    Demo application for status indicator
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Analysis Status Indicator Demo")
        self.root.geometry("600x400")
        self.root.configure(bg='#f8f9fa')
        
        # Center window
        self.center_window()
        
        # Setup UI
        self.setup_ui()
    
    def center_window(self):
        """
        Center window on screen
        """
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """
        Setup demo UI
        """
        # Title
        title_label = tk.Label(
            self.root,
            text="Analysis Status Indicator Demo",
            font=('Microsoft YaHei', 16, 'bold'),
            bg='#f8f9fa',
            fg='#212529'
        )
        title_label.pack(pady=20)
        
        # Status indicators
        indicators_frame = tk.Frame(self.root, bg='#f8f9fa')
        indicators_frame.pack(pady=20)
        
        # Create multiple indicators
        self.indicators = []
        
        # Data Loading Status
        data_frame = tk.Frame(indicators_frame, bg='#f8f9fa')
        data_frame.pack(fill=tk.X, pady=5)
        tk.Label(data_frame, text="Data Loading:", bg='#f8f9fa', fg='#495057',
                font=('Microsoft YaHei', 11, 'bold')).pack(side=tk.LEFT, padx=10)
        self.data_indicator = AnalysisStatusIndicator(data_frame)
        self.data_indicator.pack(side=tk.LEFT)
        self.indicators.append(('data', self.data_indicator))
        
        # Analysis Status
        analysis_frame = tk.Frame(indicators_frame, bg='#f8f9fa')
        analysis_frame.pack(fill=tk.X, pady=5)
        tk.Label(analysis_frame, text="Analysis:", bg='#f8f9fa', fg='#495057',
                font=('Microsoft YaHei', 11, 'bold')).pack(side=tk.LEFT, padx=10)
        self.analysis_indicator = AnalysisStatusIndicator(analysis_frame)
        self.analysis_indicator.pack(side=tk.LEFT)
        self.indicators.append(('analysis', self.analysis_indicator))
        
        # AI Analysis Status
        ai_frame = tk.Frame(indicators_frame, bg='#f8f9fa')
        ai_frame.pack(fill=tk.X, pady=5)
        tk.Label(ai_frame, text="AI Analysis:", bg='#f8f9fa', fg='#495057',
                font=('Microsoft YaHei', 11, 'bold')).pack(side=tk.LEFT, padx=10)
        self.ai_indicator = AnalysisStatusIndicator(ai_frame)
        self.ai_indicator.pack(side=tk.LEFT)
        self.indicators.append(('ai', self.ai_indicator))
        
        # Control buttons
        control_frame = tk.Frame(self.root, bg='#f8f9fa')
        control_frame.pack(pady=30)
        
        button_style = {
            'font': ('Microsoft YaHei', 10),
            'relief': tk.RAISED,
            'bd': 2,
            'padx': 15,
            'pady': 5
        }
        
        tk.Button(control_frame, text="Start Demo", command=self.start_demo,
                 bg='#28a745', fg='white', **button_style).pack(side=tk.LEFT, padx=5)
        
        tk.Button(control_frame, text="Reset", command=self.reset_demo,
                 bg='#6c757d', fg='white', **button_style).pack(side=tk.LEFT, padx=5)
        
        tk.Button(control_frame, text="Show Error", command=self.show_error,
                 bg='#dc3545', fg='white', **button_style).pack(side=tk.LEFT, padx=5)
        
        # Instructions
        instructions = tk.Text(self.root, height=8, bg='white', fg='#212529',
                              font=('Microsoft YaHei', 10), wrap=tk.WORD)
        instructions.pack(fill=tk.X, padx=20, pady=10)
        
        instructions_text = """
Status Indicator Color Scheme (Based on demo_status_messages.py):

• Gray (#6c757d): Not Analyzed - Initial state, ready for analysis
• Orange (#ff6600): Analyzing - Analysis in progress with animation
• Green (#28a745): Completed - Analysis finished successfully
• Red (#dc3545): Error - Analysis failed or encountered error

Click 'Start Demo' to see the status progression simulation.
Click 'Reset' to return all indicators to initial state.
Click 'Show Error' to demonstrate error state.
"""
        
        instructions.insert(tk.END, instructions_text)
        instructions.config(state=tk.DISABLED)
    
    def start_demo(self):
        """
        Start demo sequence
        """
        # Reset first
        self.reset_demo()
        
        # Simulate data loading
        self.root.after(500, lambda: self.data_indicator.set_status('analyzing', 'Loading data...'))
        self.root.after(2000, lambda: self.data_indicator.set_status('completed', 'Data loaded'))
        
        # Simulate analysis
        self.root.after(2500, lambda: self.analysis_indicator.set_status('analyzing', 'Running analysis...'))
        self.root.after(5000, lambda: self.analysis_indicator.set_status('completed', 'Analysis complete'))
        
        # Simulate AI analysis
        self.root.after(5500, lambda: self.ai_indicator.set_status('analyzing', 'AI analyzing...'))
        self.root.after(8000, lambda: self.ai_indicator.set_status('completed', 'AI analysis complete'))
    
    def reset_demo(self):
        """
        Reset all indicators
        """
        self.data_indicator.set_status('not_analyzed', 'Ready for data')
        self.analysis_indicator.set_status('not_analyzed', 'Ready for analysis')
        self.ai_indicator.set_status('not_analyzed', 'Ready for AI analysis')
    
    def show_error(self):
        """
        Show error state
        """
        self.data_indicator.set_status('error', 'Data load failed')
        self.analysis_indicator.set_status('error', 'Analysis failed')
        self.ai_indicator.set_status('error', 'AI analysis failed')
    
    def run(self):
        """
        Run the demo
        """
        self.root.mainloop()


if __name__ == "__main__":
    demo = StatusIndicatorDemo()
    demo.run()