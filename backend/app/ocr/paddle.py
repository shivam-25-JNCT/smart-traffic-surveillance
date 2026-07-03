import logging
import easyocr
import re

logger = logging.getLogger("traffic-anpr")

class PlateOCRReader:
    def __init__(self):
        self.reader = None

    def load_model(self):
        """EasyOCR lightweight model pre-load sequences"""
        if self.reader is None:
            try:
                logger.info("Initializing EasyOCR Lightweight Engine (English)...")
                self.reader = easyocr.Reader(['en'], gpu=False)
                logger.info("✅ EasyOCR Engine loaded successfully!")
            except Exception as e:
                logger.error(f"❌ Failed to initialize EasyOCR: {e}")
                raise e

    def clean_plate_text(self, text):
        """Standard Indian License Plate filter masks"""
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        return cleaned

    def extract_text(self, cropped_plate_frame):
        """Direct bounding array reading logic"""
        if self.reader is None:
            self.load_model()

        if cropped_plate_frame is None or cropped_plate_frame.size == 0:
            return None, 0.0

        try:
            results = self.reader.readtext(cropped_plate_frame)
            if results:
                for res in results:
                    raw_text = res[1]
                    confidence = float(res[2])
                    cleaned_text = self.clean_plate_text(raw_text)
                    
                    if len(cleaned_text) >= 4:
                        logger.info(f"🔍 [EasyOCR MATCH] Text: {cleaned_text} | Conf: {confidence:.2f}")
                        return cleaned_text, confidence
        except Exception as e:
            logger.error(f"Error during EasyOCR pipeline execution: {e}")
            
        return None, 0.0

ocr_reader = PlateOCRReader()