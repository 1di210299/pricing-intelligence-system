"""Tests for UPC validation."""
import pytest
from app.services.upc_validator import UPCValidator, UPCValidationError
from app.models.upc import UPC


class TestUPCValidator:
    """Test cases for UPC validation."""
    
    def test_valid_upc_a(self):
        """Test valid UPC-A (12 digits)."""
        # Valid UPC-A with correct checksum
        upc = UPCValidator.validate("012345678905")
        assert upc.code == "012345678905"
        assert upc.format == "UPC-A"
    
    def test_valid_upc_e(self):
        """Test valid UPC-E (8 digits)."""
        # Valid UPC-E
        upc = UPCValidator.validate("01234565")
        assert upc.code == "01234565"
        assert upc.format == "UPC-E"
    
    def test_invalid_length(self):
        """Test UPC with invalid length."""
        with pytest.raises(UPCValidationError):
            UPCValidator.validate("12345")
    
    def test_invalid_characters(self):
        """Test UPC with non-numeric characters."""
        with pytest.raises(UPCValidationError):
            UPCValidator.validate("12345ABC8905")
    
    def test_invalid_checksum(self):
        """Test UPC with invalid checksum."""
        with pytest.raises(UPCValidationError):
            # Last digit should be 5, not 6
            UPCValidator.validate("012345678906")
    
    def test_upc_with_spaces(self):
        """Test UPC with spaces (should be cleaned)."""
        upc = UPCValidator.validate("0 12345 67890 5")
        assert upc.code == "012345678905"
    
    def test_upc_with_hyphens(self):
        """Test UPC with hyphens (should be cleaned)."""
        upc = UPCValidator.validate("012-345-678-905")
        assert upc.code == "012345678905"
    
    def test_is_valid_true(self):
        """Test is_valid method returns True for valid UPC."""
        assert UPCValidator.is_valid("012345678905") is True
    
    def test_is_valid_false(self):
        """Test is_valid method returns False for invalid UPC."""
        assert UPCValidator.is_valid("012345678906") is False
        assert UPCValidator.is_valid("abc") is False
