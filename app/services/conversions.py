"""
File conversion services for FileConverter Pro.
Handles image, PDF, and DOCX conversions.
"""
import os
import subprocess
import zipfile
from pathlib import Path
from typing import List, Optional
from PIL import Image
import img2pdf
from pdf2docx import Converter
from pdf2image import convert_from_path

from app.config import settings
from app.utils.logger import app_logger, error_logger
from app.utils.file_utils import get_conversion_output_filename


class ConversionError(Exception):
    """Custom exception for conversion errors."""
    pass


class FileConverter:
    """Main file converter class."""
    
    def __init__(self):
        """Initialize converter."""
        self.libreoffice_path = settings.LIBREOFFICE_PATH
    
    def convert_image(
        self,
        input_path: str,
        output_path: str,
        target_format: str,
        quality: int = 95
    ) -> str:
        """
        Convert image format using Pillow.
        
        Args:
            input_path: Input image path
            output_path: Output image path
            target_format: Target format (jpg, png, webp)
            quality: Image quality (1-100)
            
        Returns:
            Output file path
            
        Raises:
            ConversionError: If conversion fails
        """
        try:
            with Image.open(input_path) as img:
                # Convert RGBA to RGB for JPG
                if target_format.lower() in ['jpg', 'jpeg'] and img.mode in ['RGBA', 'LA', 'P']:
                    # Create white background
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = rgb_img
                
                # Save with appropriate format
                save_kwargs = {}
                if target_format.lower() in ['jpg', 'jpeg']:
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                elif target_format.lower() == 'webp':
                    save_kwargs['quality'] = quality
                    save_kwargs['method'] = 6  # Best quality
                elif target_format.lower() == 'png':
                    save_kwargs['optimize'] = True
                
                img.save(output_path, format=target_format.upper(), **save_kwargs)
            
            app_logger.info(f"Converted image: {input_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            error_logger.error(f"Image conversion failed: {e}")
            raise ConversionError(f"Image conversion failed: {str(e)}")
    
    def convert_images_to_pdf(
        self,
        input_paths: List[str],
        output_path: str
    ) -> str:
        """
        Convert multiple images to single PDF.
        
        Args:
            input_paths: List of image paths
            output_path: Output PDF path
            
        Returns:
            Output file path
            
        Raises:
            ConversionError: If conversion fails
        """
        try:
            # Convert all images to RGB if needed
            processed_images = []
            
            for img_path in input_paths:
                with Image.open(img_path) as img:
                    # Convert to RGB if necessary
                    if img.mode in ['RGBA', 'LA', 'P']:
                        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        if img.mode == 'RGBA':
                            rgb_img.paste(img, mask=img.split()[-1])
                        else:
                            rgb_img.paste(img)
                        
                        # Save temporary RGB version
                        temp_path = img_path + '.rgb.jpg'
                        rgb_img.save(temp_path, 'JPEG')
                        processed_images.append(temp_path)
                    else:
                        processed_images.append(img_path)
            
            # Create PDF
            with open(output_path, 'wb') as f:
                f.write(img2pdf.convert(processed_images))
            
            # Clean up temporary files
            for temp_img in processed_images:
                if temp_img.endswith('.rgb.jpg'):
                    os.remove(temp_img)
            
            app_logger.info(f"Converted {len(input_paths)} images to PDF: {output_path}")
            return output_path
            
        except Exception as e:
            error_logger.error(f"Images to PDF conversion failed: {e}")
            raise ConversionError(f"Images to PDF conversion failed: {str(e)}")
    
    def convert_pdf_to_docx(
        self,
        input_path: str,
        output_path: str
    ) -> str:
        """
        Convert PDF to DOCX using pdf2docx.
        
        Args:
            input_path: Input PDF path
            output_path: Output DOCX path
            
        Returns:
            Output file path
            
        Raises:
            ConversionError: If conversion fails
        """
        try:
            cv = Converter(input_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()
            
            app_logger.info(f"Converted PDF to DOCX: {input_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            error_logger.error(f"PDF to DOCX conversion failed: {e}")
            raise ConversionError(f"PDF to DOCX conversion failed: {str(e)}")
    
    def convert_pdf_to_images(
        self,
        input_path: str,
        output_dir: str,
        output_format: str = 'png',
        dpi: int = 200
    ) -> List[str]:
        """
        Convert PDF pages to images.
        
        Args:
            input_path: Input PDF path
            output_dir: Output directory for images
            output_format: Output image format (jpg, png)
            dpi: Image DPI
            
        Returns:
            List of output image paths
            
        Raises:
            ConversionError: If conversion fails
        """
        try:
            # Convert PDF to images
            images = convert_from_path(input_path, dpi=dpi)
            
            output_paths = []
            base_name = Path(input_path).stem
            
            for i, image in enumerate(images, start=1):
                output_filename = f"{base_name}_page_{i}.{output_format}"
                output_path = os.path.join(output_dir, output_filename)
                
                # Save image
                if output_format.lower() in ['jpg', 'jpeg']:
                    image.save(output_path, 'JPEG', quality=95, optimize=True)
                else:
                    image.save(output_path, output_format.upper(), optimize=True)
                
                output_paths.append(output_path)
            
            app_logger.info(f"Converted PDF to {len(output_paths)} images: {input_path}")
            return output_paths
            
        except Exception as e:
            error_logger.error(f"PDF to images conversion failed: {e}")
            raise ConversionError(f"PDF to images conversion failed: {str(e)}")
    
    def convert_docx_to_pdf(
        self,
        input_path: str,
        output_path: str
    ) -> str:
        """
        Convert DOCX to PDF using LibreOffice headless.
        
        Args:
            input_path: Input DOCX path
            output_path: Output PDF path
            
        Returns:
            Output file path
            
        Raises:
            ConversionError: If conversion fails
        """
        try:
            # Get output directory
            output_dir = os.path.dirname(output_path)
            
            # Run LibreOffice in headless mode
            cmd = [
                self.libreoffice_path,
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                input_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                raise ConversionError(f"LibreOffice conversion failed: {result.stderr}")
            
            # LibreOffice creates file with same name but .pdf extension
            expected_output = os.path.join(
                output_dir,
                Path(input_path).stem + '.pdf'
            )
            
            # Rename if needed
            if expected_output != output_path and os.path.exists(expected_output):
                os.rename(expected_output, output_path)
            
            if not os.path.exists(output_path):
                raise ConversionError("LibreOffice did not create output file")
            
            app_logger.info(f"Converted DOCX to PDF: {input_path} -> {output_path}")
            return output_path
            
        except subprocess.TimeoutExpired:
            error_logger.error("DOCX to PDF conversion timed out")
            raise ConversionError("Conversion timed out (file too large or complex)")
        except Exception as e:
            error_logger.error(f"DOCX to PDF conversion failed: {e}")
            raise ConversionError(f"DOCX to PDF conversion failed: {str(e)}")
    
    def convert_file(
        self,
        input_path: str,
        output_path: str,
        source_format: str,
        target_format: str
    ) -> str:
        """
        Convert file based on source and target formats.
        
        Args:
            input_path: Input file path
            output_path: Output file path
            source_format: Source format
            target_format: Target format
            
        Returns:
            Output file path
            
        Raises:
            ConversionError: If conversion fails
        """
        source_format = source_format.lower()
        target_format = target_format.lower()
        
        # Image conversions
        if source_format in ['jpg', 'jpeg', 'png', 'webp']:
            if target_format in ['jpg', 'jpeg', 'png', 'webp']:
                return self.convert_image(input_path, output_path, target_format)
            elif target_format == 'pdf':
                return self.convert_images_to_pdf([input_path], output_path)
        
        # PDF conversions
        elif source_format == 'pdf':
            if target_format == 'docx':
                return self.convert_pdf_to_docx(input_path, output_path)
            elif target_format in ['jpg', 'jpeg', 'png']:
                # Convert to images and return first page
                output_dir = os.path.dirname(output_path)
                images = self.convert_pdf_to_images(input_path, output_dir, target_format)
                return images[0] if images else None
        
        # DOCX conversions
        elif source_format == 'docx':
            if target_format == 'pdf':
                return self.convert_docx_to_pdf(input_path, output_path)
        
        raise ConversionError(f"Unsupported conversion: {source_format} -> {target_format}")
    
    def create_zip_archive(self, file_paths: List[str], zip_path: str) -> str:
        """
        Create ZIP archive from multiple files.
        
        Args:
            file_paths: List of file paths to include
            zip_path: Output ZIP path
            
        Returns:
            ZIP file path
        """
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
            
            app_logger.info(f"Created ZIP archive with {len(file_paths)} files: {zip_path}")
            return zip_path
            
        except Exception as e:
            error_logger.error(f"ZIP creation failed: {e}")
            raise ConversionError(f"ZIP creation failed: {str(e)}")


# Global converter instance
converter = FileConverter()
