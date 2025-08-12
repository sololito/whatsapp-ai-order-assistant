import json
import time
from typing import Dict, List, Tuple

class InventoryChecker:
    def __init__(self, inventory_file: str = 'data/inventory.json'):
        self.inventory_file = inventory_file
        self.inventory = self._load_inventory()

    def _load_inventory(self) -> Dict:
        """Load inventory data from JSON file"""
        try:
            with open(self.inventory_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise Exception("Inventory file not found")
        except json.JSONDecodeError:
            raise Exception("Invalid inventory JSON format")

    def _normalize_item_name(self, name: str) -> str:
        """Normalize item name for matching"""
        # Remove common measurement units and extra spaces
        normalized = name.lower().strip()
        for unit in ['kg', 'g', 'l', 'ml', 'of']:
            normalized = normalized.replace(unit, '').strip()
        return normalized

    def _find_matching_item(self, item_name: str):
        """Find the best matching item in inventory"""
        normalized_input = self._normalize_item_name(item_name)
        
        # First try exact match
        for item in self.inventory['items']:
            if self._normalize_item_name(item['name']) == normalized_input:
                return item
        
        # Then try partial match
        for item in self.inventory['items']:
            if normalized_input in self._normalize_item_name(item['name']) or \
               self._normalize_item_name(item['name']) in normalized_input:
                return item
        
        # Then check variations
        for item in self.inventory['items']:
            if 'variations' in item:
                for variation in item['variations']:
                    if normalized_input in self._normalize_item_name(variation) or \
                       self._normalize_item_name(variation) in normalized_input:
                        return item
        
        return None

    def check_availability(self, items: List[Tuple[str, float]]) -> Dict:
        """
        Check item availability in inventory with flexible matching
        
        Args:
            items: List of tuples (item_name, quantity)
            
        Returns:
            Dict with available items, unavailable items, and suggested alternatives
        """
        available = []
        unavailable = []
        alternatives = {}
        
        for item_name, quantity in items:
            item = self._find_matching_item(item_name)
            
            if item:
                if item['quantity'] >= quantity:
                    available.append({
                        'name': item['name'],
                        'quantity': quantity,
                        'price': item['price'],
                        'total': item['price'] * quantity,
                        'unit': item.get('unit', 'unit')
                    })
                else:
                    unavailable.append({
                        'name': item['name'],
                        'requested': quantity,
                        'available': item['quantity'],
                        'unit': item.get('unit', 'unit')
                    })
                
                # Add variations as alternatives
                if 'variations' in item:
                    alternatives[item['name']] = item['variations']
            else:
                # If no match found, check for similar items
                similar_items = []
                normalized_input = self._normalize_item_name(item_name)
                
                for inv_item in self.inventory['items']:
                    if normalized_input in self._normalize_item_name(inv_item['name']):
                        similar_items.append(inv_item['name'])
                
                if similar_items:
                    alternatives[item_name] = similar_items
                
                unavailable.append({
                    'name': item_name,
                    'requested': quantity,
                    'available': 0,
                    'unit': 'unit',
                    'not_found': True
                })
        
        return {
            'available': available,
            'unavailable': unavailable,
            'alternatives': alternatives,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }

    def _find_similar_items(self, item_name: str) -> List[Dict]:
        """Find similar items in inventory using fuzzy matching"""
        from fuzzywuzzy import process
        item_names = [item['name'] for item in self.inventory['items']]
        matches = process.extract(item_name, item_names, limit=3)
        return [{'name': match[0], 'score': match[1]} for match in matches if match[1] > 60]

    def update_inventory(self, items: List[Dict]):
        """Update inventory after successful order"""
        for ordered_item in items:
            for inventory_item in self.inventory['items']:
                if inventory_item['name'] == ordered_item['name']:
                    inventory_item['quantity'] -= ordered_item['quantity']
                    break
        
        with open(self.inventory_file, 'w') as f:
            json.dump(self.inventory, f, indent=2)