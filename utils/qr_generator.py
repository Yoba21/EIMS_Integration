# -*- coding: utf-8 -*-

import qrcode
import base64
from io import BytesIO
import logging
from PIL import Image, ImageDraw, ImageFont
import os

_logger = logging.getLogger(__name__)


def generate_qr_code(data, size=600, error_correction=qrcode.constants.ERROR_CORRECT_L, 
                    border=4, box_size=10, fill_color="black", back_color="white"):
    """
    Generate QR code image from data
    
    Args:
        data (str): Data to encode in QR code
        size (int): Size of the QR code image (default: 600)
        error_correction: Error correction level (default: ERROR_CORRECT_L)
        border (int): Border size (default: 4)
        box_size (int): Box size (default: 10)
        fill_color (str): Fill color (default: "black")
        back_color (str): Background color (default: "white")
    
    Returns:
        str: Base64 encoded PNG image data
    """
    try:
        # Validate input data
        if not validate_qr_data(data):
            raise ValueError("Invalid QR code data")
        
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction,
            box_size=box_size,
            border=border,
        )
        
        # Add data to QR code
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color=fill_color, back_color=back_color)
        
        # Resize image to specified size
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
        
    except Exception as e:
        _logger.error("QR code generation failed: %s", str(e))
        raise


def generate_qr_code_with_logo(data, logo_path=None, size=600, logo_size_ratio=0.2):
    """
    Generate QR code with optional logo overlay
    
    Args:
        data (str): Data to encode in QR code
        logo_path (str): Path to logo image file
        size (int): Size of the QR code image
        logo_size_ratio (float): Logo size as ratio of QR code size
    
    Returns:
        str: Base64 encoded PNG image data
    """
    try:
        # Generate base QR code
        qr_code = generate_qr_code(data, size)
        
        if not logo_path or not os.path.exists(logo_path):
            return qr_code
        
        # Load logo
        logo = Image.open(logo_path)
        
        # Resize logo to fit in QR code
        logo_size = int(size * logo_size_ratio)
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        
        # Convert QR code back to PIL Image
        qr_buffer = BytesIO(base64.b64decode(qr_code))
        qr_img = Image.open(qr_buffer)
        
        # Calculate position to center logo
        logo_position = ((size - logo_size) // 2, (size - logo_size) // 2)
        
        # Paste logo onto QR code
        qr_img.paste(logo, logo_position)
        
        # Convert back to base64
        result_buffer = BytesIO()
        qr_img.save(result_buffer, format='PNG', optimize=True)
        result_buffer.seek(0)
        
        return base64.b64encode(result_buffer.getvalue()).decode('utf-8')
        
    except Exception as e:
        _logger.error("QR code with logo generation failed: %s", str(e))
        # Fallback to regular QR code
        return generate_qr_code(data, size)


def generate_qr_code_with_text(data, text="", size=600, text_position="bottom"):
    """
    Generate QR code with text below or above
    
    Args:
        data (str): Data to encode in QR code
        text (str): Text to add below QR code
        size (int): Size of the QR code image
        text_position (str): Position of text ("bottom" or "top")
    
    Returns:
        str: Base64 encoded PNG image data
    """
    try:
        if not text:
            return generate_qr_code(data, size)
        
        # Generate QR code
        qr_code = generate_qr_code(data, size)
        
        # Convert QR code back to PIL Image
        qr_buffer = BytesIO(base64.b64decode(qr_code))
        qr_img = Image.open(qr_buffer)
        
        # Create new image with space for text
        text_height = 30
        if text_position == "bottom":
            new_height = size + text_height
            new_img = Image.new('RGB', (size, new_height), 'white')
            new_img.paste(qr_img, (0, 0))
            text_y = size + 5
        else:  # top
            new_height = size + text_height
            new_img = Image.new('RGB', (size, new_height), 'white')
            new_img.paste(qr_img, (0, text_height))
            text_y = 5
        
        # Add text
        draw = ImageDraw.Draw(new_img)
        try:
            # Try to use a default font
            font = ImageFont.load_default()
        except:
            font = None
        
        # Calculate text position
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
        else:
            text_width = len(text) * 6  # Approximate width
        
        text_x = (size - text_width) // 2
        
        # Draw text
        draw.text((text_x, text_y), text, fill='black', font=font)
        
        # Convert back to base64
        result_buffer = BytesIO()
        new_img.save(result_buffer, format='PNG', optimize=True)
        result_buffer.seek(0)
        
        return base64.b64encode(result_buffer.getvalue()).decode('utf-8')
        
    except Exception as e:
        _logger.error("QR code with text generation failed: %s", str(e))
        # Fallback to regular QR code
        return generate_qr_code(data, size)


def validate_qr_data(data):
    """
    Validate QR code data
    
    Args:
        data (str): Data to validate
    
    Returns:
        bool: True if data is valid for QR code
    """
    if not data or not isinstance(data, str):
        return False
    
    # Check data length (QR codes have limits)
    if len(data) > 2953:  # Maximum for version 40, error correction L
        _logger.warning("QR code data is very long (%d chars), may cause issues", len(data))
    
    return True


def get_qr_code_info(data):
    """
    Get information about QR code data
    
    Args:
        data (str): Data to analyze
    
    Returns:
        dict: Information about the QR code
    """
    try:
        qr = qrcode.QRCode()
        qr.add_data(data)
        qr.make(fit=True)
        
        return {
            'version': qr.version,
            'size': qr.get_matrix().width,
            'data_length': len(data),
            'error_correction': qr.error_correction,
        }
    except Exception as e:
        _logger.error("Failed to get QR code info: %s", str(e))
        return None


def generate_eims_qr_code(irn, invoice_data=None):
    """
    Generate EIMS-specific QR code with IRN and optional invoice data
    
    Args:
        irn (str): Invoice Reference Number
        invoice_data (dict): Additional invoice data
    
    Returns:
        str: Base64 encoded PNG image data
    """
    try:
        # Create QR data with IRN
        qr_data = f"IRN:{irn}"
        
        # Add additional data if provided
        if invoice_data:
            if 'amount' in invoice_data:
                qr_data += f"|AMT:{invoice_data['amount']}"
            if 'date' in invoice_data:
                qr_data += f"|DATE:{invoice_data['date']}"
            if 'tin' in invoice_data:
                qr_data += f"|TIN:{invoice_data['tin']}"
        
        # Generate QR code with text
        return generate_qr_code_with_text(qr_data, f"IRN: {irn}", size=600)
        
    except Exception as e:
        _logger.error("EIMS QR code generation failed: %s", str(e))
        raise


def batch_generate_qr_codes(data_list, size=600):
    """
    Generate multiple QR codes in batch
    
    Args:
        data_list (list): List of data strings
        size (int): Size of each QR code
    
    Returns:
        list: List of base64 encoded PNG image data
    """
    results = []
    for data in data_list:
        try:
            qr_code = generate_qr_code(data, size)
            results.append(qr_code)
        except Exception as e:
            _logger.error("Failed to generate QR code for data: %s, error: %s", data, str(e))
            results.append(None)
    
    return results
