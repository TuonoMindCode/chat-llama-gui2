"""
Image Viewer Widget for displaying generated images in split-view
"""

import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk
from pathlib import Path


class ImageViewerWidget:
    """Widget for displaying generated images with scrolling and controls"""
    
    def __init__(self, parent, width=400, height=600, on_image_changed=None, zoom_mode=False):
        """
        Initialize image viewer
        
        Args:
            parent: Parent tkinter widget
            width: Widget width
            height: Widget height
            on_image_changed: Callback when image changes (for alignment with chat)
            zoom_mode: If True, hide filename and scrollbar, maximize image area
        """
        self.parent = parent
        self.width = width
        self.height = height
        self.images_list = []  # List of image paths
        self.current_image_index = 0
        self.photo_images = {}  # Cache for PhotoImage objects
        self.on_image_changed = on_image_changed  # Callback for image changes
        self.image_timestamps = {}  # Maps image path to timestamp for alignment
        self.zoom_mode = zoom_mode  # If True, hide UI elements and maximize image
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create UI widgets"""
        # Main frame
        self.main_frame = tk.Frame(self.parent, bg="#f0f0f0", relief=tk.SUNKEN, bd=1)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind resize event to update image dimensions while maintaining aspect ratio
        self.main_frame.bind("<Configure>", self._on_frame_resize)
        
        # Header frame
        header_frame = tk.Frame(self.main_frame, bg="#f0f0f0")
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Left side of header
        left_header = tk.Frame(header_frame, bg="#f0f0f0")
        left_header.pack(side=tk.LEFT)
        
        tk.Label(
            left_header,
            text="Generated Images",
            bg="#f0f0f0",
            font=("Arial", 12, "bold")
        ).pack(side=tk.LEFT)
        
        # Image count label
        self.image_count_label = tk.Label(
            left_header,
            text="(0 images)",
            bg="#f0f0f0",
            fg="#666666",
            font=("Arial", 9)
        )
        self.image_count_label.pack(side=tk.LEFT, padx=10)
        
        # Status label
        self.status_label = tk.Label(
            left_header,
            text="Ready",
            bg="#f0f0f0",
            fg="#009900",
            font=("Arial", 9)
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Right side of header - buttons
        right_header = tk.Frame(header_frame, bg="#f0f0f0")
        right_header.pack(side=tk.RIGHT)
        
        tk.Button(
            right_header,
            text="← Prev",
            command=self.show_previous_image,
            bg="#0099cc",
            fg="white",
            width=8,
            font=("Arial", 8)
        ).pack(side=tk.LEFT, padx=1)
        
        # Image index label
        self.index_label = tk.Label(
            right_header,
            text="No images",
            bg="#f0f0f0",
            fg="#333333",
            font=("Arial", 8)
        )
        self.index_label.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            right_header,
            text="Next →",
            command=self.show_next_image,
            bg="#0099cc",
            fg="white",
            width=8,
            font=("Arial", 8)
        ).pack(side=tk.LEFT, padx=1)
        
        tk.Button(
            right_header,
            text="Save",
            command=self.save_current_image,
            bg="#00cc66",
            fg="white",
            width=6,
            font=("Arial", 8)
        ).pack(side=tk.LEFT, padx=1)
        
        tk.Button(
            right_header,
            text="Clear",
            command=self.clear_all_images,
            bg="#ff6600",
            fg="white",
            width=6,
            font=("Arial", 8)
        ).pack(side=tk.LEFT, padx=1)
        
        # Image display frame
        self.display_frame = tk.Frame(self.main_frame, bg="white", relief=tk.SUNKEN, bd=1)
        self.display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Canvas for image display with scrollbar
        self.scrollbar = tk.Scrollbar(self.display_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas = tk.Canvas(
            self.display_frame,
            bg="white",
            highlightthickness=0,
            yscrollcommand=self.scrollbar.set,
            width=self.width - 30,
            height=self.height - 100
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.canvas.yview)
        
        # Inner frame for canvas
        self.canvas_frame = tk.Frame(self.canvas, bg="white")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.canvas_frame, anchor="nw")
        
        # Bind mouse wheel for image scrolling - bind to canvas_frame so it works on images too
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)  # Windows
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)   # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)   # Linux scroll down
        self.canvas_frame.bind("<MouseWheel>", self._on_mouse_wheel)  # Windows - on frame
        self.canvas_frame.bind("<Button-4>", self._on_mouse_wheel)   # Linux scroll up - on frame
        self.canvas_frame.bind("<Button-5>", self._on_mouse_wheel)   # Linux scroll down - on frame
        
        self.canvas_frame.bind("<Configure>", self._on_canvas_configure)
    
    def _on_canvas_configure(self, event):
        """Adjust canvas scroll region"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling to change images"""
        if not self.images_list:
            return
        
        # Determine scroll direction
        if event.num == 5 or event.delta < 0:  # Scroll down or wheel down
            self.show_next_image()
        else:  # Scroll up or wheel up
            self.show_previous_image()
    
    def _on_frame_resize(self, event):
        """Handle frame resize - refresh images to maintain aspect ratio"""
        # Update width based on actual frame size
        if event.width > 0:
            self.width = event.width
        # Refresh images if any are loaded - clear photo cache so images re-render at new size
        if self.images_list:
            self.photo_images.clear()  # Clear cached images so they re-render at new size
            # Re-apply zoom mode with new width to adjust canvas size properly
            self.set_zoom_mode(self.zoom_mode)
    
    def set_zoom_mode(self, enabled):
        """
        Enable or disable zoom mode
        
        When zoom mode is enabled:
        - Filename labels are hidden
        - Scrollbar is hidden
        - Images expand to fill entire area
        - Minimal padding
        """
        self.zoom_mode = enabled
        
        # Get current frame width for proper calculation
        current_frame_width = self.main_frame.winfo_width()
        if current_frame_width < 1:
            current_frame_width = self.width  # Fallback to stored width
        
        # Hide/show scrollbar and adjust canvas accordingly
        if enabled:
            # Zoom mode: hide scrollbar, expand canvas to use full width
            self.scrollbar.pack_forget()
            # Use almost full frame width (just small margin)
            new_canvas_width = current_frame_width - 15
            self.canvas.config(width=new_canvas_width)
        else:
            # Normal mode: show scrollbar, reduce canvas width for scrollbar space
            new_canvas_width = current_frame_width - 45  # Account for scrollbar
            self.canvas.config(width=new_canvas_width)
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Force geometry update and then refresh display
        self.canvas.update_idletasks()
        
        # Refresh display to apply changes
        if self.images_list:
            self.photo_images.clear()
            self.display_images()
    
    def add_image(self, image_path):
        """
        Add image to viewer
        
        Args:
            image_path: Path to image file
        """
        try:
            image_path = str(image_path)
            if Path(image_path).exists():
                self.images_list.append(image_path)
                self.current_image_index = len(self.images_list) - 1
                print(f"[DEBUG] Added image: {image_path}")
                self.display_images()
                self.scroll_to_current_image()  # Auto-scroll to new image
                self.update_status(f"Image added ({len(self.images_list)} total)", "#009900")
            else:
                print(f"[DEBUG] Image file not found: {image_path}")
                self.update_status("Image file not found", "#cc0000")
        except Exception as e:
            print(f"[DEBUG] Error adding image: {e}")
            self.update_status("Error adding image", "#cc0000")
    
    def display_image_by_path(self, image_path):
        """
        Display a specific image by path and center it in the viewer
        
        Args:
            image_path: Path to image file to display
        """
        try:
            image_path = str(image_path)
            if Path(image_path).exists():
                # Add image if not already in list
                if image_path not in self.images_list:
                    self.images_list.append(image_path)
                
                # Find and set current index
                self.current_image_index = self.images_list.index(image_path)
                print(f"[DEBUG] Displaying image by path: {image_path} (index: {self.current_image_index})")
                
                # Force refresh: clear cache and re-render to ensure zoom mode is applied
                self.photo_images.clear()
                
                # Update display
                self.display_images()
                
                # Use after to ensure display is rendered before scrolling
                self.parent.after(50, self.scroll_to_current_image)
                
                self.index_label.config(text=f"{self.current_image_index + 1} / {len(self.images_list)}")
                self.update_status(f"Centered on image", "#009900")
            else:
                print(f"[DEBUG] Image file not found: {image_path}")
                self.update_status("Image file not found", "#cc0000")
        except Exception as e:
            print(f"[DEBUG] Error displaying image by path: {e}")
            self.update_status("Error displaying image", "#cc0000")
    
    def display_images(self):
        """Display all images in the viewer (or just current in zoom mode)"""
        try:
            # Clear canvas
            for widget in self.canvas_frame.winfo_children():
                widget.destroy()
            
            if not self.images_list:
                tk.Label(
                    self.canvas_frame,
                    text="No images generated yet",
                    bg="white",
                    fg="#999999",
                    font=("Arial", 11)
                ).pack(pady=20)
                self.index_label.config(text="No images")
                self.image_count_label.config(text="(0 images)")
                return
            
            # In zoom mode, only display the current image
            # In normal mode, display all images as a scrollable list
            if self.zoom_mode:
                # Only show current image
                if 0 <= self.current_image_index < len(self.images_list):
                    current_image = self.images_list[self.current_image_index]
                    self._display_image_item(current_image, self.current_image_index)
            else:
                # Display all images as thumbnails
                for i, image_path in enumerate(self.images_list):
                    self._display_image_item(image_path, i)
            
            # Update labels
            self.image_count_label.config(text=f"({len(self.images_list)} images)")
            self.index_label.config(text=f"{self.current_image_index + 1} / {len(self.images_list)}")
            
        except Exception as e:
            print(f"[DEBUG] Error displaying images: {e}")
    
    def _display_image_item(self, image_path, index):
        """Display individual image item"""
        try:
            # Load image
            img = Image.open(image_path)
            
            # Calculate display size to fill available space
            # Get actual canvas/frame dimensions
            canvas_width = self.canvas.winfo_width()
            frame_width = self.main_frame.winfo_width()
            
            # Use whichever is larger, with fallback to self.width
            if canvas_width > 1:
                available_width = canvas_width - 20  # Small padding
            elif frame_width > 1:
                available_width = frame_width - 20
            else:
                available_width = self.width - 20
            
            # Ensure minimum reasonable size
            available_width = max(available_width, 250)
            
            max_height = 1200  # Large max height for full image display
            
            print(f"[DEBUG] Image sizing: available_width={available_width}, max_height={max_height}")
            
            # Resize image to fit available space while maintaining aspect ratio
            img.thumbnail((available_width, max_height), Image.Resampling.LANCZOS)
            
            print(f"[DEBUG] Resized image to: {img.size}")
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            self.photo_images[str(image_path)] = photo  # Keep reference
            
            # Create frame for this image
            item_frame = tk.Frame(self.canvas_frame, bg="white", relief=tk.RIDGE, bd=1)
            item_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Label with image name - only show if not in zoom mode
            if not self.zoom_mode:
                label = tk.Label(
                    item_frame,
                    text=f"Image {index + 1}: {Path(image_path).name}",
                    bg="#f0f0f0",
                    fg="#333333",
                    font=("Arial", 9),
                    anchor="w"
                )
                label.pack(fill=tk.X, padx=5, pady=2)
            
            # Image display with fill expansion
            img_label = tk.Label(item_frame, image=photo, bg="white")
            img_label.image = photo
            img_label.pack(padx=5 if not self.zoom_mode else 0, pady=5 if not self.zoom_mode else 0, fill=tk.BOTH, expand=True)
            
            # Bind mouse wheel to image label too
            img_label.bind("<MouseWheel>", self._on_mouse_wheel)  # Windows
            img_label.bind("<Button-4>", self._on_mouse_wheel)   # Linux scroll up
            img_label.bind("<Button-5>", self._on_mouse_wheel)   # Linux scroll down
            
        except Exception as e:
            print(f"[DEBUG] Error displaying image item: {e}")
            error_label = tk.Label(
                self.canvas_frame,
                text=f"Error loading: {Path(image_path).name}",
                bg="white",
                fg="#cc0000",
                font=("Arial", 9)
            )
            error_label.pack(pady=5)
    
    def show_previous_image(self):
        """Show previous image - stop at first image (don't cycle)"""
        if self.images_list and self.current_image_index > 0:
            self.current_image_index -= 1
            self.index_label.config(text=f"{self.current_image_index + 1} / {len(self.images_list)}")
            self.display_images()  # Refresh display for zoom mode
            self.scroll_to_current_image()
            self._trigger_image_changed()
    
    def show_next_image(self):
        """Show next image - stop at last image (don't cycle)"""
        if self.images_list and self.current_image_index < len(self.images_list) - 1:
            self.current_image_index += 1
            self.index_label.config(text=f"{self.current_image_index + 1} / {len(self.images_list)}")
            self.display_images()  # Refresh display for zoom mode
            self.scroll_to_current_image()
            self._trigger_image_changed()
    
    def save_current_image(self):
        """Save current image"""
        if self.images_list and self.current_image_index < len(self.images_list):
            image_path = self.images_list[self.current_image_index]
            print(f"[DEBUG] Saving image: {image_path}")
            self.update_status(f"Saved: {Path(image_path).name}", "#009900")
    
    def refresh_display(self):
        """Refresh image display - clears and redraws with current frame size"""
        # Clear the canvas frame
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()
        
        # Redisplay images with new size
        self.display_images()
    
    def scroll_to_current_image(self):
        """Scroll canvas to show the current image"""
        try:
            # In zoom mode, always scroll to top to show full image
            if self.zoom_mode:
                self.canvas.yview_moveto(0.0)
                print(f"[DEBUG] Scrolled to image {self.current_image_index + 1}, fraction: 0.0 (zoom mode)")
            else:
                # Calculate position based on image height
                # Each image is approximately: 40px label + image height + 20px padding
                # Approximate calculation for scroll position
                scroll_fraction = (self.current_image_index / max(len(self.images_list), 1)) if self.images_list else 0
                
                # Use canvas yview_moveto to scroll to fraction (0.0 to 1.0)
                # For last image, scroll near to bottom
                if self.current_image_index == len(self.images_list) - 1:
                    self.canvas.yview_moveto(1.0)  # Scroll to bottom for last image
                else:
                    self.canvas.yview_moveto(scroll_fraction)
                
                print(f"[DEBUG] Scrolled to image {self.current_image_index + 1}, fraction: {scroll_fraction}")
        except Exception as e:
            print(f"[DEBUG] Error scrolling to image: {e}")
    
    def clear_all_images(self):
        """Clear all images"""
        self.images_list.clear()
        self.current_image_index = 0
        self.photo_images.clear()
        self.display_images()
        self.update_status("Cleared all images", "#ff9900")
    
    def update_status(self, message, color="#009900"):
        """Update status label"""
        self.status_label.config(text=message, fg=color)
    
    def set_generating_status(self):
        """Set status to generating"""
        self.update_status("⏳ Generating...", "#0066cc")
    
    def set_error_status(self, message):
        """Set error status"""
        self.update_status(f"❌ {message}", "#cc0000")
    
    def set_ready_status(self):
        """Set ready status"""
        self.update_status("Ready", "#009900")
    
    def set_image_timestamp(self, image_path, timestamp):
        """Store timestamp for an image (for alignment with chat)"""
        self.image_timestamps[str(image_path)] = timestamp
    
    def get_current_image_timestamp(self):
        """Get timestamp of current image"""
        if self.images_list and self.current_image_index < len(self.images_list):
            image_path = self.images_list[self.current_image_index]
            return self.image_timestamps.get(str(image_path))
        return None
    
    def _trigger_image_changed(self):
        """Trigger callback when image changes (for alignment)"""
        if self.on_image_changed:
            timestamp = self.get_current_image_timestamp()
            self.on_image_changed(timestamp)
