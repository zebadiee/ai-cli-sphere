"""
Image Processor

Validates and processes evidence images.
Handles format validation, EXIF extraction, and thumbnail generation.
"""

import io
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ImageProcessor:
    """
    Processes and validates evidence images.
    """
    
    SUPPORTED_FORMATS = {"JPEG", "JPG", "PNG", "HEIC", "HEIF"}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    THUMBNAIL_SIZE = (300, 300)
    
    def __init__(self):
        """Initialize the image processor."""
        if not PIL_AVAILABLE:
            raise ImportError("Pillow is required for image processing. Install with: pip install Pillow")
    
    def validate_image(self, image_path: str) -> Dict:
        """
        Validate an image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Validation result with status and any errors
        """
        errors = []
        
        # Check file exists
        if not os.path.exists(image_path):
            errors.append(f"File not found: {image_path}")
            return {"valid": False, "errors": errors}
        
        # Check file size
        file_size = os.path.getsize(image_path)
        if file_size > self.MAX_FILE_SIZE:
            errors.append(f"File too large: {file_size} bytes (max {self.MAX_FILE_SIZE})")
        
        # Try to open and validate format
        try:
            with Image.open(image_path) as img:
                format_name = img.format
                if format_name not in self.SUPPORTED_FORMATS:
                    errors.append(f"Unsupported format: {format_name}")
                
                # Check image dimensions
                width, height = img.size
                if width < 100 or height < 100:
                    errors.append(f"Image too small: {width}x{height} (minimum 100x100)")
        except Exception as e:
            errors.append(f"Failed to open image: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "file_size": file_size if not errors else None
        }
    
    def validate_image_data(self, image_data: bytes) -> Dict:
        """
        Validate image data from bytes.
        
        Args:
            image_data: Image data as bytes
            
        Returns:
            Validation result
        """
        errors = []
        
        # Check size
        data_size = len(image_data)
        if data_size > self.MAX_FILE_SIZE:
            errors.append(f"Data too large: {data_size} bytes (max {self.MAX_FILE_SIZE})")
        
        # Try to open and validate
        try:
            img = Image.open(io.BytesIO(image_data))
            format_name = img.format
            if format_name not in self.SUPPORTED_FORMATS:
                errors.append(f"Unsupported format: {format_name}")
            
            # Check dimensions
            width, height = img.size
            if width < 100 or height < 100:
                errors.append(f"Image too small: {width}x{height} (minimum 100x100)")
        except Exception as e:
            errors.append(f"Failed to parse image data: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "data_size": data_size if not errors else None
        }
    
    def process_image(self, image_path: str) -> Dict:
        """
        Process an image file: extract metadata and create thumbnail.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Processing result with metadata and thumbnail
        """
        with Image.open(image_path) as img:
            # Extract basic metadata
            metadata = {
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.size[0],
                "height": img.size[1],
            }
            
            # Extract EXIF data if available
            exif_data = self._extract_exif(img)
            if exif_data:
                metadata["exif"] = exif_data
            
            # Create thumbnail
            thumbnail_data = self._create_thumbnail(img)
            
            return {
                "metadata": metadata,
                "thumbnail": thumbnail_data
            }
    
    def process_image_data(self, image_data: bytes) -> Dict:
        """
        Process image data from bytes.
        
        Args:
            image_data: Image data as bytes
            
        Returns:
            Processing result
        """
        img = Image.open(io.BytesIO(image_data))
        
        # Extract metadata
        metadata = {
            "format": img.format,
            "mode": img.mode,
            "size": img.size,
            "width": img.size[0],
            "height": img.size[1],
        }
        
        # Extract EXIF
        exif_data = self._extract_exif(img)
        if exif_data:
            metadata["exif"] = exif_data
        
        # Create thumbnail
        thumbnail_data = self._create_thumbnail(img)
        
        return {
            "metadata": metadata,
            "thumbnail": thumbnail_data
        }
    
    def _extract_exif(self, img: Image.Image) -> Optional[Dict]:
        """
        Extract EXIF data from image.
        
        Args:
            img: PIL Image object
            
        Returns:
            Dictionary of EXIF data or None
        """
        try:
            exif = img._getexif()
            if not exif:
                return None
            
            exif_data = {}
            for tag_id, value in exif.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                # Convert bytes to string if needed
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8')
                    except:
                        value = str(value)
                exif_data[tag] = value
            
            return exif_data
        except:
            return None
    
    def _create_thumbnail(self, img: Image.Image) -> bytes:
        """
        Create a thumbnail of the image.
        
        Args:
            img: PIL Image object
            
        Returns:
            Thumbnail image data as bytes
        """
        # Create a copy to avoid modifying original
        thumb = img.copy()
        thumb.thumbnail(self.THUMBNAIL_SIZE)
        
        # Convert to bytes
        buffer = io.BytesIO()
        thumb.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()


# Export main class
__all__ = ["ImageProcessor"]
