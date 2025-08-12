from typing import Dict, Optional
import json

class DeliveryOption:
    def __init__(self):
        self.delivery_fees = self._load_delivery_fees()

    def _load_delivery_fees(self) -> Dict:
        """Load delivery fees from shop info"""
        try:
            with open('data/shop_info.json', 'r') as f:
                shop_info = json.load(f)
                return shop_info.get('delivery_fees', {})
        except FileNotFoundError:
            return {}

    def set_delivery_option(self, option: str, address: Optional[str] = None) -> Dict:
        """
        Set delivery option and calculate fee
        
        Args:
            option: 'pickup' or 'delivery'
            address: Delivery address (required if option is 'delivery')
            
        Returns:
            Dict with option details and fee
        """
        if option.lower() == 'pickup':
            return {
                'option': 'pickup',
                'fee': 0,
                'address': None
            }
        elif option.lower() == 'delivery':
            if not address:
                raise ValueError("Delivery address is required")
            
            fee = self._calculate_delivery_fee(address)
            return {
                'option': 'delivery',
                'fee': fee,
                'address': address
            }
        else:
            raise ValueError("Invalid delivery option. Choose 'pickup' or 'delivery'")

    def _calculate_delivery_fee(self, address: str) -> float:
        """
        Calculate delivery fee based on address
        (Simple implementation - can be enhanced with actual distance calculation)
        """
        # Default fee if no specific zones are defined
        if not self.delivery_fees:
            return 100.0
        
        # Check if address contains any zone keywords
        for zone, fee in self.delivery_fees.items():
            if zone.lower() in address.lower():
                return fee
        
        # Return maximum fee if no zone matches
        return max(self.delivery_fees.values()) if self.delivery_fees else 150.0