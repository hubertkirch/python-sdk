"""
Unit tests for format_number function to verify scientific notation handling.

The extended exchange does not accept scientific notation (e.g., "4e-05") in
numeric fields. These tests verify that format_number properly converts such
values to decimal notation (e.g., "0.00004").
"""

from decimal import Decimal
from pacifica.api.exchange import format_number


class TestFormatNumberScientificNotation:
    """
    Tests for the primary issue: preventing scientific notation in numeric values
    sent to the exchange API.
    """

    def test_small_float_without_scientific_notation(self):
        """
        Small floats that Python's str() converts to scientific notation
        should be formatted as decimal strings.

        Python: str(0.00004) -> '4e-05'
        Expected: '0.00004'
        """
        # Very small positive floats
        assert format_number(0.00004) == "0.00004"
        assert format_number(0.000004) == "0.000004"
        assert format_number(0.0000004) == "0.0000004"
        assert format_number(0.00000001) == "0.00000001"

        # Very small negative floats
        assert format_number(-0.00004) == "-0.00004"
        assert format_number(-0.000004) == "-0.000004"

    def test_scientific_notation_string_input(self):
        """
        Strings containing scientific notation should be converted to decimal.
        """
        # Lowercase 'e'
        assert format_number("4e-05") == "0.00004"
        assert format_number("1e-06") == "0.000001"
        assert format_number("-5e-04") == "-0.0005"

        # Uppercase 'E'
        assert format_number("4E-05") == "0.00004"
        assert format_number("1E-06") == "0.000001"

        # Positive exponents
        assert format_number("1e5") == "100000"
        assert format_number("1.5e3") == "1500"

    def test_regular_floats(self):
        """
        Regular floats that don't trigger scientific notation should pass through.
        """
        assert format_number(0.1) == "0.1"
        assert format_number(0.5) == "0.5"
        assert format_number(1.0) == "1"
        assert format_number(100.5) == "100.5"
        assert format_number(9999.99) == "9999.99"
        assert format_number(-50.25) == "-50.25"

    def test_integer_inputs(self):
        """
        Integer inputs should be converted to string directly.
        """
        assert format_number(0) == "0"
        assert format_number(1) == "1"
        assert format_number(100) == "100"
        assert format_number(1000000) == "1000000"
        assert format_number(-50) == "-50"

    def test_string_inputs_without_scientific_notation(self):
        """
        String inputs without 'e' should pass through unchanged.
        """
        assert format_number("100") == "100"
        assert format_number("0.1") == "0.1"
        assert format_number("123.456") == "123.456"
        assert format_number("-99.99") == "-99.99"

    def test_decimal_input(self):
        """
        Decimal objects should be formatted correctly.
        """
        assert format_number(Decimal("0.00004")) == "0.00004"
        assert format_number(Decimal("123.45")) == "123.45"
        assert format_number(Decimal("100")) == "100"

    def test_trailing_zeros_removed(self):
        """
        Trailing zeros should be removed for cleaner output.
        """
        assert format_number(1.0) == "1"
        assert format_number(1.100) == "1.1"
        assert format_number(123.4500) == "123.45"
        assert format_number(0.500) == "0.5"

    def test_real_world_trading_values(self):
        """
        Test actual values that might occur in trading scenarios.
        """
        # Small BTC amounts (satoshi-level)
        assert format_number(0.00001) == "0.00001"
        assert format_number(0.000001) == "0.000001"

        # Small altcoin amounts
        assert format_number(0.00004) == "0.00004"  # SHIB-like values

        # Price values that could have many decimals
        assert format_number(0.00001) == "0.00001"
        assert format_number(0.0001) == "0.0001"

        # Slippage percentages
        assert format_number(0.05) == "0.05"
        assert format_number(0.005) == "0.005"

    def test_no_exponential_in_output(self):
        """
        Regression test: verify no 'e' or 'E' ever appears in output.
        """
        test_values = [
            0.00004, 0.000004, 0.0000004, 0.00000001,
            1e-5, 1e-6, 1e-7, 1e-8,
            -0.00004, -1e-5,
            1000000, 1e6
        ]

        for value in test_values:
            result = format_number(value)
            assert 'e' not in result.lower(), f"Scientific notation found in output: {result} from input {value}"


class TestFormatNumberEdgeCases:
    """Edge case tests for format_number function."""

    def test_zero(self):
        """Zero should be formatted as '0'."""
        assert format_number(0) == "0"
        assert format_number(0.0) == "0"

    def test_very_large_numbers(self):
        """Very large numbers should not use scientific notation."""
        assert format_number(1000000) == "1000000"
        assert format_number(1000000000) == "1000000000"
        assert format_number(1e10) == "10000000000"

    def test_negative_values(self):
        """Negative values should preserve the sign."""
        assert format_number(-0.1) == "-0.1"
        assert format_number(-100) == "-100"
        assert format_number(-0.00004) == "-0.00004"

    def test_preserves_decimal_precision(self):
        """
        Decimal places should be preserved (except trailing zeros).
        """
        assert format_number(0.123456789) == "0.123456789"
        assert format_number(1.23456789) == "1.23456789"


class TestFormatNumberComparisonWithStr:
    """
    Comparison tests showing how format_number differs from Python's str().
    These tests demonstrate the problem that format_number solves.
    """

    def test_python_str_uses_scientific_notation(self):
        """
        Demonstrate that Python's str() uses scientific notation
        for small floats, which the exchange doesn't accept.
        """
        # These would fail with str()
        problematic_values = [0.00004, 0.000004, 0.0000004]

        for value in problematic_values:
            python_result = str(value)
            format_result = format_number(value)

            # Python's str() uses scientific notation
            assert 'e' in python_result.lower(), f"str({value}) should use scientific notation"

            # format_number does NOT use scientific notation
            assert 'e' not in format_result.lower(), f"format_number({value}) should NOT use scientific notation"

    def test_format_number_produces_exchange_compatible_output(self):
        """
        Verify that format_number produces output that the exchange accepts.
        The exchange requires plain decimal notation, not scientific.
        """
        # Values that Python's str() converts to scientific notation
        values = [0.00004, 0.000004, 0.00000001, -0.00004]

        for value in values:
            result = format_number(value)

            # No 'e' or 'E' in the output
            assert 'e' not in result, f"Output contains 'e': {result}"

            # Only contains digits, decimal point, and optional minus sign
            assert result.replace('-', '').replace('.', '').isdigit(), \
                f"Output contains invalid characters: {result}"

            # Can be parsed back to a number
            Decimal(result)  # Should not raise
