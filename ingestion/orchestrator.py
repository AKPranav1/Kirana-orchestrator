from .schema import ParsedOrderPayload, FinalOrderManifest, ProcessedSplit, ProcessedItem, WhatsAppNotification
from .sku_match import SKUMatcher

def fetch_historical_khata_ledger(customer_name: str) -> float:
    # Person 3 will link this to MongoDB
    historical_balances = {"mohan": 450.0, "anil": 120.0, "default": 0.0}
    return historical_balances.get(customer_name.lower().strip(), 0.0)

def orchestrate_order_processing(parsed_data: ParsedOrderPayload, input_meta: dict, matcher: SKUMatcher) -> FinalOrderManifest:
    processed_splits_list = []
    whatsapp_notifications_list = []
    
    for split in parsed_data.raw_splits:
        name = split.buyer_name
        running_split_total = 0.0
        resolved_items = []
        
        for item in split.raw_items:
            # USE YOUR RAPIDFUZZ MATCHER!
            canon_name, canon_unit, score = matcher.match(item.name)
            
            # Since your catalog doesn't have prices yet, we mock a default price for the demo
            # Person 3 can update the catalog or DB later
            mock_price = 45.0 
            subtotal_cost = mock_price * item.qty
            running_split_total += subtotal_cost
            
            resolved_items.append(
                ProcessedItem(
                    item_name=canon_name,
                    quantity=item.qty,
                    unit=item.unit if item.unit else canon_unit,
                    unit_price=mock_price,
                    subtotal=subtotal_cost
                )
            )
            
        previous_debt = 0.0
        updated_debt = 0.0
        if parsed_data.payment_intent == "khata":
            previous_debt = fetch_historical_khata_ledger(name)
            updated_debt = previous_debt + running_split_total
            
        notification_text = f"🛍️ *KIRANA BILL CONFIRMATION* ({name.upper()})\n"
        for ri in resolved_items:
            notification_text += f"• {ri.item_name} x{ri.quantity}: ₹{ri.subtotal:.2f}\n"
        notification_text += f"\n*Current Order Total:* ₹{running_split_total:.2f}\n"
        
        if parsed_data.payment_intent == "khata":
            notification_text += f"💳 Added to Khata. Outstanding Balance: ₹{updated_debt:.2f}\n"

        processed_splits_list.append(
            ProcessedSplit(
                buyer_name=name, items=resolved_items, order_total=running_split_total,
                previous_ledger=previous_debt, updated_ledger=updated_debt
            )
        )
        
        whatsapp_notifications_list.append(WhatsAppNotification(recipient_name=name, message_body=notification_text))
        
    return FinalOrderManifest(
        customer_phone=input_meta.get("customer_phone", "unknown"),
        input_type=input_meta.get("input_type", "text"),
        raw_input_url=input_meta.get("raw_input_url"),
        payment_mode=parsed_data.payment_intent,
        pdf_requested=parsed_data.request_pdf,
        processed_splits=processed_splits_list,
        whatsapp_notifications=whatsapp_notifications_list,
        status="processed"
    )