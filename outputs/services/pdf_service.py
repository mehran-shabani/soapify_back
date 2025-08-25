"""
PDF generation service using WeasyPrint with Persian font support.
"""

import os
import tempfile
import logging
import time
from typing import Dict
import boto3
from django.conf import settings

# Try to import WeasyPrint, but handle Windows GTK+ issues gracefully
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except OSError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"WeasyPrint not available due to missing GTK+ libraries: {e}")
    logger.warning("PDF generation will be disabled. Install GTK+ for Windows from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
    WEASYPRINT_AVAILABLE = False
    # Dummy classes to prevent import errors
    class HTML:
        pass
    class CSS:
        pass
    class FontConfiguration:
        pass

logger = logging.getLogger(__name__)


class PDFService:
    """Service for generating PDF files from HTML content."""
    
    def __init__(self):
        if WEASYPRINT_AVAILABLE:
            self.font_config = FontConfiguration()
        else:
            self.font_config = None
        
        # استفاده از MinIO client
        from uploads.minio import get_minio_client
        self.minio_client = get_minio_client()
    
    def generate_pdf_from_html(
        self,
        html_content: str,
        output_filename: str,
        upload_to_s3: bool = True
    ) -> Dict:
        """
        Generate PDF from HTML content.
        
        Args:
            html_content: HTML content to convert
            output_filename: Name for the output file
            upload_to_s3: Whether to upload to S3
            
        Returns:
            Dict with file info and S3 details
        """
        if not WEASYPRINT_AVAILABLE:
            logger.error("PDF generation is not available. Please install GTK+ for Windows.")
            raise RuntimeError("WeasyPrint is not available due to missing GTK+ libraries. "
                             "Install from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
        
        start_time = time.time()
        
        try:
            # Create temporary file for PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            logger.info(f"Generating PDF: {output_filename}")
            
            # Generate PDF with Persian font support
            html_doc = HTML(string=html_content, base_url='.')
            
            # CSS for Persian font
            persian_css = CSS(string="""
                @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
                
                body {
                    font-family: 'Vazirmatn', 'Tahoma', 'Arial Unicode MS', sans-serif;
                    direction: rtl;
                    text-align: right;
                }
                
                @page {
                    size: A4;
                    margin: 2cm;
                    @bottom-center {
                        content: "صفحه " counter(page) " از " counter(pages);
                        font-size: 10pt;
                        color: #666;
                    }
                }
            """, font_config=self.font_config)
            
            # Generate PDF
            html_doc.write_pdf(
                temp_pdf_path,
                stylesheets=[persian_css],
                font_config=self.font_config
            )
            
            # Get file size
            file_size = os.path.getsize(temp_pdf_path)
            generation_time = time.time() - start_time
            
            logger.info(f"PDF generated in {generation_time:.2f}s, size: {file_size} bytes")
            
            result = {
                'local_path': temp_pdf_path,
                'file_size': file_size,
                'generation_time': generation_time,
                'filename': output_filename
            }
            
            # Upload to S3 if requested
            if upload_to_s3:
                s3_result = self._upload_pdf_to_s3(temp_pdf_path, output_filename)
                result.update(s3_result)
            
            return result
            
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            # Clean up temp file on error
            if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            raise
    
    def _upload_pdf_to_s3(self, local_path: str, filename: str) -> Dict:
        """Upload PDF file to S3 and return details."""
        try:
            # Generate S3 key
            s3_key = f"outputs/pdf/{filename}"
            
            # Upload file
            self.minio_client.upload_file(
                local_path,
                settings.MINIO_MEDIA_BUCKET,
                s3_key,
                ExtraArgs={
                    'ContentType': 'application/pdf',
                    'ContentDisposition': f'attachment; filename="{filename}"'
                }
            )
            
            logger.info(f"Uploaded PDF to S3: {s3_key}")
            
            return {
                's3_key': s3_key,
                's3_bucket': settings.MINIO_MEDIA_BUCKET,
                'uploaded': True
            }
            
        except Exception as e:
            logger.error(f"Failed to upload PDF to S3: {e}")
            return {
                's3_key': None,
                's3_bucket': None,
                'uploaded': False,
                'upload_error': str(e)
            }
        finally:
            # Clean up local file
            if os.path.exists(local_path):
                os.unlink(local_path)
    
    def generate_presigned_download_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """
        Generate presigned URL for PDF download.
        
        Args:
            s3_key: S3 object key
            expires_in: URL expiration time in seconds
            
        Returns:
            Presigned download URL
        """
        try:
            presigned_url = self.minio_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.MINIO_MEDIA_BUCKET,
                    'Key': s3_key,
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned URL for {s3_key}")
            return presigned_url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            raise
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up old temporary PDF files."""
        try:
            temp_dir = tempfile.gettempdir()
            current_time = time.time()
            cleaned_count = 0
            
            for filename in os.listdir(temp_dir):
                if filename.endswith('.pdf'):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > (max_age_hours * 3600):
                            os.unlink(file_path)
                            cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {file_path}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} old PDF files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"PDF cleanup failed: {e}")
            return 0



