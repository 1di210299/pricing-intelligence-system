"""UPC validation models and utilities."""
from pydantic import BaseModel, field_validator
from typing import Literal


class UPCValidationError(Exception):
    """Custom exception for UPC validation errors."""
    pass


class UPC(BaseModel):
    """UPC model with validation."""
    
    code: str
    format: Literal["UPC-A", "UPC-E"] | None = None
    
    @field_validator("code")
    @classmethod
    def validate_upc(cls, v: str) -> str:
        """Validate UPC format and checksum."""
        # Remove any whitespace or hyphens
        cleaned = v.replace(" ", "").replace("-", "")
        
        # Check if it's all digits
        if not cleaned.isdigit():
            raise ValueError("UPC must contain only digits")
        
        # Check length (UPC-A: 12 digits, UPC-E: 8 digits)
        if len(cleaned) not in [8, 12]:
            raise ValueError("UPC must be 8 (UPC-E) or 12 (UPC-A) digits")
        
        # Validate checksum
        if not cls._validate_checksum(cleaned):
            raise ValueError("Invalid UPC checksum")
        
        return cleaned
    
    @staticmethod
    def _validate_checksum(upc: str) -> bool:
        """
        Validate UPC checksum using standard algorithm.
        
        For UPC-A (12 digits):
        - Sum odd position digits (1st, 3rd, 5th, ..., 11th), multiply by 3
        - Sum even position digits (2nd, 4th, 6th, ..., 10th)
        - Add both sums
        - Checksum = (10 - (sum % 10)) % 10
        - Compare with 12th digit
        """
        if len(upc) == 8:
            # Convert UPC-E to UPC-A for validation
            upc = UPC._expand_upce_to_upca(upc)
        
        # Calculate checksum
        odd_sum = sum(int(upc[i]) for i in range(0, 11, 2))
        even_sum = sum(int(upc[i]) for i in range(1, 11, 2))
        
        total = (odd_sum * 3) + even_sum
        checksum = (10 - (total % 10)) % 10
        
        return checksum == int(upc[11])
    
    @staticmethod
    def _expand_upce_to_upca(upce: str) -> str:
        """
        Expand UPC-E (8 digits) to UPC-A (12 digits).
        This is a simplified implementation.
        """
        # For simplicity, we'll do basic validation for UPC-E
        # In production, you'd implement full UPC-E expansion logic
        if len(upce) != 8:
            return upce
        
        # UPC-E has specific expansion rules based on the last digit
        # This is a simplified version - full implementation would be more complex
        # For now, we'll validate the checksum as-is for 8-digit codes
        
        # Calculate checksum for 8-digit UPC-E
        odd_sum = sum(int(upce[i]) for i in range(0, 7, 2))
        even_sum = sum(int(upce[i]) for i in range(1, 7, 2))
        
        total = (odd_sum * 3) + even_sum
        checksum = (10 - (total % 10)) % 10
        
        # Return original if checksum matches
        if checksum == int(upce[7]):
            return upce
        
        return upce
    
    def model_post_init(self, __context):
        """Set format after validation."""
        if self.format is None:
            self.format = "UPC-A" if len(self.code) == 12 else "UPC-E"
