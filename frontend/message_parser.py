import re
from typing import List, Tuple

class MessageParser:
    def parse_order_message(self, message: str) -> List[Tuple[str, float]]:
        """
        Parse natural language order message into list of (item, quantity) tuples
        
        Args:
            message: Natural language order (e.g., "2 loaves of bread and 1kg sugar")
            
        Returns:
            List of tuples (item_name, quantity)
        """
        # Normalize the message
        message = message.lower().strip()
        
        # Common patterns
        patterns = [
            r'(\d+\.?\d*)\s*(?:x|×)\s*([^\d]+)',  # "2 x bread"
            r'(\d+\.?\d*)\s*(?:loaves?|slices?)\s*of\s*([^\d]+)',  # "2 loaves of bread"
            r'(\d+\.?\d*)\s*(?:kg|kilos?|kilograms?)\s*of?\s*([^\d]+)',  # "1kg sugar"
            r'(\d+\.?\d*)\s*(?:l|liters?|litres?)\s*of?\s*([^\d]+)',  # "1l milk"
            r'(\d+\.?\d*)\s*([^\d]+)',  # "2 bread"
            r'([^\d]+)\s*(\d+\.?\d*)',  # "bread 2" (less common)
        ]
        
        items = []
        
        # Try to split by common conjunctions first
        parts = re.split(r'\band\b|\bplus\b|\b,\s*', message)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            matched = False
            
            # Try each pattern
            for pattern in patterns:
                match = re.search(pattern, part)
                if match:
                    quantity = float(match.group(1))
                    item = match.group(2).strip()
                    
                    # Clean up item name
                    item = re.sub(r'\bof\b|\bthe\b|\ba\b|\ban\b', '', item).strip()
                    item = re.sub(r'\s+', ' ', item)
                    
                    items.append((item, quantity))
                    matched = True
                    break
            
            # If no pattern matched, try to extract just quantity and item
            if not matched:
                # Look for quantity at start
                match = re.match(r'(\d+\.?\d*)\s*(.+)', part)
                if match:
                    quantity = float(match.group(1))
                    item = match.group(2).strip()
                    items.append((item, quantity))
                else:
                    # Assume quantity of 1
                    items.append((part, 1.0))
        
        return items