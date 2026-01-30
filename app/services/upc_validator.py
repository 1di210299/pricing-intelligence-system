"""UPC validation service."""
from app.models.upc import UPC, UPCValidationError


class UPCValidator:
    """Service for validating UPC codes."""
    
    @staticmethod
    def validate(upc_code: str) -> UPC:
        """
        Validate a UPC code.
        
        Args:
            upc_code: UPC string to validate
            
        Returns:
            UPC: Validated UPC object
            
        Raises:
            UPCValidationError: If validation fails
        """
        try:
            upc = UPC(code=upc_code)
            return upc
        except ValueError as e:
            raise UPCValidationError(f"Invalid UPC: {str(e)}") from e
    
    @staticmethod
    def is_valid(upc_code: str) -> bool:
        """
        Check if a UPC code is valid without raising exceptions.
        
        Args:
            upc_code: UPC string to check
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            UPCValidator.validate(upc_code)
            return True
        except UPCValidationError:
            return False
